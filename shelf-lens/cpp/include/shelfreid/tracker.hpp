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

// Where bottle b stands from bottle a (a < b) in the frames that saw both: the sums of the
// offsets of b's box from a's, in units of each frame's median box height, and the numbers
// of frames: dx between the centres (n: boxes not cut, a box cut at the top still has its
// centre), dy between the bottoms (ny: boxes inside the frame). A frame sees
// the shelf without the drift of the map, so the planogram lays the bottles out from these.
struct Offset {
    double dx = 0, dy = 0;
    int n = 0, ny = 0;
};

// The sums of a bottle's box sizes in the same units, and the number of frames.
struct Shape {
    double width = 0, height = 0;
    int n = 0;
};

// A bottle of the map: its box corners in map coordinates (the pixels of keyframe 0).
struct Placed {
    int id = 0;
    Quad quad{};
    int hits = 0, first_frame = 0, last_seen = 0;
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
    std::vector<cv::Point2f> keyframe_points, frame_points;   // the matches it was fitted to
};

using Neighbours = std::vector<std::pair<int, int>>;   // left, right box of each box

class Tracker {
public:
    Tracker(Size2 size, StreamConfig cfg = {});
    virtual ~Tracker() = default;

    // The synchronous step: the reference of the two loops.
    virtual std::vector<Shown> step(int number, const cv::Mat& frame, std::vector<Detection> detections);

    Mat3 H() const;   // the frame -> the map
    // Every bottle of the map where the map puts it now (after the pose graph's last
    // optimisation), in the order of the ids.
    std::vector<Placed> placed() const;

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
    mutable std::string flow_failure;   // why the last flow failed (empty: it did not)
    // The motion of the picture since the last step, current frame -> previous step's frame,
    // from the frame-by-frame motion (FrameMotion) when the caller has it. The flow starts
    // its points where it puts them (so a large move between steps does not lose them), and
    // takes it when the flow fails, instead of a jump. The step uses and clears it.
    std::optional<Mat3> motion_hint;
    int hinted = 0;   // steps whose flow failed and the hint stood in
    std::map<int, Votes> votes;   // box -> votes of this frame
    std::map<std::pair<int, int>, Offset> offsets;   // (a, b), a < b
    std::map<int, Shape> shapes;

    // Counters.
    int dropped_edges = 0, rescued = 0, vetoed = 0, suggested = 0, jumps = 0, found = 0,
        new_grounds = 0, merged_young = 0, dropped = 0, lost_motion = 0, label_checks = 0,
        label_confirmed = 0, conflicted = 0, conflicts = 0, closed = 0, aliased = 0;
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
    void rename(int old_id, int new_id, const char* why);   // `why`: for SHELFREID_TRACE
    double width() const;
    Matrix point_distance(const std::vector<Box>& boxes, const std::vector<cv::Point2d>& centres,
                          const std::vector<cv::Vec2d>& spans) const;
    Matrix same_place(const std::vector<int>& one, const std::vector<int>& two) const;
    std::vector<char> in_view(const std::vector<cv::Point2d>& centres, double margin = 0.0) const;
    Quad local_quad(const Box& box, int anchor) const;
    Quad frame_quad() const;
    // Too little of a bottle to go by: cut by a side of the frame (its centre is off) or the
    // bottom (its label hidden), or by the top with less than cfg.min_visible of the running
    // bottle height left.
    bool cut(const Box& box) const;
    // Inside the frame, no edge touched: a box to refine a bottle's place on the map with.
    bool whole(const Box& box) const;
    // The box made whole: as it is when not cut; cut only at the top and showing at least
    // cfg.min_visible of a bottle, with its top where a bottle of the running height would
    // have it; else nothing.
    std::optional<Box> completed(const Box& box) const;
    std::optional<double> running(std::optional<double> value, std::vector<double> samples, double q) const;
    std::vector<Detection> whole_bottles(const std::vector<Detection>& detections);

    // Motion and keyframes.
    std::optional<Mat3> flow(const cv::Mat& gray_prev, const cv::Mat& gray, const std::vector<Box>& boxes_prev,
                             const std::optional<Mat3>& hint = std::nullopt) const;
    Registration register_points(const std::vector<cv::Point2f>& points_k, const std::vector<cv::Point2f>& points_f) const;
    FrameFeatures features_of(const cv::Mat& frame, const std::vector<Detection>& detections) const;
    std::optional<Good> register_to(const FrameFeatures& features, int index) const;
    // Whether registration `g` of a frame agrees with where the flow put that frame (`frame_ref`,
    // `frame_P`, at step `step`; `seen`: the steps keyframes were last registered). Within
    // cfg.alias_tolerance bottle widths of it, always. Further: never for the reference
    // keyframe or one registered lately (the flow ties them to the frame, a registration only
    // corrects the drift); for a keyframe met long ago (a loop back, where the drift MAY be
    // that large), unless the flow's place fits the matches about as well as the
    // registration's (cfg.alias_support, cfg.alias_ambiguity): then the matches are a row of
    // one wine matched to a neighbour.
    bool agrees(const Good& g, int frame_ref, const Mat3& frame_P, int step, const std::map<int, int>& seen) const;
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
    void learn_offsets(const std::vector<Shown>& shown);
    // Whether SHELFREID_TRACE_FRAMES ("from-to") holds this frame number.
    static bool traced(int number);
    int index_of(int bottle_id) const;
    cv::Mat gray_of(const cv::Mat& frame) const;
};

// Drop weak, wide, thin and contained boxes (detect.py, `clean_bottles`).
std::vector<Detection> clean_bottles(const std::vector<Detection>& detections, double min_score = 0.6,
                                     double max_aspect = 1.0, double min_aspect = 0.15, double contained = 0.5);

}  // namespace shelfreid
