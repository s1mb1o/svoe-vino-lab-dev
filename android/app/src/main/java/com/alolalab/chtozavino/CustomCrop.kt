package com.alolalab.chtozavino

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.round

internal data class CustomCrop(val image: Bitmap, val crop: Bitmap, val foreground: FloatArray)

/** Preserve the measured zero-rotation renderer, including margins outside the source. */
internal fun customCrop(source: Bitmap, mask: SegmentationMask): CustomCrop {
    require(mask.values.size == mask.width * mask.height)
    require(mask.values.all { it.isFinite() && it in 0f..1f })
    var minX = mask.width
    var minY = mask.height
    var maxX = -1
    var maxY = -1
    var points = 0
    for (y in 0 until mask.height) {
        var first = mask.width
        var last = -1
        for (x in 0 until mask.width) if (mask.values[y * mask.width + x] >= .5f) {
            first = min(first, x); last = max(last, x)
        }
        if (last >= 0) {
            points += if (first == last) 1 else 2
            minX = min(minX, first); maxX = max(maxX, last)
            minY = min(minY, y); maxY = max(maxY, y)
        }
    }
    if (points < 3) throw ImageRecognitionException("DIS не нашёл главный объект. Снимите бутылку ближе.")
    val cellWidth = source.width.toDouble() / mask.width
    val cellHeight = source.height.toDouble() / mask.height
    val boundLeft = (minX + .5) * cellWidth - cellWidth / 2
    val boundRight = (maxX + .5) * cellWidth + cellWidth / 2
    val boundTop = (minY + .5) * cellHeight - cellHeight / 2
    val boundBottom = (maxY + .5) * cellHeight + cellHeight / 2
    val dx = (boundRight - boundLeft) * .04
    val dy = (boundBottom - boundTop) * .04
    val left = floor(boundLeft - dx)
    val top = floor(boundTop - dy)
    val width = ceil(boundRight + dx - left).toInt().coerceAtLeast(1)
    val height = ceil(boundBottom + dy - top).toInt().coerceAtLeast(1)
    val scale = min(1.0, 1024.0 / max(width, height))
    val outputWidth = max(1, round(width * scale).toInt())
    val outputHeight = max(1, round(height * scale).toInt())
    val sx = outputWidth.toDouble() / width
    val sy = outputHeight.toDouble() / height
    val transform = Matrix().apply {
        setValues(floatArrayOf(sx.toFloat(), 0f, (-left * sx).toFloat(),
            0f, sy.toFloat(), (-top * sy).toFloat(), 0f, 0f, 1f))
    }
    val image = Bitmap.createBitmap(outputWidth, outputHeight, Bitmap.Config.ARGB_8888)
    var crop: Bitmap? = null
    try {
        Canvas(image).apply {
            drawColor(Color.WHITE)
            drawBitmap(source, transform, Paint(Paint.FILTER_BITMAP_FLAG))
        }
        crop = image.copy(Bitmap.Config.ARGB_8888, false)
        val pixels = IntArray(outputWidth * outputHeight)
        image.getPixels(pixels, 0, outputWidth, 0, 0, outputWidth, outputHeight)
        fun sample(x: Double, y: Double): Float {
            if (x < 0 || y < 0 || x >= source.width || y >= source.height) return 0f
            val mx = (x / cellWidth - .5).coerceIn(0.0, mask.width - 1.0)
            val my = (y / cellHeight - .5).coerceIn(0.0, mask.height - 1.0)
            val ix = floor(mx).toInt(); val iy = floor(my).toInt()
            val fx = mx - ix; val fy = my - iy
            fun value(xx: Int, yy: Int): Float = if (xx in 0 until mask.width && yy in 0 until mask.height)
                mask.values[yy * mask.width + xx].coerceIn(0f, 1f) else 0f
            return ((1 - fy) * ((1 - fx) * value(ix, iy) + fx * value(ix + 1, iy)) +
                fy * ((1 - fx) * value(ix, iy + 1) + fx * value(ix + 1, iy + 1))).toFloat()
        }
        val foreground = FloatArray(pixels.size)
        for (y in 0 until outputHeight) for (x in 0 until outputWidth) {
            val alpha = sample(left + (x + .5) / sx, top + (y + .5) / sy).coerceIn(0f, 1f)
            val index = y * outputWidth + x
            foreground[index] = alpha
            val color = pixels[index]
            fun channel(shift: Int) = ((((color ushr shift) and 255) * alpha + 255 * (1 - alpha)) + .5f)
                .toInt().coerceIn(0, 255)
            pixels[index] = Color.rgb(channel(16), channel(8), channel(0))
        }
        image.setPixels(pixels, 0, outputWidth, 0, 0, outputWidth, outputHeight)
        return CustomCrop(image, checkNotNull(crop), foreground)
    } catch (error: Throwable) {
        crop?.recycle(); image.recycle(); throw error
    }
}
