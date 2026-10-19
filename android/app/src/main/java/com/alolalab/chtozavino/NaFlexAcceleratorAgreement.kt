package com.alolalab.chtozavino

/** Reject finite GPU vectors that disagree with the same CPU graph. */
internal fun validateNaFlexAcceleratorAgreement(gpu: FloatArray, cpu: FloatArray) {
    if (gpu.size != BASE_NAFLEX_VECTOR_DIMENSION || cpu.size != gpu.size ||
        gpu.any { !it.isFinite() } || cpu.any { !it.isFinite() }
    ) {
        throw ImageRecognitionException("Проверка GPU SigLIP2 вернула некорректный вектор.")
    }
    var product = 0.0
    var gpuNorm = 0.0
    var cpuNorm = 0.0
    var maximumError = 0f
    for (index in gpu.indices) {
        product += gpu[index].toDouble() * cpu[index]
        gpuNorm += gpu[index].toDouble() * gpu[index]
        cpuNorm += cpu[index].toDouble() * cpu[index]
        maximumError = maxOf(maximumError, kotlin.math.abs(gpu[index] - cpu[index]))
    }
    val cosine = product / kotlin.math.sqrt(gpuNorm * cpuNorm)
    if (!cosine.isFinite() || cosine < 0.99999 || maximumError > 0.001f) {
        throw ImageRecognitionException("GPU SigLIP2 не прошёл сравнение с CPU. Используем CPU.")
    }
}
