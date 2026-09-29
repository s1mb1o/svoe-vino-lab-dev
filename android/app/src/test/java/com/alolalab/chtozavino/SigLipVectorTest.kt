package com.alolalab.chtozavino

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class SigLipVectorTest {
    @Test
    fun normalizesAValidVector() {
        assertArrayEquals(
            floatArrayOf(0.6f, 0.8f),
            normalizeSigLipVector(floatArrayOf(3f, 4f), expectedSize = 2),
            0.0001f,
        )
    }

    @Test
    fun rejectsAnEmptyVector() {
        assertThrows(ImageRecognitionException::class.java) {
            normalizeSigLipVector(floatArrayOf(0f, 0f), expectedSize = 2)
        }
    }

    @Test
    fun rejectsANonFiniteVector() {
        assertThrows(ImageRecognitionException::class.java) {
            normalizeSigLipVector(floatArrayOf(1f, Float.NaN), expectedSize = 2)
        }
    }

    @Test
    fun rejectsAnUnexpectedSize() {
        assertThrows(ImageRecognitionException::class.java) {
            normalizeSigLipVector(floatArrayOf(1f), expectedSize = 2)
        }
    }
}
