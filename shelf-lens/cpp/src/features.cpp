#include "shelfreid/cv.hpp"
#include "shelfreid/features.hpp"

#include <algorithm>
#include <cmath>
#include <unordered_map>


namespace shelfreid {

FrameFeatures extract(const cv::Mat& image, const FeatureConfig& cfg, const cv::Mat& mask_in) {
    FrameFeatures out;
    out.size = {static_cast<double>(image.cols), static_cast<double>(image.rows)};
    cv::Mat gray;
    if (image.channels() == 3) cv::cvtColor(image, gray, cv::COLOR_BGR2GRAY);
    else gray = image;
    const double scale = std::min(1.0, cfg.max_side / static_cast<double>(std::max(image.cols, image.rows)));
    cv::Mat mask = mask_in;
    if (scale < 1.0) {
        const cv::Size size(static_cast<int>(std::lround(image.cols * scale)),
                            static_cast<int>(std::lround(image.rows * scale)));
        cv::resize(gray, gray, size, 0, 0, cv::INTER_AREA);
        if (!mask.empty()) cv::resize(mask, mask, size, 0, 0, cv::INTER_NEAREST);
    }
    static thread_local cv::Ptr<cv::SIFT> sift;
    static thread_local int sift_features = -1;
    if (!sift || sift_features != cfg.max_features) {
        sift = cv::SIFT::create(cfg.max_features);
        sift_features = cfg.max_features;
    }
    std::vector<cv::KeyPoint> keypoints;
    cv::Mat descriptors;
    sift->detectAndCompute(gray, mask, keypoints, descriptors);
    if (static_cast<int>(keypoints.size()) > cfg.max_features) {
        std::vector<int> order(keypoints.size());
        for (size_t i = 0; i < order.size(); ++i) order[i] = static_cast<int>(i);
        std::stable_sort(order.begin(), order.end(),
                         [&](int x, int y) { return keypoints[x].response > keypoints[y].response; });
        order.resize(cfg.max_features);
        std::vector<cv::KeyPoint> kept;
        cv::Mat rows(static_cast<int>(order.size()), descriptors.cols, descriptors.type());
        for (size_t i = 0; i < order.size(); ++i) {
            kept.push_back(keypoints[order[i]]);
            descriptors.row(order[i]).copyTo(rows.row(static_cast<int>(i)));
        }
        keypoints.swap(kept);
        descriptors = rows;
    }
    out.points.reserve(keypoints.size());
    for (const auto& kp : keypoints)
        out.points.emplace_back(static_cast<float>(kp.pt.x / scale), static_cast<float>(kp.pt.y / scale));
    out.descriptors = descriptors;
    return out;
}

void match(const FrameFeatures& a, const FrameFeatures& b, const FeatureConfig& cfg,
           std::vector<cv::Point2f>& points_a, std::vector<cv::Point2f>& points_b) {
    points_a.clear();
    points_b.clear();
    if (a.descriptors.empty() || b.descriptors.empty() || a.points.size() < 2 || b.points.size() < 2)
        return;
    cv::BFMatcher matcher(cv::NORM_L2);
    std::vector<std::vector<cv::DMatch>> knn;
    matcher.knnMatch(b.descriptors, a.descriptors, knn, 2);
    std::vector<std::pair<int, int>> pairs;   // (index in B, index in A), in the order of B
    for (const auto& c : knn)
        if (c.size() == 2 && c[0].distance < cfg.ratio * c[1].distance)
            pairs.emplace_back(c[0].queryIdx, c[0].trainIdx);
    if (cfg.mutual && !pairs.empty()) {
        std::vector<cv::DMatch> back;
        matcher.match(a.descriptors, b.descriptors, back);
        std::unordered_map<int, int> from_a;
        for (const auto& m : back) from_a[m.queryIdx] = m.trainIdx;
        std::vector<std::pair<int, int>> kept;
        for (const auto& [ib, ia] : pairs) {
            auto it = from_a.find(ia);
            if (it != from_a.end() && it->second == ib) kept.emplace_back(ib, ia);
        }
        pairs.swap(kept);
    }
    for (const auto& [ib, ia] : pairs) {
        points_a.push_back(a.points[ia]);
        points_b.push_back(b.points[ib]);
    }
}

cv::Mat boxes_mask(const Size2& size, const std::vector<Box>& boxes) {
    cv::Mat mask = cv::Mat::zeros(static_cast<int>(size.height), static_cast<int>(size.width), CV_8U);
    for (const auto& b : boxes) {
        const int x1 = std::max(0, static_cast<int>(std::lround(b[0])));
        const int y1 = std::max(0, static_cast<int>(std::lround(b[1])));
        const int x2 = std::min(mask.cols, std::max(0, static_cast<int>(std::lround(b[2]))));
        const int y2 = std::min(mask.rows, std::max(0, static_cast<int>(std::lround(b[3]))));
        if (x2 > x1 && y2 > y1) mask(cv::Rect(x1, y1, x2 - x1, y2 - y1)).setTo(255);
    }
    return mask;
}

}  // namespace shelfreid
