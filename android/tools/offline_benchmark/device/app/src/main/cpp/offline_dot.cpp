#include <arm_neon.h>
#include <cstddef>

extern "C" void offline_dot_rows(const float* matrix, int rows, int dimension,
                                  const float* query, float* output) {
    for (int row = 0; row < rows; ++row) {
        const float* values = matrix + static_cast<std::size_t>(row) * dimension;
        float32x4_t a = vdupq_n_f32(0), b = a, c = a, d = a;
        int column = 0;
        for (; column + 16 <= dimension; column += 16) {
            a = vfmaq_f32(a, vld1q_f32(values + column), vld1q_f32(query + column));
            b = vfmaq_f32(b, vld1q_f32(values + column + 4), vld1q_f32(query + column + 4));
            c = vfmaq_f32(c, vld1q_f32(values + column + 8), vld1q_f32(query + column + 8));
            d = vfmaq_f32(d, vld1q_f32(values + column + 12), vld1q_f32(query + column + 12));
        }
        float score = vaddvq_f32(vaddq_f32(vaddq_f32(a,b),vaddq_f32(c,d)));
        for (; column < dimension; ++column) score += values[column] * query[column];
        output[row] = score;
    }
}

#ifdef __ANDROID__
#include <jni.h>
#include <vector>
extern "C" JNIEXPORT jfloatArray JNICALL
Java_com_alolalab_chtozavino_offlinebench_NativeDot_score(
    JNIEnv* env, jobject, jobject matrix, jint rows, jint dimension, jfloatArray query) {
    auto* data = static_cast<const float*>(env->GetDirectBufferAddress(matrix));
    jlong capacity = env->GetDirectBufferCapacity(matrix);
    if (!data || rows < 1 || dimension < 1 || env->GetArrayLength(query) != dimension ||
        static_cast<jlong>(rows) * dimension * sizeof(float) > capacity) {
        env->ThrowNew(env->FindClass("java/lang/IllegalArgumentException"), "Invalid dot-product input.");
        return nullptr;
    }
    float* vector = env->GetFloatArrayElements(query,nullptr);
    std::vector<float> scores(rows);
    offline_dot_rows(data,rows,dimension,vector,scores.data());
    env->ReleaseFloatArrayElements(query,vector,JNI_ABORT);
    auto result = env->NewFloatArray(rows);
    env->SetFloatArrayRegion(result,0,rows,scores.data());
    return result;
}
#endif
