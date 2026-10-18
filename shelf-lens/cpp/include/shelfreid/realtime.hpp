// The tracker in two loops, as on a phone (realtime.py): a fast loop each frame and a slow
// loop on one frame at a time, whose result lands `latency` steps later (deterministic for
// tests; on the phone the slow loop runs on its own thread and lands when it is done).
#pragma once

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

class RealtimeTracker : public Tracker {
public:
    RealtimeTracker(Size2 size, StreamConfig cfg = {}, int latency = 3);

    std::vector<Shown> step(int number, const cv::Mat& frame, std::vector<Detection> detections) override;

    // The two halves of the slow loop, for a thread of its own: `slow` reads the state of
    // frame t and computes; `apply` (on the thread of the fast loop) lands the result.
    SlowResult slow(const Snapshot& snap);
    void apply(SlowResult& result);

    int latency;
    int slow_every = 0;      // the least steps between two slow jobs (0: whenever asked)
    int last_slow = kNever;
    std::optional<SlowResult> inflight;
    int lost_since = 0;
    std::set<int> provisional;
    std::vector<double> fast_seconds, slow_seconds;

private:
    bool asks() const;
    void land();
    void slow_labels(const Snapshot& snap, const FrameFeatures& features, SlowResult& result);
};

}  // namespace shelfreid
