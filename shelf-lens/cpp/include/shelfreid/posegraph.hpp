// A pose graph of keyframes on the shelf plane (posegraph.py). Node i is the homography
// of keyframe i into the map; node 0 stays fixed. Edge (i, j, T): T maps keyframe j into
// keyframe i. The optimisation moves the nodes so that G_i T and G_j agree on a grid of
// points of keyframe j, with the robust loss soft_l1, and a price on a change of the shape
// of a node (`stiffness`).
#pragma once

#include <string>
#include <tuple>
#include <vector>

#include "shelfreid/geometry.hpp"

namespace shelfreid {

struct Edge {
    int i = 0, j = 0;
    Mat3 T = Mat3::eye();
    double weight = 1.0;
    std::string kind = "odometry";   // odometry | loop | chain
};

class PoseGraph {
public:
    explicit PoseGraph(Size2 size, int grid = 3, double loss_scale = 20.0, double stiffness = 3000.0);

    int add(const Mat3& G);
    void connect(int i, int j, const Mat3& T, double weight, const std::string& kind);
    // Add a loop or chain edge, replacing the earlier one of the same pair and kind.
    void replace(const Edge& edge);
    // The largest disagreement of an edge with the poses, in map pixels.
    double error(const Edge& edge) const;
    // (largest edge error before, after).
    std::pair<double, double> optimize(int max_iterations = 50);
    // Optimise, drop the non-odometry edges still off by more than `outlier`, optimise
    // again: (error before, error after, dropped edges).
    std::tuple<double, double, int> optimize_robust(double outlier = 150.0, int rounds = 3);

    std::vector<Mat3> poses;
    std::vector<Edge> edges;

private:
    Size2 size_;
    std::vector<cv::Point2d> grid_;
    double loss_scale_, stiffness_;
    Mat3 norm_, inv_norm_;
};

}  // namespace shelfreid
