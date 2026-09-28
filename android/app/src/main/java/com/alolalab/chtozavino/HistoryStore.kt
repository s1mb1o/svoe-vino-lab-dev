package com.alolalab.chtozavino

import android.content.Context
import android.graphics.Bitmap
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

private const val HISTORY_LIMIT = 50

class HistoryStore(private val context: Context) {
    private val preferences = context.getSharedPreferences("history", Context.MODE_PRIVATE)
    private val imageDirectory = File(context.filesDir, "history")

    fun list(): List<HistoryEntry> {
        val source = preferences.getString("rows", "[]") ?: "[]"
        return runCatching {
            val array = JSONArray(source)
            buildList {
                for (index in 0 until array.length()) {
                    val row = array.getJSONObject(index)
                    add(
                        HistoryEntry(
                            id = row.getString("id"),
                            timestamp = row.getLong("timestamp"),
                            source = RecognitionSource.valueOf(row.getString("source")),
                            wineName = row.getString("wine_name"),
                            pageUrl = row.getString("page_url"),
                            score = row.getDouble("score").toFloat(),
                            previewPath = row.optString("preview_path").ifEmpty { null },
                        ),
                    )
                }
            }
        }.getOrDefault(emptyList())
    }

    fun add(source: RecognitionSource, match: WineMatch, preview: Bitmap?): List<HistoryEntry> {
        imageDirectory.mkdirs()
        val id = "${System.currentTimeMillis()}-${UUID.randomUUID()}"
        val previewPath = preview?.let { savePreview(id, it) }
        val entry = HistoryEntry(
            id = id,
            timestamp = System.currentTimeMillis(),
            source = source,
            wineName = match.wine.name,
            pageUrl = match.wine.pageUrl,
            score = match.score,
            previewPath = previewPath,
        )
        val old = list()
        val rows = (listOf(entry) + old).take(HISTORY_LIMIT)
        (old - rows.toSet()).forEach { removed ->
            removed.previewPath?.let { File(it).delete() }
        }
        val json = JSONArray()
        rows.forEach { row ->
            json.put(
                JSONObject()
                    .put("id", row.id)
                    .put("timestamp", row.timestamp)
                    .put("source", row.source.name)
                    .put("wine_name", row.wineName)
                    .put("page_url", row.pageUrl)
                    .put("score", row.score.toDouble())
                    .put("preview_path", row.previewPath ?: ""),
            )
        }
        preferences.edit().putString("rows", json.toString()).apply()
        return rows
    }

    fun clear() {
        preferences.edit().remove("rows").apply()
        imageDirectory.listFiles()?.forEach(File::delete)
    }

    private fun savePreview(id: String, bitmap: Bitmap): String {
        val maxSide = 512
        val scale = minOf(1f, maxSide.toFloat() / maxOf(bitmap.width, bitmap.height))
        val preview = if (scale < 1f) {
            Bitmap.createScaledBitmap(
                bitmap,
                (bitmap.width * scale).toInt().coerceAtLeast(1),
                (bitmap.height * scale).toInt().coerceAtLeast(1),
                true,
            )
        } else {
            bitmap
        }
        val file = File(imageDirectory, "$id.jpg")
        file.outputStream().use { output ->
            if (!preview.compress(Bitmap.CompressFormat.JPEG, 88, output)) {
                throw IllegalStateException("Не удалось сохранить изображение истории.")
            }
        }
        if (preview !== bitmap) preview.recycle()
        return file.absolutePath
    }
}
