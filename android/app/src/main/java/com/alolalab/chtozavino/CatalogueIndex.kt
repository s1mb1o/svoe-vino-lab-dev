package com.alolalab.chtozavino

import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.net.URI
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.nio.channels.FileChannel
import kotlin.math.sqrt

private data class CandidateRef(
    val row: Int,
    val slug: String,
)

enum class ReferenceAggregation(val id: String) {
    MAX(MAX_REFERENCE_AGGREGATION),
    TOP2_MEAN(TOP2_MEAN_REFERENCE_AGGREGATION),
    ;

    companion object {
        fun fromId(value: String): ReferenceAggregation = entries.firstOrNull { it.id == value }
            ?: throw IllegalArgumentException("unknown reference aggregation: $value")
    }
}

private data class TopScores(
    var first: Float = Float.NEGATIVE_INFINITY,
    var second: Float = Float.NEGATIVE_INFINITY,
) {
    fun add(value: Float) {
        if (value > first) {
            second = first
            first = value
        } else if (value > second) {
            second = value
        }
    }

    fun aggregate(mode: ReferenceAggregation): Float = when (mode) {
        ReferenceAggregation.MAX -> first
        ReferenceAggregation.TOP2_MEAN -> if (second.isFinite()) {
            (first + second) / 2f
        } else {
            first
        }
    }
}

class CatalogueIndex private constructor(
    private val vectors: FloatBuffer,
    private val vectorCount: Int,
    private val vectorDimension: Int,
    private val candidates: List<CandidateRef>,
    private val wines: Map<String, WineCard>,
    private val codes: Map<String, Set<String>>,
) {
    companion object {
        fun load(pack: InstalledModelPack): CatalogueIndex {
            val wines = linkedMapOf<String, WineCard>()
            pack.file("wines.jsonl").forEachLine { line ->
                if (line.isBlank()) return@forEachLine
                val row = JSONObject(line)
                val slug = row.requiredString("wine_slug")
                if (slug in wines) throw ModelPackException("Повтор вина в wines.jsonl: $slug")
                wines[slug] = WineCard(
                    slug = slug,
                    name = row.requiredString("name"),
                    pageUrl = row.requiredString("page_url").also {
                        if (!it.startsWith("https://vino-svoe.ru/wines/")) {
                            throw ModelPackException("Некорректная ссылка вина $slug.")
                        }
                    },
                    producer = row.optionalString("producer"),
                    category = row.optionalString("category"),
                    region = row.optionalString("region"),
                    color = row.optionalString("color"),
                    grapes = row.optionalString("grapes"),
                    imagePath = row.optionalString("image_path")?.let { relative ->
                        val root = File(pack.directory, "images").canonicalPath + File.separator
                        val image = File(pack.directory, relative)
                        if (!relative.startsWith("images/") || !image.canonicalPath.startsWith(root) ||
                            !image.isFile
                        ) {
                            throw ModelPackException("Некорректное изображение вина $slug.")
                        }
                        image.absolutePath
                    },
                )
            }
            if (wines.size != pack.manifest.wineCount) {
                throw ModelPackException("Число вин в wines.jsonl не совпадает с manifest.json.")
            }

            val candidates = mutableListOf<CandidateRef>()
            pack.file("candidates.jsonl").forEachLine { line ->
                if (line.isBlank()) return@forEachLine
                val row = JSONObject(line)
                if (row.optString("view") != "full") return@forEachLine
                val vectorRow = row.optInt("vector_row", -1)
                val slug = row.requiredString("wine_slug")
                if (vectorRow !in 0 until pack.manifest.vectorCount) {
                    throw ModelPackException("Некорректный vector_row в candidates.jsonl.")
                }
                if (slug !in wines) {
                    throw ModelPackException("Неизвестное вино в candidates.jsonl: $slug")
                }
                candidates += CandidateRef(vectorRow, slug)
            }
            if (candidates.isEmpty()) {
                throw ModelPackException("В candidates.jsonl нет векторов full.")
            }

            val codeRows = linkedMapOf<String, MutableSet<String>>()
            pack.file("codes.jsonl").forEachLine { line ->
                if (line.isBlank()) return@forEachLine
                val row = JSONObject(line)
                val slug = row.requiredString("wine_slug")
                if (slug !in wines) {
                    throw ModelPackException("Неизвестное вино в codes.jsonl: $slug")
                }
                val key = normalizeCode(row.requiredString("value"))
                if (key.isNotEmpty()) codeRows.getOrPut(key) { linkedSetOf() }.add(slug)
            }

            val mapped = FileInputStream(pack.file("vectors.f32")).channel.use { channel ->
                channel.map(FileChannel.MapMode.READ_ONLY, 0, channel.size())
                    .order(ByteOrder.LITTLE_ENDIAN)
                    .asFloatBuffer()
            }
            return CatalogueIndex(
                vectors = mapped,
                vectorCount = pack.manifest.vectorCount,
                vectorDimension = pack.manifest.vectorDimension,
                candidates = candidates,
                wines = wines,
                codes = codeRows,
            )
        }

        internal fun normalizeCode(raw: String): String {
            val text = raw.trim()
            if (text.matches(Regex("[0-9]+"))) {
                return when (text.length) {
                    8, 12, 13, 14 -> "gtin:${text.padStart(14, '0')}"
                    else -> "raw:$text"
                }
            }
            val url = runCatching {
                val source = URI(text)
                val scheme = source.scheme?.lowercase() ?: return@runCatching null
                val host = source.host?.lowercase() ?: return@runCatching null
                if (scheme !in setOf("http", "https")) return@runCatching null
                val port = if ((scheme == "http" && source.port == 80) ||
                    (scheme == "https" && source.port == 443)
                ) -1 else source.port
                URI(scheme, null, host, port, source.path.ifEmpty { "/" }, source.query, null)
                    .toASCIIString()
            }.getOrNull()
            return if (url != null) "url:$url" else "raw:$text"
        }
    }

    fun findCode(raw: String): List<WineMatch> {
        return codes[normalizeCode(raw)].orEmpty()
            .mapNotNull(wines::get)
            .sortedBy { it.name }
            .map { WineMatch(it, 1f) }
    }

    fun search(
        query: FloatArray,
        limit: Int = 5,
        aggregation: ReferenceAggregation = ReferenceAggregation.MAX,
    ): List<WineMatch> {
        require(query.size == vectorDimension)
        val normalized = query.copyOf()
        var normSquared = 0.0
        for (value in normalized) normSquared += value * value
        val norm = sqrt(normSquared).toFloat()
        require(norm.isFinite() && norm > 0f) { "SigLIP2 вернул пустой вектор." }
        for (index in normalized.indices) normalized[index] /= norm

        val best = hashMapOf<String, TopScores>()
        for (candidate in candidates) {
            if (candidate.row !in 0 until vectorCount) continue
            val offset = candidate.row * vectorDimension
            var score = 0f
            for (dimension in 0 until vectorDimension) {
                score += normalized[dimension] * vectors.get(offset + dimension)
            }
            best.getOrPut(candidate.slug, ::TopScores).add(score)
        }
        return best.entries
            .map { it.key to it.value.aggregate(aggregation) }
            .sortedWith(compareByDescending<Pair<String, Float>> { it.second }.thenBy { it.first })
            .take(limit)
            .mapNotNull { (slug, score) -> wines[slug]?.let { WineMatch(it, score) } }
    }
}

private fun JSONObject.requiredString(name: String): String {
    val value = optString(name).trim()
    if (value.isEmpty()) throw ModelPackException("Поле $name должно быть непустой строкой.")
    return value
}

private fun JSONObject.optionalString(name: String): String? {
    if (isNull(name)) return null
    return optString(name).trim().ifEmpty { null }
}
