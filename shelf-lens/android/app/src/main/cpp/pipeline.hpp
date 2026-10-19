// The work of the app on its frames, apart from showing them. Every frame gives its motion
// (shelfreid::FrameMotion), so the boxes of the last processed frame follow the picture and
// the tracker gets the motion since its last step as a hint (no lost track when a frame is
// dropped or the phone is close to the shelf). Every 3rd frame goes through the bottle
// detector and the tracker, on two threads in a row: while the tracker takes frame t, the
// detector already runs on frame t+1. A frame that arrives while the detector is busy
// replaces the waiting one (the latest frame wins, as a camera drops frames).
#pragma once

#include <chrono>
#include <condition_variable>
#include <deque>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include <opencv2/core.hpp>

#include "detector.hpp"
#include "shelfreid/motion.hpp"
#include "shelfreid/realtime.hpp"

namespace shelfreid {

class Pipeline {
public:
    // Loads the detector: seconds (NNAPI compiles). `cv_threads`: the size of OpenCV's pool (it
    // runs one parallel region at a time, so the slow loop's SIFT and the fast loop's flow
    // contend for it; 1 runs every call serially; 0 keeps OpenCV's default). `cheap_slow`: the
    // slow loop's SIFT on a 960 px copy with 2500 features instead of 1280 px and 4000 (half
    // the time; 99.1-99.7% the same ids on the test shots).
    Pipeline(const std::string& model_path, int cv_threads, bool cheap_slow);
    ~Pipeline();

    // A new shot of frames this size (upright); drops the tracker of the last one.
    void begin(int width, int height);
    void end();

    // The motion of this frame from the previous one: the similarity (shift, scale, a small
    // turn) that takes a point of the previous upright frame to this one, x' = A [x y 1]^T;
    // false when the flow does not find it (too few points agree). `luma` is the Y plane as
    // the source gives it, `rotation` the clockwise turn that makes it upright.
    bool motion(int frame, const cv::Mat& luma, int rotation, cv::Matx23d& transform);
    // An upright BGR frame for the detector and the tracker.
    void submit(int frame, cv::Mat bgr);

    struct Result {
        int frame = -1;
        std::vector<Shown> shown;
    };
    Result latest() const;
    std::string stats() const;

private:
    struct Job {
        int frame = -1;
        cv::Mat bgr;
        std::vector<Detection> detections;
        std::chrono::steady_clock::time_point arrived;
    };
    void detect_loop();
    void track_loop();

    std::unique_ptr<BottleDetector> detector_;
    std::unique_ptr<RealtimeTracker> tracker_;
    StreamConfig cfg_;
    int cv_threads_ = 0;

    std::mutex mutex_;
    std::condition_variable wake_;
    std::optional<Job> to_detect_, to_track_;
    bool stop_ = true;
    std::thread detect_thread_, track_thread_;

    mutable std::mutex result_mutex_;
    Result result_;
    std::vector<double> detect_ms_, latency_ms_, fast_ms_, slow_ms_, landed_;
    std::deque<std::chrono::steady_clock::time_point> done_;
    int submitted_ = 0, dropped_ = 0;
    size_t bottles_ = 0, keyframes_ = 0;
    int ids_ = 0;

    FrameMotion frame_motion_;
    mutable std::mutex chain_mutex_;
    MotionChain chain_;        // the motion of the recent frames, for the tracker's hints
    int last_tracked_ = -1;    // the frame of the tracker's last step
};

}  // namespace shelfreid
