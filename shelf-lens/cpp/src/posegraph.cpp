#include "shelfreid/posegraph.hpp"

#include <algorithm>
#include <cmath>

#include <Eigen/Dense>

namespace shelfreid {

namespace {

constexpr int kShape[6] = {0, 1, 3, 4, 6, 7};   // the corrections other than the shift

Mat3 correction(const double* d) {
    return Mat3(1 + d[0], d[1], d[2], d[3], 1 + d[4], d[5], d[6], d[7], 1.0);
}

}  // namespace

PoseGraph::PoseGraph(Size2 size, int grid, double loss_scale, double stiffness)
    : size_(size), loss_scale_(loss_scale), stiffness_(stiffness) {
    for (int a = 0; a < grid; ++a) {
        const double x = (0.1 + 0.8 * a / (grid - 1)) * size.width;
        for (int b = 0; b < grid; ++b) {
            const double y = (0.1 + 0.8 * b / (grid - 1)) * size.height;
            grid_.emplace_back(x, y);
        }
    }
    const double w = size.width, h = size.height;
    norm_ = Mat3(2 / w, 0, -1, 0, 2 / w, -h / w, 0, 0, 1);
    inv_norm_ = norm_.inv();
}

int PoseGraph::add(const Mat3& G) {
    poses.push_back(normalized(G));
    return static_cast<int>(poses.size()) - 1;
}

void PoseGraph::connect(int i, int j, const Mat3& T, double weight, const std::string& kind) {
    edges.push_back(Edge{i, j, normalized(T), weight, kind});
}

void PoseGraph::replace(const Edge& edge) {
    edges.erase(std::remove_if(edges.begin(), edges.end(),
                               [&](const Edge& e) {
                                   return e.kind == edge.kind &&
                                          ((e.i == edge.i && e.j == edge.j) || (e.i == edge.j && e.j == edge.i));
                               }),
                edges.end());
    edges.push_back(edge);
}

double PoseGraph::error(const Edge& edge) const {
    const Mat3 A = poses[edge.i] * edge.T;
    double worst = 0.0;
    for (const auto& p : grid_) worst = std::max(worst, cv::norm(project(A, p) - project(poses[edge.j], p)));
    return worst;
}

std::pair<double, double> PoseGraph::optimize(int max_iterations) {
    const int n = static_cast<int>(poses.size());
    if (n < 2 || edges.empty()) return {0.0, 0.0};
    double before = 0.0;
    for (const auto& e : edges) before = std::max(before, error(e));
    const std::vector<Mat3> start = poses;
    const int params = 8 * (n - 1);
    const int per_edge = 2 * static_cast<int>(grid_.size());
    const int rows = per_edge * static_cast<int>(edges.size()) + 6 * (n - 1);
    std::vector<std::vector<cv::Point2d>> mapped;   // the grid mapped by each edge's T
    for (const auto& e : edges) mapped.push_back(project(e.T, grid_));

    auto pose = [&](const Eigen::VectorXd& x, int node) -> Mat3 {
        if (node == 0) return start[0];
        return start[node] * inv_norm_ * correction(x.data() + 8 * (node - 1)) * norm_;
    };
    auto edge_residuals = [&](const Mat3& Pi, const Mat3& Pj, int k, double* out) {
        const double s = std::sqrt(edges[k].weight);
        for (size_t g = 0; g < grid_.size(); ++g) {
            const cv::Point2d a = project(Pi, mapped[k][g]);
            const cv::Point2d b = project(Pj, grid_[g]);
            out[2 * g] = (a.x - b.x) * s;
            out[2 * g + 1] = (a.y - b.y) * s;
        }
    };
    auto residuals = [&](const Eigen::VectorXd& x, Eigen::VectorXd& r) {
        r.resize(rows);
        for (size_t k = 0; k < edges.size(); ++k)
            edge_residuals(pose(x, edges[k].i), pose(x, edges[k].j), static_cast<int>(k),
                           r.data() + per_edge * k);
        const int base = per_edge * static_cast<int>(edges.size());
        for (int node = 0; node < n - 1; ++node)
            for (int c = 0; c < 6; ++c) r[base + 6 * node + c] = stiffness_ * x[8 * node + kShape[c]];
    };
    const double C2 = loss_scale_ * loss_scale_;
    auto robust_cost = [&](const Eigen::VectorXd& r) {
        double cost = 0.0;
        for (int i = 0; i < r.size(); ++i) cost += 2.0 * (std::sqrt(1.0 + r[i] * r[i] / C2) - 1.0);
        return 0.5 * C2 * cost;
    };

    Eigen::VectorXd x = Eigen::VectorXd::Zero(params), r;
    residuals(x, r);
    double cost = robust_cost(r);
    double lambda = 1e-3;
    const double h = 1e-6;
    for (int iteration = 0; iteration < max_iterations; ++iteration) {
        // The Jacobian, block by block: an edge depends on its two nodes alone.
        Eigen::MatrixXd J = Eigen::MatrixXd::Zero(rows, params);
        std::vector<double> plus(per_edge), base_r(per_edge);
        for (size_t k = 0; k < edges.size(); ++k) {
            const Edge& e = edges[k];
            for (int node : {e.i, e.j}) {
                if (node == 0 || (node == e.j && e.i == e.j)) continue;
                for (int c = 0; c < 8; ++c) {
                    Eigen::VectorXd xp = x;
                    xp[8 * (node - 1) + c] += h;
                    edge_residuals(pose(xp, e.i), pose(xp, e.j), static_cast<int>(k), plus.data());
                    for (int q = 0; q < per_edge; ++q)
                        J(per_edge * k + q, 8 * (node - 1) + c) += (plus[q] - r[per_edge * k + q]) / h;
                }
            }
        }
        const int base = per_edge * static_cast<int>(edges.size());
        for (int node = 0; node < n - 1; ++node)
            for (int c = 0; c < 6; ++c) J(base + 6 * node + c, 8 * node + kShape[c]) = stiffness_;
        // soft_l1 as weights (iteratively reweighted least squares).
        Eigen::VectorXd w(rows);
        for (int i = 0; i < rows; ++i) w[i] = 1.0 / std::sqrt(1.0 + r[i] * r[i] / C2);
        const Eigen::MatrixXd JtW = J.transpose() * w.asDiagonal();
        const Eigen::MatrixXd A = JtW * J;
        const Eigen::VectorXd g = JtW * r;
        bool improved = false;
        for (int attempt = 0; attempt < 10; ++attempt) {
            Eigen::MatrixXd Ad = A;
            Ad.diagonal() += lambda * A.diagonal().cwiseMax(1e-9);
            const Eigen::VectorXd delta = Ad.ldlt().solve(-g);
            const Eigen::VectorXd xn = x + delta;
            Eigen::VectorXd rn;
            residuals(xn, rn);
            const double cn = robust_cost(rn);
            if (cn < cost) {
                const double gain = (cost - cn) / std::max(cost, 1e-12);
                x = xn;
                r = rn;
                cost = cn;
                lambda = std::max(lambda / 3.0, 1e-9);
                improved = true;
                if (gain < 1e-10) iteration = max_iterations;
                break;
            }
            lambda *= 4.0;
        }
        if (!improved) break;
    }
    for (int node = 0; node < n; ++node) poses[node] = normalized(pose(x, node));
    double after = 0.0;
    for (const auto& e : edges) after = std::max(after, error(e));
    return {before, after};
}

std::tuple<double, double, int> PoseGraph::optimize_robust(double outlier, int rounds) {
    auto [before, after] = optimize();
    int dropped = 0;
    for (int round = 0; round < rounds; ++round) {
        int worst = -1;
        double worst_error = outlier;
        for (size_t k = 0; k < edges.size(); ++k) {
            if (edges[k].kind == "odometry") continue;
            const double e = error(edges[k]);
            if (e > worst_error) {
                worst_error = e;
                worst = static_cast<int>(k);
            }
        }
        if (worst < 0) break;
        edges.erase(edges.begin() + worst);
        ++dropped;
        after = optimize().second;
    }
    return {before, after, dropped};
}

}  // namespace shelfreid
