#include "shelfreid/planogram.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <map>
#include <numeric>
#include <sstream>

namespace shelfreid {

namespace {

constexpr double kDuplicate = 0.4;   // a bottle whose quad covers this share of another's (or is covered) is the same
constexpr double kRowSlack = 0.3;    // a neighbour's bottom within this many heights across the row
constexpr double kAdjacent = 1.0;    // a neighbour's gap at most this many widths
constexpr double kJoinSlack = 0.4;   // rows join with their ends this close across, in heights
constexpr double kJoinGap = 3.0;     // and a gap of at most this many heights
constexpr int kUnitWindow = 3;       // the bottles each side whose heights make a bottle's unit
constexpr int kShort = 3;            // a shelf of fewer bottles is a stray piece
constexpr double kStraySlack = 0.6;  // which joins the shelf it lies in, this close across, in heights
constexpr int kMinSeen = 2;          // a pair of bottles counts for the layout when frames saw it this often
constexpr int kSeenCap = 30;         // and as much as this many frames at most

// A bottle in its own frame: the midpoints of its bottom and top edges, the direction of
// the row (along its bottom and top edges) and across it (downwards).
struct Local {
    int id = 0, hits = 0, first_frame = 0;
    Quad quad{};
    cv::Point2d bottom, top;
    cv::Vec2d u, n;
    double width = 0, height = 0;
};

Local local(const Placed& p) {
    Local l;
    l.id = p.id, l.hits = p.hits, l.first_frame = p.first_frame, l.quad = p.quad;
    const Quad& q = p.quad;   // top left, top right, bottom right, bottom left
    l.bottom = (q[3] + q[2]) * 0.5;
    l.top = (q[0] + q[1]) * 0.5;
    const cv::Point2d along = (q[2] - q[3]) + (q[1] - q[0]);
    const double norm = std::max(std::hypot(along.x, along.y), 1e-9);
    l.u = {along.x / norm, along.y / norm};
    l.n = {-l.u[1], l.u[0]};
    l.width = (cv::norm(q[1] - q[0]) + cv::norm(q[2] - q[3])) / 2;
    l.height = std::abs((l.bottom - l.top).dot(cv::Point2d(l.n[0], l.n[1])));
    return l;
}

// Where `other`'s bottom is from `from`'s, along its row and across it.
std::pair<double, double> offset(const Local& from, const Local& other) {
    const cv::Point2d d = other.bottom - from.bottom;
    return {d.x * from.u[0] + d.y * from.u[1], d.x * from.n[0] + d.y * from.n[1]};
}

double median(std::vector<double> v) {
    std::sort(v.begin(), v.end());
    return v.empty() ? 0.0 : v[v.size() / 2];
}

}  // namespace

Planogram planogram(const std::vector<Placed>& bottles, const std::map<int, std::map<int, int>>& right,
                    const std::set<int>& skip, double aspect, const std::map<std::pair<int, int>, Offset>* offsets,
                    const std::map<int, Shape>* shapes) {
    Planogram result;
    // The bottles kept: the most seen first, so a duplicate loses to the bottle it repeats.
    std::vector<Local> all;
    for (const auto& p : bottles)
        if (!skip.count(p.id)) all.push_back(local(p));
    std::stable_sort(all.begin(), all.end(), [](const Local& a, const Local& b) {
        return a.hits != b.hits ? a.hits > b.hits : a.first_frame < b.first_frame;
    });
    std::vector<Local> kept;
    for (const auto& b : all) {
        bool repeats = false;
        for (const auto& k : kept)
            if (shared(b.quad, k.quad) > kDuplicate || shared(k.quad, b.quad) > kDuplicate) {
                repeats = true;
                break;
            }
        if (repeats) result.duplicates.push_back(b.id);
        else kept.push_back(b);
    }
    std::sort(result.duplicates.begin(), result.duplicates.end());
    const int n = static_cast<int>(kept.size());
    if (n == 0) return result;
    std::map<int, int> index;
    for (int i = 0; i < n; ++i) index[kept[i].id] = i;

    // The right neighbour of each bottle: the frames' habit, else the nearest one by the map.
    struct Link {
        int to = kNone;
        bool seen = false;   // the frames saw it there
        double along = 0;
    };
    std::vector<Link> next(n);
    for (int a = 0; a < n; ++a) {
        const Local& la = kept[a];
        auto habit = right.find(la.id);
        if (habit != right.end() && !habit->second.empty()) {
            const auto top = std::max_element(habit->second.begin(), habit->second.end(),
                                              [](const auto& x, const auto& y) { return x.second < y.second; });
            auto it = index.find(top->first);
            if (it != index.end()) {
                const auto [along, across] = offset(la, kept[it->second]);
                if (along > 0 && std::abs(across) < 2 * kRowSlack * la.height) next[a] = {it->second, true, along};
            }
        }
        if (next[a].to != kNone) continue;
        for (int c = 0; c < n; ++c) {
            if (c == a) continue;
            const Local& lc = kept[c];
            const auto [along, across] = offset(la, lc);
            if (along <= 0.4 * std::min(la.width, lc.width) || std::abs(across) >= kRowSlack * la.height) continue;
            if (along - (la.width + lc.width) / 2 >= kAdjacent * la.width) continue;
            if (next[a].to == kNone || along < next[a].along) next[a] = {c, false, along};
        }
    }
    // A bottle is the right neighbour of one bottle at most: the one the frames saw, else the nearest.
    std::vector<int> prev(n, kNone);
    for (int a = 0; a < n; ++a) {
        const int c = next[a].to;
        if (c == kNone) continue;
        const int other = prev[c];
        const bool better = other == kNone || (next[a].seen && !next[other].seen) ||
                            (next[a].seen == next[other].seen && next[a].along < next[other].along);
        if (better) {
            if (other != kNone) next[other].to = kNone;
            prev[c] = a;
        } else {
            next[a].to = kNone;
        }
    }

    // The rows the links make.
    std::vector<std::vector<int>> rows;
    std::vector<char> placed(n, 0);
    auto follow = [&](int start) {
        std::vector<int> row;
        for (int i = start; i != kNone && !placed[i]; i = next[i].to) {
            placed[i] = 1;
            row.push_back(i);
        }
        rows.push_back(row);
    };
    for (int i = 0; i < n; ++i)
        if (prev[i] == kNone) follow(i);
    for (int i = 0; i < n; ++i)
        if (!placed[i]) follow(i);   // a ring of links, should one happen

    // Rows join across gaps: the end of one where another starts, the closest pairs first.
    struct Join {
        double gap;
        int from, to;
    };
    std::vector<Join> joins;
    for (int r = 0; r < static_cast<int>(rows.size()); ++r)
        for (int s = 0; s < static_cast<int>(rows.size()); ++s) {
            if (r == s) continue;
            const Local& end = kept[rows[r].back()];
            const Local& start = kept[rows[s].front()];
            const auto [along, across] = offset(end, start);
            const double gap = along - (end.width + start.width) / 2;
            if (along > 0 && std::abs(across) < kJoinSlack * end.height && gap > -std::max(end.width, start.width) &&
                gap < kJoinGap * end.height)
                joins.push_back({gap, r, s});
        }
    std::sort(joins.begin(), joins.end(), [](const Join& a, const Join& b) { return a.gap < b.gap; });
    std::vector<int> after(rows.size(), kNone), before(rows.size(), kNone), group(rows.size());
    std::iota(group.begin(), group.end(), 0);
    std::function<int(int)> root = [&](int r) { return group[r] == r ? r : group[r] = root(group[r]); };
    for (const auto& j : joins) {
        if (after[j.from] != kNone || before[j.to] != kNone || root(j.from) == root(j.to)) continue;
        after[j.from] = j.to;
        before[j.to] = j.from;
        group[root(j.from)] = root(j.to);
    }
    std::vector<std::vector<int>> shelves;
    for (int r = 0; r < static_cast<int>(rows.size()); ++r) {
        if (before[r] != kNone) continue;
        std::vector<int> shelf;
        for (int s = r; s != kNone; s = after[s]) shelf.insert(shelf.end(), rows[s].begin(), rows[s].end());
        shelves.push_back(shelf);
    }

    // A stray piece (a bottle or two the links left alone: a duplicate the map put aside, a
    // bottle seen at an angle) goes into the shelf it lies in, next to its nearest bottle.
    for (auto& piece : shelves) {
        if (piece.empty() || piece.size() >= kShort) continue;
        std::vector<int>* home = nullptr;
        size_t at = 0;
        double nearest = 1e18;
        for (auto& shelf : shelves) {
            if (shelf.size() < kShort) continue;
            for (size_t i = 0; i < shelf.size(); ++i) {
                const auto [along, across] = offset(kept[shelf[i]], kept[piece.front()]);
                if (std::abs(across) < kStraySlack * kept[shelf[i]].height && std::abs(along) < nearest)
                    nearest = std::abs(along), home = &shelf, at = i + (along > 0 ? 1 : 0);
            }
        }
        if (!home) continue;
        home->insert(home->begin() + static_cast<long>(at), piece.begin(), piece.end());
        piece.clear();
    }
    shelves.erase(std::remove_if(shelves.begin(), shelves.end(), [](const auto& s) { return s.empty(); }), shelves.end());

    // The order of the shelves: S is above T when T's bottles are lower where they meet S's
    // (a bottle of T across from one of S), else where they come closest.
    const int m = static_cast<int>(shelves.size());
    auto above = [&](int s, int t) {
        int votes = 0;
        double closest = 1e18;
        int nearest = 0;
        for (int a : shelves[s])
            for (int b : shelves[t]) {
                const auto [along, across] = offset(kept[a], kept[b]);
                const double reach = (kept[a].width + kept[b].width) / 2;
                if (std::abs(along) < reach) votes += across > 0 ? 1 : -1;
                if (std::abs(along) < closest) closest = std::abs(along), nearest = across > 0 ? 1 : -1;
            }
        return votes != 0 ? votes > 0 : nearest > 0;
    };
    std::vector<int> higher(m, 0);   // the shelves above each
    std::vector<double> mean_y(m, 0);
    for (int s = 0; s < m; ++s) {
        for (int t = 0; t < m; ++t)
            if (t != s && above(t, s)) ++higher[s];
        for (int a : shelves[s]) mean_y[s] += kept[a].bottom.y / shelves[s].size();
    }
    std::vector<int> order(m);
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](int a, int b) {
        return higher[a] != higher[b] ? higher[a] > higher[b] : mean_y[a] > mean_y[b];   // the bottom one first
    });

    // The map's layout, each shelf from 0: sizes and gaps in bottle heights. The map
    // stretches unevenly (more one way than the other where keyframe 0 saw the shelf at an
    // angle), so a height is in units of the heights around and a width or a gap in units of
    // the widths around, times the shape of a bottle in the frames (`aspect`). It stands in
    // for the frames' layout below where the frames have nothing.
    std::map<int, double> centre_of, width_of, height_of;   // bottle id -> bottle heights
    for (int s : order) {
        const auto& ids = shelves[s];
        const int k = static_cast<int>(ids.size());
        std::vector<double> tall(k), wide(k);
        for (int i = 0; i < k; ++i) {
            std::vector<double> heights, widths;
            for (int j = std::max(0, i - kUnitWindow); j <= std::min(k - 1, i + kUnitWindow); ++j) {
                heights.push_back(kept[ids[j]].height);
                widths.push_back(kept[ids[j]].width);
            }
            tall[i] = std::max(median(heights), 1e-6);
            wide[i] = std::max(median(widths), 1e-6) / aspect;
        }
        double x = 0;
        for (int i = 0; i < k; ++i) {
            const Local& b = kept[ids[i]];
            if (i > 0) {
                const Local& a = kept[ids[i - 1]];
                const double gap = offset(a, b).first - (a.width + b.width) / 2;
                x += std::max(0.0, gap / ((wide[i - 1] + wide[i]) / 2));
            }
            width_of[b.id] = b.width / wide[i];
            height_of[b.id] = b.height / tall[i];
            centre_of[b.id] = x + width_of[b.id] / 2;
            x += width_of[b.id];
        }
    }

    // The frames' layout: the centres that fit best (least squares) the offsets of the pairs
    // seen together, a shelf above or below included, so the shelves line up with each other
    // and the map's drift between passes stays out. A far pair counts less (the perspective
    // of a frame bends it), a pair seen once not at all.
    if (offsets && !offsets->empty()) {
        std::map<int, int> slot;
        std::vector<int> ids;
        for (int s : order)
            for (int i : shelves[s]) slot[kept[i].id] = static_cast<int>(ids.size()), ids.push_back(kept[i].id);
        const int m = static_cast<int>(ids.size());
        std::vector<int> group(m);
        std::iota(group.begin(), group.end(), 0);
        std::function<int(int)> top = [&](int i) { return group[i] == i ? i : group[i] = top(group[i]); };
        cv::Mat A = cv::Mat::eye(m, m, CV_64F) * 1e-6, rhs = cv::Mat::zeros(m, 1, CV_64F);
        for (const auto& [pair, o] : *offsets) {
            const auto a = slot.find(pair.first), b = slot.find(pair.second);
            if (a == slot.end() || b == slot.end() || o.n < kMinSeen) continue;
            const int i = a->second, j = b->second;
            const double mean = o.dx / o.n, w = std::min(o.n, kSeenCap) / std::pow(1 + std::abs(mean), 2);
            A.at<double>(i, i) += w, A.at<double>(j, j) += w, A.at<double>(i, j) -= w, A.at<double>(j, i) -= w;
            rhs.at<double>(i) -= w * mean, rhs.at<double>(j) += w * mean;
            group[top(i)] = top(j);
        }
        cv::Mat x;
        if (cv::solve(A, rhs, x, cv::DECOMP_CHOLESKY)) {
            // The largest group of bottles the frames link sets the layout. Another group (no
            // frame saw one of its bottles whole with one of the first: an empty place between
            // them, say) keeps the map's layout on each shelf, moved to the nearest bottles
            // of the first group on that shelf (the map's gap to them stays).
            std::map<int, int> size;
            for (int i = 0; i < m; ++i) ++size[top(i)];
            const int main = std::max_element(size.begin(), size.end(),
                                              [](const auto& p, const auto& q) { return p.second < q.second; })->first;
            std::vector<double> all;
            for (int i = 0; i < m; ++i)
                if (top(i) == main) all.push_back(x.at<double>(i) - centre_of[ids[i]]);
            std::map<std::pair<int, int>, double> moved;   // (group, shelf) -> shift
            for (int s : order) {
                std::map<int, std::vector<int>> parts;     // group -> its bottles (slots) on this shelf
                for (int i : shelves[s]) parts[top(slot[kept[i].id])].push_back(slot[kept[i].id]);
                for (const auto& [g, mine] : parts) {
                    if (g == main) continue;
                    double at = 0;
                    for (int i : mine) at += centre_of[ids[i]] / mine.size();
                    std::vector<std::pair<double, double>> near;   // distance, shift
                    if (parts.count(main))
                        for (int i : parts[main]) near.emplace_back(std::abs(centre_of[ids[i]] - at), x.at<double>(i) - centre_of[ids[i]]);
                    std::sort(near.begin(), near.end());
                    std::vector<double> shift;
                    for (size_t q = 0; q < near.size() && q < 3; ++q) shift.push_back(near[q].second);
                    moved[{g, s}] = shift.empty() ? median(all) : median(shift);
                }
            }
            for (int s : order)
                for (int k : shelves[s]) {
                    const int i = slot[kept[k].id];
                    centre_of[ids[i]] = top(i) == main ? x.at<double>(i) : centre_of[ids[i]] + moved[{top(i), s}];
                }
        }
        if (shapes)
            for (const int id : ids) {
                const auto it = shapes->find(id);
                if (it != shapes->end() && it->second.n > 0)
                    width_of[id] = it->second.width / it->second.n, height_of[id] = it->second.height / it->second.n;
            }
    }

    // The facings of each shelf left to right; two that overlap meet halfway. The left edge
    // of the leftmost facing of all is 0.
    double left_most = 1e18;
    for (int s : order)
        for (int i : shelves[s]) left_most = std::min(left_most, centre_of[kept[i].id] - width_of[kept[i].id] / 2);
    for (int s : order) {
        std::vector<int> ids;
        for (int i : shelves[s]) ids.push_back(kept[i].id);
        std::sort(ids.begin(), ids.end(), [&](int a, int b) { return centre_of[a] < centre_of[b]; });
        std::vector<double> lo, hi;
        for (int id : ids) lo.push_back(centre_of[id] - width_of[id] / 2 - left_most), hi.push_back(lo.back() + width_of[id]);
        for (size_t i = 1; i < ids.size(); ++i)
            if (lo[i] < hi[i - 1]) {
                const double meet = (lo[i] + hi[i - 1]) / 2;
                hi[i - 1] = std::max(meet, lo[i - 1] + 0.05);
                lo[i] = std::min(meet, hi[i] - 0.05);
            }
        Shelf shelf;
        for (size_t i = 0; i < ids.size(); ++i) shelf.facings.push_back({ids[i], lo[i], hi[i] - lo[i], height_of[ids[i]]});
        shelf.width = hi.empty() ? 0 : hi.back();
        result.shelves.push_back(shelf);
    }
    return result;
}

Planogram planogram(const Tracker& tracker, const std::set<int>& skip) {
    double aspect = 0.3;
    if (tracker.bottle_width && tracker.bottle_height && *tracker.bottle_height > 0)
        aspect = std::clamp(*tracker.bottle_width / *tracker.bottle_height, 0.2, 0.45);
    return planogram(tracker.placed(), tracker.right, skip, aspect, &tracker.offsets, &tracker.shapes);
}

std::string to_json(const Planogram& p) {
    std::ostringstream out;
    out.setf(std::ios::fixed);
    out.precision(3);
    out << "{\"shelves\": [";
    for (size_t s = 0; s < p.shelves.size(); ++s) {
        const Shelf& shelf = p.shelves[s];
        out << (s ? ", " : "") << "{\"width\": " << shelf.width << ", \"facings\": [";
        for (size_t i = 0; i < shelf.facings.size(); ++i) {
            const Facing& f = shelf.facings[i];
            out << (i ? ", " : "") << "{\"bottle\": " << f.bottle << ", \"x\": " << f.x << ", \"width\": " << f.width
                << ", \"height\": " << f.height << "}";
        }
        out << "]}";
    }
    out << "], \"duplicates\": [";
    for (size_t i = 0; i < p.duplicates.size(); ++i) out << (i ? ", " : "") << p.duplicates[i];
    out << "]}";
    return out.str();
}

}  // namespace shelfreid
