#include "shelfreid/realtime.hpp"

#include <algorithm>
#include <chrono>
#include <numeric>

namespace shelfreid {

namespace {
double since(std::chrono::steady_clock::time_point t) {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - t).count();
}
}  // namespace

RealtimeTracker::RealtimeTracker(Size2 size_, StreamConfig cfg_, int latency_)
    : Tracker(size_, cfg_), latency(latency_) {}

std::vector<Shown> RealtimeTracker::step(int number, const cv::Mat& frame, std::vector<Detection> detections) {
    const auto started = std::chrono::steady_clock::now();
    const cv::Mat gray = gray_of(frame);
    std::vector<Detection> scored;
    for (const auto& d : detections)
        if (d.score >= cfg.min_score) scored.push_back(d);
    detections = whole_bottles(scored);
    if (previous) {
        const auto step_H = flow(previous->first, gray, previous->second);
        if (!step_H) {
            ++lost_motion;
            jump();
            lost_since = count;
            inflight.reset();   // its frame lies before the jump
        } else {
            P = P * *step_H;
            M = M * *step_H;
        }
    }
    if (keyframes.empty()) add_keyframe(number, features_of(frame, detections));   // the first frame
    land();
    trusted = trust();
    votes.clear();   // the labels are the slow loop's
    const int before = next_id;
    std::vector<Shown> shown = associate(number, detections, trusted);
    for (int id = before; id < next_id; ++id) provisional.insert(id);
    for (auto it = provisional.begin(); it != provisional.end();)
        it = index_of(*it) == kNone ? provisional.erase(it) : std::next(it);
    for (auto& item : shown)
        if (provisional.count(item.bottle)) item.status = "pending";
    std::vector<Box> boxes;
    for (const auto& d : detections) boxes.push_back(d.box);
    previous = std::make_pair(gray, boxes);
    fast_seconds.push_back(since(started));
    if (!inflight && asks() && count - last_slow >= slow_every) {
        last_slow = count;
        Snapshot snap;
        snap.number = number;
        snap.count = count;
        snap.frame = frame;
        snap.detections = detections;
        snap.shown = shown;
        snap.ref = ref;
        snap.P = P;
        snap.M = M;
        snap.anchored = anchored;
        snap.lost = lost;
        snap.trusted = trusted;
        snap.wanted = wanted;
        wanted.clear();
        need_registration = false;
        const auto t = std::chrono::steady_clock::now();
        inflight = slow(snap);
        inflight->seconds = since(t);
        slow_seconds.push_back(inflight->seconds);
    }
    ++count;
    if (latency == 0) land();
    return shown;
}

bool RealtimeTracker::asks() const {
    return lost || !trusted || need_registration || !provisional.empty() || count % cfg.reloc_every == 0 ||
           needs_keyframe();
}

void RealtimeTracker::land() {
    if (!inflight || inflight->due > count) return;
    SlowResult result = std::move(*inflight);
    inflight.reset();
    apply(result);
}

SlowResult RealtimeTracker::slow(const Snapshot& snap) {
    SlowResult result;
    result.due = snap.count + latency;
    result.snap = snap;
    const FrameFeatures features = features_of(snap.frame, snap.detections);
    std::vector<int> order;
    if (snap.lost) {
        order.resize(keyframes.size());
        std::iota(order.begin(), order.end(), 0);
    } else {
        const Quad quad = project(graph.poses[snap.ref] * snap.P, corners(size));
        const cv::Point2d middle = centre(quad);
        const double w = cv::norm(quad[1] - quad[0]);
        std::vector<std::pair<double, int>> candidates;
        for (int k = 0; k < static_cast<int>(keyframes.size()); ++k) {
            const Quad other = keyframe_quad(k);
            if (cv::norm(centre(other) - middle) <= cfg.search_radius * w) candidates.emplace_back(shared(quad, other), k);
        }
        std::sort(candidates.begin(), candidates.end(), std::greater<>());
        for (size_t q = 0; q < candidates.size() && static_cast<int>(q) < cfg.loop_candidates; ++q)
            order.push_back(candidates[q].second);
        int added = 0;
        for (int k : snap.wanted) {
            if (added >= cfg.loop_candidates) break;
            if (std::find(order.begin(), order.end(), k) == order.end()) order.push_back(k), ++added;
        }
    }
    std::vector<Good> good;
    for (int k : order)
        if (auto g = register_to(features, k))
            if (!snap.lost || g->strong) good.push_back(*g);
    for (const auto& g : good) result.good.push_back(g.index);
    std::vector<std::pair<Edge, bool>> edges;
    if (!good.empty()) {
        const Good best = *std::max_element(good.begin(), good.end(),
                                            [](const Good& a, const Good& b) { return a.inliers < b.inliers; });
        result.found = std::make_pair(best.index, best.R);
        if (!snap.lost) {
            for (const auto& g : good)
                if (g.index != best.index) {
                    const Mat3 T = g.R * best.R.inv();
                    edges.push_back({Edge{g.index, best.index, normalized(T), cfg.loop_weight, "loop"}, g.strong && best.strong});
                }
            const bool ref_registered = std::find(result.good.begin(), result.good.end(), snap.ref) != result.good.end();
            if (!ref_registered && snap.count - snap.anchored <= cfg.fresh_steps) {
                const Mat3 T = best.R * snap.P.inv();
                edges.push_back({Edge{best.index, snap.ref, normalized(T), cfg.chain_weight, "chain"}, best.strong});
            }
        }
    } else if (snap.lost) {
        result.new_ground = snap.count - lost_since > cfg.max_wait;
    }
    if (!edges.empty()) {
        PoseGraph copy = graph;
        for (const auto& [edge, strong] : edges) {
            const double e = copy.error(edge) / size.width;
            if (e > cfg.max_jump || (e > cfg.small_correction && !strong)) continue;
            copy.replace(edge);
            result.worst = std::max(result.worst, e);
        }
        if (result.worst * size.width > cfg.optimize_above) {
            dropped_edges += std::get<2>(copy.optimize_robust());
            result.optimised = true;
        }
        result.graph = std::move(copy);
    }
    // The pose of frame t as this result leaves it, for the keyframe and the labels.
    const int saved_ref = ref;
    const Mat3 saved_P = P;
    const bool saved_trusted = trusted;
    ref = result.found ? result.found->first : snap.ref;
    P = result.found ? result.found->second : snap.P;
    trusted = snap.trusted && !snap.lost;
    if (!snap.lost && needs_keyframe()) {
        SlowResult::NewKeyframe kf{features, ref, Mat3::eye(), 0.0, ""};
        if (result.found) {
            kf.T = result.found->second, kf.weight = cfg.loop_weight, kf.kind = "odometry";
        } else if (auto direct = register_to(features, snap.ref)) {
            kf.T = direct->R, kf.weight = cfg.loop_weight, kf.kind = "odometry";
        } else {
            kf.T = snap.P, kf.weight = cfg.chain_weight, kf.kind = "chain";
        }
        result.keyframe = kf;
    }
    if (!snap.lost) slow_labels(snap, features, result);
    ref = saved_ref;
    P = saved_P;
    trusted = saved_trusted;
    if (result.new_ground) result.keyframe = SlowResult::NewKeyframe{features, kNone, Mat3::eye(), 0.0, "new ground"};
    return result;
}

void RealtimeTracker::slow_labels(const Snapshot& snap, const FrameFeatures& features, SlowResult& result) {
    std::vector<Box> boxes;
    for (const auto& d : snap.detections) boxes.push_back(d.box);
    const auto descriptors = box_descriptors(&features, boxes);
    for (size_t i = 0; i < snap.shown.size(); ++i) {
        const int id = snap.shown[i].bottle;
        const int k = id == kNone ? kNone : index_of(id);
        if (k == kNone || descriptors[i].rows == 0 || provisional.count(id)) continue;
        const Bottle& bottle = bottles[k];
        if (bottle.appearance == 1 && static_cast<int>(bottle.label.size()) < cfg.label_views &&
            snap.count - bottle.labelled >= cfg.label_gap)
            result.labels.emplace_back(id, descriptors[i].rowRange(0, std::min(descriptors[i].rows, cfg.label_size)).clone());
    }
    votes = label_votes(descriptors, boxes);
    std::map<int, int> matched;
    for (size_t i = 0; i < snap.shown.size(); ++i) {
        const int id = snap.shown[i].bottle;
        const int k = id == kNone ? kNone : index_of(id);
        if (k != kNone && !provisional.count(id)) matched[static_cast<int>(i)] = k;
    }
    const std::map<int, int> before = matched;
    std::vector<cv::Point2d> centres;
    std::vector<cv::Vec2d> spans;
    points({}, centres, spans);
    check_rows(snap.number, boxes, matched, centres, spans);
    votes.clear();
    std::set<int> moved;
    for (const auto& [i, k] : matched) {
        auto b = before.find(i);
        if (b != before.end() && b->second == k) continue;
        const int held_id = b != before.end() ? bottles[b->second].id : snap.shown[i].bottle;
        result.moves.push_back(Move{i, held_id, bottles[k].id});
        moved.insert(held_id);
    }
    for (const auto& s : snap.shown)
        if (provisional.count(s.bottle) && !moved.count(s.bottle)) result.confirmed.insert(s.bottle);
}

void RealtimeTracker::apply(SlowResult& result) {
    const Snapshot& snap = result.snap;
    const Mat3 chain = snap.M.inv() * M;   // the current frame -> frame t
    for (int index : result.good) verified[index] = snap.count;
    if (result.found) {
        if (result.graph) graph = std::move(*result.graph);
        ref = result.found->first;
        P = result.found->second * chain;
        anchored = localized = snap.count;
        if (snap.lost) {
            lost = false;
            ++found;
        }
        if (result.optimised) merge_duplicates();
    }
    if (result.keyframe) {
        const auto& kf = *result.keyframe;
        int index;
        if (kf.kind == "new ground") {
            double far_right = -1e300;
            for (int k = 0; k < static_cast<int>(keyframes.size()); ++k)
                for (const auto& p : keyframe_quad(k)) far_right = std::max(far_right, p.x);
            index = graph.add(Mat3(1, 0, far_right + size.width, 0, 1, 0, 0, 0, 1));
            lost = false;
            ++new_grounds;
        } else {
            index = graph.add(graph.poses[kf.ref] * kf.T);
            graph.connect(kf.ref, index, kf.T, kf.weight, kf.kind);
        }
        keyframes.push_back(Keyframe{snap.number, snap.count, kf.features});
        ref = index;
        P = chain;
        anchored = localized = snap.count;
        verified[index] = snap.count;
    }
    for (auto& [id, descriptors] : result.labels) {
        const int k = index_of(id);
        if (k != kNone && static_cast<int>(bottles[k].label.size()) < cfg.label_views) {
            bottles[k].label.push_back(descriptors);
            bottles[k].labelled = snap.count;
        }
    }
    for (int id : result.confirmed) provisional.erase(id);
    // A provisional bottle that left the view before a slow result saw it stays new.
    for (const auto& b : bottles)
        if (provisional.count(b.id) && b.left && b.first_step <= snap.count) provisional.erase(b.id);
    if (!result.moves.empty()) {
        // Each bottle that a box should carry takes over the track the box had.
        struct Track {
            std::optional<Box> box;
            Mat3 M;
            int seen;
        };
        std::map<int, Track> tracks;
        for (const auto& b : bottles) tracks[b.id] = Track{b.last_box, b.last_M, b.last_seen};
        std::set<int> held_ids, given;
        std::map<int, int> took;
        for (const auto& m : result.moves)
            if (m.held != kNone) held_ids.insert(m.held), took[m.held] = m.target;
        for (const auto& m : result.moves) {
            const int k = index_of(m.target);
            if (k == kNone) continue;
            Bottle& bottle = bottles[k];
            auto t = m.held == kNone ? tracks.end() : tracks.find(m.held);
            if (t != tracks.end() && t->second.box) {
                bottle.last_box = t->second.box;
                bottle.last_M = t->second.M;
                bottle.last_seen = t->second.seen;
            } else {   // the box had no bottle: its box at t
                bottle.last_box = snap.detections[m.box].box;
                bottle.last_M = snap.M;
                bottle.last_seen = snap.count;
            }
            if (bottle.left) {
                bottle.appearance += 1;
                bottle.left = false;
            }
            given.insert(m.target);
        }
        std::set<int> gone;
        for (int held : held_ids) {
            if (given.count(held)) continue;
            const int k = index_of(held);
            if (k == kNone) continue;
            Bottle& bottle = bottles[k];
            bottle.last_box.reset();
            bottle.left = true;
            if (bottle.first_step >= snap.count - cfg.young_steps && index_of(took[held]) != kNone) {
                rename(held, took[held]);
                gone.insert(held);
            }
        }
        if (!gone.empty()) {
            bottles.erase(std::remove_if(bottles.begin(), bottles.end(), [&](const Bottle& b) { return gone.count(b.id) > 0; }),
                          bottles.end());
            merged_young += static_cast<int>(gone.size());
            for (int id : gone) provisional.erase(id);
        }
    }
}

}  // namespace shelfreid
