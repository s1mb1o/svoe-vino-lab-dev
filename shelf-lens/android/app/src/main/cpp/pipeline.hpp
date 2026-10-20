// The work of the app on its frames, apart from showing them. Every frame gives its motion
// (shelfreid::FrameMotion), so the boxes of the last processed frame follow the picture and
// the tracker gets the motion since its last step as a hint (no lost track when a frame is
// dropped or the phone is close to the shelf). Every 3rd frame goes through the bottle
// detector and the tracker, on two threads in a row: while the tracker takes frame t, the
// detector already runs on frame t+1. A frame that arrives while the detector is busy
// replaces the waiting one (the latest frame wins, as a camera drops frames).
#pragma once

#include <array>
#include <set>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <map>
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
    // Loads the detector (slow: NNAPI compiles the model). `cv_threads`: the size of OpenCV's
    // pool (it runs one parallel region at a time, so the slow loop's SIFT and the fast loop's
    // flow contend for it; 1 runs every call serially; 0 keeps OpenCV's default).
    // `cheap_slow`: the slow loop's SIFT on a 960 px copy with 2500 features instead of
    // 1280 px and 4000. `accelerator`: the detector on NNAPI, else on 4 CPU threads.
    Pipeline(const std::string& model_path, int cv_threads, bool cheap_slow, bool accelerator);
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

    // The frames stopped and start again from elsewhere (the camera was off): the motion
    // and the tracker's flow start over, the tracker finds its place on the map again, the
    // map and the recognition stay.
    void interrupt();

    struct Result {
        int frame = -1;
        std::vector<Shown> shown;
        std::vector<int> recognized;   // a box: 1 its wine is known, 2 a crop waits for the server or its answer, else 0
    };
    Result latest() const;
    std::string stats() const;

    // Recognition of the wines by the server, one bottle crop a request (/v1/match). Every
    // other tracker step (so the reserve spans more time) offers, for each bottle not yet sure
    // whose box is at least kGate of the frame height (the server finds the producer from
    // there) and not cut by the frame, its crop to the bottle's reserve, from its first sight
    // on (before the tracker confirms it): at most kKeptPerBottle crops of different frames,
    // by quality = sharpness x (height / the bottle's largest height)^2 (a large crop first,
    // but a blurred one loses to a sharper slightly smaller one); a new crop pushes out the
    // worst. At most kKeptCrops crops in all: the worst of the bottles with more than one go
    // first. One request a bottle (kMaxAttempts), with the best crop of its reserve,
    // kMatureMs after the bottle first fit (a borderline first crop does not go when a better
    // one comes a moment later), once the tracker confirmed it (not a duplicate it merges
    // away). The crops are sent apart from the steps (take_crop), so the queue drains after a
    // video ends and for bottles gone from the frame: no more than kMaxInflight requests out,
    // a bottle in view first (the shelf the user looks at), then the largest crop; the
    // reserve is freed when its crop goes. The answer decides (kAgree = 1). A request left
    // without an answer (no network, the server busy) puts its crop back and does not count;
    // the bottle goes again kRetryMs later, twice as long after each such failure in a row, up
    // to kRetryMaxMs. A request refused for good (a bad request) counts: the bottle stays
    // unknown.
    static constexpr double kGate = 0.19;
    static constexpr int kMaxAttempts = 1, kAgree = 1, kMaxInflight = 4, kKeptPerBottle = 4, kKeptCrops = 80,
                         kMatureMs = 1000, kRetryMs = 2000, kRetryMaxMs = 30000;
    // What became of a request (Recognizer.java has the same numbers).
    enum Outcome { kAnswered = 0, kRetry = 1, kRefused = 2 };
    // Off: no more requests, and the crops kept for them go (the boxes turn grey).
    void set_recognition(bool on);
    // The next crop to send, or empty: five little-endian int32 (bottle, frame, box height in
    // px, sharpness x 10, crops it was chosen from), then the PNG. It picks the crop when a
    // slot is free.
    std::vector<unsigned char> take_crop();
    // What came of the request for a crop (an Outcome; slug and name of the first candidate
    // when answered). The decision when this answer changes it: "slug\tname\tsure|unsure",
    // else empty.
    std::string answer(int bottle, int frame, int height, const std::string& slug, const std::string& name, int outcome);
    // Every bottle met, as a JSON array of {"id", "state", "height" (px), "share" (of the
    // frame height), "frame" (last seen), "requests", "answers", "sure", "kept" (crops in the
    // reserve), "suitable" (a crop of it went to the reserve), "wine"}; state: known, asking,
    // waiting (a crop kept for a slot), answered, done asking, unconfirmed, small, cut,
    // eligible (it passed the gate, recognition off).
    std::string recognition_table() const;
    // The bottles of the map (provisional ones left out), those whose wine is known, those
    // with a crop waiting for the server or its answer, and 1 while the tracker has lost its
    // place on the map, or waits to register to it with a box in view waiting for that (the
    // boxes add nothing to the map then), else 0.
    std::array<int, 4> summary() const;
    // A small JPEG of the bottle's latest crop (renewed every 10 tracker steps), or empty.
    std::vector<unsigned char> thumbnail(int bottle) const;
    // The planogram of the map as it is now (shelfreid/planogram.hpp, provisional bottles
    // left out) as JSON: {"shelves": [{"width", "facings": [{"bottle", "x", "width",
    // "height", "slug", "name", "sure"}]}], "duplicates": [...]}, the bottom shelf first;
    // slug and name empty while the wine is not known.
    std::string planogram() const;

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
    mutable std::mutex tracker_mutex_;   // the tracker's steps against a read of its map (planogram)
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
    size_t bottles_ = 0, keyframes_ = 0, provisional_ = 0;
    bool lost_ = false;
    int ids_ = 0;

    struct Recognition {
        int attempts = 0, inflight = 0, last_step = -1000, answers = 0;
        bool done = false, sure = false;
        bool confirmed = false;               // the tracker keeps it (its last box was not provisional)
        bool suitable = false;                // a crop of it went to the reserve (or would have, recognition off)
        std::map<std::string, int> votes;     // slug -> answers naming it first
        std::map<std::string, std::string> names;
        std::string best_slug;                // the answer from the largest crop
        int best_height = 0;
        std::string slug, name;
        std::string state = "small";          // why it is or is not asked (recognition_table)
        int height = 0, frame = -1, thumb_step = -1000;
        double share = 0;
        std::vector<unsigned char> thumb;
        struct Candidate {
            cv::Mat crop;
            int height = 0, frame = -1;
            double sharpness = 0;
        };
        std::vector<Candidate> kept;          // the reserve: the best crops not sent yet
        Candidate sent;                       // the crop out, put back if its request fails
        int max_height = 0;                   // the largest box seen while it fit
        std::chrono::steady_clock::time_point first_fit{};   // when it first fit (zero: not yet)
        std::chrono::steady_clock::time_point retry_at{};   // not sent again before this
        int failures = 0;                     // requests in a row left without an answer
        // The colour of its box: 1 green (the wine is known), 2 yellow (a crop waits for the
        // server or its answer), 0 grey.
        int colour() const { return done && !slug.empty() ? 1 : (!kept.empty() || inflight > 0) ? 2 : 0; }
        double quality(const Candidate& c) const {
            const double size = max_height > 0 ? static_cast<double>(c.height) / max_height : 1.0;
            return c.sharpness * size * size;
        }
    };
    std::vector<unsigned char> dispatch();   // under recognition_mutex_
    int queued() const;                      // bottles with a crop to send, unsent: under recognition_mutex_
    // `kept`: the bottles the map keeps for good (not provisional), in view or not.
    void plan_recognition(int frame, const cv::Mat& bgr, const std::vector<Shown>& shown, const std::set<int>& kept);
    mutable std::mutex recognition_mutex_;
    bool recognition_on_ = false;
    std::map<int, Recognition> recognitions_;
    std::deque<std::vector<unsigned char>> outbox_;
    int out_ = 0;                  // crops queued or in flight
    int track_steps_ = 0, sent_ = 0, answered_ = 0, failed_ = 0, accepted_ = 0;
    int shown_frame_ = -1;         // the frame of the last step: a bottle seen there is in view

    FrameMotion frame_motion_;
    mutable std::mutex chain_mutex_;
    MotionChain chain_;        // the motion of the recent frames, for the tracker's hints
    int last_tracked_ = -1;    // the frame of the tracker's last step
};

}  // namespace shelfreid
