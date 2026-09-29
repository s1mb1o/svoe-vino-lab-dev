package com.alolalab.chtozavino

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AcceleratorSettingsTest {
    @Test
    fun unknownModeUsesAuto() {
        assertEquals(AcceleratorMode.AUTO, AcceleratorMode.fromPreference("OTHER"))
    }

    @Test
    fun autoUsesDetectedAcceleratorsAndAllowsSafeFallback() {
        val settings = recognitionAccelerators(
            disMode = AcceleratorMode.AUTO,
            sigLip2Mode = AcceleratorMode.AUTO,
            automaticDis = ModelAccelerator.GPU,
            automaticSigLip2 = ModelAccelerator.CPU,
        )

        assertEquals(ModelAccelerator.GPU, settings.dis)
        assertEquals(ModelAccelerator.CPU, settings.sigLip2)
        assertTrue(settings.allowDisCpuFallback)
        assertTrue(settings.allowSigLip2CpuFallback)
    }

    @Test
    fun unresolvedAutoUsesCpu() {
        val settings = recognitionAccelerators(
            disMode = AcceleratorMode.AUTO,
            sigLip2Mode = AcceleratorMode.AUTO,
            automaticDis = null,
            automaticSigLip2 = null,
        )

        assertEquals(ModelAccelerator.CPU, settings.dis)
        assertEquals(ModelAccelerator.CPU, settings.sigLip2)
    }

    @Test
    fun explicitGpuDoesNotEnableAutomaticFallback() {
        val settings = recognitionAccelerators(
            disMode = AcceleratorMode.GPU,
            sigLip2Mode = AcceleratorMode.GPU,
            automaticDis = ModelAccelerator.CPU,
            automaticSigLip2 = ModelAccelerator.CPU,
        )

        assertEquals(ModelAccelerator.GPU, settings.dis)
        assertEquals(ModelAccelerator.GPU, settings.sigLip2)
        assertFalse(settings.allowDisCpuFallback)
        assertFalse(settings.allowSigLip2CpuFallback)
    }
}
