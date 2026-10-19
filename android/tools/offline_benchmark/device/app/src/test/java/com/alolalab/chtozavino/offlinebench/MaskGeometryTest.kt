package com.alolalab.chtozavino.offlinebench

import kotlin.math.abs
import org.junit.Assert.*
import org.junit.Test

class MaskGeometryTest {
    @Test fun cardinalGuardHasStrictBoundary() {
        for(angle in listOf(0.0,4.99,-4.99,87.0,178.0,-88.0))assertEquals(0.0,MaskGeometry.guarded(angle),0.0)
        assertEquals(5.0,MaskGeometry.guarded(5.0),0.0)
        assertEquals(-5.0,MaskGeometry.guarded(-5.0),0.0)
        assertEquals(85.0,MaskGeometry.guarded(85.0),0.0)
    }
    @Test fun emptyMaskFailsWithoutFullImageFallback() {
        assertThrows(IllegalArgumentException::class.java) { DenseMask(FloatArray(16),4,4,40,40).hull() }
    }
    @Test fun sourceCoordinatesPreserveLetterboxPadding() {
        val mask=DenseMask(floatArrayOf(0f,1f,0f,1f),2,2,20,20,-10.0,0.0,20.0,10.0)
        assertEquals(1f,mask.sample(20.0-1e-6,5.0),1e-6f)
        assertEquals(0f,mask.sample(-1.0,5.0),0f)
        assertEquals(0f,mask.sample(1.0,21.0),0f)
    }
    @Test fun tallBottleStaysUprightAndInvertedNeckTurns() {
        val width=60;val height=150
        fun bottle(invert: Boolean): DenseMask {
            val pixels=FloatArray(width*height)
            for(y in 0 until height)for(x in 0 until width) {
                val yy=if(invert)height-1-y else y
                if(yy in 5..59 && x in 24..35 || yy in 60..144 && x in 10..49)pixels[y*width+x]=1f
            }
            return DenseMask(pixels,width,height,width,height)
        }
        assertEquals(0.0,MaskGeometry.bestAngle(bottle(false)),.1)
        assertEquals(180.0,abs(MaskGeometry.bestAngle(bottle(true))),.1)
    }
    @Test fun meanIsNormalized() {
        assertArrayEquals(floatArrayOf(.70710677f,.70710677f),unitMean(floatArrayOf(1f,0f),floatArrayOf(0f,1f)),1e-6f)
    }
}
