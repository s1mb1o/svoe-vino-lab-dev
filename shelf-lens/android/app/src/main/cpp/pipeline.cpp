#include "pipeline.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

#include <android/log.h>
#include <pthread.h>
#include <sys/resource.h>

#include "shelfreid/cv.hpp"   // OpenCV 4 or 5: flow, features, estimateAffinePartial2D

namespace shelfreid {

namespace {

using Clock = std::chrono::steady_clock;

// A name for the profilers, and a nice value (negative: before the default threads).
void label_thread(const char* name, int nice) {
    pthread_setname_np(pthread_self(), name);
    setpriority(PRIO_PROCESS, 0, nice);
}

double ms(Clock::time_point a, Clock::time_point b) { return std::chrono::duration<double, std::milli>(b - a).count(); }

// A percentile of the last `window` values.
double recent(const std::vector<double>& values, double q, size_t window = 100) {
    if (values.empty()) return 0.0;
    std::vector<double> v(values.end() - static_cast<long>(std::min(window, values.size())), values.end());
    std::sort(v.begin(), v.end());
    return v[static_cast<size_t>(std::lround(q / 100.0 * (v.size() - 1)))];
}

void keep_last(std::vector<double>& v, size_t n = 300) {
    if (v.size() > 2 * n) v.erase(v.begin(), v.end() - static_cast<long>(n));
}

}  // namespace

Pipeline::Pipeline(const std::string& model_path, int cv_threads, bool cheap_slow)
    : detector_(std::make_unique<BottleDetector>(model_path)), cv_threads_(cv_threads) {
    if (cv_threads > 0) cv::setNumThreads(cv_threads);
    if (cheap_slow) {
        cfg_.features.max_side = 960;
        cfg_.features.max_features = 2500;
    }
    // The first run on the accelerator is slow (it finishes compiling): spend it here.
    cv::Mat grey(1920, 1080, CV_8UC3, cv::Scalar(114, 114, 114));
    (*detector_)(grey);
}

Pipeline::~Pipeline() { end(); }

void Pipeline::begin(int width, int height) {
    end();
    std::lock_guard<std::mutex> lock(mutex_);
    tracker_ = std::make_unique<RealtimeTracker>(Size2{double(width), double(height)}, cfg_, -1);
    to_detect_.reset();
    to_track_.reset();
    frame_motion_.reset();
    {
        std::lock_guard<std::mutex> chain_lock(chain_mutex_);
        chain_.reset();
    }
    last_tracked_ = -1;
    {
        std::lock_guard<std::mutex> r(result_mutex_);
        result_ = Result{};
        detect_ms_.clear(), latency_ms_.clear(), fast_ms_.clear(), slow_ms_.clear(), landed_.clear();
        done_.clear();
        submitted_ = dropped_ = 0;
        bottles_ = keyframes_ = 0;
        ids_ = 0;
    }
    stop_ = false;
    detect_thread_ = std::thread([this] { detect_loop(); });
    track_thread_ = std::thread([this] { track_loop(); });
}

void Pipeline::end() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (stop_) return;
        stop_ = true;
    }
    wake_.notify_all();
    if (detect_thread_.joinable()) detect_thread_.join();
    if (track_thread_.joinable()) track_thread_.join();
}

bool Pipeline::motion(int frame, const cv::Mat& luma, int rotation, cv::Matx23d& transform) {
    const bool found = frame_motion_.step(luma, rotation, transform);
    std::lock_guard<std::mutex> lock(chain_mutex_);
    chain_.add(frame, transform, found);
    return found;
}

void Pipeline::submit(int frame, cv::Mat bgr) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (stop_) return;
        if (to_detect_) ++dropped_;
        to_detect_ = Job{frame, std::move(bgr), {}, Clock::now()};
        ++submitted_;
    }
    wake_.notify_all();
}

void Pipeline::detect_loop() {
    label_thread("detector", -4);
    while (true) {
        Job job;
        {
            std::unique_lock<std::mutex> lock(mutex_);
            wake_.wait(lock, [this] { return stop_ || to_detect_.has_value(); });
            if (stop_) return;
            job = std::move(*to_detect_);
            to_detect_.reset();
        }
        const auto raw = (*detector_)(job.bgr);
        job.detections = clean_bottles(raw, cfg_.min_score);
        static int logged = 0;
        if (logged < 3) {
            ++logged;
            __android_log_print(ANDROID_LOG_INFO, "shelfreid", "detector on frame %d (%dx%d): %zu raw, %zu kept", job.frame,
                                job.bgr.cols, job.bgr.rows, raw.size(), job.detections.size());
        }
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (to_track_) ++dropped_;
            to_track_ = std::move(job);
        }
        {
            std::lock_guard<std::mutex> r(result_mutex_);
            detect_ms_.push_back(detector_->last_ms);
            keep_last(detect_ms_);
        }
        wake_.notify_all();
    }
}

void Pipeline::track_loop() {
    label_thread("tracker", -4);
    while (true) {
        Job job;
        {
            std::unique_lock<std::mutex> lock(mutex_);
            wake_.wait(lock, [this] { return stop_ || to_track_.has_value(); });
            if (stop_) return;
            job = std::move(*to_track_);
            to_track_.reset();
        }
        if (last_tracked_ >= 0) {
            std::lock_guard<std::mutex> chain_lock(chain_mutex_);
            tracker_->motion_hint = chain_.back(last_tracked_, job.frame);
        }
        last_tracked_ = job.frame;
        auto shown = tracker_->step(job.frame, job.bgr, std::move(job.detections));
        const auto now = Clock::now();
        const RealtimeTracker& t = *tracker_;
        std::lock_guard<std::mutex> r(result_mutex_);
        result_.frame = job.frame;
        result_.shown = std::move(shown);
        latency_ms_.push_back(ms(job.arrived, now));
        if (!t.fast_seconds.empty()) fast_ms_.push_back(t.fast_seconds.back() * 1000);
        slow_ms_.assign(t.slow_seconds.end() - static_cast<long>(std::min<size_t>(30, t.slow_seconds.size())), t.slow_seconds.end());
        landed_.assign(t.landed_after.end() - static_cast<long>(std::min<size_t>(30, t.landed_after.size())), t.landed_after.end());
        keep_last(latency_ms_), keep_last(fast_ms_);
        done_.push_back(now);
        while (!done_.empty() && ms(done_.front(), now) > 3000) done_.pop_front();
        bottles_ = t.bottles.size();
        keyframes_ = t.keyframes.size();
        ids_ = t.next_id;
    }
}

Pipeline::Result Pipeline::latest() const {
    std::lock_guard<std::mutex> r(result_mutex_);
    return result_;
}

std::string Pipeline::stats() const {
    std::lock_guard<std::mutex> r(result_mutex_);
    std::vector<double> slow(slow_ms_);
    for (auto& v : slow) v *= 1000;
    char out[512];
    std::snprintf(out, sizeof(out),
                  "bottles %zu  ids %d  keyframes %zu\n"
                  "processed %.1f/s  latency %.0f ms  dropped %d of %d\n"
                  "detector %s %.0f ms (p95 %.0f)\n"
                  "fast %.0f ms (p95 %.0f)  slow %.0f ms  lands after %.0f\n"
                  "opencv threads %d  slow-loop sift %d px / %d",
                  bottles_, ids_, keyframes_, done_.size() / 3.0, recent(latency_ms_, 50), dropped_, submitted_,
                  detector_->provider.c_str(), recent(detect_ms_, 50), recent(detect_ms_, 95), recent(fast_ms_, 50),
                  recent(fast_ms_, 95), recent(slow, 50), recent(landed_, 50), cv::getNumThreads(),
                  cfg_.features.max_side, cfg_.features.max_features);
    return out;
}

}  // namespace shelfreid
