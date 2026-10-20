package com.alolalab.chtozavino.offlinebench

import android.graphics.Bitmap
import android.graphics.ImageDecoder
import java.io.File
import java.nio.ByteBuffer

internal fun discardAlpha(bytes: ByteArray,width: Int,height: Int,rowBytes: Int) {
    require(width>0 && height>0 && rowBytes>=width*4 && bytes.size>=height*rowBytes)
    for(y in 0 until height) for(x in 0 until width) bytes[y*rowBytes+x*4+3]=0xff.toByte()
}

internal fun decodeFullImage(file: File): Bitmap {
    // Match production BitmapLoader.decode(..., fullResolution=true), not a display conversion.
    val decoded=ImageDecoder.decodeBitmap(ImageDecoder.createSource(file)) { decoder,info,_ ->
        require(info.size.width.toLong()*info.size.height<=24_000_000)
        decoder.allocator=ImageDecoder.ALLOCATOR_SOFTWARE
        decoder.isUnpremultipliedRequired=true
        decoder.isMutableRequired=true
        info.colorSpace?.let(decoder::setTargetColorSpace)
    }
    val bitmap=if(decoded.config==Bitmap.Config.ARGB_8888)decoded
        else checkNotNull(decoded.copy(Bitmap.Config.ARGB_8888,true)).also { decoded.recycle() }
    if(bitmap.hasAlpha()) {
        val buffer=ByteBuffer.allocate(bitmap.byteCount)
        bitmap.copyPixelsToBuffer(buffer)
        discardAlpha(buffer.array(),bitmap.width,bitmap.height,bitmap.rowBytes)
        buffer.rewind();bitmap.copyPixelsFromBuffer(buffer)
        bitmap.setHasAlpha(false);bitmap.setPremultiplied(true)
    }
    return bitmap
}
