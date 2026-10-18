// The one-to-one assignment of rows to columns with the least total distance; only pairs
// at most `limit` apart count (associate.py, `hungarian`).
#pragma once

#include <utility>
#include <vector>

namespace shelfreid {

using Matrix = std::vector<std::vector<double>>;   // rows x columns; inf: not comparable

// (row, column) pairs, by row.
std::vector<std::pair<int, int>> hungarian(const Matrix& distance, double limit);

}  // namespace shelfreid
