// The boxes of a frame against the bottles of the map: tracking, rescue, re-identification,
// neighbour habits, the check of the rows by labels, conflicts with the map, new bottles,
// young duplicates.
#include <algorithm>
#include <iostream>
#include <cmath>
#include <functional>
#include <limits>
#include <numeric>


#include "shelfreid/cv.hpp"
#include "shelfreid/tracker.hpp"

namespace shelfreid {

double percentile(std::vector<double> v, double q);

namespace {

std::map<int, int> assign_pool(const Tracker* self, const std::vector<int>& pool, const std::vector<int>& free,
                               double limit, const std::vector<Box>& boxes, const std::vector<cv::Point2d>& centres,
                               const std::vector<cv::Vec2d>& spans,
                               const std::function<Matrix(const std::vector<Box>&, const std::vector<cv::Point2d>&,
                                                          const std::vector<cv::Vec2d>&)>& distance_of) {
    std::map<int, int> out;
    if (pool.empty() || free.empty()) return out;
    std::vector<Box> fb;
    for (int i : free) fb.push_back(boxes[i]);
    std::vector<cv::Point2d> pc;
    std::vector<cv::Vec2d> ps;
    for (int k : pool) pc.push_back(centres[k]), ps.push_back(spans[k]);
    for (const auto& [i, j] : hungarian(distance_of(fb, pc, ps), limit)) out[free[i]] = pool[j];
    (void)self;
    return out;
}

void add_vote(Votes& votes, int k) {
    for (auto& [key, n] : votes)
        if (key == k) {
            ++n;
            return;
        }
    votes.emplace_back(k, 1);
}

int votes_for(const Votes* votes, int k) {
    if (!votes) return 0;
    for (const auto& [key, n] : *votes)
        if (key == k) return n;
    return 0;
}

}  // namespace

std::vector<Shown> Tracker::associate(int number, const std::vector<Detection>& detections, bool trusted_now) {
    std::vector<cv::Point2d> centres;
    std::vector<cv::Vec2d> spans;
    points({}, centres, spans);
    const auto view = in_view(centres);
    std::vector<int> tracked, old, near, unconfirmed;
    for (size_t k = 0; k < bottles.size(); ++k)
        if (view[k] && !bottles[k].left && count - bottles[k].last_seen <= cfg.track_gap)
            tracked.push_back(static_cast<int>(k));
    std::set<int> confirmed;
    for (const auto& [k, step] : verified)
        if (count - step <= cfg.trust_steps) confirmed.insert(k);
    const std::set<int> tracked_set(tracked.begin(), tracked.end());
    for (size_t k = 0; k < bottles.size(); ++k)
        if (view[k] && !tracked_set.count(static_cast<int>(k))) old.push_back(static_cast<int>(k));
    for (int k : old) {
        bool is_near = false;
        for (int c : confirmed)
            if (std::abs(bottles[k].anchor - c) <= cfg.anchor_window) is_near = true;
        (is_near ? near : unconfirmed).push_back(k);
    }
    std::vector<Box> boxes;
    for (const auto& d : detections) boxes.push_back(d.box);
    auto distance_of = [this](const std::vector<Box>& b, const std::vector<cv::Point2d>& c,
                              const std::vector<cv::Vec2d>& s) { return point_distance(b, c, s); };
    auto assign = [&](const std::vector<int>& pool, const std::vector<int>& free, double limit,
                      const std::vector<cv::Point2d>& c, const std::vector<cv::Vec2d>& s) {
        return assign_pool(this, pool, free, limit, boxes, c, s, distance_of);
    };

    std::vector<int> free(detections.size());
    std::iota(free.begin(), free.end(), 0);
    std::vector<cv::Point2d> last_c;
    std::vector<cv::Vec2d> last_s;
    tracked_points(last_c, last_s);
    std::map<int, int> first = assign(tracked, free, cfg.track_distance, last_c, last_s);
    {
        std::vector<int> rest_free, rest_lost;
        std::set<int> taken;
        for (const auto& [i, k] : first) taken.insert(k);
        for (int i : free)
            if (!first.count(i)) rest_free.push_back(i);
        for (int k : tracked)
            if (!taken.count(k)) rest_lost.push_back(k);
        for (const auto& [i, k] : rescue(boxes, rest_free, rest_lost, first, last_c)) first[i] = k;
    }
    const std::map<int, int> by_flow = first;   // for the trace: how each box got its bottle
    // A box with too little of a bottle (cut) is not re-identified: it waits to show more.
    {
        std::vector<int> f;
        for (int i : free)
            if (!first.count(i) && !cut(boxes[i])) f.push_back(i);
        free.swap(f);
    }
    std::map<int, int> second = trusted_now ? assign(near, free, cfg.reid_distance, centres, spans) : std::map<int, int>{};
    std::map<int, int> matched = first;
    for (const auto& [i, k] : second) matched[i] = k;
    {
        std::vector<int> f;
        for (int i : free)
            if (!second.count(i)) f.push_back(i);
        free.swap(f);
    }
    const std::map<int, int> maybe =
        trusted_now ? assign(unconfirmed, free, cfg.reid_distance, centres, spans) : std::map<int, int>{};
    std::set<int> waiting;
    for (const auto& [i, k] : maybe) {
        waiting.insert(i);
        wanted.insert(bottles[k].anchor);
    }
    waited = waiting.empty() ? 0 : waited + 1;
    if (waited > cfg.max_wait) waiting.clear();
    if (!waiting.empty()) need_registration = true;

    const Neighbours neighbours = neighbours_of(boxes);
    std::map<int, int> ids;
    for (const auto& [i, k] : matched) ids[i] = bottles[k].id;
    auto id_at = [&](int box) { auto it = ids.find(box); return it == ids.end() ? kNone : it->second; };
    // A re-identification that the history of the neighbours contradicts is vetoed.
    for (const auto& [i, k] : second) {
        const auto [l, r] = neighbours[i];
        if (contradicted(ids[i], l == kNone ? kNone : id_at(l), r == kNone ? kNone : id_at(r))) {
            matched.erase(i);
            ids.erase(i);
            ++vetoed;
        }
    }
    // The boxes left over take the habitual neighbours of their neighbours.
    for (int round = 0; round < 3; ++round) {
        std::set<int> taken;
        for (const auto& [i, k] : matched) taken.insert(k);
        bool changed = false;
        for (int i = 0; i < static_cast<int>(detections.size()); ++i) {
            if (matched.count(i) || cut(boxes[i])) continue;
            const auto [l, r] = neighbours[i];
            const int from_left = (l != kNone && ids.count(l)) ? habit(right, ids[l]) : kNone;
            const int from_right = (r != kNone && ids.count(r)) ? habit(left, ids[r]) : kNone;
            if (from_left != kNone && from_right != kNone && from_left != from_right) continue;
            const int suggestion = from_left != kNone ? from_left : from_right;
            const int k = suggestion == kNone ? kNone : index_of(suggestion);
            if (k == kNone || taken.count(k) ||
                std::abs(centres[k].x - (boxes[i][0] + boxes[i][2]) / 2) > cfg.habit_reach * width())
                continue;
            matched[i] = k;
            ids[i] = suggestion;
            taken.insert(k);
            waiting.erase(i);
            ++suggested;
            changed = true;
        }
        if (!changed) break;
    }
    const std::map<int, int> by_habit = matched;
    // Every row is checked against the labels of its boxes; the boxes left free take the
    // released bottles by place.
    const std::set<int> released = lost ? std::set<int>{} : check_rows(number, boxes, matched, centres, spans);
    if (!released.empty()) {
        std::set<int> owned;
        for (const auto& [i, k] : matched) owned.insert(k);
        std::vector<int> f;
        for (int i = 0; i < static_cast<int>(detections.size()); ++i)
            if (!matched.count(i) && !cut(boxes[i])) f.push_back(i);
        std::set<int> pool_set(released.begin(), released.end());
        for (int k : near)
            if (!owned.count(k)) pool_set.insert(k);
        std::vector<int> pool;
        for (int k : pool_set)
            if (!owned.count(k)) pool.push_back(k);
        for (const auto& [i, k] : assign(pool, f, cfg.reid_distance, centres, spans)) matched[i] = k;
        ids.clear();
        for (const auto& [i, k] : matched) ids[i] = bottles[k].id;
        for (const auto& [i, k] : matched) waiting.erase(i);
    }
    const auto [conflict_boxes, closed_boxes] = conflicts_of(boxes, matched, ids, neighbours, centres, spans, view);
    if (traced(number)) {
        std::cerr << "assoc frame " << number << ":";
        for (int i = 0; i < static_cast<int>(boxes.size()); ++i) {
            auto m = matched.find(i);
            const auto same = [&](const std::map<int, int>& stage) { auto s = stage.find(i); return m != matched.end() && s != stage.end() && s->second == m->second; };
            std::cerr << " [" << static_cast<int>(boxes[i][0]) << "-" << static_cast<int>(boxes[i][2]) << "," << static_cast<int>(boxes[i][1])
                      << " " << (m == matched.end() ? std::string("-") : std::to_string(bottles[m->second].id)) << " "
                      << (m == matched.end() ? "free" : same(by_flow) ? "flow" : same(second) ? "place" : same(by_habit) ? "habit" : "rows") << "]";
        }
        std::cerr << "\n";
    }

    std::vector<Shown> shown;
    const size_t count_before = bottles.size();
    for (int i = 0; i < static_cast<int>(detections.size()); ++i) {
        const Detection& det = detections[i];
        // A box cut at the top but showing most of a bottle is completed. A box that starts a
        // bottle keeps off the bottom (bottom_margin): a bottle top above the edge has no label.
        auto made_whole = completed(det.box);
        if (made_whole && det.box[3] > size.height * (1 - cfg.bottom_margin)) made_whole.reset();
        auto m = matched.find(i);
        if (m != matched.end()) {
            Bottle& bottle = bottles[m->second];
            if (bottle.left) {
                bottle.appearance += 1;
                bottle.left = false;
            }
            bottle.last_seen = count;
            bottle.last_box = boxes[i];
            bottle.last_M = M;
            if (whole(det.box) && bottle.hits < cfg.settle_hits) observe(bottle, det.box);
            shown.push_back(Shown{det.box, bottle.appearance == 1 ? "new" : "returning", bottle.id});
        } else if (closed_boxes.count(i)) {
            shown.push_back(Shown{det.box, "ignored", kNone});
        } else if (made_whole && det.score >= cfg.new_score &&
                   (!trusted_now || waiting.count(i) || conflict_boxes.count(i))) {
            shown.push_back(Shown{det.box, "pending", kNone});
        } else if (made_whole && det.score >= cfg.new_score) {
            Bottle bottle;
            bottle.id = next_id++;
            bottle.anchor = ref;
            bottle.quad = project(P, box_corners(*made_whole));
            bottle.first_frame = number;
            bottle.last_seen = count;
            bottle.first_step = count;
            bottle.last_box = det.box;
            bottle.last_M = M;
            bottles.push_back(bottle);
            shown.push_back(Shown{det.box, "new", bottle.id});
        } else {
            shown.push_back(Shown{det.box, "ignored", kNone});
        }
    }
    // A bottle whose centre is now clearly outside the frame has left the view.
    const auto inside = in_view(centres, cfg.leave_margin * width());
    for (size_t k = 0; k < count_before; ++k)
        if (!inside[k]) bottles[k].left = true;
    shown = merge_young(std::move(shown), neighbours);
    for (size_t i = 0; i < neighbours.size(); ++i) {
        const int r = neighbours[i].second;
        const int a = shown[i].bottle, b = r == kNone ? kNone : shown[r].bottle;
        if (a != kNone && b != kNone && a != b) {
            right[a][b] += 1;
            left[b][a] += 1;
        }
    }
    learn_offsets(shown);
    return shown;
}

void Tracker::learn_offsets(const std::vector<Shown>& shown) {
    const double margin = cfg.edge_margin * size.width;
    // A box cut at a side or the bottom is no use (cut()); one cut at the top still has its
    // centre, but not its height.
    auto upright = [&](const Box& b) { return b[1] >= margin; };
    std::vector<size_t> seen;
    std::vector<double> heights, widths;
    for (size_t i = 0; i < shown.size(); ++i) {
        const Box& b = shown[i].box;
        if (shown[i].bottle == kNone || shown[i].status == "ignored" || cut(b)) continue;
        seen.push_back(i);
        widths.push_back(b[2] - b[0]);
        if (upright(b)) heights.push_back(b[3] - b[1]);
    }
    if (seen.empty()) return;
    // The unit: the median height of the boxes not cut at the top, or, close to a shelf where
    // every box is, the median width over the shape of a bottle.
    const double aspect = bottle_width && bottle_height ? std::clamp(*bottle_width / *bottle_height, 0.2, 0.45) : 0.3;
    const double unit = std::max(heights.empty() ? percentile(widths, 50) / aspect : percentile(heights, 50), 1.0);
    for (size_t i : seen) {
        const Box& b = shown[i].box;
        if (!upright(b)) continue;
        Shape& shape = shapes[shown[i].bottle];
        shape.width += (b[2] - b[0]) / unit;
        shape.height += (b[3] - b[1]) / unit;
        ++shape.n;
    }
    for (size_t p = 0; p < seen.size(); ++p)
        for (size_t q = p + 1; q < seen.size(); ++q) {
            const Shown* one = &shown[seen[p]];
            const Shown* two = &shown[seen[q]];
            if (one->bottle == two->bottle) continue;
            if (one->bottle > two->bottle) std::swap(one, two);
            Offset& o = offsets[{one->bottle, two->bottle}];
            o.dx += ((two->box[0] + two->box[2]) - (one->box[0] + one->box[2])) / 2 / unit;
            ++o.n;
            if (upright(one->box) && upright(two->box)) o.dy += (two->box[3] - one->box[3]) / unit, ++o.ny;
        }
}

std::vector<cv::Mat> Tracker::box_descriptors(const FrameFeatures* features, const std::vector<Box>& boxes) const {
    std::vector<cv::Mat> out(boxes.size());
    if (!features || features->descriptors.empty() || features->points.empty()) return out;
    for (size_t i = 0; i < boxes.size(); ++i) {
        if (cut(boxes[i])) continue;
        const auto& [x1, y1, x2, y2] = boxes[i];
        cv::Mat rows;
        for (size_t p = 0; p < features->points.size(); ++p) {
            const auto& pt = features->points[p];
            if (pt.x >= x1 && pt.x <= x2 && pt.y >= y1 && pt.y <= y2) rows.push_back(features->descriptors.row(static_cast<int>(p)));
        }
        out[i] = rows.empty() ? cv::Mat(0, features->descriptors.cols, CV_32F) : rows;
    }
    return out;
}

std::map<int, Votes> Tracker::label_votes(const std::vector<cv::Mat>& descriptors, const std::vector<Box>& boxes) const {
    std::map<int, Votes> out;
    std::vector<int> labelled;
    for (size_t k = 0; k < bottles.size(); ++k)
        if (!bottles[k].label.empty()) labelled.push_back(static_cast<int>(k));
    const bool any = std::any_of(descriptors.begin(), descriptors.end(), [](const cv::Mat& d) { return d.rows > 0; });
    if (labelled.empty() || !any) return out;
    std::vector<cv::Point2d> centres;
    std::vector<cv::Vec2d> spans;
    points({}, centres, spans);
    const double w = width(), height = bottle_height.value_or(0.25 * size.height);
    cv::BFMatcher matcher(cv::NORM_L2);
    for (size_t i = 0; i < descriptors.size(); ++i) {
        const cv::Mat& query = descriptors[i];
        if (query.rows < cfg.label_votes) continue;
        const auto& [x1, y1, x2, y2] = boxes[i];
        std::vector<int> near;
        for (int k : labelled)
            if (std::abs(centres[k].x - (x1 + x2) / 2) <= cfg.label_reach * w &&
                std::abs(centres[k].y - (y1 + y2) / 2) <= 0.5 * height)
                near.push_back(k);
        if (near.empty()) continue;
        cv::Mat train;
        std::vector<int> owner;
        for (int k : near)
            for (const auto& view : bottles[k].label) {
                train.push_back(view);
                owner.insert(owner.end(), view.rows, k);
            }
        std::vector<std::vector<cv::DMatch>> knn;
        matcher.knnMatch(query, train, knn, std::min(8, train.rows));
        Votes votes;
        for (const auto& candidates : knn) {
            if (candidates.empty()) continue;
            const cv::DMatch& best = candidates[0];
            const cv::DMatch* other = nullptr;
            for (size_t q = 1; q < candidates.size(); ++q)
                if (owner[candidates[q].trainIdx] != owner[best.trainIdx]) {
                    other = &candidates[q];
                    break;
                }
            if (!other || best.distance < cfg.label_ratio * other->distance) add_vote(votes, owner[best.trainIdx]);
        }
        out[static_cast<int>(i)] = votes;
    }
    return out;
}

int Tracker::says(const Votes* v) const {
    if (!v || v->empty()) return kNone;
    std::vector<int> ranked;
    int best = kNone, most = -1;
    for (const auto& [k, n] : *v) {
        ranked.push_back(n);
        if (n > most) most = n, best = k;
    }
    std::sort(ranked.begin(), ranked.end(), std::greater<>());
    if (ranked[0] >= cfg.label_votes && (ranked.size() == 1 || ranked[0] >= cfg.label_margin * ranked[1])) return best;
    return kNone;
}

bool Tracker::twins(int a, int b) const {
    const auto& one_v = bottles[a].label;
    const auto& two_v = bottles[b].label;
    if (one_v.empty() || two_v.empty()) return false;
    cv::Mat one, two;
    for (const auto& v : one_v) one.push_back(v);
    for (const auto& v : two_v) two.push_back(v);
    cv::BFMatcher matcher(cv::NORM_L2);
    auto share = [&](const cv::Mat& x, const cv::Mat& y) {
        std::vector<std::vector<cv::DMatch>> knn;
        matcher.knnMatch(x, y, knn, 2);
        int good = 0;
        for (const auto& c : knn)
            if (c.size() == 2 && c[0].distance < cfg.label_ratio * c[1].distance) ++good;
        return good / static_cast<double>(std::max(x.rows, 1));
    };
    return std::min(share(one, two), share(two, one)) >= cfg.label_twins;
}

std::set<int> Tracker::check_rows(int number, const std::vector<Box>& boxes, std::map<int, int>& matched,
                                  const std::vector<cv::Point2d>& centres, const std::vector<cv::Vec2d>& spans) {
    const double w = width(), height = bottle_height.value_or(0.25 * size.height);
    std::map<int, int> said;   // box -> the bottle its label names
    for (const auto& [i, v] : votes)
        if (!cut(boxes[i])) said[i] = says(&v);
    auto says_at = [&](int i) { auto it = said.find(i); return it == said.end() ? kNone : it->second; };
    auto held_at = [&](int i) { auto it = matched.find(i); return it == matched.end() ? kNone : it->second; };
    auto votes_at = [&](int i) -> const Votes* { auto it = votes.find(i); return it == votes.end() ? nullptr : &it->second; };
    for (const auto& [i, k] : matched)
        if (votes.count(i) && !bottles[k].label.empty()) {
            ++label_checks;
            if (says_at(i) == k) ++label_confirmed;
        }
    auto middle = [&](int i) { return cv::Point2d((boxes[i][0] + boxes[i][2]) / 2, (boxes[i][1] + boxes[i][3]) / 2); };
    std::set<int> released;
    auto log = [&](int i, int k, const std::string& outcome) {
        const int held = held_at(i);
        contradictions.push_back(Contradiction{number, i, held == kNone ? kNone : bottles[held].id, bottles[k].id,
                                               votes_for(votes_at(i), k), held == kNone ? 0 : votes_for(votes_at(i), held),
                                               outcome});
    };
    for (const auto& row : rows_of(boxes)) {
        std::map<int, int> named;
        for (int i : row)
            if (says_at(i) != kNone) named[says_at(i)] += 1;
        std::set<int> confirmed, kept;
        for (int i : row)
            if (says_at(i) != kNone && held_at(i) == says_at(i)) confirmed.insert(i), kept.insert(held_at(i));
        std::vector<std::pair<int, int>> anchors;   // box, bottle, in the order of the row
        for (int i : row) {
            const int k = says_at(i), held = held_at(i);
            if (k == kNone || named[k] > 1) continue;
            if (held != kNone && held != k && (bottles[held].label.empty() || twins(held, k))) continue;
            anchors.emplace_back(i, k);
        }
        if (std::all_of(anchors.begin(), anchors.end(), [&](const auto& a) { return held_at(a.first) == a.second; }))
            continue;   // the labels of the row agree with its ids
        std::map<int, cv::Point2d> shifts;
        std::map<int, int> anchor_of;
        for (const auto& [i, k] : anchors) shifts[i] = middle(i) - centres[k], anchor_of[i] = k;
        auto agreeing = [&](int i) {
            std::vector<int> out;
            for (const auto& [i2, k2] : anchors)
                if (std::abs(shifts[i2].x - shifts[i].x) <= cfg.label_tolerance * w &&
                    std::abs(shifts[i2].y - shifts[i].y) <= 0.3 * height)
                    out.push_back(i2);
            return out;
        };
        int best = anchors[0].first;
        std::pair<int, int> best_key{-1, -1};
        for (const auto& [i, k] : anchors) {
            const auto group = agreeing(i);
            int agree = 0;
            for (int j : group)
                if (held_at(j) == anchor_of[j]) ++agree;
            const std::pair<int, int> key{static_cast<int>(group.size()), agree};
            if (key > best_key) best_key = key, best = i;
        }
        const auto group = agreeing(best);
        const std::set<int> group_set(group.begin(), group.end());
        std::vector<int> wrong;
        for (int i : group)
            if (held_at(i) != anchor_of[i]) wrong.push_back(i);
        for (const auto& [i, k] : anchors)
            if (!group_set.count(i) && held_at(i) != k) log(i, k, "outvoted");
        if (wrong.empty()) continue;
        if (static_cast<int>(group.size()) < cfg.label_support) {
            for (int i : wrong) log(i, anchor_of[i], "lone");
            continue;
        }
        std::vector<double> sx, sy;
        for (int i : group) sx.push_back(shifts[i].x), sy.push_back(shifts[i].y);
        const cv::Point2d shift(percentile(sx, 50), percentile(sy, 50));
        std::map<int, int> target;
        for (int i : group) target[i] = anchor_of[i];
        std::set<int> target_bottles, keyframes_of;
        for (const auto& [i, k] : target) target_bottles.insert(k), keyframes_of.insert(bottles[k].anchor);
        std::vector<int> others;
        for (int i : row)
            if (!target.count(i) && !confirmed.count(i) && !cut(boxes[i])) others.push_back(i);
        std::vector<int> pool;
        for (size_t k = 0; k < bottles.size(); ++k) {
            if (target_bottles.count(static_cast<int>(k)) || kept.count(static_cast<int>(k))) continue;
            for (int a : keyframes_of)
                if (std::abs(bottles[k].anchor - a) <= cfg.anchor_window) {
                    pool.push_back(static_cast<int>(k));
                    break;
                }
        }
        if (!others.empty() && !pool.empty()) {
            std::vector<Box> ob;
            for (int i : others) ob.push_back(boxes[i]);
            std::vector<cv::Point2d> pc;
            std::vector<cv::Vec2d> ps;
            for (int k : pool) pc.push_back(centres[k] + shift), ps.push_back(spans[k] + cv::Vec2d(shift.y, shift.y));
            for (const auto& [a, b] : hungarian(point_distance(ob, pc, ps), cfg.reid_distance)) target[others[a]] = pool[b];
        }
        std::set<int> target_values;
        for (const auto& [i, k] : target) target_values.insert(k);
        std::vector<int> changes;
        for (int i : row) {
            auto t = target.find(i);
            if (t == target.end() || held_at(i) == t->second || confirmed.count(i)) continue;
            if (kept.count(t->second) && t->second != held_at(i)) continue;
            changes.push_back(i);
        }
        for (int i : changes) log(i, target[i], cfg.label_fix ? "fixed" : "logged");
        if (!cfg.label_fix) continue;
        std::map<int, int> owner;
        for (const auto& [j, k] : matched) owner[k] = j;
        for (int i : changes) {
            const int k = target[i];
            auto h = owner.find(k);
            if (h != owner.end() && !target.count(h->second)) matched.erase(h->second);   // the box loses its bottle
            const int held = held_at(i);
            if (held != kNone && !target_values.count(held)) released.insert(held);
            matched[i] = k;
            owner[k] = i;
            released.erase(k);
        }
    }
    return released;
}

void Tracker::learn_labels(const std::vector<Shown>& shown, const std::vector<cv::Mat>& descriptors) {
    for (size_t i = 0; i < shown.size(); ++i) {
        const int k = shown[i].bottle == kNone ? kNone : index_of(shown[i].bottle);
        if (k == kNone || descriptors[i].rows == 0) continue;
        Bottle& bottle = bottles[k];
        if (bottle.appearance == 1 && static_cast<int>(bottle.label.size()) < cfg.label_views &&
            count - bottle.labelled >= cfg.label_gap) {
            bottle.label.push_back(descriptors[i].rowRange(0, std::min(descriptors[i].rows, cfg.label_size)).clone());
            bottle.labelled = count;
        }
    }
}

std::pair<std::set<int>, std::set<int>> Tracker::conflicts_of(
    const std::vector<Box>& boxes, const std::map<int, int>& matched, const std::map<int, int>& ids,
    const Neighbours& neighbours, const std::vector<cv::Point2d>& centres, const std::vector<cv::Vec2d>& spans,
    const std::vector<char>& view) {
    std::map<int, int> owner;
    for (const auto& [i, k] : matched) owner[k] = i;
    std::vector<int> free;
    for (int i = 0; i < static_cast<int>(boxes.size()); ++i)
        if (!matched.count(i) && !cut(boxes[i])) free.push_back(i);
    std::set<int> conflict_boxes, closed_boxes;
    auto id_at = [&](int box) { auto it = ids.find(box); return it == ids.end() ? kNone : it->second; };
    for (int i : free) {
        const auto [l, r] = neighbours[i];
        const int li = l == kNone ? kNone : id_at(l), ri = r == kNone ? kNone : id_at(r);
        if (li != kNone && ri != kNone && (habit(right, li) == ri || habit(left, ri) == li)) closed_boxes.insert(i);
    }
    std::vector<int> open;
    for (int i : free)
        if (!closed_boxes.count(i)) open.push_back(i);
    if (!open.empty() && !owner.empty()) {
        std::vector<Box> ob;
        for (int i : open) ob.push_back(boxes[i]);
        const Matrix distance = point_distance(ob, centres, spans);
        for (size_t a = 0; a < open.size(); ++a) {
            const int i = open[a];
            std::vector<int> on;
            for (size_t k = 0; k < centres.size(); ++k)
                if (distance[a][k] <= cfg.reid_distance && view[k]) on.push_back(static_cast<int>(k));
            const auto [l, r] = neighbours[i];
            for (const auto& [table, side] : {std::make_pair(&right, l), std::make_pair(&left, r)}) {
                const int side_id = side == kNone ? kNone : id_at(side);
                const int h = side_id == kNone ? kNone : habit(*table, side_id);
                if (h != kNone) {
                    const int k = index_of(h);
                    if (k != kNone) on.push_back(k);
                }
            }
            for (int k : on) {
                auto o = owner.find(k);
                if (o != owner.end() && o->second != i) {
                    conflict_boxes.insert(i);
                    break;
                }
            }
        }
    }
    conflicted = conflict_boxes.empty() ? 0 : conflicted + 1;
    if (conflicted > cfg.max_wait) conflict_boxes.clear();
    conflicts += static_cast<int>(conflict_boxes.size());
    closed += static_cast<int>(closed_boxes.size());
    return {conflict_boxes, closed_boxes};
}

std::map<int, int> Tracker::rescue(const std::vector<Box>& boxes, const std::vector<int>& free,
                                   const std::vector<int>& lost_ones, const std::map<int, int>& matched,
                                   const std::vector<cv::Point2d>& centres) {
    std::map<int, int> found_now;
    if (free.empty() || lost_ones.empty() || static_cast<int>(matched.size()) < cfg.rescue_support) return found_now;
    const double w = width();
    std::vector<std::pair<int, cv::Point2d>> pairs;
    for (const auto& [i, k] : matched)
        pairs.emplace_back(k, cv::Point2d((boxes[i][0] + boxes[i][2]) / 2, (boxes[i][1] + boxes[i][3]) / 2) - centres[k]);
    const double inf = std::numeric_limits<double>::infinity();
    Matrix distance(free.size(), std::vector<double>(lost_ones.size(), inf));
    for (size_t b = 0; b < lost_ones.size(); ++b) {
        const int k = lost_ones[b];
        std::vector<double> ox, oy;
        for (const auto& [m, offset] : pairs)
            if (cv::norm(centres[m] - centres[k]) <= cfg.rescue_radius * w) ox.push_back(offset.x), oy.push_back(offset.y);
        if (static_cast<int>(ox.size()) < cfg.rescue_support) continue;
        const double x = centres[k].x + percentile(ox, 50), y = centres[k].y + percentile(oy, 50);
        for (size_t a = 0; a < free.size(); ++a) {
            const auto& [x1, y1, x2, y2] = boxes[free[a]];
            const double slack = 0.25 * (y2 - y1);
            if (y1 - slack <= y && y <= y2 + slack) distance[a][b] = std::abs((x1 + x2) / 2 - x) / std::max(x2 - x1, 0.8 * w);
        }
    }
    for (const auto& [a, b] : hungarian(distance, cfg.rescue_distance)) found_now[free[a]] = lost_ones[b];
    rescued += static_cast<int>(found_now.size());
    return found_now;
}

std::vector<Shown> Tracker::merge_young(std::vector<Shown> shown, const Neighbours& neighbours) {
    std::vector<int> young, old;
    for (size_t k = 0; k < bottles.size(); ++k) {
        const int age = count - bottles[k].first_step;
        if (age > 0 && age <= cfg.young_steps) young.push_back(static_cast<int>(k));
        if (age > cfg.young_steps && place_confirmed(bottles[k])) old.push_back(static_cast<int>(k));
    }
    if (young.empty() || old.empty()) return shown;
    std::map<int, int> at;
    for (size_t i = 0; i < shown.size(); ++i)
        if (shown[i].bottle != kNone) at[shown[i].bottle] = static_cast<int>(i);
    auto sides = [&](int bottle_id) -> std::pair<int, int> {
        auto it = at.find(bottle_id);
        if (it == at.end()) return {kNone, kNone};
        const auto [l, r] = neighbours[it->second];
        return {l == kNone ? kNone : shown[l].bottle, r == kNone ? kNone : shown[r].bottle};
    };
    Matrix distance = same_place(young, old);
    std::set<int> detected;
    for (const auto& s : shown)
        if (s.bottle != kNone) detected.insert(s.bottle);
    const double inf = std::numeric_limits<double>::infinity();
    for (size_t i = 0; i < young.size(); ++i)
        for (size_t j = 0; j < old.size(); ++j) {
            const Bottle& a = bottles[young[i]];
            const Bottle& b = bottles[old[j]];
            const auto [sl, sr] = sides(a.id);
            if ((detected.count(a.id) && detected.count(b.id)) || a.first_step <= b.last_seen || contradicted(b.id, sl, sr))
                distance[i][j] = inf;
        }
    std::map<int, int> into;   // young id -> old bottle index
    for (const auto& [i, j] : hungarian(distance, cfg.merge_distance)) into[bottles[young[i]].id] = old[j];
    if (into.empty()) return shown;
    for (auto& item : shown) {
        auto t = into.find(item.bottle);
        if (t == into.end()) continue;
        Bottle& target = bottles[t->second];
        if (target.left || count - target.last_seen > cfg.track_gap) target.appearance += 1;
        target.left = false;
        target.last_seen = count;
        item.bottle = target.id;
        item.status = target.appearance == 1 ? "new" : "returning";
    }
    std::vector<std::pair<int, int>> renames;
    for (const auto& [young_id, k] : into) renames.emplace_back(young_id, bottles[k].id);
    bottles.erase(std::remove_if(bottles.begin(), bottles.end(), [&](const Bottle& b) { return into.count(b.id) > 0; }),
                  bottles.end());
    for (const auto& [young_id, target_id] : renames) rename(young_id, target_id, "young duplicate");
    merged_young += static_cast<int>(into.size());
    return shown;
}

}  // namespace shelfreid
