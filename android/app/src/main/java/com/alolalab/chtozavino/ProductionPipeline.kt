package com.alolalab.chtozavino

import android.content.Context
import org.json.JSONObject

internal const val KEY_RECOGNITION_PIPELINE = "recognition_pipeline"
internal const val DUAL_PIPELINE_PACK_VERSION = 7
internal const val CUSTOM_MODEL_FILE = "base-p512-weighted.tflite"
internal const val CUSTOM_MANIFEST_FILE = "base-p512-weighted.manifest.json"
internal const val CUSTOM_DIS_FILE = "dis768.tflite"
internal const val CUSTOM_VECTORS_FILE = "custom_vectors.f32"
internal const val CUSTOM_CANDIDATES_FILE = "custom_candidates.jsonl"
internal val CUSTOM_PAYLOAD_HASHES = mapOf(
    CUSTOM_MODEL_FILE to "6d626149ec6460ef3c57efd671d75691a7f98628f0d1eddefc8c203f818d5ab7",
    CUSTOM_MANIFEST_FILE to "a74907ca301be4a8f8dd8a89673b631efc02e8d69e0b7bfaede3d50cba234a51",
    CUSTOM_DIS_FILE to "b8ede77d06da09f9220d40d8c0735eebbd474d443915d48e2c5f44855b596c94",
    CUSTOM_VECTORS_FILE to "684be34d3d200b6b130bb8192060799036d57ced096e25f2a955be1cf384286b",
)
internal val CUSTOM_PAYLOADS = CUSTOM_PAYLOAD_HASHES.keys + CUSTOM_CANDIDATES_FILE

internal fun verifiedDualGpuDevice(manufacturer: String, model: String): Boolean =
    manufacturer.equals("Google", ignoreCase = true) && model == "Pixel 8"

enum class RecognitionPipeline(val label: String) {
    DIS768_CUSTOM("DIS-768 · обрезка · custom"),
    STANDARD("Полное фото · standard");

    companion object {
        fun fromPreference(value: String?): RecognitionPipeline = entries.firstOrNull {
            it.name == value
        } ?: DIS768_CUSTOM
    }
}

internal fun savedRecognitionPipeline(context: Context): RecognitionPipeline =
    RecognitionPipeline.fromPreference(context.getSharedPreferences(SETTINGS_PREFERENCES, 0)
        .getString(KEY_RECOGNITION_PIPELINE, null))

internal fun selectedPayload(name: String, custom: Boolean): String = if (!custom) name else when (name) {
    COMPLETE_NAFLEX_MODEL_FILE -> CUSTOM_MODEL_FILE
    COMPLETE_NAFLEX_MANIFEST_FILE -> CUSTOM_MANIFEST_FILE
    "dis.tflite" -> CUSTOM_DIS_FILE
    "vectors.f32" -> CUSTOM_VECTORS_FILE
    "candidates.jsonl" -> CUSTOM_CANDIDATES_FILE
    else -> name
}

internal fun validateCustomContract(json: JSONObject, files: Map<String, PackFile>) {
    if (json.optString("default_pipeline") != RecognitionPipeline.DIS768_CUSTOM.name) {
        throw ModelPackException("Пакет не объявляет основной конвейер DIS-768 custom.")
    }
    for ((name, expected) in CUSTOM_PAYLOAD_HASHES) {
        if (files[name]?.sha256 != expected) {
            throw ModelPackException("Модель или индекс DIS-768 custom не совпадает: $name.")
        }
    }
    if (files[CUSTOM_VECTORS_FILE]?.bytes != json.getInt("wine_count").toLong() * 768 * 4) {
        throw ModelPackException("Размер custom-индекса не совпадает с числом вин.")
    }
}
