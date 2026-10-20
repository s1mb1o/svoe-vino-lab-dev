// The app's native side: a Pipeline (bottle detector + tracker on threads of their own) fed
// with YUV frames from the camera or the video decoder.
#include <jni.h>

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <string>
#include <unordered_set>
#include <vector>

#include <android/log.h>
#include <opencv2/imgproc.hpp>

#include "pipeline.hpp"

using namespace shelfreid;

namespace {

// The pipelines alive. A call holds `life` shared while it runs and finds its pipeline here;
// destroy holds it alone, so it waits for the calls in progress, and a call that comes later
// (a worker thread of the app that outlived the pipeline) finds none and does nothing.
std::shared_mutex life;
std::unordered_set<Pipeline*> alive;

struct Use {
    std::shared_lock<std::shared_mutex> lock{life};
    Pipeline* const pipeline;
    explicit Use(jlong handle)
        : pipeline(alive.count(reinterpret_cast<Pipeline*>(handle)) ? reinterpret_cast<Pipeline*>(handle) : nullptr) {}
};

std::string text(JNIEnv* env, jstring s) {
    if (s == nullptr) return {};
    const char* chars = env->GetStringUTFChars(s, nullptr);
    std::string out(chars);
    env->ReleaseStringUTFChars(s, chars);
    return out;
}

// A YUV_420_888 image (an Android Image) as an upright BGR frame. The chroma is
// semi-planar (NV12 or NV21) when its pixel stride is 2 and the planes interleave, planar
// otherwise.
cv::Mat to_bgr(const cv::Mat& y, const uint8_t* u, const uint8_t* v, int uv_row_stride, int uv_pixel_stride, int rotation) {
    const int w = y.cols, h = y.rows;
    cv::Mat bgr;
    if (uv_pixel_stride == 2 && v == u + 1) {
        cv::cvtColorTwoPlane(y, cv::Mat(h / 2, w / 2, CV_8UC2, const_cast<uint8_t*>(u), uv_row_stride), bgr,
                             cv::COLOR_YUV2BGR_NV12);
    } else if (uv_pixel_stride == 2 && u == v + 1) {
        cv::cvtColorTwoPlane(y, cv::Mat(h / 2, w / 2, CV_8UC2, const_cast<uint8_t*>(v), uv_row_stride), bgr,
                             cv::COLOR_YUV2BGR_NV21);
    } else {
        cv::Mat i420(h * 3 / 2, w, CV_8UC1);
        y.copyTo(i420.rowRange(0, h));
        uint8_t* pu = i420.ptr(h);
        uint8_t* pv = pu + (w / 2) * (h / 2);
        for (int r = 0; r < h / 2; ++r)
            for (int c = 0; c < w / 2; ++c) {
                *pu++ = u[r * uv_row_stride + c * uv_pixel_stride];
                *pv++ = v[r * uv_row_stride + c * uv_pixel_stride];
            }
        cv::cvtColor(i420, bgr, cv::COLOR_YUV2BGR_I420);
    }
    switch (((rotation % 360) + 360) % 360) {
        case 90: cv::rotate(bgr, bgr, cv::ROTATE_90_CLOCKWISE); break;
        case 180: cv::rotate(bgr, bgr, cv::ROTATE_180); break;
        case 270: cv::rotate(bgr, bgr, cv::ROTATE_90_COUNTERCLOCKWISE); break;
        default: break;
    }
    return bgr;
}

}  // namespace

// Loads the detector (slow: the accelerator compiles the model); see Pipeline for
// `cv_threads`, `cheap_slow` and `accelerator`. 0 on failure.
extern "C" JNIEXPORT jlong JNICALL Java_com_alolalab_shelflens_Native_create(JNIEnv* env, jclass, jstring model_path,
                                                                          jint cv_threads, jboolean cheap_slow,
                                                                          jboolean accelerator) {
    try {
        auto* pipeline = new Pipeline(text(env, model_path), cv_threads, cheap_slow, accelerator);
        std::unique_lock<std::shared_mutex> lock(life);
        alive.insert(pipeline);
        return reinterpret_cast<jlong>(pipeline);
    } catch (const std::exception&) {
        return 0;
    }
}

// A new shot of upright frames this size.
extern "C" JNIEXPORT void JNICALL Java_com_alolalab_shelflens_Native_begin(JNIEnv*, jclass, jlong handle, jint width,
                                                                        jint height) {
    Use use(handle);
    if (use.pipeline) use.pipeline->begin(width, height);
}

extern "C" JNIEXPORT void JNICALL Java_com_alolalab_shelflens_Native_end(JNIEnv*, jclass, jlong handle) {
    Use use(handle);
    if (use.pipeline) use.pipeline->end();
}

// One YUV_420_888 frame: its motion from the previous frame, the six numbers of the
// similarity x' = a0 x + a1 y + a2, y' = a3 x + a4 y + a5 in upright pixels, and a seventh:
// 1 when the flow found it, 0 when not (then the identity). With `process`, the frame also
// goes to the detector and the tracker.
extern "C" JNIEXPORT jfloatArray JNICALL Java_com_alolalab_shelflens_Native_pushFrame(
    JNIEnv* env, jclass, jlong handle, jint frame, jobject y_buffer, jint y_row_stride, jobject u_buffer,
    jobject v_buffer, jint uv_row_stride, jint uv_pixel_stride, jint width, jint height, jint rotation,
    jboolean process) {
    Use use(handle);
    Pipeline* pipeline = use.pipeline;
    auto* y = static_cast<uint8_t*>(env->GetDirectBufferAddress(y_buffer));
    auto* u = static_cast<uint8_t*>(env->GetDirectBufferAddress(u_buffer));
    auto* v = static_cast<uint8_t*>(env->GetDirectBufferAddress(v_buffer));
    float motion[7] = {1, 0, 0, 0, 1, 0, 0};
    if (pipeline != nullptr && y != nullptr) {
        const cv::Mat luma(height, width, CV_8UC1, y, y_row_stride);
        cv::Matx23d a;
        const bool found = pipeline->motion(frame, luma, rotation, a);
        for (int k = 0; k < 6; ++k) motion[k] = static_cast<float>(a.val[k]);
        motion[6] = found ? 1.f : 0.f;
        if (process && u != nullptr && v != nullptr) {
            cv::Mat bgr = to_bgr(luma, u, v, uv_row_stride, uv_pixel_stride, rotation);
            static int logged = 0;
            if (logged < 3) {
                ++logged;
                const cv::Scalar mean = cv::mean(bgr);
                __android_log_print(ANDROID_LOG_INFO, "shelfreid",
                                    "frame %d: %dx%d y-stride %d uv-stride %d uv-pixel %d v-u %ld rot %d -> bgr %dx%d mean %.0f %.0f %.0f",
                                    frame, width, height, y_row_stride, uv_row_stride, uv_pixel_stride, long(v - u), rotation,
                                    bgr.cols, bgr.rows, mean[0], mean[1], mean[2]);
            }
            pipeline->submit(frame, std::move(bgr));
        }
    }
    jfloatArray out = env->NewFloatArray(7);
    env->SetFloatArrayRegion(out, 0, 7, motion);
    return out;
}

// The last processed frame: its number, then six floats a box: x1, y1, x2, y2, state
// (0 a bottle whose wine is not known yet, 1 known, 2 a crop of it waits for the server or
// its answer, 3 not a bottle the tracker keeps (cut, too weak), 4 a bottle found but not on
// the map yet: the tracker waits to know where it is), bottle id (-1 none).
extern "C" JNIEXPORT jfloatArray JNICALL Java_com_alolalab_shelflens_Native_latest(JNIEnv* env, jclass, jlong handle) {
    Use use(handle);
    if (!use.pipeline) return nullptr;
    const auto result = use.pipeline->latest();
    std::vector<float> out{static_cast<float>(result.frame)};
    out.reserve(1 + result.shown.size() * 6);
    for (size_t i = 0; i < result.shown.size(); ++i) {
        const auto& s = result.shown[i];
        const int state = s.bottle == kNone ? (s.status == "pending" ? 4 : 3)
                                            : (i < result.recognized.size() ? result.recognized[i] : 0);
        out.insert(out.end(), {float(s.box[0]), float(s.box[1]), float(s.box[2]), float(s.box[3]), float(state),
                               float(s.bottle)});
    }
    jfloatArray array = env->NewFloatArray(static_cast<jsize>(out.size()));
    env->SetFloatArrayRegion(array, 0, static_cast<jsize>(out.size()), out.data());
    return array;
}

extern "C" JNIEXPORT jstring JNICALL Java_com_alolalab_shelflens_Native_stats(JNIEnv* env, jclass, jlong handle) {
    Use use(handle);
    return use.pipeline ? env->NewStringUTF(use.pipeline->stats().c_str()) : nullptr;
}

extern "C" JNIEXPORT void JNICALL Java_com_alolalab_shelflens_Native_destroy(JNIEnv*, jclass, jlong handle) {
    auto* pipeline = reinterpret_cast<Pipeline*>(handle);
    {
        std::unique_lock<std::shared_mutex> lock(life);   // after the calls in progress
        if (!alive.erase(pipeline)) return;
    }
    delete pipeline;
}

extern "C" JNIEXPORT void JNICALL Java_com_alolalab_shelflens_Native_setRecognition(JNIEnv*, jclass, jlong handle,
                                                                                 jboolean on) {
    Use use(handle);
    if (use.pipeline) use.pipeline->set_recognition(on);
}

// The next crop to send: five little-endian int32 (bottle, frame, box height, sharpness x
// 10, crops it was chosen from), then the PNG; null when none waits.
extern "C" JNIEXPORT jbyteArray JNICALL Java_com_alolalab_shelflens_Native_takeCrop(JNIEnv* env, jclass, jlong handle) {
    Use use(handle);
    if (!use.pipeline) return nullptr;
    const auto crop = use.pipeline->take_crop();
    if (crop.empty()) return nullptr;
    jbyteArray out = env->NewByteArray(static_cast<jsize>(crop.size()));
    env->SetByteArrayRegion(out, 0, static_cast<jsize>(crop.size()), reinterpret_cast<const jbyte*>(crop.data()));
    return out;
}

// What came of the request for a crop (Pipeline::Outcome); the decision
// ("slug\tname\tsure|unsure") when this answer changes it, else null.
extern "C" JNIEXPORT jstring JNICALL Java_com_alolalab_shelflens_Native_answer(JNIEnv* env, jclass, jlong handle,
                                                                            jint bottle, jint frame, jint height,
                                                                            jstring slug, jstring name, jint outcome) {
    Use use(handle);
    if (!use.pipeline) return nullptr;
    const std::string decision = use.pipeline->answer(bottle, frame, height, text(env, slug), text(env, name), outcome);
    return decision.empty() ? nullptr : env->NewStringUTF(decision.c_str());
}

// Every bottle met, as JSON (Pipeline::recognition_table).
extern "C" JNIEXPORT jstring JNICALL Java_com_alolalab_shelflens_Native_recognitionTable(JNIEnv* env, jclass,
                                                                                      jlong handle) {
    Use use(handle);
    return use.pipeline ? env->NewStringUTF(use.pipeline->recognition_table().c_str()) : nullptr;
}

// A small JPEG of the bottle's latest crop, or null.
extern "C" JNIEXPORT jbyteArray JNICALL Java_com_alolalab_shelflens_Native_thumbnail(JNIEnv* env, jclass, jlong handle,
                                                                                  jint bottle) {
    Use use(handle);
    if (!use.pipeline) return nullptr;
    const auto jpeg = use.pipeline->thumbnail(bottle);
    if (jpeg.empty()) return nullptr;
    jbyteArray out = env->NewByteArray(static_cast<jsize>(jpeg.size()));
    env->SetByteArrayRegion(out, 0, static_cast<jsize>(jpeg.size()), reinterpret_cast<const jbyte*>(jpeg.data()));
    return out;
}

// The planogram of the map as it is now, as JSON (Pipeline::planogram).
extern "C" JNIEXPORT jstring JNICALL Java_com_alolalab_shelflens_Native_planogram(JNIEnv* env, jclass, jlong handle) {
    Use use(handle);
    return use.pipeline ? env->NewStringUTF(use.pipeline->planogram().c_str()) : nullptr;
}

// Four ints (Pipeline::summary): the bottles of the map, those whose wine is known, those
// waiting for the server, and 1 while the tracker has lost its place on the map.
extern "C" JNIEXPORT jintArray JNICALL Java_com_alolalab_shelflens_Native_summary(JNIEnv* env, jclass, jlong handle) {
    Use use(handle);
    const auto s = use.pipeline ? use.pipeline->summary() : std::array<int, 4>{};
    jintArray out = env->NewIntArray(4);
    const jint values[4] = {s[0], s[1], s[2], s[3]};
    env->SetIntArrayRegion(out, 0, 4, values);
    return out;
}

// The frames start again after a break (the camera was off): the map stays.
extern "C" JNIEXPORT void JNICALL Java_com_alolalab_shelflens_Native_interrupt(JNIEnv*, jclass, jlong handle) {
    Use use(handle);
    if (use.pipeline) use.pipeline->interrupt();
}
