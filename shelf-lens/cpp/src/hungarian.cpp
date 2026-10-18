#include "shelfreid/hungarian.hpp"

#include <algorithm>
#include <limits>

namespace shelfreid {

namespace {

constexpr double kFar = 1e6;

// The Hungarian method (potentials, O(n^2 m)) for n <= m: the column of each row.
std::vector<int> solve(const Matrix& cost, int n, int m) {
    const double inf = std::numeric_limits<double>::infinity();
    std::vector<double> u(n + 1, 0.0), v(m + 1, 0.0);
    std::vector<int> p(m + 1, 0), way(m + 1, 0);
    for (int i = 1; i <= n; ++i) {
        p[0] = i;
        int j0 = 0;
        std::vector<double> minv(m + 1, inf);
        std::vector<char> used(m + 1, 0);
        do {
            used[j0] = 1;
            const int i0 = p[j0];
            double delta = inf;
            int j1 = 0;
            for (int j = 1; j <= m; ++j) {
                if (used[j]) continue;
                const double cur = cost[i0 - 1][j - 1] - u[i0] - v[j];
                if (cur < minv[j]) {
                    minv[j] = cur;
                    way[j] = j0;
                }
                if (minv[j] < delta) {
                    delta = minv[j];
                    j1 = j;
                }
            }
            for (int j = 0; j <= m; ++j) {
                if (used[j]) {
                    u[p[j]] += delta;
                    v[j] -= delta;
                } else {
                    minv[j] -= delta;
                }
            }
            j0 = j1;
        } while (p[j0] != 0);
        do {
            const int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0);
    }
    std::vector<int> column(n, -1);
    for (int j = 1; j <= m; ++j)
        if (p[j]) column[p[j] - 1] = j - 1;
    return column;
}

}  // namespace

std::vector<std::pair<int, int>> hungarian(const Matrix& distance, double limit) {
    std::vector<std::pair<int, int>> out;
    const int rows = static_cast<int>(distance.size());
    if (rows == 0) return out;
    const int cols = static_cast<int>(distance[0].size());
    if (cols == 0) return out;
    const bool transpose = rows > cols;
    const int n = transpose ? cols : rows, m = transpose ? rows : cols;
    Matrix cost(n, std::vector<double>(m));
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j) {
            const double d = transpose ? distance[j][i] : distance[i][j];
            cost[i][j] = d <= limit ? d : kFar;
        }
    const std::vector<int> column = solve(cost, n, m);
    for (int i = 0; i < n; ++i) {
        const int j = column[i];
        if (j < 0 || cost[i][j] >= kFar) continue;
        if (transpose) out.emplace_back(j, i);
        else out.emplace_back(i, j);
    }
    std::sort(out.begin(), out.end());
    return out;
}

}  // namespace shelfreid
