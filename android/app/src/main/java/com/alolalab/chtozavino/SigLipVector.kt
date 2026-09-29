package com.alolalab.chtozavino

import kotlin.math.sqrt

internal fun normalizeSigLipVector(
    vector: FloatArray,
    expectedSize: Int = VECTOR_DIMENSION,
): FloatArray {
    if (vector.size != expectedSize) {
        throw ImageRecognitionException(
            "SigLIP2 вернул ${vector.size} значений вместо $expectedSize.",
        )
    }
    var normSquared = 0.0
    for (value in vector) {
        if (!value.isFinite()) {
            throw ImageRecognitionException("SigLIP2 вернул некорректный вектор.")
        }
        normSquared += value * value
    }
    val norm = sqrt(normSquared).toFloat()
    if (!norm.isFinite() || norm <= 1e-12f) {
        throw ImageRecognitionException("SigLIP2 вернул пустой вектор.")
    }
    for (index in vector.indices) vector[index] /= norm
    return vector
}
