package com.alolalab.chtozavino

import android.content.Context

internal const val SETTINGS_PREFERENCES = "settings"
internal const val KEY_AUTOMATIC_DIS_ACCELERATOR = "automatic_dis_accelerator"
internal const val KEY_AUTOMATIC_SIGLIP2_ACCELERATOR = "automatic_siglip2_accelerator"
internal const val KEY_DIS_ACCELERATOR_MODE = "dis_accelerator_mode"
internal const val KEY_SIGLIP2_ACCELERATOR_MODE = "siglip2_accelerator_mode"

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

fun savedRecognitionAccelerators(context: Context): RecognitionAccelerators {
    val preferences = context.getSharedPreferences(SETTINGS_PREFERENCES, 0)
    return recognitionAccelerators(
        disMode = AcceleratorMode.fromPreference(
            preferences.getString(KEY_DIS_ACCELERATOR_MODE, null),
        ),
        sigLip2Mode = AcceleratorMode.fromPreference(
            preferences.getString(KEY_SIGLIP2_ACCELERATOR_MODE, null),
        ),
        automaticDis = ModelAccelerator.fromPreference(
            preferences.getString(KEY_AUTOMATIC_DIS_ACCELERATOR, null),
        ),
        automaticSigLip2 = ModelAccelerator.fromPreference(
            preferences.getString(KEY_AUTOMATIC_SIGLIP2_ACCELERATOR, null),
        ),
    )
}

private fun resolveAccelerator(
    mode: AcceleratorMode,
    automatic: ModelAccelerator?,
): ModelAccelerator = when (mode) {
    AcceleratorMode.AUTO -> automatic ?: ModelAccelerator.CPU
    AcceleratorMode.GPU -> ModelAccelerator.GPU
    AcceleratorMode.CPU -> ModelAccelerator.CPU
}
