#include "shelfreid/cv.hpp"
#include "shelfreid/motion.hpp"

#include <cmath>
#include <vector>

namespace shelfreid {

namespace {

// A point of the source frame (width x height) in the upright frame, the source turned
// clockwise by `rotation` degrees (as cv::rotate turns it).
cv::Point2f upright(cv::Point2f p, int rotation, int width, int height) {
    switch (((rotation % 360) + 360) % 360) {
        case 90: return {height - 1 - p.y, p.x};
        case 180: return {width - 1 - p.x, height - 1 - p.y};
        case 270: return {p.y, width - 1 - p.x};
        default: return p;
    }
}

}  // namespace

bool FrameMotion::step(const cv::Mat& luma, int rotation, cv::Matx23d& transform) {
    constexpr int kScale = 4;   // the flow runs on a quarter-size luma
    cv::Mat small;
    cv::resize(luma, small, cv::Size(luma.cols / kScale, luma.rows / kScale), 0, 0, cv::INTER_AREA);
    transform = cv::Matx23d(1, 0, 0, 0, 1, 0);
    const bool first = prev_.empty() || prev_.size() != small.size();
    cv::Mat prev = prev_;
    prev_ = small;
    if (first) return true;
    std::vector<cv::Point2f> p, q;
    cv::goodFeaturesToTrack(prev, p, 150, 0.01, 6);
    if (p.size() < 10) return false;
    std::vector<uchar> status;
    std::vector<float> error;
    cv::calcOpticalFlowPyrLK(prev, small, p, q, status, error, cv::Size(15, 15), 3);
    std::vector<cv::Point2f> from, to;
    for (size_t i = 0; i < p.size(); ++i) {
        if (!status[i]) continue;
        from.push_back(upright(p[i] * kScale, rotation, luma.cols, luma.rows));
        to.push_back(upright(q[i] * kScale, rotation, luma.cols, luma.rows));
    }
    if (from.size() < 10) return false;
    std::vector<uchar> inliers;
    const cv::Mat a = cv::estimateAffinePartial2D(from, to, inliers, cv::RANSAC, 4.0, 1000, 0.99);
    if (a.empty() || cv::countNonZero(inliers) < 10) return false;
    const cv::Matx23d found(a.ptr<double>(0)[0], a.ptr<double>(0)[1], a.ptr<double>(0)[2], a.ptr<double>(1)[0],
                            a.ptr<double>(1)[1], a.ptr<double>(1)[2]);
    // One frame of a hand-held phone scales by a few percent at most.
    const double scale = std::hypot(found(0, 0), found(1, 0));
    if (scale < 0.9 || scale > 1.1) return false;
    transform = found;
    return true;
}

void MotionChain::add(int frame, const cv::Matx23d& motion, bool found) {
    if (found) {
        const Mat3 step(motion(0, 0), motion(0, 1), motion(0, 2), motion(1, 0), motion(1, 1), motion(1, 2), 0, 0, 1);
        product_ = step * product_;
    } else {
        broken_ = frame;
    }
    frames_[frame] = Entry{product_, broken_};
    while (!frames_.empty() && frames_.begin()->first < frame - 600) frames_.erase(frames_.begin());
}

std::optional<Mat3> MotionChain::back(int from, int to) const {
    const auto a = frames_.find(from), b = frames_.find(to);
    if (a == frames_.end() || b == frames_.end() || to < from) return std::nullopt;
    if (b->second.broken > from) return std::nullopt;   // a frame between them has no motion
    // to -> first -> from
    return normalized(a->second.product * b->second.product.inv());
}

}  // namespace shelfreid
