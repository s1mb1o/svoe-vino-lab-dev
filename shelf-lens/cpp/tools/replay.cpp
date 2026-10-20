// Runs the tracker on a video with cached detections and writes each step as a JSON line, in
// the format of the Python dumps: [frame, [[x1, y1, x2, y2, status, bottle], ...]].
//
//   replay VIDEO|FRAMES_DIR DETS.jsonl sync|rt:N|rt:async OUT.jsonl [--every 3] [--slow-every K] [--pace MS]
//          [--min-score S] [--new-score S] [--max-side PX] [--max-features N] [--loop-candidates N]
//          [--cv-threads N] [--keep-steps 1] [--hints 1] [--map MAP.json] [--planogram PLANOGRAM.json]
//          [--poses POSES.jsonl] [--interrupt FRAME] [--skip FROM-TO]
//
// --interrupt breaks the picture before that frame, as the app does when the camera comes
// back after a pause (rt only): the tracker finds its place on the map again. --skip gives the
// tracker no frame from FROM to TO and breaks the picture at TO: the camera paused and moved
// meanwhile.
//
// --map writes the map at the end: the frame size, each bottle's corners in map coordinates
// (keyframe 0's pixels) and whether it is still provisional; --planogram the planogram of
// that map (planogram.hpp); --poses each step's frame -> map homography and the motion-only
// one: [frame, H (9), M (9), ref].
//
// rt:async runs the slow loop on a thread of its own; --pace makes each step last at least
// MS milliseconds, as frames come from a camera.
//
// FRAMES_DIR holds the frames of the steps as NNNNNN.jpg (frame number): a phone MAY not
// read the video (HEVC with a rotation in the metadata).
#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <cstdlib>
#include <string>
#include <thread>

#include <nlohmann/json.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/videoio.hpp>

#include <opencv2/imgproc.hpp>

#include "shelfreid/motion.hpp"
#include "shelfreid/planogram.hpp"
#include "shelfreid/realtime.hpp"

using namespace shelfreid;

static double pct(std::vector<double> v, double q) {
    if (v.empty()) return 0.0;
    std::sort(v.begin(), v.end());
    const double pos = q / 100.0 * (v.size() - 1);
    const size_t lo = static_cast<size_t>(std::floor(pos)), hi = static_cast<size_t>(std::ceil(pos));
    return v[lo] + (v[hi] - v[lo]) * (pos - lo);
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "usage: replay VIDEO DETS.jsonl sync|rt:N OUT.jsonl [--every 3]\n";
        return 2;
    }
    const std::string video_path = argv[1], dets_path = argv[2], mode = argv[3], out_path = argv[4];
    int every = 3, slow_every = 0, pace_ms = 0;
    double min_score = -1, new_score = -1;
    int max_side = -1, max_features = -1, loop_candidates = -1, cv_threads = -2;
    bool keep_steps = false;   // --every without rescaling the parameters in steps, as the app drops frames
    bool hints = false;        // the frame-by-frame motion as the tracker's hint, as the app gives it
    std::string map_path, planogram_path, poses_path;
    int interrupt_at = -1, skip_from = -1, skip_to = -1;
    for (int a = 5; a + 1 < argc; ++a) {
        if (std::string(argv[a]) == "--skip") {
            const std::string span = argv[a + 1];
            skip_from = std::stoi(span.substr(0, span.find('-')));
            skip_to = interrupt_at = std::stoi(span.substr(span.find('-') + 1));
        }
        if (std::string(argv[a]) == "--every") every = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--slow-every") slow_every = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--pace") pace_ms = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--map") map_path = argv[a + 1];
        if (std::string(argv[a]) == "--planogram") planogram_path = argv[a + 1];
        if (std::string(argv[a]) == "--poses") poses_path = argv[a + 1];
        if (std::string(argv[a]) == "--interrupt") interrupt_at = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--min-score") min_score = std::stod(argv[a + 1]);
        if (std::string(argv[a]) == "--new-score") new_score = std::stod(argv[a + 1]);
        if (std::string(argv[a]) == "--max-side") max_side = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--max-features") max_features = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--loop-candidates") loop_candidates = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--cv-threads") cv_threads = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--keep-steps") keep_steps = std::string(argv[a + 1]) != "0";
        if (std::string(argv[a]) == "--hints") hints = std::string(argv[a + 1]) != "0";
    }

    StreamConfig cfg;
    // Another detector MAY score on another scale: the least score of a box, and of a box
    // that starts a bottle.
    if (min_score >= 0) cfg.min_score = min_score;
    // The cost of the slow loop: the SIFT copy, its features, the keyframes tried.
    if (max_side > 0) cfg.features.max_side = max_side;
    if (max_features > 0) cfg.features.max_features = max_features;
    if (loop_candidates > 0) cfg.loop_candidates = loop_candidates;
    // OpenCV runs one parallel region at a time: while the slow loop's SIFT holds it, the
    // fast loop's parallel calls run serially. The pool size is the knob (1: no pool).
    if (cv_threads > -2) cv::setNumThreads(cv_threads);
    if (new_score >= 0) cfg.new_score = new_score;
    // The parameters in steps are set for every 3rd frame of 30 fps (10 steps a second);
    // a sparser stream scales them to keep their times.
    if (every != 3 && !keep_steps) {
        const double k = 3.0 / every;
        auto scale = [&](int& v) { v = std::max(1, static_cast<int>(std::lround(v * k))); };
        for (int* v : {&cfg.track_gap, &cfg.reloc_every, &cfg.recent_steps, &cfg.fresh_steps, &cfg.trust_steps,
                       &cfg.max_wait, &cfg.young_steps, &cfg.label_gap})
            scale(*v);
    }
    std::map<int, std::vector<Detection>> dets;
    {
        std::ifstream in(dets_path);
        std::string line;
        while (std::getline(in, line)) {
            if (line.empty()) continue;
            const auto row = nlohmann::json::parse(line);
            std::vector<Detection> raw;
            for (const auto& b : row["boxes"])
                raw.push_back(Detection{{b[0].get<double>(), b[1].get<double>(), b[2].get<double>(), b[3].get<double>()},
                                        b[4].get<double>()});
            dets[row["frame"].get<int>()] = clean_bottles(raw, cfg.min_score);
        }
    }
    const bool from_dir = std::filesystem::is_directory(video_path);
    cv::VideoCapture capture;
    auto frame_at = [&](int number, cv::Mat& frame) -> bool {
        if (from_dir) {
            char name[32];
            std::snprintf(name, sizeof(name), "/%06d.jpg", number);
            frame = cv::imread(video_path + name);
            return !frame.empty();
        }
        return capture.read(frame);
    };
    if (!from_dir) {
        capture.open(video_path);
        if (!capture.isOpened()) {
            std::cerr << "cannot open " << video_path << "\n";
            return 1;
        }
    }
    cv::Mat frame;
    if (!frame_at(0, frame)) {
        std::cerr << "no first frame\n";
        return 1;
    }
    const Size2 size{static_cast<double>(frame.cols), static_cast<double>(frame.rows)};
    std::unique_ptr<Tracker> tracker;
    RealtimeTracker* rt = nullptr;
    if (mode == "sync") {
        tracker = std::make_unique<Tracker>(size, cfg);
    } else {
        const int latency = mode == "rt:async" ? -1 : std::stoi(mode.substr(3));
        auto r = std::make_unique<RealtimeTracker>(size, cfg, latency);
        rt = r.get();
        rt->slow_every = slow_every;
        tracker = std::move(r);
    }
    std::ofstream out(out_path);
    std::ofstream poses;
    if (!poses_path.empty()) poses.open(poses_path);
    int number = 0, pending_steps = 0, last_step = -1;
    FrameMotion frame_motion;
    MotionChain chain;
    cv::Mat grey;
    std::vector<double> step_seconds;
    while (true) {
        if (hints && !from_dir) {
            cv::cvtColor(frame, grey, cv::COLOR_BGR2GRAY);
            cv::Matx23d m;
            const bool found = frame_motion.step(grey, 0, m);
            chain.add(number, m, found);
        }
        if (number % every == 0 && !(number >= skip_from && number < skip_to)) {
            auto it = dets.find(number);
            if (it == dets.end()) break;
            if (number > 0 && from_dir && !frame_at(number, frame)) break;
            const auto t = std::chrono::steady_clock::now();
            if (hints && last_step >= 0) tracker->motion_hint = chain.back(last_step, number);
            if (rt && interrupt_at >= 0 && number >= interrupt_at) {
                rt->interrupt();
                tracker->motion_hint.reset();
                interrupt_at = -1;
            }
            last_step = number;
            const auto shown = tracker->step(number, frame, it->second);
            step_seconds.push_back(std::chrono::duration<double>(std::chrono::steady_clock::now() - t).count());
            if (std::getenv("SHELFREID_TRACE")) {
                // One line a step: the state of localisation, for finding where a shot breaks.
                const Tracker& tr = *tracker;
                std::cerr << "step " << tr.count - 1 << " frame " << number << " t " << number / 30.0 << "s lost " << tr.lost
                          << " trusted " << tr.trusted << " ref " << tr.ref << " kf " << tr.keyframes.size() << " jumps "
                          << tr.jumps << " lost_motion " << tr.lost_motion << " found " << tr.found << " new_grounds "
                          << tr.new_grounds << " hinted " << tr.hinted << " bottles " << tr.bottles.size() << " ids " << tr.next_id << " boxes "
                          << it->second.size() << (tr.flow_failure.empty() ? "" : " flow: " + tr.flow_failure) << "\n";
            }
            if (pace_ms > 0) std::this_thread::sleep_until(t + std::chrono::milliseconds(pace_ms));
            nlohmann::json boxes = nlohmann::json::array();
            bool pending = false;
            for (const auto& s : shown) {
                nlohmann::json item = nlohmann::json::array();
                for (double v : s.box) item.push_back(static_cast<long>(std::nearbyint(v)));   // as Python round()
                item.push_back(s.status);
                if (s.bottle == kNone) item.push_back(nullptr);
                else item.push_back(s.bottle);
                boxes.push_back(item);
                pending |= s.status == "pending";
            }
            pending_steps += pending;
            out << nlohmann::json::array({number, boxes}).dump() << "\n";
            if (poses.is_open()) {
                const Mat3 h = tracker->H(), m = tracker->M;
                nlohmann::json row = nlohmann::json::array({number});
                nlohmann::json hj = nlohmann::json::array(), mj = nlohmann::json::array();
                for (int k = 0; k < 9; ++k) hj.push_back(h.val[k]), mj.push_back(m.val[k]);
                row.push_back(hj);
                row.push_back(mj);
                row.push_back(tracker->ref);
                poses << row.dump() << "\n";
            }
        }
        ++number;
        if (!from_dir && !capture.read(frame)) break;
    }
    std::cout << mode << " bottles " << tracker->bottles.size() << " ids " << tracker->next_id << " white steps "
              << pending_steps << " jumps " << tracker->jumps << " found " << tracker->found << " merged young "
              << tracker->merged_young << " aliased " << tracker->aliased << " forgotten " << tracker->forgotten << " | step p50 " << pct(step_seconds, 50) * 1000 << " p95 " << pct(step_seconds, 95) * 1000
              << " ms";
    if (rt)
        std::cout << " | fast p50 " << pct(rt->fast_seconds, 50) * 1000 << " p95 " << pct(rt->fast_seconds, 95) * 1000
                  << " ms; slow jobs " << rt->slow_seconds.size() << " p50 " << pct(rt->slow_seconds, 50) * 1000 << " p95 "
                  << pct(rt->slow_seconds, 95) * 1000 << " ms; landed after p50 "
                  << pct(std::vector<double>(rt->landed_after.begin(), rt->landed_after.end()), 50) << " p95 "
                  << pct(std::vector<double>(rt->landed_after.begin(), rt->landed_after.end()), 95) << " steps";
        if (std::getenv("SHELFREID_PROFILE")) {
            const double jobs = static_cast<double>(rt->slow_seconds.size());
            for (const auto& [part, total] : rt->slow_profile)
                std::cout << "  slow " << part << ": " << (part == "registrations" ? total / jobs : total / jobs * 1000)
                          << (part == "registrations" ? " a job" : " ms a job") << "\n";
        }
    std::cout << std::endl;
    if (!map_path.empty()) {
        nlohmann::json bottles = nlohmann::json::array();
        for (const auto& p : tracker->placed()) {
            nlohmann::json quad = nlohmann::json::array();
            for (const auto& c : p.quad) quad.push_back({std::round(c.x * 10) / 10, std::round(c.y * 10) / 10});
            bottles.push_back({{"id", p.id}, {"quad", quad}, {"hits", p.hits}, {"first_frame", p.first_frame},
                               {"provisional", rt && rt->provisional.count(p.id) > 0}});
        }
        std::ofstream(map_path) << nlohmann::json{{"width", size.width}, {"height", size.height},
                                                  {"keyframes", tracker->keyframes.size()}, {"bottles", bottles}}.dump(1);
    }
    if (!planogram_path.empty())
        std::ofstream(planogram_path) << to_json(planogram(*tracker, rt ? rt->provisional : std::set<int>{}));
    return 0;
}
