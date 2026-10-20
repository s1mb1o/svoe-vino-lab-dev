#include "shelfreid/cv.hpp"
#include "shelfreid/geometry.hpp"

#include <algorithm>
#include <cmath>


namespace shelfreid {

cv::Point2d project(const Mat3& H, const cv::Point2d& p) {
    const double x = H(0, 0) * p.x + H(0, 1) * p.y + H(0, 2);
    const double y = H(1, 0) * p.x + H(1, 1) * p.y + H(1, 2);
    const double w = H(2, 0) * p.x + H(2, 1) * p.y + H(2, 2);
    return {x / w, y / w};
}

std::vector<cv::Point2d> project(const Mat3& H, const std::vector<cv::Point2d>& points) {
    std::vector<cv::Point2d> out;
    out.reserve(points.size());
    for (const auto& p : points) out.push_back(project(H, p));
    return out;
}

Quad project(const Mat3& H, const Quad& quad) {
    Quad out;
    for (int i = 0; i < 4; ++i) out[i] = project(H, quad[i]);
    return out;
}

Quad corners(const Size2& size) {
    return {cv::Point2d(0, 0), cv::Point2d(size.width, 0), cv::Point2d(size.width, size.height),
            cv::Point2d(0, size.height)};
}

Quad box_corners(const Box& b) {
    return {cv::Point2d(b[0], b[1]), cv::Point2d(b[2], b[1]), cv::Point2d(b[2], b[3]),
            cv::Point2d(b[0], b[3])};
}

cv::Point2d centre(const Quad& q) {
    return {(q[0].x + q[1].x + q[2].x + q[3].x) / 4.0, (q[0].y + q[1].y + q[2].y + q[3].y) / 4.0};
}

static std::vector<cv::Point2f> as_float(const Quad& q) {
    return {cv::Point2f(q[0]), cv::Point2f(q[1]), cv::Point2f(q[2]), cv::Point2f(q[3])};
}

double area(const Quad& quad) { return std::abs(cv::contourArea(as_float(quad))); }

double shared(const Quad& a, const Quad& b) {
    std::vector<cv::Point2f> inter;
    const double overlap = cv::intersectConvexConvex(as_float(a), as_float(b), inter);
    return overlap / std::max(area(a), 1e-6);
}

Mat3 normalized(const Mat3& H) { return H * (1.0 / H(2, 2)); }

std::optional<std::string> check(const Mat3& H0, const Size2& size_b, const HomographyConfig& cfg) {
    const Mat3 H = normalized(H0);
    const Quad quad = corners(size_b);
    double wmin = 1e300, wmax = -1e300;
    for (const auto& p : quad) {
        const double w = H(2, 0) * p.x + H(2, 1) * p.y + H(2, 2);
        wmin = std::min(wmin, w);
        wmax = std::max(wmax, w);
    }
    if (wmin <= 0) return std::string("frame B crosses the horizon");
    if (wmax / wmin > cfg.max_w_ratio) return std::string("perspective stretch");
    const double det = H(0, 0) * H(1, 1) - H(0, 1) * H(1, 0);
    if (det <= 0) return std::string("mirrored");
    const double scale = std::sqrt(det);
    if (!(1.0 / cfg.max_scale <= scale && scale <= cfg.max_scale)) return std::string("scale");
    if (!cv::isContourConvex(as_float(project(H, quad))))
        return std::string("frame B is not convex in frame A");
    return std::nullopt;
}

double coverage(const Mat3& H, const std::vector<cv::Point2f>& inliers_b, const Size2& size_a,
                const Size2& size_b, double area_b) {
    if (inliers_b.size() < 3) return 0.0;
    const Quad a_in_b = project(H.inv(), corners(size_a));
    std::vector<cv::Point2f> inter;
    const double overlap = cv::intersectConvexConvex(as_float(corners(size_b)), as_float(a_in_b), inter);
    if (overlap <= 0) return 0.0;
    std::vector<cv::Point2f> hull;
    cv::convexHull(inliers_b, hull);
    const double room = area_b > 0 ? std::min(overlap, area_b) : overlap;
    return std::min(1.0, cv::contourArea(hull) / room);
}

Registration estimate(const std::vector<cv::Point2f>& points_a,
                      const std::vector<cv::Point2f>& points_b, const Size2& size_a,
                      const Size2& size_b, const HomographyConfig& cfg, double area_b) {
    Registration r;
    const int count = static_cast<int>(points_a.size());
    r.matches = count;
    if (count < std::max(4, cfg.min_inliers)) {
        r.reason = std::to_string(count) + " matches";
        return r;
    }
    const double threshold = cfg.ransac_threshold * std::hypot(size_a.width, size_a.height);
    std::vector<uchar> mask;
    cv::Mat H = cv::findHomography(points_b, points_a, cv::USAC_MAGSAC, threshold, mask, 10000, 0.999);
    if (H.empty()) {
        r.reason = "no homography";
        return r;
    }
    Mat3 Hm;
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) Hm(i, j) = H.at<double>(i, j);
    Hm = normalized(Hm);
    r.H = Hm;
    std::vector<cv::Point2f> inliers_b;
    for (int i = 0; i < count; ++i)
        if (mask[i]) inliers_b.push_back(points_b[i]);
    r.inliers = static_cast<int>(inliers_b.size());
    std::optional<std::string> reason;
    if (r.inliers < cfg.min_inliers) reason = std::to_string(r.inliers) + " inliers";
    else if (r.inliers < cfg.min_inlier_ratio * count) reason = "inlier ratio";
    else reason = check(Hm, size_b, cfg);
    if (!reason) {
        // Frame B has to overlap frame A.
        const Quad quad = project(Hm, corners(size_b));
        std::vector<cv::Point2f> inter;
        const double overlap_a = cv::intersectConvexConvex(as_float(quad), as_float(corners(size_a)), inter);
        if (overlap_a <= 0) reason = "no overlap";
    }
    if (!reason) {
        r.coverage = coverage(Hm, inliers_b, size_a, size_b, area_b);
        if (r.coverage < cfg.min_coverage) reason = "inliers cover too little of the overlap";
    }
    r.ok = !reason;
    r.reason = reason ? *reason : "ok";
    return r;
}

}  // namespace shelfreid
