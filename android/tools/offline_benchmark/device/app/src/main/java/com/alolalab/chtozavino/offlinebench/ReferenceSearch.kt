package com.alolalab.chtozavino.offlinebench

import java.io.File
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.json.JSONArray
import org.json.JSONObject

internal fun child(directory: File, name: String): File {
    val file = File(directory, name).canonicalFile
    require(file.path.startsWith(directory.canonicalPath + File.separator)) { "Unsafe pack path." }
    return file
}

internal class TopMean(private val wineCount: Int, private val k: Int) {
    private val best = FloatArray(wineCount * k) { Float.NEGATIVE_INFINITY }
    private val counts = IntArray(wineCount)
    init { require(k in 1..3) }
    fun add(wine: Int, value: Float) {
        require(wine in 0 until wineCount && value.isFinite())
        counts[wine]++
        val offset = wine * k
        for (position in 0 until k) {
            if (value > best[offset + position]) {
                for (tail in k - 1 downTo position + 1) best[offset + tail] = best[offset + tail - 1]
                best[offset + position] = value
                break
            }
        }
    }
    fun result(): FloatArray = FloatArray(wineCount) { wine ->
        val count = minOf(k, counts[wine])
        if (count == 0) Float.NEGATIVE_INFINITY
        else ((0 until count).sumOf { best[wine * k + it].toDouble() } / count).toFloat()
    }
}

internal fun fuse(bottle: FloatArray, label: FloatArray?, bottleWeight: Double): DoubleArray {
    require(bottleWeight in 0.0..1.0)
    require(label == null || label.size == bottle.size)
    return DoubleArray(bottle.size) { wine ->
        val b = bottle[wine].toDouble()
        val l = label?.get(wine)?.toDouble() ?: Double.NEGATIVE_INFINITY
        when {
            b.isFinite() && l.isFinite() -> bottleWeight * b + (1 - bottleWeight) * l
            else -> maxOf(b, l)
        }
    }
}

internal fun ranked(scores: DoubleArray, slugs: List<String>, k: Int): JSONArray {
    require(scores.size == slugs.size && k in 1..20)
    val order = scores.indices.filter { scores[it].isFinite() }.sortedWith(
        compareByDescending<Int> { scores[it] }.thenBy { slugs[it] },
    )
    return JSONArray().apply {
        order.take(k).forEachIndexed { rank, wine ->
            put(JSONObject().put("slug", slugs[wine]).put("score", scores[wine]).put("rank", rank + 1))
        }
    }
}

/** Read bounded blocks. Do not retain a multi-gigabyte reference matrix in app RAM. */
internal class ReferenceIndex(directory: File, specification: JSONObject, private val wines: Int) {
    private val dimension = specification.getInt("dimension")
    private val rows = specification.getInt("rows")
    private val matrix = child(directory, specification.getString("vectors"))
    private val ownerFile = child(directory, specification.getString("owners"))
    private val owners: IntArray
    private val blockRows = 1024
    private val buffer = ByteBuffer.allocateDirect(blockRows * dimension * 4).order(ByteOrder.LITTLE_ENDIAN)
    init {
        require(rows > 0 && dimension == 1152)
        require(matrix.length() == rows.toLong() * dimension * 4)
        require(ownerFile.length() == rows.toLong() * 4)
        val bytes = ByteBuffer.wrap(ownerFile.readBytes()).order(ByteOrder.LITTLE_ENDIAN).asIntBuffer()
        owners = IntArray(rows).also { bytes.get(it) }
        require(owners.all { it in 0 until wines })
    }
    fun score(query: FloatArray, aggregation: String): FloatArray {
        require(query.size == dimension && query.all { it.isFinite() })
        val k = when (aggregation) {
            "max" -> 1
            "top2-mean" -> 2
            "top3-mean" -> 3
            else -> error("Unknown reference aggregation.")
        }
        val result = TopMean(wines, k)
        FileInputStream(matrix).channel.use { channel ->
            var start = 0
            while (start < rows) {
                val count = minOf(blockRows, rows - start)
                buffer.clear()
                buffer.limit(count * dimension * 4)
                while (buffer.hasRemaining()) check(channel.read(buffer) > 0) { "Truncated reference matrix." }
                buffer.flip()
                val values = NativeDot.score(buffer, count, dimension, query)
                for (index in values.indices) result.add(owners[start + index], values[index])
                start += count
            }
        }
        return result.result()
    }
}
