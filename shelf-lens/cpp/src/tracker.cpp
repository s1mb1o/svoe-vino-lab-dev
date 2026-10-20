// The tracker: geometry of the map in the frame, motion, keyframes, and the synchronous
// step. The association is in associate.cpp.
#include "shelfreid/cv.hpp"
#include "shelfreid/tracker.hpp"

#include <algorithm>
#include <cstdlib>
#include <cstdio>
#ifdef __ANDROID__
#include <android/log.h>
#endif
#include <iostream>
#include <cmath>
#include <numeric>


namespace shelfreid {

double percentile(std::vector<double> v, double q) {
    std::sort(v.begin(), v.end());
    const double pos = q / 100.0 * (v.size() - 1);
    const size_t lo = static_cast<size_t>(std::floor(pos)), hi = static_cast<size_t>(std::ceil(pos));
    return v[lo] + (v[hi] - v[lo]) * (pos - lo);
}

Tracker::Tracker(Size2 size_, StreamConfig cfg_) : size(size_), cfg(cfg_), graph(size_) {}

Mat3 Tracker::H() const { return ref == kNone ? P : graph.poses[ref] * P; }

std::vector<Placed> Tracker::placed() const {
    std::vector<Placed> out;
    for (const Bottle& b : bottles)
        out.push_back({b.id, project(graph.poses[b.anchor], b.quad), b.hits, b.first_frame, b.last_seen});
    std::sort(out.begin(), out.end(), [](const Placed& a, const Placed& b) { return a.id < b.id; });
    return out;
}

Quad Tracker::keyframe_quad(int index) const { return project(graph.poses[index], corners(size)); }

void Tracker::points(const std::vector<int>& which, std::vector<cv::Point2d>& centres,
                     std::vector<cv::Vec2d>& spans) const {
    const Mat3 inverse = H().inv();
    std::map<int, Mat3> into;
    const size_t n = which.empty() ? bottles.size() : which.size();
    centres.assign(n, {});
    spans.assign(n, {});
    for (size_t k = 0; k < n; ++k) {
        const Bottle& b = bottles[which.empty() ? k : which[k]];
        auto it = into.find(b.anchor);
        if (it == into.end()) it = into.emplace(b.anchor, inverse * graph.poses[b.anchor]).first;
        const Quad quad = project(it->second, b.quad);
        centres[k] = project(it->second, centre(b.quad));
        double lo = quad[0].y, hi = quad[0].y;
        for (const auto& p : quad) lo = std::min(lo, p.y), hi = std::max(hi, p.y);
        spans[k] = {lo, hi};
    }
}

void Tracker::tracked_points(std::vector<cv::Point2d>& centres, std::vector<cv::Vec2d>& spans) const {
    points({}, centres, spans);
    const Mat3 inverse = M.inv();
    for (size_t k = 0; k < bottles.size(); ++k) {
        const Bottle& b = bottles[k];
        if (!b.last_box) continue;
        const Quad quad = project(inverse * b.last_M, box_corners(*b.last_box));
        centres[k] = centre(quad);
        double lo = quad[0].y, hi = quad[0].y;
        for (const auto& p : quad) lo = std::min(lo, p.y), hi = std::max(hi, p.y);
        spans[k] = {lo, hi};
    }
}

std::vector<std::vector<int>> Tracker::rows_of(const std::vector<Box>& boxes) const {
    const double height = bottle_height.value_or(0.25 * size.height);
    std::vector<int> order(boxes.size());
    std::iota(order.begin(), order.end(), 0);
    std::stable_sort(order.begin(), order.end(), [&](int a, int b) { return boxes[a][3] < boxes[b][3]; });
    std::vector<std::vector<int>> rows;
    for (int i : order) {
        if (!rows.empty() && boxes[i][3] - boxes[rows.back().back()][3] <= cfg.row_gap * height)
            rows.back().push_back(i);
        else
            rows.push_back({i});
    }
    for (auto& row : rows)
        std::stable_sort(row.begin(), row.end(),
                         [&](int a, int b) { return boxes[a][0] + boxes[a][2] < boxes[b][0] + boxes[b][2]; });
    return rows;
}

Neighbours Tracker::neighbours_of(const std::vector<Box>& boxes) const {
    Neighbours result(boxes.size(), {kNone, kNone});
    auto mid = [&](int i) { return (boxes[i][0] + boxes[i][2]) / 2; };
    for (const auto& row : rows_of(boxes))
        for (size_t q = 0; q + 1 < row.size(); ++q) {
            const int a = row[q], b = row[q + 1];
            const double w = std::max({boxes[a][2] - boxes[a][0], boxes[b][2] - boxes[b][0], 0.8 * width()});
            if (mid(b) - mid(a) <= cfg.adjacent_gap * w) {
                result[a].second = b;
                result[b].first = a;
            }
        }
    return result;
}

bool Tracker::place_confirmed(const Bottle& bottle) const {
    for (const auto& [k, step] : verified)
        if (std::abs(bottle.anchor - k) <= cfg.anchor_window && count - step <= cfg.trust_steps) return true;
    return false;
}

bool Tracker::contradicted(int bottle_id, int left_id, int right_id) const {
    if (left_id != kNone) {
        const int h = habit(right, left_id);
        if (h != kNone && h != bottle_id) return true;
    }
    if (right_id != kNone) {
        const int h = habit(left, right_id);
        if (h != kNone && h != bottle_id) return true;
    }
    return false;
}

int Tracker::habit(const std::map<int, std::map<int, int>>& table, int bottle) const {
    auto it = table.find(bottle);
    if (it == table.end() || it->second.empty()) return kNone;
    int top = kNone, best = -1, total = 0;
    for (const auto& [other, c] : it->second) {
        total += c;
        if (c > best) best = c, top = other;
    }
    return (best >= cfg.habit_count && best >= cfg.habit_share * total) ? top : kNone;
}

void Tracker::rename(int old_id, int new_id, const char* why) {
    if (std::getenv("SHELFREID_TRACE")) std::cerr << "rename " << old_id << " -> " << new_id << " (" << why << ") step " << count << "\n";
    for (auto* table : {&right, &left}) {
        std::map<int, int> counts;
        auto it = table->find(old_id);
        if (it != table->end()) {
            counts = it->second;
            table->erase(it);
        }
        auto& mine = (*table)[new_id];
        for (const auto& [other, c] : counts)
            if (other != new_id) mine[other] += c;
        for (auto& [owner, cs] : *table) {
            auto f = cs.find(old_id);
            if (f == cs.end()) continue;
            const int c = f->second;
            cs.erase(f);
            if (owner != new_id) cs[new_id] += c;
        }
    }
    // The offsets of the old id become the new id's (the pair of the two goes).
    std::map<std::pair<int, int>, Offset> moved;
    for (auto it = offsets.begin(); it != offsets.end();) {
        auto [a, b] = it->first;
        if (a != old_id && b != old_id) {
            ++it;
            continue;
        }
        Offset o = it->second;
        it = offsets.erase(it);
        if (a == old_id) a = new_id;
        if (b == old_id) b = new_id;
        if (a == b) continue;
        if (a > b) std::swap(a, b), o.dx = -o.dx, o.dy = -o.dy;
        Offset& into = moved[{a, b}];
        into.dx += o.dx, into.dy += o.dy, into.n += o.n, into.ny += o.ny;
    }
    for (const auto& [key, o] : moved) {
        Offset& into = offsets[key];
        into.dx += o.dx, into.dy += o.dy, into.n += o.n, into.ny += o.ny;
    }
    auto s = shapes.find(old_id);
    if (s != shapes.end()) {
        Shape& into = shapes[new_id];
        into.width += s->second.width, into.height += s->second.height, into.n += s->second.n;
        shapes.erase(old_id);
    }
}

bool Tracker::whole_in_view(const Bottle& b) const {
    const Quad quad = project(H().inv() * graph.poses[b.anchor], b.quad);
    const double m = cfg.edge_margin * size.width;
    for (const auto& p : quad)
        if (p.x < m || p.x > size.width - m || p.y < m || p.y > size.height - m) return false;
    return true;
}

void Tracker::forget(int id) {
    if (std::getenv("SHELFREID_TRACE")) std::cerr << "forget " << id << " step " << count << "\n";
    for (auto* table : {&right, &left}) {
        table->erase(id);
        for (auto& [owner, cs] : *table) cs.erase(id);
    }
    for (auto it = offsets.begin(); it != offsets.end();)
        it = it->first.first == id || it->first.second == id ? offsets.erase(it) : std::next(it);
    shapes.erase(id);
    bottles.erase(std::remove_if(bottles.begin(), bottles.end(), [&](const Bottle& b) { return b.id == id; }), bottles.end());
}

double Tracker::width() const { return bottle_width.value_or(0.1 * size.width); }

Matrix Tracker::point_distance(const std::vector<Box>& boxes, const std::vector<cv::Point2d>& centres,
                               const std::vector<cv::Vec2d>& spans) const {
    const double inf = std::numeric_limits<double>::infinity();
    Matrix distance(boxes.size(), std::vector<double>(centres.size(), inf));
    for (size_t i = 0; i < boxes.size(); ++i) {
        const auto& [x1, y1, x2, y2] = boxes[i];
        const double middle = (y1 + y2) / 2;
        const double w = std::max(x2 - x1, 0.8 * width());
        for (size_t k = 0; k < centres.size(); ++k)
            if (centres[k].y >= y1 && centres[k].y <= y2 && spans[k][0] <= middle && spans[k][1] >= middle)
                distance[i][k] = std::abs(centres[k].x - (x1 + x2) / 2) / w;
    }
    return distance;
}

Matrix Tracker::same_place(const std::vector<int>& one, const std::vector<int>& two) const {
    const double inf = std::numeric_limits<double>::infinity();
    std::vector<cv::Point2d> c1, c2;
    std::vector<cv::Vec2d> s1, s2;
    points(one, c1, s1);
    points(two, c2, s2);
    Matrix distance(one.size(), std::vector<double>(two.size(), inf));
    for (size_t i = 0; i < one.size(); ++i)
        for (size_t j = 0; j < two.size(); ++j)
            if (c2[j].y >= s1[i][0] && c2[j].y <= s1[i][1] && s2[j][0] <= c1[i].y && s2[j][1] >= c1[i].y)
                distance[i][j] = std::abs(c2[j].x - c1[i].x) / width();
    return distance;
}

std::vector<char> Tracker::in_view(const std::vector<cv::Point2d>& centres, double margin) const {
    std::vector<char> out(centres.size());
    for (size_t k = 0; k < centres.size(); ++k)
        out[k] = centres[k].x >= -margin && centres[k].x < size.width + margin && centres[k].y >= -margin &&
                 centres[k].y < size.height + margin;
    return out;
}

Quad Tracker::local_quad(const Box& box, int anchor) const {
    return project(graph.poses[anchor].inv() * H(), box_corners(box));
}

Quad Tracker::frame_quad() const { return project(H(), corners(size)); }

bool Tracker::cut(const Box& b) const { return !completed(b); }

bool Tracker::traced(int number) {
    static const std::pair<int, int> range = [] {
        const char* env = std::getenv("SHELFREID_TRACE_FRAMES");
        int from = 1, to = 0;
        if (env) std::sscanf(env, "%d-%d", &from, &to);
        return std::make_pair(from, to);
    }();
    return number >= range.first && number <= range.second;
}

bool Tracker::whole(const Box& b) const {
    const double margin = cfg.edge_margin * size.width;
    return b[0] >= margin && b[1] >= margin && b[2] <= size.width - margin && b[3] <= size.height - margin;
}

std::optional<Box> Tracker::completed(const Box& b) const {
    const double margin = cfg.edge_margin * size.width;
    if (b[0] < margin || b[2] > size.width - margin || b[3] > size.height - margin) return std::nullopt;
    if (b[1] >= margin) return b;
    if (!bottle_height || b[3] - b[1] < cfg.min_visible * *bottle_height) return std::nullopt;
    Box whole = b;
    whole[1] = std::min(b[1], b[3] - *bottle_height);
    return whole;
}

std::optional<double> Tracker::running(std::optional<double> value, std::vector<double> samples, double q) const {
    if (samples.size() < 3) return value;
    const double sample = percentile(std::move(samples), q);
    if (!value) return sample;
    return (1 - cfg.height_rate) * *value + cfg.height_rate * sample;
}

std::vector<Detection> Tracker::whole_bottles(const std::vector<Detection>& input) {
    const double margin = cfg.edge_margin * size.width;
    std::vector<Detection> dets;
    for (const auto& d : input)
        if (margin <= d.box[0] && d.box[2] <= size.width - margin) dets.push_back(d);
    dropped += static_cast<int>(input.size() - dets.size());
    std::vector<double> heights;
    for (const auto& d : dets)
        if (d.box[1] > margin && d.box[3] < size.height - margin) heights.push_back(d.box[3] - d.box[1]);
    bottle_height = running(bottle_height, heights, 75);
    if (!bottle_height || dets.empty()) return dets;
    // Rows by the bottom edge.
    std::vector<int> order(dets.size());
    std::iota(order.begin(), order.end(), 0);
    std::stable_sort(order.begin(), order.end(), [&](int a, int b) { return dets[a].box[3] < dets[b].box[3]; });
    std::vector<std::vector<int>> rows;
    for (int i : order) {
        if (!rows.empty() && dets[i].box[3] - dets[rows.back().back()].box[3] <= cfg.row_gap * *bottle_height)
            rows.back().push_back(i);
        else
            rows.push_back({i});
    }
    std::vector<Detection> kept;
    for (const auto& row : rows) {
        std::vector<double> hs;
        for (int i : row) hs.push_back(dets[i].box[3] - dets[i].box[1]);
        double reference = *bottle_height;
        if (row.size() > 1) {
            reference = percentile(hs, 75);
            if (reference < cfg.min_row_height * *bottle_height) continue;
        }
        for (size_t q = 0; q < row.size(); ++q)
            if (hs[q] >= cfg.min_height * reference) kept.push_back(dets[row[q]]);
    }
    std::vector<double> widths;
    for (const auto& d : kept)
        if (d.box[0] > margin && d.box[2] < size.width - margin) widths.push_back(d.width());
    bottle_width = running(bottle_width, widths, 50);
    if (bottle_width) {
        std::vector<Detection> narrow;
        for (const auto& d : kept)
            if (d.width() >= cfg.min_width * *bottle_width || d.box[0] <= margin || d.box[2] >= size.width - margin)
                narrow.push_back(d);
        kept.swap(narrow);
    }
    {
        std::vector<Detection> front;
        for (const auto& d : kept) {
            double covered = 0;
            for (const auto& o : kept) {
                if (&o == &d || o.width() <= d.width()) continue;
                const double across = std::min(d.box[2], o.box[2]) - std::max(d.box[0], o.box[0]);
                const double up = std::min(d.box[3], o.box[3]) - std::max(d.box[1], o.box[1]);
                if (across > 0 && up >= 0.5 * std::min(d.box[3] - d.box[1], o.box[3] - o.box[1])) covered += across;
            }
            if (covered < cfg.peek_overlap * d.width()) front.push_back(d);
        }
        kept.swap(front);
    }
    std::stable_sort(kept.begin(), kept.end(), [](const Detection& a, const Detection& b) { return a.score > b.score; });
    std::vector<Detection> unique;
    for (const auto& det : kept) {
        const double height = det.box[3] - det.box[1];
        bool dup = false;
        for (const auto& u : unique) {
            if (std::min(det.box[2], u.box[2]) - std::max(det.box[0], u.box[0]) >=
                    cfg.duplicate_overlap * std::min(det.width(), u.width()) &&
                std::min(det.box[3], u.box[3]) - std::max(det.box[1], u.box[1]) >=
                    0.5 * std::max(height, u.box[3] - u.box[1])) {
                dup = true;
                break;
            }
        }
        if (!dup) unique.push_back(det);
    }
    dropped += static_cast<int>(dets.size() - unique.size());
    return unique;
}

cv::Mat Tracker::gray_of(const cv::Mat& frame) const {
    cv::Mat small, gray;
    cv::resize(frame, small, cv::Size(), cfg.flow_scale, cfg.flow_scale, cv::INTER_AREA);
    if (small.channels() == 3) cv::cvtColor(small, gray, cv::COLOR_BGR2GRAY);
    else gray = small;
    return gray;
}

std::optional<Mat3> Tracker::flow(const cv::Mat& gray_prev, const cv::Mat& gray, const std::vector<Box>& boxes_prev,
                                  const std::optional<Mat3>& hint) const {
    const double s = cfg.flow_scale;
    cv::Mat mask = cv::Mat::zeros(gray_prev.size(), CV_8U);
    for (const auto& b : boxes_prev) {
        const int x1 = std::max(0, static_cast<int>(b[0] * s)), y1 = std::max(0, static_cast<int>(b[1] * s));
        const int x2 = std::min(mask.cols, static_cast<int>(b[2] * s)), y2 = std::min(mask.rows, static_cast<int>(b[3] * s));
        if (x2 > x1 && y2 > y1) mask(cv::Rect(x1, y1, x2 - x1, y2 - y1)).setTo(255);
    }
    std::vector<cv::Point2f> pts;
    if (cv::countNonZero(mask) > 0) cv::goodFeaturesToTrack(gray_prev, pts, cfg.max_corners, 0.01, 7, mask);
    if (static_cast<int>(pts.size()) < cfg.min_flow_points)
        cv::goodFeaturesToTrack(gray_prev, pts, cfg.max_corners, 0.01, 7);
    if (static_cast<int>(pts.size()) < cfg.min_flow_points) {
        flow_failure = "corners " + std::to_string(pts.size());
        return std::nullopt;
    }
    const cv::TermCriteria criteria(cv::TermCriteria::EPS | cv::TermCriteria::COUNT, 30, 0.01);
    std::vector<cv::Point2f> moved, back;
    std::vector<uchar> status, status_back;
    std::vector<float> err;
    int flags = 0;
    if (hint) {
        // Each point starts where the frame-by-frame motion puts it; the way back starts at the
        // point itself.
        const Mat3 S(s, 0, 0, 0, s, 0, 0, 0, 1);
        const Mat3 forward = S * hint->inv() * S.inv();   // previous -> current, at the flow's scale
        cv::perspectiveTransform(pts, moved, cv::Mat(forward));
        back = pts;
        flags = cv::OPTFLOW_USE_INITIAL_FLOW;
    }
    cv::calcOpticalFlowPyrLK(gray_prev, gray, pts, moved, status, err, cv::Size(21, 21), 4, criteria, flags);
    cv::calcOpticalFlowPyrLK(gray, gray_prev, moved, back, status_back, err, cv::Size(21, 21), 4, criteria, flags);
    std::vector<cv::Point2f> from, to;
    for (size_t i = 0; i < pts.size(); ++i)
        if (status[i] && status_back[i] && cv::norm(back[i] - pts[i]) < 1.0) {
            from.push_back(moved[i]);
            to.push_back(pts[i]);
        }
    if (static_cast<int>(from.size()) < cfg.min_flow_points) {
        flow_failure = "tracked " + std::to_string(from.size()) + " of " + std::to_string(pts.size());
        return std::nullopt;
    }
    std::vector<uchar> inliers;
    cv::Mat Hm = cv::findHomography(from, to, cv::USAC_MAGSAC, 2.0, inliers);
    if (Hm.empty() || cv::countNonZero(inliers) < cfg.min_flow_points) {
        flow_failure = "homography inliers " + std::to_string(Hm.empty() ? 0 : cv::countNonZero(inliers)) + " of " +
                       std::to_string(from.size());
        return std::nullopt;
    }
    Mat3 Hs;
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) Hs(i, j) = Hm.at<double>(i, j);
    const Mat3 S(s, 0, 0, 0, s, 0, 0, 0, 1);
    const Mat3 Hf = normalized(S.inv() * Hs * S);
    if (const auto why = check(Hf, size, cfg.homography)) {
        flow_failure = "implausible: " + *why;
        return std::nullopt;
    }
    flow_failure.clear();
    return Hf;
}

Registration Tracker::register_points(const std::vector<cv::Point2f>& points_k,
                                      const std::vector<cv::Point2f>& points_f, double area_f) const {
    return estimate(points_k, points_f, size, size, cfg.homography, area_f);
}

FrameFeatures Tracker::features_of(const cv::Mat& frame, const std::vector<Detection>& detections) const {
    std::vector<Box> boxes;
    for (const auto& d : detections) boxes.push_back(d.box);
    return extract(frame, cfg.features, boxes_mask(size, boxes));
}

std::optional<Good> Tracker::register_to(const FrameFeatures& features, int index) const {
    std::vector<cv::Point2f> pk, pf;
    match(keyframes[index].features, features, cfg.features, pk, pf);
    const Registration r = register_points(pk, pf, features.area);
    if (std::getenv("SHELFREID_TRACE_REG"))
        std::cerr << "register to keyframe " << index << ": " << features.points.size() << " points, " << r.matches
                  << " matches, " << r.inliers << " inliers, coverage " << r.coverage << (r.ok ? "" : ", " + r.reason) << "\n";
#ifdef __ANDROID__
    if (lost)   // why the tracker does not find its place again, in the phone's log
        __android_log_print(ANDROID_LOG_INFO, "shelfreid", "relocalize to keyframe %d: %zu points (keyframe %zu), %d matches, %d inliers, coverage %.2f%s%s",
                            index, features.points.size(), keyframes[index].features.points.size(), r.matches, r.inliers, r.coverage,
                            r.ok ? "" : ", ", r.reason.c_str());
#endif
    if (!(r.ok && r.inliers >= cfg.min_loop_inliers && r.coverage >= cfg.min_loop_coverage)) return std::nullopt;
    // Strong: many inliers, or fewer (a bottle or two in view) that are nearly all the matches.
    const bool strong = (r.inliers >= cfg.strong_inliers || r.inliers >= cfg.strong_ratio * r.matches) &&
                        r.coverage >= cfg.strong_coverage;
    return Good{index, r.H, strong, r.inliers, std::move(pk), std::move(pf)};
}

bool Tracker::agrees(const Good& g, int frame_ref, const Mat3& frame_P, int step, const std::map<int, int>& seen) const {
    if (frame_ref == kNone) return true;
    const Mat3 flow = graph.poses[g.index].inv() * graph.poses[frame_ref] * frame_P;   // the frame -> keyframe, by the flow
    const Mat3 between = flow.inv() * g.R;                                             // the frame -> itself
    const double bottle = bottle_width.value_or(0.1 * size.width);
    double moved = 0;
    for (double at : {0.25, 0.5, 0.75}) {
        const cv::Point2d p(at * size.width, 0.5 * size.height);
        moved = std::max(moved, cv::norm(project(between, p) - p));
    }
    if (moved <= cfg.alias_tolerance * bottle) return true;
    const auto v = seen.find(g.index);
    if (g.index == frame_ref || (v != seen.end() && step - v->second <= cfg.trust_steps)) return false;
    int by_flow = 0, by_registration = 0;
    const double reach = cfg.alias_support * bottle;
    for (size_t i = 0; i < g.frame_points.size(); ++i) {
        const cv::Point2d f(g.frame_points[i].x, g.frame_points[i].y), k(g.keyframe_points[i].x, g.keyframe_points[i].y);
        by_flow += cv::norm(project(flow, f) - k) < reach;
        by_registration += cv::norm(project(g.R, f) - k) < reach;
    }
    return by_flow < cfg.alias_ambiguity * by_registration;
}

std::vector<Good> Tracker::registrations(const FrameFeatures& features, const std::vector<int>& candidates) {
    std::vector<Good> good;
    for (int index : candidates)
        if (auto g = register_to(features, index)) {
            good.push_back(*g);
            verified[index] = count;
        }
    return good;
}

void Tracker::relocalize(int number, const FrameFeatures& features) {
    const Quad quad = frame_quad();
    const cv::Point2d middle = centre(quad);
    const double w = cv::norm(quad[1] - quad[0]);
    std::vector<std::pair<double, int>> candidates;
    for (int index = 0; index < static_cast<int>(keyframes.size()); ++index) {
        const Quad other = keyframe_quad(index);
        if (cv::norm(centre(other) - middle) <= cfg.search_radius * w)
            candidates.emplace_back(shared(quad, other), index);
    }
    std::sort(candidates.begin(), candidates.end(), std::greater<>());
    std::vector<int> order;
    for (size_t q = 0; q < candidates.size() && static_cast<int>(q) < cfg.loop_candidates; ++q)
        order.push_back(candidates[q].second);
    int added = 0;
    for (int k : wanted) {
        if (added >= cfg.loop_candidates) break;
        if (std::find(order.begin(), order.end(), k) == order.end()) order.push_back(k), ++added;
    }
    wanted.clear();
    const auto seen = verified;
    std::vector<Good> good = registrations(features, order);
    for (auto g = good.begin(); g != good.end();) {
        if (agrees(*g, ref, P, count, seen)) {
            ++g;
            continue;
        }
        ++aliased;
        if (seen.count(g->index)) verified[g->index] = seen.at(g->index);
        else verified.erase(g->index);
        g = good.erase(g);
    }
    if (good.empty()) return;
    const Good best = *std::max_element(good.begin(), good.end(),
                                        [](const Good& a, const Good& b) { return a.inliers < b.inliers; });
    std::vector<std::pair<Edge, bool>> edges;
    for (const auto& g : good)
        if (g.index != best.index) {
            const Mat3 T = g.R * best.R.inv();
            edges.push_back({Edge{g.index, best.index, normalized(T), cfg.loop_weight, "loop"}, g.strong && best.strong});
        }
    const bool ref_registered = std::any_of(good.begin(), good.end(), [&](const Good& g) { return g.index == ref; });
    if (!ref_registered && count - anchored <= cfg.fresh_steps) {
        const Mat3 T = best.R * P.inv();
        edges.push_back({Edge{best.index, ref, normalized(T), cfg.chain_weight, "chain"}, best.strong});
    }
    double worst = 0.0;
    for (const auto& [edge, strong] : edges) {
        const double e = graph.error(edge) / size.width;
        if (e > cfg.max_jump || (e > cfg.small_correction && !strong)) continue;
        graph.replace(edge);
        worst = std::max(worst, e);
    }
    ref = best.index;
    P = best.R;
    anchored = localized = count;
    if (worst * size.width > cfg.optimize_above) {
        dropped_edges += std::get<2>(graph.optimize_robust());
        merge_duplicates();
    }
}

int Tracker::merge_duplicates() {
    std::vector<cv::Point2d> centres;
    std::vector<cv::Vec2d> spans;
    points({}, centres, spans);
    const auto view = in_view(centres);
    std::vector<int> seen;
    for (size_t k = 0; k < bottles.size(); ++k)
        if (view[k]) seen.push_back(static_cast<int>(k));
    if (seen.size() < 2) return 0;
    const Matrix distance = same_place(seen, seen);
    std::vector<std::tuple<double, int, int>> pairs;
    for (size_t a = 0; a < seen.size(); ++a)
        for (size_t b = 0; b < seen.size(); ++b) {
            const Bottle& one = bottles[seen[a]];
            const Bottle& two = bottles[seen[b]];
            if (one.id < two.id && distance[a][b] <= cfg.merge_distance && two.first_step > one.last_seen &&
                place_confirmed(one))
                pairs.emplace_back(distance[a][b], static_cast<int>(a), static_cast<int>(b));
        }
    std::sort(pairs.begin(), pairs.end());
    std::set<int> gone;
    for (const auto& [d, a, b] : pairs) {
        Bottle& one = bottles[seen[a]];
        const Bottle& two = bottles[seen[b]];
        if (gone.count(one.id) || gone.count(two.id)) continue;
        absorb(one, two);
        rename(two.id, one.id, "duplicate after relocalisation");
        gone.insert(two.id);
    }
    bottles.erase(std::remove_if(bottles.begin(), bottles.end(), [&](const Bottle& b) { return gone.count(b.id) > 0; }),
                  bottles.end());
    return static_cast<int>(gone.size());
}

void Tracker::absorb(Bottle& earlier, const Bottle& later) {
    if (later.last_seen > earlier.last_seen) {
        if (earlier.left || count - earlier.last_seen > cfg.track_gap) earlier.appearance += 1;
        earlier.left = later.left;
        earlier.last_seen = later.last_seen;
    }
}

bool Tracker::richer(const FrameFeatures& f) const {
    if (ref == kNone || !trusted) return false;
    const double have = static_cast<double>(keyframes[ref].features.points.size()), now = static_cast<double>(f.points.size());
    // A keyframe too poor to register to (a registration needs min_loop_inliers of its points).
    return have < 2.0 * cfg.min_loop_inliers && now >= cfg.richer_ratio * have && now >= have + cfg.richer_points;
}

bool Tracker::needs_keyframe() const {
    if (keyframes.empty()) return true;
    if (!trusted) return false;
    const Quad quad = frame_quad();
    double most = 0.0;
    for (int k = 0; k < static_cast<int>(keyframes.size()); ++k) most = std::max(most, shared(quad, keyframe_quad(k)));
    return most < cfg.keyframe_overlap;
}

void Tracker::add_keyframe(int number, const FrameFeatures& features) {
    Mat3 T = P;
    double weight = cfg.chain_weight;
    std::string kind = "chain";
    if (ref != kNone) {
        const auto seen = verified;
        const auto good = registrations(features, {ref});
        if (!good.empty() && agrees(good[0], ref, P, count, seen)) T = good[0].R, weight = cfg.loop_weight, kind = "odometry";
        else if (!good.empty()) ++aliased;
    }
    const Mat3 pose = ref == kNone ? T : graph.poses[ref] * T;
    const int index = graph.add(pose);
    keyframes.push_back(Keyframe{number, count, features});
    if (ref != kNone) graph.connect(ref, index, T, weight, kind);
    ref = index;
    P = Mat3::eye();
    anchored = count;
    verified[index] = count;
}

void Tracker::jump() {
    lost = true;
    lost_steps = 0;
    ++jumps;
    anchored = localized = kNever;
    verified.clear();
    wanted.clear();
    need_registration = false;
    for (auto& b : bottles) b.left = true;
}

void Tracker::find(int number, const FrameFeatures& features) {
    const auto saved = verified;
    std::vector<int> all(keyframes.size());
    std::iota(all.begin(), all.end(), 0);
    std::vector<Good> good;
    for (const auto& g : registrations(features, all))
        if (g.strong) good.push_back(g);
    if (!good.empty()) {
        const Good best = *std::max_element(good.begin(), good.end(),
                                            [](const Good& a, const Good& b) { return a.inliers < b.inliers; });
        ref = best.index;
        P = best.R;
        anchored = localized = count;
        lost = false;
        ++found;
        return;
    }
    verified = saved;
    // A map with no bottle on it yet holds nothing to keep in place: it starts again here.
    if ((++lost_steps > cfg.max_wait && cfg.new_ground) || bottles.empty()) {
        double far_right = -1e300;
        for (int k = 0; k < static_cast<int>(keyframes.size()); ++k)
            for (const auto& p : keyframe_quad(k)) far_right = std::max(far_right, p.x);
        const int index = graph.add(Mat3(1, 0, far_right + size.width, 0, 1, 0, 0, 0, 1));
        keyframes.push_back(Keyframe{number, count, features});
        ref = index;
        P = Mat3::eye();
        anchored = localized = count;
        verified[index] = count;
        lost = false;
        ++new_grounds;
    }
}

bool Tracker::near_old_keyframe() const {
    const Quad quad = frame_quad();
    const cv::Point2d middle = centre(quad);
    const double w = cv::norm(quad[1] - quad[0]);
    for (int k = 0; k < static_cast<int>(keyframes.size()); ++k)
        if (count - keyframes[k].step > cfg.recent_steps && cv::norm(centre(keyframe_quad(k)) - middle) <= cfg.search_radius * w)
            return true;
    return false;
}

bool Tracker::trust() {
    if (lost) return false;
    if (count - localized <= cfg.trust_steps || !near_old_keyframe()) {
        untrusted = 0;
        return true;
    }
    ++untrusted;
    // Near the map but not registered to it: the flow is not trusted until a registration, or,
    // with cfg.new_ground, until max_wait steps have passed.
    return cfg.new_ground && untrusted > cfg.max_wait;
}

void Tracker::observe(Bottle& bottle, const Box& box) {
    const double weight = 1.0 / (bottle.hits + 1);
    const Quad local = local_quad(box, bottle.anchor);
    for (int c = 0; c < 4; ++c) bottle.quad[c] = (1 - weight) * bottle.quad[c] + weight * local[c];
    bottle.hits += 1;
}

int Tracker::index_of(int bottle_id) const {
    for (size_t k = 0; k < bottles.size(); ++k)
        if (bottles[k].id == bottle_id) return static_cast<int>(k);
    return kNone;
}

std::vector<Shown> Tracker::step(int number, const cv::Mat& frame, std::vector<Detection> detections) {
    const cv::Mat gray = gray_of(frame);
    std::vector<Detection> scored;
    for (const auto& d : detections)
        if (d.score >= cfg.min_score) scored.push_back(d);
    detections = whole_bottles(scored);
    if (previous) {
        auto step_H = flow(previous->first, gray, previous->second, motion_hint);
        if (!step_H && motion_hint) {
            step_H = motion_hint;   // the picture moved continuously: no jump
            ++hinted;
            flow_failure += " (the motion hint stood in)";
        }
        if (!step_H) {
            ++lost_motion;
            jump();
        } else {
            P = P * *step_H;
            M = M * *step_H;
        }
    }
    std::optional<FrameFeatures> features;
    if (keyframes.empty()) {
        features = features_of(frame, detections);
        add_keyframe(number, *features);
    } else if (lost) {
        features = features_of(frame, detections);
        find(number, *features);
    } else if (count % cfg.reloc_every == 0 || !trusted || need_registration) {
        need_registration = false;
        features = features_of(frame, detections);
        relocalize(number, *features);
    }
    std::vector<Box> boxes;
    for (const auto& d : detections) boxes.push_back(d.box);
    const auto descriptors = box_descriptors(features ? &*features : nullptr, boxes);
    votes = lost ? std::map<int, Votes>{} : label_votes(descriptors, boxes);
    trusted = trust();
    std::vector<Shown> shown = associate(number, detections, trusted);
    learn_labels(shown, descriptors);
    if (needs_keyframe() || (features && richer(*features))) add_keyframe(number, features ? *features : features_of(frame, detections));
    previous = std::make_pair(gray, boxes);
    ++count;
    motion_hint.reset();
    return shown;
}

std::vector<Detection> clean_bottles(const std::vector<Detection>& detections, double min_score, double max_aspect,
                                     double min_aspect, double contained) {
    std::vector<Detection> candidates;
    for (const auto& d : detections) {
        const double h = d.box[3] - d.box[1];
        if (d.score >= min_score && min_aspect * h <= d.width() && d.width() <= max_aspect * h) candidates.push_back(d);
    }
    std::stable_sort(candidates.begin(), candidates.end(), [](const Detection& a, const Detection& b) {
        return a.width() * (a.box[3] - a.box[1]) > b.width() * (b.box[3] - b.box[1]);
    });
    std::vector<Detection> kept;
    for (const auto& det : candidates) {
        const auto& [x1, y1, x2, y2] = det.box;
        const double a = (x2 - x1) * (y2 - y1);
        bool inside = false;
        for (const auto& other : kept) {
            const double ix = std::max(0.0, std::min(x2, other.box[2]) - std::max(x1, other.box[0]));
            const double iy = std::max(0.0, std::min(y2, other.box[3]) - std::max(y1, other.box[1]));
            if (ix * iy >= contained * a) {
                inside = true;
                break;
            }
        }
        if (!inside) kept.push_back(det);
    }
    return kept;
}

}  // namespace shelfreid
