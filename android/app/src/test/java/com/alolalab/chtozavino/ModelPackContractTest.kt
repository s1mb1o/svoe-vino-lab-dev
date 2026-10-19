package com.alolalab.chtozavino

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class ModelPackContractTest {
    @Test
    fun `legacy contract keeps the fixed 768 dimensional runtime`() {
        val contract = parseModelPackContract(
            JSONObject()
                .put("format", "svoe-vino-android-model-pack")
                .put("format_version", 3)
                .put("pipeline", LEGACY_PIPELINE_ID)
                .put("model", LEGACY_SIGLIP_MODEL)
                .put("vector_dim", LEGACY_VECTOR_DIMENSION),
        )

        assertFalse(contract.isNaFlex)
        assertEquals(LEGACY_SIGLIP_RUNTIME, contract.sigLip2Runtime)
        assertEquals(LEGACY_VECTOR_DIMENSION, contract.vectorDimension)
    }

    @Test
    fun `version four accepts the exact p512 NaFlex split`() {
        val contract = parseModelPackContract(naFlexManifest())

        assertTrue(contract.isNaFlex)
        assertEquals(NAFLEX_SIGLIP_RUNTIME, contract.sigLip2Runtime)
        assertEquals(NAFLEX_VECTOR_DIMENSION, contract.vectorDimension)
        assertEquals(512, contract.maxNumPatches)
    }

    @Test
    fun `version four rejects a legacy vector dimension`() {
        val manifest = naFlexManifest().put("vector_dim", LEGACY_VECTOR_DIMENSION)

        assertThrows(ModelPackException::class.java) {
            parseModelPackContract(manifest)
        }
    }

    @Test
    fun `version four rejects an unsupported patch limit`() {
        val manifest = naFlexManifest().put("max_num_patches", 384)

        assertThrows(ModelPackException::class.java) {
            parseModelPackContract(manifest)
        }
    }

    @Test
    fun `version five accepts Base NaFlex with foreground pooling`() {
        val contract = parseModelPackContract(baseNaFlexManifest())

        assertTrue(contract.isNaFlex)
        assertEquals(BASE_NAFLEX_VECTOR_DIMENSION, contract.vectorDimension)
        assertEquals(FOREGROUND_POOLING_MODE, contract.poolingMode)
        assertEquals(TOP2_MEAN_REFERENCE_AGGREGATION, contract.referenceAggregation)
        assertFalse(contract.gpuCompatible)
    }

    @Test
    fun `version five rejects the SO400M dimension`() {
        val manifest = baseNaFlexManifest().put("vector_dim", NAFLEX_VECTOR_DIMENSION)

        assertThrows(ModelPackException::class.java) {
            parseModelPackContract(manifest)
        }
    }

    @Test
    fun `version five records an explicit validated GPU`() {
        val contract = parseModelPackContract(baseNaFlexManifest().put("gpu_compatible", true))

        assertTrue(contract.gpuCompatible)
    }

    private fun naFlexManifest(): JSONObject = JSONObject()
        .put("format", "svoe-vino-android-model-pack")
        .put("format_version", 4)
        .put("pipeline", NAFLEX_PIPELINE_ID)
        .put("model", NAFLEX_SIGLIP_MODEL)
        .put("siglip2_runtime", NAFLEX_SIGLIP_RUNTIME)
        .put("vector_dim", NAFLEX_VECTOR_DIMENSION)
        .put("patch_size", NAFLEX_PATCH_SIZE)
        .put("max_num_patches", 512)
        .put("position_embedding_grid", 16)

    private fun baseNaFlexManifest(): JSONObject = JSONObject()
        .put("format", "svoe-vino-android-model-pack")
        .put("format_version", 5)
        .put("pipeline", NAFLEX_PIPELINE_ID)
        .put("model", BASE_NAFLEX_SIGLIP_MODEL)
        .put("siglip2_runtime", NAFLEX_SIGLIP_RUNTIME)
        .put("vector_dim", BASE_NAFLEX_VECTOR_DIMENSION)
        .put("patch_size", NAFLEX_PATCH_SIZE)
        .put("max_num_patches", 256)
        .put("position_embedding_grid", 16)
        .put("pooling_mode", FOREGROUND_POOLING_MODE)
        .put("reference_aggregation", TOP2_MEAN_REFERENCE_AGGREGATION)
}
