package com.alolalab.chtozavino.offlinebench

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import kotlin.math.*

internal data class MattingFrame(val bitmap: Bitmap, val foreground: FloatArray,
                                 val label: FloatArray?, val angle: Double,
                                 val sourceCropWidth: Int, val sourceCropHeight: Int,
                                 val renderScale: Double) : AutoCloseable {
    override fun close() { bitmap.recycle() }
}

internal fun renderFrame(source: Bitmap, matte: DenseMask, label: DenseMask?,
                         angle: Double, margin: Double = 0.0): MattingFrame {
    val bounds = MaskGeometry.bounds(matte, angle)
    val dx = (bounds.right - bounds.left) * margin
    val dy = (bounds.bottom - bounds.top) * margin
    val left = floor(bounds.left - dx)
    val top = floor(bounds.top - dy)
    val width = ceil(bounds.right + dx - left).toInt().coerceAtLeast(1)
    val height = ceil(bounds.bottom + dy - top).toInt().coerceAtLeast(1)
    // The frozen desktop campaign also limits prepared RGB to a 1024-pixel long edge.
    val scale = min(1.0, 1024.0 / max(width,height))
    val outputWidth = max(1,round(width * scale).toInt())
    val outputHeight = max(1,round(height * scale).toInt())
    val sx = outputWidth.toDouble() / width
    val sy = outputHeight.toDouble() / height
    val c = cos(Math.toRadians(angle))
    val s = sin(Math.toRadians(angle))
    val transform = Matrix().apply {
        setValues(floatArrayOf((c*sx).toFloat(),(s*sx).toFloat(),(-left*sx).toFloat(),
            (-s*sy).toFloat(),(c*sy).toFloat(),(-top*sy).toFloat(),0f,0f,1f))
    }
    val image = Bitmap.createBitmap(outputWidth,outputHeight,Bitmap.Config.ARGB_8888)
    try {
        val canvas = Canvas(image)
        canvas.drawColor(Color.WHITE)
        canvas.drawBitmap(source,transform,Paint(Paint.FILTER_BITMAP_FLAG))
        val pixels = IntArray(outputWidth * outputHeight)
        image.getPixels(pixels,0,outputWidth,0,0,outputWidth,outputHeight)
        val foreground = FloatArray(pixels.size)
        val labelValues = if(label == null) null else FloatArray(pixels.size)
        for (y in 0 until outputHeight) for (x in 0 until outputWidth) {
            val xx = left + (x+.5)/sx
            val yy = top + (y+.5)/sy
            val sourceX = xx*c-yy*s
            val sourceY = xx*s+yy*c
            val index = y * outputWidth + x
            val alpha = matte.sample(sourceX,sourceY).coerceIn(0f,1f)
            foreground[index] = alpha
            if (labelValues != null) labelValues[index] = label!!.sample(sourceX,sourceY).coerceIn(0f,1f)
            val color = pixels[index]
            fun channel(shift: Int) = ((((color ushr shift) and 255)*alpha + 255*(1-alpha))+.5f).toInt().coerceIn(0,255)
            pixels[index] = Color.rgb(channel(16),channel(8),channel(0))
        }
        image.setPixels(pixels,0,outputWidth,0,0,outputWidth,outputHeight)
        return MattingFrame(image,foreground,labelValues,angle,width,height,scale)
    } catch (error: Throwable) {
        image.recycle()
        throw error
    }
}
