package com.alolalab.chtozavino.offlinebench

import kotlin.math.abs
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min
import kotlin.math.round

internal object MaskCoverage {
    private data class Weights(val start: Int, val values: DoubleArray)
    private fun weights(input: Int, output: Int, box: Boolean): Array<Weights> {
        val scale = input.toDouble() / output
        val filterScale = max(1.0, scale)
        val support = filterScale * if (box) .5 else 1.0
        return Array(output) { index ->
            val center = (index + .5) * scale
            val start = max(0, (center - support + .5).toInt())
            val end = min(input, (center + support + .5).toInt())
            val values = DoubleArray(end - start) {
                val distance = (it + start - center + .5) * (1.0 / filterScale)
                if (box) { if (distance > -.5 && distance <= .5) 1.0 else 0.0 }
                else max(0.0, 1 - abs(distance))
            }
            val sum = values.sum()
            require(sum > 0)
            Weights(start, DoubleArray(values.size) { values[it] / sum })
        }
    }
    /** Pillow 11.3 L-image BOX uses 22-bit coefficients and rounds after each axis. */
    fun legacy(mask: FloatArray, width: Int, height: Int, gw: Int, gh: Int): FloatArray {
        require(mask.size == width * height)
        val xs = weights(width, gw, true)
        val ys = weights(height, gh, true)
        val precision = 1 shl 22
        val rounding = 1 shl 21
        val xCoefficients = xs.map { w -> IntArray(w.values.size) { (w.values[it]*precision+.5).toInt() } }
        val yCoefficients = ys.map { w -> IntArray(w.values.size) { (w.values[it]*precision+.5).toInt() } }
        val horizontal = IntArray(gw * height)
        for (y in 0 until height) for (x in 0 until gw) {
            val w = xs[x]
            var value = rounding
            for (i in w.values.indices) value += round(mask[y * width + w.start + i].coerceIn(0f,1f) * 255).toInt() * xCoefficients[x][i]
            horizontal[y * gw + x] = (value shr 22).coerceIn(0,255)
        }
        return FloatArray(gw * gh) { index ->
            val y = index / gw
            val x = index % gw
            val w = ys[y]
            var value = rounding
            for (i in w.values.indices) value += horizontal[(w.start + i) * gw + x] * yCoefficients[y][i]
            (value shr 22).coerceIn(0,255) / 255f
        }
    }
    /** Float masks use the actual NaFlex resize and 16x16 patch coverage. */
    fun exact(mask: FloatArray, width: Int, height: Int, gw: Int, gh: Int): FloatArray {
        require(mask.size == width * height)
        val rw = gw * 16
        val rh = gh * 16
        val xs = weights(width, rw, false)
        val ys = weights(height, rh, false)
        val horizontal = FloatArray(rw * height)
        for (y in 0 until height) for (x in 0 until rw) {
            val w = xs[x]
            var value = 0.0
            for (i in w.values.indices) value += mask[y * width + w.start + i] * w.values[i]
            horizontal[y * rw + x] = value.toFloat()
        }
        val sums = DoubleArray(gw * gh)
        for (y in 0 until rh) for (x in 0 until rw) {
            val w = ys[y]
            var value = 0.0
            for (i in w.values.indices) value += horizontal[(w.start + i) * rw + x] * w.values[i]
            sums[(y / 16) * gw + x / 16] += value.toFloat().coerceIn(0f,1f)
        }
        return FloatArray(sums.size) { (sums[it] / 256).toFloat() }
    }
    fun logWeights(foreground: FloatArray, label: FloatArray?, budget: Int,
                   background: Float, boost: Float): FloatArray {
        require(foreground.isNotEmpty() && foreground.size <= budget)
        require(label == null || label.size == foreground.size)
        var total = 0f
        val weights = FloatArray(budget)
        for (i in foreground.indices) {
            val f = foreground[i].coerceIn(0f,1f)
            val l = min(f, label?.get(i)?.coerceIn(0f,1f) ?: 0f)
            val value = background * (1 - f) + f + (boost - 1) * l
            require(value.isFinite() && value >= 0)
            weights[i] = value
            total += value
        }
        // Match the declared desktop zero-sum policy, without unmasking padding.
        if (total == 0f) for (i in foreground.indices) weights[i] = 1f
        return FloatArray(budget) { i ->
            if (i >= foreground.size) 0f else if (weights[i] > 0f) ln(weights[i]) else -10000f
        }
    }
}
