package com.alolalab.chtozavino.offlinebench

import android.graphics.Bitmap
import java.nio.ByteBuffer
import java.security.MessageDigest

internal fun fullImageCoverage(mask: DenseMask?,width: Int,height: Int): FloatArray {
    require(width>0 && height>0)
    if(mask==null)return FloatArray(width*height) { 1f }
    require(mask.sourceWidth==width && mask.sourceHeight==height)
    return FloatArray(width*height) { index -> mask.sample(index%width+.5,index/width+.5).coerceIn(0f,1f) }
}

internal fun fullImageFrame(source: Bitmap,mask: DenseMask?): MattingFrame {
    // Copy ownership only. Do not draw, crop, composite, rotate, or resize RGB.
    val copy=checkNotNull(source.copy(Bitmap.Config.ARGB_8888,false))
    try {
        return MattingFrame(copy,fullImageCoverage(mask,source.width,source.height),null,
            0.0,source.width,source.height,1.0)
    } catch(error: Throwable) { copy.recycle();throw error }
}

internal fun bitmapRgb(bitmap: Bitmap): ByteArray {
    require(bitmap.config==Bitmap.Config.ARGB_8888 && !bitmap.hasAlpha())
    val buffer=ByteBuffer.allocate(bitmap.byteCount);bitmap.copyPixelsToBuffer(buffer)
    val raw=buffer.array();val rgb=ByteArray(bitmap.width*bitmap.height*3)
    val rowBytes=bitmap.rowBytes;val width=bitmap.width;val height=bitmap.height
    for(y in 0 until height) for(x in 0 until width) {
        val source=y*rowBytes+x*4;val target=(y*width+x)*3
        raw.copyInto(rgb,target,source,source+3)
    }
    return rgb
}

internal fun bitmapPixelSha(bitmap: Bitmap): String = MessageDigest.getInstance("SHA-256")
    .digest(bitmapRgb(bitmap)).joinToString("") { "%02x".format(it.toInt() and 255) }
