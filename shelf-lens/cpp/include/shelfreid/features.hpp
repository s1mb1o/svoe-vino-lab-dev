// SIFT keypoints of a frame and the matching of two frames (features.py).
#pragma once

#include <vector>

#include <opencv2/core.hpp>

#include "shelfreid/config.hpp"
#include "shelfreid/geometry.hpp"

namespace shelfreid {

struct FrameFeatures {
    Size2 size;
    std::vector<cv::Point2f> points;   // pixels of the full-resolution frame
    cv::Mat descriptors;               // CV_32F, one row a point
};

// The keypoints of one BGR or gray frame; `mask` (CV_8U, frame size) MAY be empty.
FrameFeatures extract(const cv::Mat& image, const FeatureConfig& cfg, const cv::Mat& mask);

// The matched points (points of A, points of B), row by row: the ratio test and mutual
// nearest neighbours.
void match(const FrameFeatures& a, const FrameFeatures& b, const FeatureConfig& cfg,
           std::vector<cv::Point2f>& points_a, std::vector<cv::Point2f>& points_b);

// A uint8 mask, 255 inside the boxes.
cv::Mat boxes_mask(const Size2& size, const std::vector<Box>& boxes);

}  // namespace shelfreid
