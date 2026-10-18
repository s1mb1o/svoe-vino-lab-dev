// Run the tracker on a video with cached detections and dump each step as JSON lines, in
// the format of the Python dumps: [frame, [[x1, y1, x2, y2, status, bottle], ...]].
//
//   replay VIDEO|FRAMES_DIR DETS.jsonl sync|rt:N|rt:async OUT.jsonl [--every 3] [--slow-every K] [--pace MS]
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
#include <string>
#include <thread>

#include <nlohmann/json.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/videoio.hpp>

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
    for (int a = 5; a + 1 < argc; ++a) {
        if (std::string(argv[a]) == "--every") every = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--slow-every") slow_every = std::stoi(argv[a + 1]);
        if (std::string(argv[a]) == "--pace") pace_ms = std::stoi(argv[a + 1]);
    }

    StreamConfig cfg;
    // The parameters in steps are set for every 3rd frame of 30 fps (10 steps a second);
    // a sparser stream scales them to keep their times.
    if (every != 3) {
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
    int number = 0, pending_steps = 0;
    std::vector<double> step_seconds;
    while (true) {
        if (number % every == 0) {
            auto it = dets.find(number);
            if (it == dets.end()) break;
            if (number > 0 && from_dir && !frame_at(number, frame)) break;
            const auto t = std::chrono::steady_clock::now();
            const auto shown = tracker->step(number, frame, it->second);
            step_seconds.push_back(std::chrono::duration<double>(std::chrono::steady_clock::now() - t).count());
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
        }
        ++number;
        if (!from_dir && !capture.read(frame)) break;
    }
    std::cout << mode << " bottles " << tracker->bottles.size() << " ids " << tracker->next_id << " white steps "
              << pending_steps << " jumps " << tracker->jumps << " found " << tracker->found << " merged young "
              << tracker->merged_young << " | step p50 " << pct(step_seconds, 50) * 1000 << " p95 " << pct(step_seconds, 95) * 1000
              << " ms";
    if (rt)
        std::cout << " | fast p50 " << pct(rt->fast_seconds, 50) * 1000 << " p95 " << pct(rt->fast_seconds, 95) * 1000
                  << " ms; slow jobs " << rt->slow_seconds.size() << " p50 " << pct(rt->slow_seconds, 50) * 1000 << " p95 "
                  << pct(rt->slow_seconds, 95) * 1000 << " ms; landed after p50 "
                  << pct(std::vector<double>(rt->landed_after.begin(), rt->landed_after.end()), 50) << " p95 "
                  << pct(std::vector<double>(rt->landed_after.begin(), rt->landed_after.end()), 95) << " steps";
    std::cout << std::endl;
    return 0;
}
