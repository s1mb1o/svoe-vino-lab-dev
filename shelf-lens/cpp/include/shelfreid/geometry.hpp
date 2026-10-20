// Homographies of the shelf plane: projection, the checks of a plausible camera motion,
// and the registration of two frames from matched points (homography.py).
#pragma once

#include <array>
#include <optional>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

#include "shelfreid/config.hpp"

namespace shelfreid {

using Mat3 = cv::Matx33d;
using Box = std::array<double, 4>;   // x1, y1, x2, y2
using Quad = std::array<cv::Point2d, 4>;

struct Size2 {
    double width = 0, height = 0;
};

inline Mat3 eye3() { return Mat3::eye(); }

cv::Point2d project(const Mat3& H, const cv::Point2d& p);
std::vector<cv::Point2d> project(const Mat3& H, const std::vector<cv::Point2d>& points);
Quad project(const Mat3& H, const Quad& quad);
Quad corners(const Size2& size);
Quad box_corners(const Box& box);
cv::Point2d centre(const Quad& quad);
double area(const Quad& quad);
// The share of quad_a that quad_b covers.
double shared(const Quad& quad_a, const Quad& quad_b);
Mat3 normalized(const Mat3& H);

// Why H is not a plausible camera motion of frame B, or nothing.
std::optional<std::string> check(const Mat3& H, const Size2& size_b, const HomographyConfig& cfg);
// The share of the overlap, in frame B, that the convex hull of the inliers of B covers; of
// `area_b` px at most when the points of B can be in that much of it only (the bottles' boxes):
// one bottle in view covers a tenth of a frame, all of what it can.
double coverage(const Mat3& H, const std::vector<cv::Point2f>& inliers_b, const Size2& size_a,
                const Size2& size_b, double area_b = 0);

struct Registration {
    bool ok = false;
    std::string reason;
    Mat3 H = Mat3::eye();   // frame B -> frame A
    int matches = 0;
    int inliers = 0;
    double coverage = 0.0;
};

// The homography B -> A from matched points (MAGSAC), and its checks (`area_b`: as coverage's).
Registration estimate(const std::vector<cv::Point2f>& points_a,
                      const std::vector<cv::Point2f>& points_b, const Size2& size_a,
                      const Size2& size_b, const HomographyConfig& cfg, double area_b = 0);

}  // namespace shelfreid
