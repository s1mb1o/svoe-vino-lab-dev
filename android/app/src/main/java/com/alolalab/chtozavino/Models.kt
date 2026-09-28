package com.alolalab.chtozavino

import android.graphics.Bitmap

data class WineCard(
    val slug: String,
    val name: String,
    val pageUrl: String,
    val producer: String? = null,
    val category: String? = null,
    val region: String? = null,
    val color: String? = null,
    val grapes: String? = null,
)

data class WineMatch(
    val wine: WineCard,
    val score: Float,
)

enum class RecognitionSource {
    IMAGE,
    CODE,
}

data class DebugImages(
    val disMask: Bitmap,
    val crop: Bitmap,
    val whiteBackground: Bitmap,
)

data class RecognitionOutput(
    val matches: List<WineMatch>,
    val debugImages: DebugImages,
    val disMs: Long,
    val embeddingMs: Long,
    val searchMs: Long,
    val disAccelerator: String,
    val embeddingAccelerator: String,
)

data class ModelPackInfo(
    val version: String,
    val vectorCount: Int,
    val wineCount: Int,
    val installedAt: Long,
)

data class HistoryEntry(
    val id: String,
    val timestamp: Long,
    val source: RecognitionSource,
    val wineName: String,
    val pageUrl: String,
    val score: Float,
    val previewPath: String?,
)

data class UiState(
    val ageAccepted: Boolean = false,
    val modelPack: ModelPackInfo? = null,
    val selectedImage: Bitmap? = null,
    val matches: List<WineMatch> = emptyList(),
    val debugImages: DebugImages? = null,
    val history: List<HistoryEntry> = emptyList(),
    val isBusy: Boolean = false,
    val progressText: String? = null,
    val technicalText: String? = null,
    val scannedCode: String? = null,
    val error: String? = null,
)
