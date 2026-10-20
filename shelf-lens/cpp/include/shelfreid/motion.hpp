// The motion between consecutive frames, every frame: sparse flow on a quarter-size luma and
// a similarity (shift, scale, a small turn) fitted with RANSAC. Between neighbouring frames
// the picture moves little, so this holds where the tracker's flow between its steps (every
// 3rd frame or rarer) MAY lose its points: close to a shelf a small turn of the phone moves
// the picture a lot. The app draws its boxes with it, and the tracker takes the motion since
// its last step as a hint (Tracker::motion_hint).
#pragma once

#include <map>

#include <opencv2/core.hpp>

#include "shelfreid/geometry.hpp"

namespace shelfreid {

class FrameMotion {
public:
    // The similarity taking a point of the previous upright frame to this one, x' = A [x y 1]^T;
    // false when the flow does not find it (then the identity). `luma`: the Y plane or the grey
    // frame as the source gives it; `rotation`: the clockwise turn that makes it upright.
    bool step(const cv::Mat& luma, int rotation, cv::Matx23d& transform);
    void reset() { prev_.release(); }

private:
    cv::Mat prev_;
};

// The chained motions of the recent frames: where each frame lies relative to the first,
// and the motion between two of them.
class MotionChain {
public:
    // A frame and its motion from the previous one (`found` false: unknown).
    void add(int frame, const cv::Matx23d& motion, bool found);
    // The homography taking a point of frame `to` to frame `from` (the tracker's convention:
    // the current frame into the previous one); none when either frame is unknown or the
    // motion of a frame between them was not found.
    std::optional<Mat3> back(int from, int to) const;
    void reset() { frames_.clear(); }

private:
    struct Entry {
        Mat3 product;     // first frame -> this frame
        int broken = -1;  // the last frame up to here whose motion was not found
    };
    std::map<int, Entry> frames_;
    Mat3 product_ = Mat3::eye();
    int broken_ = -1;
};

}  // namespace shelfreid
