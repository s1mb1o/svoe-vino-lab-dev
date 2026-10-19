// The tracker in two loops, as on a phone (realtime.py): a fast loop each frame and a slow
// loop on one frame at a time. Its result lands `latency` steps later (deterministic, for
// tests), or, with a negative latency, the slow loop runs on a thread of its own and its
// result lands on the first step after it is done (the phone).
#pragma once

#include <map>
#include <memory>
#include <string>
#include <optional>
#include <set>
#include <vector>

#include "shelfreid/tracker.hpp"

namespace shelfreid {

struct Snapshot {
    int number = 0, count = 0;
    cv::Mat frame;
    std::vector<Detection> detections;
    std::vector<Shown> shown;
    int ref = kNone;
    Mat3 P = Mat3::eye(), M = Mat3::eye();
    int anchored = 0;
    bool lost = false, trusted = true;
    std::set<int> wanted;
};

struct Move {
    int box;
    int held;     // the bottle id the box held at t, or kNone
    int target;   // the bottle id it should hold
};

struct SlowResult {
    int due = 0;
    Snapshot snap;
    std::optional<std::pair<int, Mat3>> found;   // keyframe, R: frame t -> keyframe
    std::vector<int> good;
    std::optional<PoseGraph> graph;              // with the loop edges, optimised
    double worst = 0.0;
    bool optimised = false;
    bool new_ground = false;
    struct NewKeyframe {
        FrameFeatures features;
        int ref;
        Mat3 T;
        double weight;
        std::string kind;
    };
    std::optional<NewKeyframe> keyframe;
    std::vector<std::pair<int, cv::Mat>> labels;   // bottle id, descriptors
    std::vector<Move> moves;
    std::set<int> confirmed;                       // provisional bottles seen and kept
    double seconds = 0.0;
};

class SlowWorker;

class RealtimeTracker : public Tracker {
public:
    RealtimeTracker(Size2 size, StreamConfig cfg = {}, int latency = 3);

    std::vector<Shown> step(int number, const cv::Mat& frame, std::vector<Detection> detections) override;

    // The two halves of the slow loop, for a thread of its own: `slow` reads the state of
    // frame t and computes; `apply` (on the thread of the fast loop) lands the result.
    SlowResult slow(const Snapshot& snap);
    void apply(SlowResult& result);

    int latency;             // steps; negative: a thread of its own
    int slow_every = 0;      // the least steps between two slow jobs (0: whenever asked)
    int last_slow = kNever;
    std::optional<SlowResult> inflight;
    int lost_since = 0;
    std::set<int> provisional;
    std::vector<double> fast_seconds, slow_seconds;
    std::map<std::string, double> slow_profile;   // seconds by part of the slow job (latency >= 0 only)
    std::vector<int> landed_after;   // the steps from the frame of a result to its landing

private:
    bool asks() const;
    void land();
    void slow_labels(const Snapshot& snap, const FrameFeatures& features, SlowResult& result);
    Snapshot snapshot(int number, const cv::Mat& frame, const std::vector<Detection>& detections,
                      const std::vector<Shown>& shown);

    // The thread of the slow loop. A job runs on a copy of the tracker taken when it starts
    // (the graph, the keyframes, the bottles; the descriptors are shared and only read).
    std::shared_ptr<SlowWorker> worker_;
    int generation_ = 0;   // a jump drops the results of the frames before it
};

}  // namespace shelfreid
