package com.alolalab.chtozavino

import org.junit.Assert.assertThrows
import org.junit.Test

class NaFlexAcceleratorAgreementTest {
    private fun vector() = FloatArray(768).also { it[0] = 1f }

    @Test
    fun `matching vectors pass`() = validateNaFlexAcceleratorAgreement(vector(), vector())

    @Test
    fun `finite incompatible GPU vectors fail`() {
        val gpu = vector().also { it[0] = 0.8f; it[1] = 0.6f }
        assertThrows(ImageRecognitionException::class.java) {
            validateNaFlexAcceleratorAgreement(gpu, vector())
        }
    }

    @Test
    fun `zero nonfinite and wrong dimensions fail`() {
        listOf(FloatArray(768), vector().also { it[5] = Float.NaN }, FloatArray(1152))
            .forEach { gpu ->
                assertThrows(ImageRecognitionException::class.java) {
                    validateNaFlexAcceleratorAgreement(gpu, vector())
                }
            }
    }
}
