package com.alolalab.chtozavino

import org.junit.Assert.*
import org.junit.Test
import java.io.File
import kotlin.math.ln

class ProductionPipelineTest {
    @Test fun `unmeasured phones retain the dual GPU guard`() {
        assertTrue(verifiedDualGpuDevice("Google", "Pixel 8"))
        assertFalse(verifiedDualGpuDevice("Google", "Pixel 8 Pro"))
        assertFalse(verifiedDualGpuDevice("Other", "Pixel 8"))
    }

    @Test fun `new and invalid preferences select the measured custom pipeline`() {
        assertEquals(RecognitionPipeline.DIS768_CUSTOM, RecognitionPipeline.fromPreference(null))
        assertEquals(RecognitionPipeline.DIS768_CUSTOM, RecognitionPipeline.fromPreference("invalid"))
        assertEquals(RecognitionPipeline.STANDARD, RecognitionPipeline.fromPreference("STANDARD"))
    }

    @Test fun `switching changes both graph and reference files without changing standard bytes`() {
        val base = InstalledModelPack(File("fixture"), ModelPackManifest(7, "test", 2093, 2093,
            2093, 0, emptyMap(), sigLip2Runtime = COMPLETE_NAFLEX_RUNTIME))
        val custom = base.forPipeline(RecognitionPipeline.DIS768_CUSTOM)
        assertEquals(CUSTOM_MODEL_FILE, custom.file(COMPLETE_NAFLEX_MODEL_FILE).name)
        assertEquals(CUSTOM_MANIFEST_FILE, custom.file(COMPLETE_NAFLEX_MANIFEST_FILE).name)
        assertEquals(CUSTOM_VECTORS_FILE, custom.file("vectors.f32").name)
        assertEquals(CUSTOM_CANDIDATES_FILE, custom.file("candidates.jsonl").name)
        assertEquals(CUSTOM_DIS_FILE, custom.file("dis.tflite").name)
        assertEquals("wines.jsonl", custom.file("wines.jsonl").name)
        assertEquals(FOREGROUND_POOLING_MODE, custom.manifest.poolingMode)
        val standard = custom.forPipeline(RecognitionPipeline.STANDARD)
        assertEquals(COMPLETE_NAFLEX_MODEL_FILE, standard.file(COMPLETE_NAFLEX_MODEL_FILE).name)
        assertEquals("vectors.f32", standard.file("vectors.f32").name)
        assertEquals(STANDARD_POOLING_MODE, standard.manifest.poolingMode)
        assertEquals(RecognitionPipeline.STANDARD, base.copy(manifest = base.manifest.copy(formatVersion = 6))
            .forPipeline(RecognitionPipeline.DIS768_CUSTOM).pipeline)
    }

    @Test fun `custom log weights preserve fractional coverage and masked padding`() {
        val weights = CustomPooling.logWeights(floatArrayOf(0f, .5f, 1f), 5)
        assertArrayEquals(floatArrayOf(ln(.1f), ln(.55f), 0f, 0f, 0f), weights, .000001f)
    }

    @Test fun `coverage uses whole patches and preserves constant masks`() {
        assertArrayEquals(floatArrayOf(.25f, .25f),
            CustomPooling.coverage(FloatArray(35 * 70) { .25f }, 35, 70, 1, 2), .000001f)
        val mask = FloatArray(32 * 16) { if (it % 32 < 16) 1f else 0f }
        assertArrayEquals(floatArrayOf(1f, 0f), CustomPooling.coverage(mask, 32, 16, 2, 1), .000001f)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `nonfinite weights cannot enter the model`() { CustomPooling.logWeights(floatArrayOf(Float.NaN)) }
}
