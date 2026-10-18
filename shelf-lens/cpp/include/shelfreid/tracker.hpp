// Unique bottles over a video stream, frame by frame (stream.py): the motion of the
// camera by optical flow, the place on the shelf map by a pose graph of keyframes, the
// boxes against the bottles of the map, the labels of the bottles and the check of the
// rows. `step` is the synchronous tracker, the reference; realtime.hpp splits it in two
// loops.
#pragma once

#include <map>
#include <optional>
#include <set>
#include <string>
#include <utility>
#include <vector>

#include <opencv2/core.hpp>

#include "shelfreid/config.hpp"
#include "shelfreid/features.hpp"
#include "shelfreid/geometry.hpp"
#include "shelfreid/hungarian.hpp"
#include "shelfreid/posegraph.hpp"

namespace shelfreid {

constexpr int kNone = -1;
constexpr int kNever = -1000000000;

struct Detection {
    Box box{};
    double score = 1.0;
    double width() const { return box[2] - box[0]; }
};

struct Shown {
    Box box{};
    std::string status;   // new | returning | pending | ignored
    int bottle = kNone;
};

struct Bottle {
    int id = 0;
    int anchor = 0;               // the keyframe of the coordinates of `quad`
    Quad quad{};                  // box corners in the anchor keyframe
    int first_frame = 0;
    int last_seen = 0;            // the tracker step of the last sight
    int first_step = 0;
    int appearance = 1;
    bool left = false;
    int hits = 1;
    std::optional<Box> last_box;  // the last box and the chain of motions at that frame
    Mat3 last_M = Mat3::eye();
    std::vector<cv::Mat> label;   // SIFT descriptors, one matrix a view
    int labelled = kNever;
};

struct Keyframe {
    int frame = 0;
    int step = 0;
    FrameFeatures features;
};

// The votes of a box for the bottles (indices), in the order of their first vote.
using Votes = std::vector<std::pair<int, int>>;

struct Contradiction {
    int frame, box, held, named, votes_named, votes_held;
    std::string outcome;
};

// A good registration: keyframe, R (frame -> keyframe), strong, inliers.
struct Good {
    int index;
    Mat3 R;
    bool strong;
    int inliers;
};

using Neighbours = std::vector<std::pair<int, int>>;   // left, right box of each box

class Tracker {
public:
    Tracker(Size2 size, StreamConfig cfg = {});
    virtual ~Tracker() = default;

    // The synchronous step: the reference of the two loops.
    virtual std::vector<Shown> step(int number, const cv::Mat& frame, std::vector<Detection> detections);

    Mat3 H() const;   // the frame -> the map

    // The state.
    Size2 size;
    StreamConfig cfg;
    PoseGraph graph;
    std::vector<Keyframe> keyframes;
    int ref = kNone;
    Mat3 P = Mat3::eye();   // frame -> reference keyframe
    Mat3 M = Mat3::eye();   // frame -> first frame by the motions alone
    int anchored = 0;
    std::map<int, int> verified;   // keyframe -> step of its last registration
    int waited = 0;
    std::map<int, std::map<int, int>> right, left;   // neighbour history
    std::set<int> wanted;
    bool need_registration = false;
    std::vector<Bottle> bottles;
    int next_id = 0;
    std::optional<std::pair<cv::Mat, std::vector<Box>>> previous;
    int count = 0;
    int localized = kNever;
    int untrusted = 0;
    bool lost = false;
    int lost_steps = 0;
    bool trusted = true;
    std::optional<double> bottle_height, bottle_width;
    std::map<int, Votes> votes;   // box -> votes of this frame

    // Counters.
    int dropped_edges = 0, rescued = 0, vetoed = 0, suggested = 0, jumps = 0, found = 0,
        new_grounds = 0, merged_young = 0, dropped = 0, lost_motion = 0, label_checks = 0,
        label_confirmed = 0, conflicted = 0, conflicts = 0, closed = 0;
    std::vector<Contradiction> contradictions;

protected:
    // Geometry of the map in the frame.
    Quad keyframe_quad(int index) const;
    void points(const std::vector<int>& which, std::vector<cv::Point2d>& centres,
                std::vector<cv::Vec2d>& spans) const;   // which: bottle indices; empty -> all
    void tracked_points(std::vector<cv::Point2d>& centres, std::vector<cv::Vec2d>& spans) const;
    std::vector<std::vector<int>> rows_of(const std::vector<Box>& boxes) const;
    Neighbours neighbours_of(const std::vector<Box>& boxes) const;
    bool place_confirmed(const Bottle& bottle) const;
    bool contradicted(int bottle_id, int left_id, int right_id) const;
    int habit(const std::map<int, std::map<int, int>>& table, int bottle) const;
    void rename(int old_id, int new_id);
    double width() const;
    Matrix point_distance(const std::vector<Box>& boxes, const std::vector<cv::Point2d>& centres,
                          const std::vector<cv::Vec2d>& spans) const;
    Matrix same_place(const std::vector<int>& one, const std::vector<int>& two) const;
    std::vector<char> in_view(const std::vector<cv::Point2d>& centres, double margin = 0.0) const;
    Quad local_quad(const Box& box, int anchor) const;
    Quad frame_quad() const;
    bool cut(const Box& box) const;
    std::optional<double> running(std::optional<double> value, std::vector<double> samples, double q) const;
    std::vector<Detection> whole_bottles(const std::vector<Detection>& detections);

    // Motion and keyframes.
    std::optional<Mat3> flow(const cv::Mat& gray_prev, const cv::Mat& gray, const std::vector<Box>& boxes_prev) const;
    Registration register_points(const std::vector<cv::Point2f>& points_k, const std::vector<cv::Point2f>& points_f) const;
    FrameFeatures features_of(const cv::Mat& frame, const std::vector<Detection>& detections) const;
    std::optional<Good> register_to(const FrameFeatures& features, int index) const;
    std::vector<Good> registrations(const FrameFeatures& features, const std::vector<int>& candidates);
    void relocalize(int number, const FrameFeatures& features);
    int merge_duplicates();
    void absorb(Bottle& earlier, const Bottle& later);
    bool needs_keyframe() const;
    void add_keyframe(int number, const FrameFeatures& features);
    void jump();
    void find(int number, const FrameFeatures& features);
    bool near_old_keyframe() const;
    bool trust();

    // Association.
    std::vector<Shown> associate(int number, const std::vector<Detection>& detections, bool trusted_now);
    std::vector<cv::Mat> box_descriptors(const FrameFeatures* features, const std::vector<Box>& boxes) const;
    std::map<int, Votes> label_votes(const std::vector<cv::Mat>& descriptors, const std::vector<Box>& boxes) const;
    int says(const Votes* votes) const;
    bool twins(int a, int b) const;
    std::set<int> check_rows(int number, const std::vector<Box>& boxes, std::map<int, int>& matched,
                             const std::vector<cv::Point2d>& centres, const std::vector<cv::Vec2d>& spans);
    void learn_labels(const std::vector<Shown>& shown, const std::vector<cv::Mat>& descriptors);
    std::pair<std::set<int>, std::set<int>> conflicts_of(const std::vector<Box>& boxes, const std::map<int, int>& matched,
                                                         const std::map<int, int>& ids, const Neighbours& neighbours,
                                                         const std::vector<cv::Point2d>& centres,
                                                         const std::vector<cv::Vec2d>& spans,
                                                         const std::vector<char>& view);
    std::map<int, int> rescue(const std::vector<Box>& boxes, const std::vector<int>& free, const std::vector<int>& lost_ones,
                              const std::map<int, int>& matched, const std::vector<cv::Point2d>& centres);
    std::vector<Shown> merge_young(std::vector<Shown> shown, const Neighbours& neighbours);
    void observe(Bottle& bottle, const Box& box);
    int index_of(int bottle_id) const;
    cv::Mat gray_of(const cv::Mat& frame) const;
};

// Drop weak, wide, thin and contained boxes (detect.py, `clean_bottles`).
std::vector<Detection> clean_bottles(const std::vector<Detection>& detections, double min_score = 0.6,
                                     double max_aspect = 1.0, double min_aspect = 0.15, double contained = 0.5);

}  // namespace shelfreid
