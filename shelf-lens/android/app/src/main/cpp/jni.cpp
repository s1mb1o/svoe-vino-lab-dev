// The tracker for the app: one RealtimeTracker with the slow loop on a thread of its own,
// fed with frames (Android bitmaps) and, until the phone has a detector, the cached
// detections of a replay.
#include <android/bitmap.h>
#include <jni.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>
#include <opencv2/imgproc.hpp>

#include "shelfreid/realtime.hpp"

using namespace shelfreid;

namespace {

struct Engine {
    std::unique_ptr<RealtimeTracker> tracker;
    std::map<int, std::vector<Detection>> detections;   // frame number -> boxes
};

// A percentile of the last `window` values, in the unit of the values.
double recent(const std::vector<double>& values, double q, size_t window) {
    if (values.empty()) return 0.0;
    std::vector<double> v(values.end() - std::min(window, values.size()), values.end());
    std::sort(v.begin(), v.end());
    const double pos = q / 100.0 * (v.size() - 1);
    const size_t lo = static_cast<size_t>(std::floor(pos)), hi = static_cast<size_t>(std::ceil(pos));
    return v[lo] + (v[hi] - v[lo]) * (pos - lo);
}

int status_code(const std::string& status) {
    if (status == "new") return 0;
    if (status == "returning") return 1;
    if (status == "pending") return 2;
    return 3;
}

}  // namespace

extern "C" JNIEXPORT jlong JNICALL Java_ru_svoevino_shelfreid_Native_create(JNIEnv* env, jclass, jint width,
                                                                          jint height, jstring detections_path) {
    auto* engine = new Engine;
    StreamConfig cfg;
    engine->tracker = std::make_unique<RealtimeTracker>(Size2{double(width), double(height)}, cfg, -1);
    const char* path = env->GetStringUTFChars(detections_path, nullptr);
    std::ifstream in(path);
    env->ReleaseStringUTFChars(detections_path, path);
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        const auto row = nlohmann::json::parse(line);
        std::vector<Detection> raw;
        for (const auto& b : row["boxes"])
            raw.push_back(Detection{{b[0].get<double>(), b[1].get<double>(), b[2].get<double>(), b[3].get<double>()},
                                    b[4].get<double>()});
        engine->detections[row["frame"].get<int>()] = clean_bottles(raw, cfg.min_score);
    }
    return reinterpret_cast<jlong>(engine);
}

// The boxes of the frame: x1, y1, x2, y2, status (0 new, 1 returning, 2 waiting, 3 ignored),
// bottle id (-1 none), six floats a box.
extern "C" JNIEXPORT jfloatArray JNICALL Java_ru_svoevino_shelfreid_Native_step(JNIEnv* env, jclass, jlong handle,
                                                                              jint number, jobject bitmap) {
    auto* engine = reinterpret_cast<Engine*>(handle);
    AndroidBitmapInfo info;
    void* pixels = nullptr;
    if (AndroidBitmap_getInfo(env, bitmap, &info) != ANDROID_BITMAP_RESULT_SUCCESS ||
        info.format != ANDROID_BITMAP_FORMAT_RGBA_8888 ||
        AndroidBitmap_lockPixels(env, bitmap, &pixels) != ANDROID_BITMAP_RESULT_SUCCESS)
        return env->NewFloatArray(0);
    cv::Mat bgr;
    cv::cvtColor(cv::Mat(static_cast<int>(info.height), static_cast<int>(info.width), CV_8UC4, pixels, info.stride), bgr,
                 cv::COLOR_RGBA2BGR);
    AndroidBitmap_unlockPixels(env, bitmap);
    static const std::vector<Detection> none;
    auto it = engine->detections.find(number);
    const auto shown = engine->tracker->step(number, bgr, it == engine->detections.end() ? none : it->second);
    std::vector<float> out;
    out.reserve(shown.size() * 6);
    for (const auto& s : shown) {
        out.insert(out.end(), {float(s.box[0]), float(s.box[1]), float(s.box[2]), float(s.box[3]),
                               float(status_code(s.status)), float(s.bottle)});
    }
    jfloatArray array = env->NewFloatArray(static_cast<jsize>(out.size()));
    env->SetFloatArrayRegion(array, 0, static_cast<jsize>(out.size()), out.data());
    return array;
}

extern "C" JNIEXPORT jstring JNICALL Java_ru_svoevino_shelfreid_Native_stats(JNIEnv* env, jclass, jlong handle) {
    const RealtimeTracker& t = *reinterpret_cast<Engine*>(handle)->tracker;
    const std::vector<double> landed(t.landed_after.begin(), t.landed_after.end());
    char text[256];
    std::snprintf(text, sizeof(text),
                  "bottles %zu  ids %d  keyframes %zu\nfast %.0f ms (p95 %.0f)  slow %.0f ms (p95 %.0f)  lands after %.0f steps",
                  t.bottles.size(), t.next_id, t.keyframes.size(), recent(t.fast_seconds, 50, 100) * 1000,
                  recent(t.fast_seconds, 95, 100) * 1000, recent(t.slow_seconds, 50, 30) * 1000,
                  recent(t.slow_seconds, 95, 30) * 1000, recent(landed, 50, 30));
    return env->NewStringUTF(text);
}

extern "C" JNIEXPORT void JNICALL Java_ru_svoevino_shelfreid_Native_destroy(JNIEnv*, jclass, jlong handle) {
    delete reinterpret_cast<Engine*>(handle);
}
