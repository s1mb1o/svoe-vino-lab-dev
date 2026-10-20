package com.alolalab.chtozavino

import kotlin.math.abs
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min

/** Fractional coverage uses the same separable filter and rounding as the measured pilot. */
internal object CustomPooling {
    private data class Weights(val start: Int, val values: DoubleArray)

    private fun weights(input: Int, output: Int): Array<Weights> {
        require(input > 0 && output > 0)
        val scale = input.toDouble() / output
        val filterScale = max(1.0, scale)
        return Array(output) { index ->
            val center = (index + .5) * scale
            val start = max(0, (center - filterScale + .5).toInt())
            val end = min(input, (center + filterScale + .5).toInt())
            val values = DoubleArray(end - start) {
                val distance = (it + start - center + .5) * (1.0 / filterScale)
                max(0.0, 1 - abs(distance))
            }
            val sum = values.sum()
            require(sum > 0)
            Weights(start, DoubleArray(values.size) { values[it] / sum })
        }
    }

    fun coverage(mask: FloatArray, width: Int, height: Int, gw: Int, gh: Int): FloatArray {
        require(mask.size == width * height && mask.all { it.isFinite() && it in 0f..1f })
        require(gw > 0 && gh > 0 && gw * gh <= 512)
        val rw = gw * 16
        val rh = gh * 16
        val xs = weights(width, rw)
        val ys = weights(height, rh)
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
            sums[(y / 16) * gw + x / 16] += value.toFloat().coerceIn(0f, 1f)
        }
        return FloatArray(sums.size) { (sums[it] / 256).toFloat() }
    }

    fun logWeights(foreground: FloatArray, budget: Int = 512): FloatArray {
        require(foreground.isNotEmpty() && foreground.size <= budget)
        require(foreground.all { it.isFinite() && it in 0f..1f })
        return FloatArray(budget) { index ->
            if (index >= foreground.size) 0f
            else ln(.1f * (1 - foreground[index]) + foreground[index])
        }
    }
}
