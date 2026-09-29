package com.alolalab.chtozavino

enum class AcceleratorMode {
    AUTO,
    GPU,
    CPU;

    companion object {
        fun fromPreference(value: String?): AcceleratorMode = entries.firstOrNull {
            it.name == value
        } ?: AUTO
    }
}

enum class ModelAccelerator {
    GPU,
    CPU;

    companion object {
        fun fromPreference(value: String?): ModelAccelerator? = entries.firstOrNull {
            it.name == value
        }
    }
}

data class AcceleratorProbeResult(
    val dis: ModelAccelerator,
    val sigLip2: ModelAccelerator,
    val disGpuFailure: String? = null,
    val sigLip2GpuFailure: String? = null,
)

data class RecognitionAccelerators(
    val dis: ModelAccelerator,
    val sigLip2: ModelAccelerator,
    val allowDisCpuFallback: Boolean,
    val allowSigLip2CpuFallback: Boolean,
)

fun recognitionAccelerators(
    disMode: AcceleratorMode,
    sigLip2Mode: AcceleratorMode,
    automaticDis: ModelAccelerator?,
    automaticSigLip2: ModelAccelerator?,
): RecognitionAccelerators = RecognitionAccelerators(
    dis = resolveAccelerator(disMode, automaticDis),
    sigLip2 = resolveAccelerator(sigLip2Mode, automaticSigLip2),
    allowDisCpuFallback = disMode == AcceleratorMode.AUTO,
    allowSigLip2CpuFallback = sigLip2Mode == AcceleratorMode.AUTO,
)

private fun resolveAccelerator(
    mode: AcceleratorMode,
    automatic: ModelAccelerator?,
): ModelAccelerator = when (mode) {
    AcceleratorMode.AUTO -> automatic ?: ModelAccelerator.CPU
    AcceleratorMode.GPU -> ModelAccelerator.GPU
    AcceleratorMode.CPU -> ModelAccelerator.CPU
}
