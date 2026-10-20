#include "pipeline.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

#include <android/log.h>
#include <pthread.h>
#include <sys/resource.h>

#include <opencv2/imgcodecs.hpp>

#include "shelfreid/cv.hpp"   // OpenCV 4 or 5: flow, features, estimateAffinePartial2D
#include "shelfreid/planogram.hpp"

namespace shelfreid {

namespace {

using Clock = std::chrono::steady_clock;

// A name for the profilers, and a nice value (negative: before the default threads).
void label_thread(const char* name, int nice) {
    pthread_setname_np(pthread_self(), name);
    setpriority(PRIO_PROCESS, 0, nice);
}

double ms(Clock::time_point a, Clock::time_point b) { return std::chrono::duration<double, std::milli>(b - a).count(); }

// The sharpness of a crop: the variance of the Laplacian of its grey copy at a height of
// 300 px, so crops of different sizes compare.
double sharpness(const cv::Mat& crop) {
    cv::Mat grey, small, lap;
    cv::cvtColor(crop, grey, cv::COLOR_BGR2GRAY);
    const double k = 300.0 / grey.rows;
    cv::resize(grey, small, cv::Size(std::max(8, static_cast<int>(std::lround(grey.cols * k))), 300), 0, 0,
               k < 1 ? cv::INTER_AREA : cv::INTER_LINEAR);
    cv::Laplacian(small, lap, CV_64F);
    cv::Scalar mean, dev;
    cv::meanStdDev(lap, mean, dev);
    return dev[0] * dev[0];
}

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
    {
        std::lock_guard<std::mutex> t(tracker_mutex_);
        tracker_ = std::make_unique<RealtimeTracker>(Size2{double(width), double(height)}, cfg_, -1);
    }
    to_detect_.reset();
    to_track_.reset();
    frame_motion_.reset();
    {
        std::lock_guard<std::mutex> chain_lock(chain_mutex_);
        chain_.reset();
    }
    last_tracked_ = -1;
    {
        std::lock_guard<std::mutex> r(recognition_mutex_);
        recognitions_.clear();
        outbox_.clear();
        out_ = track_steps_ = sent_ = answered_ = failed_ = accepted_ = 0;
        shown_frame_ = -1;
    }
    {
        std::lock_guard<std::mutex> r(result_mutex_);
        result_ = Result{};
        detect_ms_.clear(), latency_ms_.clear(), fast_ms_.clear(), slow_ms_.clear(), landed_.clear();
        done_.clear();
        submitted_ = dropped_ = 0;
        bottles_ = keyframes_ = provisional_ = 0;
        lost_ = false;
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
        std::vector<Shown> shown;
        {
            std::lock_guard<std::mutex> t(tracker_mutex_);
            if (last_tracked_ >= 0) {
                std::lock_guard<std::mutex> chain_lock(chain_mutex_);
                tracker_->motion_hint = chain_.back(last_tracked_, job.frame);
            }
            last_tracked_ = job.frame;
            shown = tracker_->step(job.frame, job.bgr, std::move(job.detections));
        }
        std::set<int> kept;   // the bottles the map keeps for good (this thread alone changes the tracker)
        for (const auto& b : tracker_->bottles)
            if (!tracker_->provisional.count(b.id)) kept.insert(b.id);
        plan_recognition(job.frame, job.bgr, shown, kept);
        std::vector<int> recognized;
        int queue[5];   // for the log: queued, out, sent, answered, failed
        {
            std::lock_guard<std::mutex> rl(recognition_mutex_);
            shown_frame_ = job.frame;
            queue[0] = queued(), queue[1] = out_, queue[2] = sent_, queue[3] = answered_, queue[4] = failed_;
            for (const auto& item : shown) {
                const auto it = item.bottle == kNone ? recognitions_.end() : recognitions_.find(item.bottle);
                recognized.push_back(it == recognitions_.end() ? 0 : it->second.colour());
            }
        }
        const auto now = Clock::now();
        const RealtimeTracker& t = *tracker_;
        std::lock_guard<std::mutex> r(result_mutex_);
        result_.frame = job.frame;
        result_.shown = std::move(shown);
        result_.recognized = std::move(recognized);
        latency_ms_.push_back(ms(job.arrived, now));
        if (!t.fast_seconds.empty()) fast_ms_.push_back(t.fast_seconds.back() * 1000);
        slow_ms_.assign(t.slow_seconds.end() - static_cast<long>(std::min<size_t>(30, t.slow_seconds.size())), t.slow_seconds.end());
        landed_.assign(t.landed_after.end() - static_cast<long>(std::min<size_t>(30, t.landed_after.size())), t.landed_after.end());
        keep_last(latency_ms_), keep_last(fast_ms_);
        done_.push_back(now);
        while (!done_.empty() && ms(done_.front(), now) > 3000) done_.pop_front();
        bottles_ = t.bottles.size();
        provisional_ = t.provisional.size();
        // The boxes add nothing to the map now: the tracker lost its place, or it waits to
        // register to the map and a box in view waits for it (bottles it follows keep their boxes).
        bool waiting_box = false;
        for (const auto& s : result_.shown) waiting_box |= s.bottle == kNone && s.status == "pending";
        lost_ = t.lost || (!t.trusted && waiting_box);
        // The tracker's state in the log once a second.
        static Clock::time_point logged{};
        if (ms(logged, now) > 1000) {
            logged = now;
            __android_log_print(ANDROID_LOG_INFO, "shelfreid",
                                "state frame %d step %d lost %d trusted %d untrusted %d registered %d steps ago, keyframes %zu, "
                                "slow jobs %zu, found %d, jumps %d, lost motion %d, hinted %d, aliased %d, bottles %zu (%zu provisional), "
                                "boxes %zu; recognition: queued %d, out %d, sent %d, answered %d, failed %d%s%s",
                                job.frame, t.count, t.lost ? 1 : 0, t.trusted ? 1 : 0, t.untrusted, t.count - t.localized,
                                t.keyframes.size(), t.slow_seconds.size(), t.found, t.jumps, t.lost_motion, t.hinted, t.aliased,
                                t.bottles.size(), t.provisional.size(), result_.shown.size(), queue[0], queue[1], queue[2], queue[3],
                                queue[4],
                                t.flow_failure.empty() ? "" : ", flow: ", t.flow_failure.c_str());
        }
        keyframes_ = t.keyframes.size();
        ids_ = t.next_id;
    }
}

Pipeline::Result Pipeline::latest() const {
    Result result;
    {
        std::lock_guard<std::mutex> r(result_mutex_);
        result = result_;
    }
    // Whether each wine is known, as of now: an answer may come after the last step (the end
    // of a video), and the box turns green all the same.
    std::lock_guard<std::mutex> rl(recognition_mutex_);
    result.recognized.assign(result.shown.size(), 0);
    for (size_t i = 0; i < result.shown.size(); ++i) {
        const auto it = result.shown[i].bottle == kNone ? recognitions_.end() : recognitions_.find(result.shown[i].bottle);
        result.recognized[i] = it == recognitions_.end() ? 0 : it->second.colour();
    }
    return result;
}

std::array<int, 4> Pipeline::summary() const {
    std::array<int, 4> out{};
    {
        std::lock_guard<std::mutex> r(result_mutex_);
        out[0] = static_cast<int>(bottles_ - std::min(provisional_, bottles_));
        out[3] = lost_ ? 1 : 0;
    }
    std::lock_guard<std::mutex> rl(recognition_mutex_);
    for (const auto& [id, rec] : recognitions_) {
        const int colour = rec.colour();
        out[1] += colour == 1;
        out[2] += colour == 2;
    }
    out[1] = std::min(out[1], out[0]);
    return out;
}

void Pipeline::interrupt() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        to_detect_.reset();
        to_track_.reset();
    }
    frame_motion_.reset();
    {
        std::lock_guard<std::mutex> chain_lock(chain_mutex_);
        chain_.reset();
    }
    {
        std::lock_guard<std::mutex> t(tracker_mutex_);
        last_tracked_ = -1;   // no motion hint across the break
        if (tracker_) tracker_->interrupt();
    }
    std::lock_guard<std::mutex> r(result_mutex_);
    result_.frame = -1;   // the old boxes belong to the old picture
    result_.shown.clear();
    result_.recognized.clear();
}

std::string Pipeline::stats() const {
    std::lock_guard<std::mutex> rl(recognition_mutex_);
    std::lock_guard<std::mutex> r(result_mutex_);
    std::vector<double> slow(slow_ms_);
    for (auto& v : slow) v *= 1000;
    char out[640];
    std::snprintf(out, sizeof(out),
                  "bottles %zu  ids %d  keyframes %zu\n"
                  "processed %.1f/s  latency %.0f ms  dropped %d of %d\n"
                  "detector %s %.0f ms (p95 %.0f)\n"
                  "fast %.0f ms (p95 %.0f)  slow %.0f ms  lands after %.0f\n"
                  "opencv threads %d  slow-loop sift %d px / %d\n"
                  "wines: %d recognised, %d requests, %d answers, %d failed, %d out",
                  bottles_, ids_, keyframes_, done_.size() / 3.0, recent(latency_ms_, 50), dropped_, submitted_,
                  detector_->provider.c_str(), recent(detect_ms_, 50), recent(detect_ms_, 95), recent(fast_ms_, 50),
                  recent(fast_ms_, 95), recent(slow, 50), recent(landed_, 50), cv::getNumThreads(),
                  cfg_.features.max_side, cfg_.features.max_features, accepted_, sent_, answered_, failed_, out_);
    return out;
}

void Pipeline::set_recognition(bool on) {
    std::lock_guard<std::mutex> r(recognition_mutex_);
    recognition_on_ = on;
}

void Pipeline::plan_recognition(int frame, const cv::Mat& bgr, const std::vector<Shown>& shown, const std::set<int>& kept) {
    std::lock_guard<std::mutex> r(recognition_mutex_);
    ++track_steps_;
    // Confirmed: the map keeps the bottle, in view or not (one confirmed after it left the view
    // goes too; a duplicate the tracker merged away never does).
    for (auto& [id, rec] : recognitions_) rec.confirmed = kept.count(id) > 0;
    const double W = bgr.cols, H = bgr.rows;
    auto crop_of = [&](const Box& b) {
        const double mx = 0.06 * (b[2] - b[0]), my = 0.06 * (b[3] - b[1]);
        const int x1 = std::max(0, static_cast<int>(b[0] - mx)), y1 = std::max(0, static_cast<int>(b[1] - my));
        const int x2 = std::min(bgr.cols, static_cast<int>(b[2] + mx)), y2 = std::min(bgr.rows, static_cast<int>(b[3] + my));
        return x2 > x1 && y2 > y1 ? bgr(cv::Rect(x1, y1, x2 - x1, y2 - y1)) : cv::Mat();
    };
    for (const auto& item : shown) {
        if (item.bottle == kNone) continue;
        const Box& b = item.box;
        Recognition& rec = recognitions_[item.bottle];
        const int h = static_cast<int>(std::lround(b[3] - b[1]));
        rec.height = h;
        rec.share = h / H;
        rec.frame = frame;
        if (track_steps_ - rec.thumb_step >= 10) {   // a small copy of the latest crop, for the table
            const cv::Mat crop = crop_of(b);
            if (!crop.empty()) {
                cv::Mat small;
                const double k = std::min(1.0, 320.0 / crop.rows);
                cv::resize(crop, small, cv::Size(), k, k, cv::INTER_AREA);
                cv::imencode(".jpg", small, rec.thumb, {cv::IMWRITE_JPEG_QUALITY, 85});
                rec.thumb_step = track_steps_;
            }
        }
        const bool cut = b[0] < 0.01 * W || b[2] > 0.99 * W || b[1] < 0.01 * H || b[3] > 0.99 * H;
        const bool asking_done = rec.answers >= kMaxAttempts || rec.attempts >= kMaxAttempts;
        const bool fit = !rec.sure && !asking_done && h >= kGate * H && !cut;
        // The crop goes to the bottle's reserve (a raw copy: the PNG is made when it is sent),
        // every other step only: the reserve then spans more time, its crops differ more.
        if (recognition_on_ && fit && track_steps_ % 2 == 0) {
            if (rec.first_fit == Clock::time_point{}) rec.first_fit = Clock::now();
            rec.max_height = std::max(rec.max_height, h);
            const cv::Mat crop = crop_of(b);
            if (!crop.empty()) {
                Recognition::Candidate c{cv::Mat(), h, frame, sharpness(crop)};
                if (static_cast<int>(rec.kept.size()) < kKeptPerBottle) {
                    c.crop = crop.clone();
                    rec.kept.push_back(std::move(c));
                } else {
                    auto worst = std::min_element(rec.kept.begin(), rec.kept.end(), [&](const auto& x, const auto& y) {
                        return rec.quality(x) < rec.quality(y);
                    });
                    if (rec.quality(c) > rec.quality(*worst)) c.crop = crop.clone(), *worst = std::move(c);
                }
            }
        }
        if (rec.sure) rec.state = "known";
        else if (rec.inflight > 0) rec.state = "asking";
        else if (asking_done) rec.state = "done asking";
        else if (!rec.kept.empty()) rec.state = rec.confirmed ? "waiting" : "unconfirmed";   // a crop kept
        else if (!rec.confirmed) rec.state = "unconfirmed";
        else if (h < kGate * H) rec.state = "small";
        else if (cut) rec.state = "cut";
        else rec.state = recognition_on_ ? "waiting" : "eligible";
    }
    // At most kKeptCrops crops in memory: the worst of the bottles with more than one go first.
    while (true) {
        int total = 0;
        for (const auto& [id, rec] : recognitions_) total += static_cast<int>(rec.kept.size());
        if (total <= kKeptCrops) break;
        Recognition* from = nullptr;
        size_t worst = 0;
        double low = 1e300;
        for (bool spare : {true, false}) {
            for (auto& [id, rec] : recognitions_)
                for (size_t i = 0; i < rec.kept.size(); ++i)
                    if ((!spare || rec.kept.size() > 1) && rec.quality(rec.kept[i]) < low)
                        low = rec.quality(rec.kept[i]), from = &rec, worst = i;
            if (from) break;
        }
        if (!from) break;
        from->kept.erase(from->kept.begin() + static_cast<long>(worst));
    }
}

std::vector<unsigned char> Pipeline::dispatch() {
    if (!recognition_on_ || out_ >= kMaxInflight) return {};
    const auto now = Clock::now();
    auto best_of = [](const Recognition& rec) {
        return std::max_element(rec.kept.begin(), rec.kept.end(),
                                [&](const auto& x, const auto& y) { return rec.quality(x) < rec.quality(y); });
    };
    Recognition* pick = nullptr;
    int pick_id = kNone;
    for (auto& [id, rec] : recognitions_) {
        if (rec.kept.empty() || !rec.confirmed || rec.inflight > 0 || rec.sure || rec.answers >= kMaxAttempts ||
            rec.attempts >= kMaxAttempts)
            continue;
        if (rec.attempts > 0 && ms(rec.last_sent, now) < kSpacingMs) continue;
        // The bottle fit long enough for its reserve to hold crops of different moments.
        if (ms(rec.first_fit, now) < kMatureMs) continue;
        // A bottle in view first (the shelf the user looks at now), then the fewest attempts,
        // then the largest crop.
        const bool in_view = rec.frame >= shown_frame_;
        if (pick) {
            const bool pick_in_view = pick->frame >= shown_frame_;
            if (in_view != pick_in_view) {
                if (!in_view) continue;
            } else if (rec.attempts > pick->attempts ||
                       (rec.attempts == pick->attempts && best_of(rec)->height <= best_of(*pick)->height)) {
                continue;
            }
        }
        pick = &rec, pick_id = id;
    }
    if (!pick) return {};
    auto chosen = best_of(*pick);
    std::vector<unsigned char> png;
    const int choices = static_cast<int>(pick->kept.size());
    if (!cv::imencode(".png", chosen->crop, png)) {   // lossless
        pick->kept.erase(chosen);
        return {};
    }
    const int32_t header[5] = {pick_id, chosen->frame, chosen->height,
                               static_cast<int32_t>(std::lround(chosen->sharpness * 10)), choices};
    std::vector<unsigned char> packed(sizeof(header) + png.size());
    std::memcpy(packed.data(), header, sizeof(header));
    std::memcpy(packed.data() + sizeof(header), png.data(), png.size());
    pick->sent = std::move(*chosen);
    pick->kept.clear();   // the reserve is spent: the next request takes crops of later frames
    pick->kept.shrink_to_fit();
    ++pick->attempts, ++pick->inflight;
    pick->last_sent = now;
    pick->state = "asking";
    ++out_, ++sent_;
    return packed;
}

int Pipeline::queued() const {
    int n = 0;
    for (const auto& [id, rec] : recognitions_)
        n += !rec.kept.empty() && rec.inflight == 0 && !rec.sure && rec.attempts < kMaxAttempts;
    return n;
}

std::vector<unsigned char> Pipeline::take_crop() {
    std::lock_guard<std::mutex> r(recognition_mutex_);
    if (outbox_.empty()) return dispatch();
    auto crop = std::move(outbox_.front());
    outbox_.pop_front();
    return crop;
}

std::string Pipeline::answer(int bottle, int, int height, const std::string& slug, const std::string& name, bool ok) {
    std::lock_guard<std::mutex> r(recognition_mutex_);
    out_ = std::max(0, out_ - 1);
    auto it = recognitions_.find(bottle);
    if (it == recognitions_.end()) return {};
    Recognition& rec = it->second;
    rec.inflight = std::max(0, rec.inflight - 1);
    if (!ok || slug.empty()) {
        ++failed_;
        if (!ok) {   // no answer: the crop goes back to the reserve, and the attempt does not count
            rec.attempts = std::max(0, rec.attempts - 1);
            if (rec.kept.empty() && !rec.sent.crop.empty()) rec.kept.push_back(std::move(rec.sent));
        }
        rec.sent = {};
        return {};
    }
    rec.sent = {};
    ++answered_, ++rec.answers;
    ++rec.votes[slug];
    rec.names[slug] = name;
    if (height > rec.best_height) rec.best_height = height, rec.best_slug = slug;
    // The decision: the wine named first most often; a tie goes to the largest crop's.
    std::string pick;
    int most = 0;
    for (const auto& [s, n] : rec.votes)
        if (n > most || (n == most && s == rec.best_slug)) pick = s, most = n;
    const bool sure = most >= kAgree;
    const bool changed = !rec.done || rec.slug != pick || rec.sure != sure;
    if (!rec.done) ++accepted_;
    rec.done = true, rec.sure = sure, rec.slug = pick, rec.name = rec.names[pick];
    return changed ? pick + "\t" + rec.name + "\t" + (sure ? "sure" : "unsure") : std::string();
}

namespace {

std::string json_text(const std::string& s) {
    std::string out = "\"";
    for (char c : s) {
        if (c == '"' || c == '\\') out += '\\', out += c;
        else if (static_cast<unsigned char>(c) < 0x20) out += ' ';
        else out += c;
    }
    return out + "\"";
}

}  // namespace

std::string Pipeline::recognition_table() const {
    std::lock_guard<std::mutex> r(recognition_mutex_);
    std::string out = "[";
    char line[256];
    for (const auto& [id, rec] : recognitions_) {
        if (out.size() > 1) out += ",";
        // The state as of now (answers may come after the last step); the gate's reason from the
        // last step where it was seen otherwise.
        std::string state = rec.state;
        if (rec.sure) state = "known";
        else if (rec.inflight > 0) state = "asking";
        else if (rec.answers >= kMaxAttempts || rec.attempts >= kMaxAttempts) state = "done asking";
        else if (!rec.kept.empty()) state = "waiting";
        else if (rec.done) state = "answered";
        std::snprintf(line, sizeof(line),
                      "{\"id\":%d,\"state\":\"%s\",\"height\":%d,\"share\":%.3f,\"frame\":%d,\"requests\":%d,"
                      "\"answers\":%d,\"sure\":%s,\"kept\":%d,",
                      id, state.c_str(), rec.height, rec.share, rec.frame, rec.attempts, rec.answers,
                      rec.sure ? "true" : "false", static_cast<int>(rec.kept.size()));
        out += line;
        out += "\"wine\":" + json_text(rec.done ? rec.name : "") + "}";
    }
    return out + "]";
}

std::string Pipeline::planogram() const {
    Planogram plan;
    {
        std::lock_guard<std::mutex> t(tracker_mutex_);
        if (!tracker_) return "{\"shelves\":[],\"duplicates\":[]}";
        plan = shelfreid::planogram(*tracker_, tracker_->provisional);
    }
    std::lock_guard<std::mutex> r(recognition_mutex_);
    std::string out = "{\"shelves\":[";
    char number[160];
    for (size_t s = 0; s < plan.shelves.size(); ++s) {
        const Shelf& shelf = plan.shelves[s];
        std::snprintf(number, sizeof(number), "%s{\"width\":%.3f,\"facings\":[", s ? "," : "", shelf.width);
        out += number;
        for (size_t i = 0; i < shelf.facings.size(); ++i) {
            const Facing& f = shelf.facings[i];
            const auto it = recognitions_.find(f.bottle);
            const bool known = it != recognitions_.end() && it->second.done && !it->second.slug.empty();
            std::snprintf(number, sizeof(number), "%s{\"bottle\":%d,\"x\":%.3f,\"width\":%.3f,\"height\":%.3f,",
                          i ? "," : "", f.bottle, f.x, f.width, f.height);
            out += number;
            out += "\"slug\":" + json_text(known ? it->second.slug : "") + ",\"name\":" +
                   json_text(known ? it->second.name : "") + ",\"sure\":" + (known && it->second.sure ? "true" : "false") +
                   "}";
        }
        out += "]}";
    }
    out += "],\"duplicates\":[";
    for (size_t i = 0; i < plan.duplicates.size(); ++i) out += (i ? "," : "") + std::to_string(plan.duplicates[i]);
    return out + "]}";
}

std::vector<unsigned char> Pipeline::thumbnail(int bottle) const {
    std::lock_guard<std::mutex> r(recognition_mutex_);
    const auto it = recognitions_.find(bottle);
    return it == recognitions_.end() ? std::vector<unsigned char>{} : it->second.thumb;
}

}  // namespace shelfreid
