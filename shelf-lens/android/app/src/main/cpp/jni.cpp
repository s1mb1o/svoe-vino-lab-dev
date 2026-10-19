// The app's native side: a Pipeline (bottle detector + tracker on threads of their own) fed
// with YUV frames from the camera or the video decoder.
#include <jni.h>

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <memory>
#include <string>
#include <vector>

#include <android/log.h>
#include <opencv2/imgproc.hpp>

#include "pipeline.hpp"

using namespace shelfreid;

namespace {

std::string text(JNIEnv* env, jstring s) {
    if (s == nullptr) return {};
    const char* chars = env->GetStringUTFChars(s, nullptr);
    std::string out(chars);
    env->ReleaseStringUTFChars(s, chars);
    return out;
}

int status_code(const std::string& status) {
    if (status == "new") return 0;
    if (status == "returning") return 1;
    if (status == "pending") return 2;
    return 3;
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

// Loads the detector (seconds: the accelerator compiles the model); see Pipeline for
// `cv_threads` and `cheap_slow`. 0 on failure.
extern "C" JNIEXPORT jlong JNICALL Java_ru_svoevino_shelfreid_Native_create(JNIEnv* env, jclass, jstring model_path,
                                                                          jint cv_threads, jboolean cheap_slow) {
    try {
        return reinterpret_cast<jlong>(new Pipeline(text(env, model_path), cv_threads, cheap_slow));
    } catch (const std::exception&) {
        return 0;
    }
}

// A new shot of upright frames this size.
extern "C" JNIEXPORT void JNICALL Java_ru_svoevino_shelfreid_Native_begin(JNIEnv*, jclass, jlong handle, jint width,
                                                                        jint height) {
    reinterpret_cast<Pipeline*>(handle)->begin(width, height);
}

extern "C" JNIEXPORT void JNICALL Java_ru_svoevino_shelfreid_Native_end(JNIEnv*, jclass, jlong handle) {
    reinterpret_cast<Pipeline*>(handle)->end();
}

// One YUV_420_888 frame: its motion from the previous frame, the six numbers of the
// similarity x' = a0 x + a1 y + a2, y' = a3 x + a4 y + a5 in upright pixels, and a seventh:
// 1 when the flow found it, 0 when not (then the identity). With `process`, the frame also
// goes to the detector and the tracker.
extern "C" JNIEXPORT jfloatArray JNICALL Java_ru_svoevino_shelfreid_Native_pushFrame(
    JNIEnv* env, jclass, jlong handle, jint frame, jobject y_buffer, jint y_row_stride, jobject u_buffer,
    jobject v_buffer, jint uv_row_stride, jint uv_pixel_stride, jint width, jint height, jint rotation,
    jboolean process) {
    auto* pipeline = reinterpret_cast<Pipeline*>(handle);
    auto* y = static_cast<uint8_t*>(env->GetDirectBufferAddress(y_buffer));
    auto* u = static_cast<uint8_t*>(env->GetDirectBufferAddress(u_buffer));
    auto* v = static_cast<uint8_t*>(env->GetDirectBufferAddress(v_buffer));
    float motion[7] = {1, 0, 0, 0, 1, 0, 0};
    if (y != nullptr) {
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

// The last processed frame: its number, then six floats a box: x1, y1, x2, y2, status
// (0 new, 1 returning, 2 waiting, 3 ignored), bottle id (-1 none).
extern "C" JNIEXPORT jfloatArray JNICALL Java_ru_svoevino_shelfreid_Native_latest(JNIEnv* env, jclass, jlong handle) {
    const auto result = reinterpret_cast<Pipeline*>(handle)->latest();
    std::vector<float> out{static_cast<float>(result.frame)};
    out.reserve(1 + result.shown.size() * 6);
    for (const auto& s : result.shown)
        out.insert(out.end(), {float(s.box[0]), float(s.box[1]), float(s.box[2]), float(s.box[3]),
                               float(status_code(s.status)), float(s.bottle)});
    jfloatArray array = env->NewFloatArray(static_cast<jsize>(out.size()));
    env->SetFloatArrayRegion(array, 0, static_cast<jsize>(out.size()), out.data());
    return array;
}

extern "C" JNIEXPORT jstring JNICALL Java_ru_svoevino_shelfreid_Native_stats(JNIEnv* env, jclass, jlong handle) {
    return env->NewStringUTF(reinterpret_cast<Pipeline*>(handle)->stats().c_str());
}

extern "C" JNIEXPORT void JNICALL Java_ru_svoevino_shelfreid_Native_destroy(JNIEnv*, jclass, jlong handle) {
    delete reinterpret_cast<Pipeline*>(handle);
}
