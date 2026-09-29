package com.alolalab.chtozavino

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class DisMaskTest {
    @Test
    fun normalizesTheMeasuredLiteRtOutputRange() {
        val mask = floatArrayOf(0.5f, 0.6155f, 0.731f)

        assertArrayEquals(floatArrayOf(0f, 0.5f, 1f), normalizeDisMask(mask), 0.0001f)
    }

    @Test
    fun rejectsAFlatMask() {
        assertThrows(ImageRecognitionException::class.java) {
            normalizeDisMask(floatArrayOf(0.5f, 0.5f))
        }
    }

    @Test
    fun rejectsANonFiniteMask() {
        assertThrows(ImageRecognitionException::class.java) {
            normalizeDisMask(floatArrayOf(0f, Float.NaN, 1f))
        }
    }

    @Test
    fun rejectsAnUnexpectedSize() {
        assertThrows(ImageRecognitionException::class.java) {
            validateDisOutput(floatArrayOf(0f, 1f), expectedSize = 3)
        }
    }
}
