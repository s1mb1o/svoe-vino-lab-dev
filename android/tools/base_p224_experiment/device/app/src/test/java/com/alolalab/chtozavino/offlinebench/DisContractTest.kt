package com.alolalab.chtozavino.offlinebench

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import org.json.JSONArray
import com.google.ai.edge.litert.CompiledModel

class DisContractTest {
    private fun metadata(size: Int)=JSONObject().put("precision","float32")
        .put("input_shape",JSONArray(listOf(1,3,size,size)))
        .put("output_shape",JSONArray(listOf(1,1,size,size)))
    @Test fun disSupportsOnlyVerifiedSquareInputSizes() {
        for(size in listOf(512,768,1024))assertEquals(size,disInputSize(metadata(size)))
        try { disInputSize(metadata(640));fail() } catch(expected: IllegalArgumentException) { }
    }
    @Test fun disRejectsWrongInputChannelsAndOutputSize() {
        for(invalid in listOf(metadata(512).put("input_shape",JSONArray(listOf(1,1,512,512))),
            metadata(768).put("output_shape",JSONArray(listOf(1,1,1024,1024))),metadata(512).put("precision","float16"))) {
            try { disInputSize(invalid);fail() } catch(expected: IllegalArgumentException) { }
        }
    }
    @Test fun disUsesFp32WithoutForcedBuffers() {
        val options=requireNotNull(disOptions().gpuOptions)
        assertEquals(CompiledModel.GpuOptions.Precision.FP32,options.precision)
        assertEquals(CompiledModel.GpuOptions.BufferStorageType.DEFAULT,options.bufferStorageType)
        assertEquals(false,options.serializeProgramCache)
    }
    private fun row(number: Int)=JSONObject().put("number",number).put("name","DIS")
        .put("budget",512).put("pooling","fractional-bg010")
        .put("query_frame",if(number==7)"full-image" else "bottle-crop-white")
        .put("segmenter","GPU").put("segmenter_model","DIS")
        .put("reference_policy","previous-matched-custom")
        .put("model_manifest","model.json").put("vectors","vectors.f32").put("model_sha256","sha")
        .put("effective_profile",JSONObject().put("parameters",JSONObject()
            .put("max_num_patches",512).put("pooling","fractional-bg010")))
    @Test fun normalizedMaskMatchesProduction() {
        assertArrayEquals(floatArrayOf(0f,.5f,1f),normalizedDisMask(floatArrayOf(2f,3f,4f)),1e-7f)
    }
    @Test(expected=IllegalArgumentException::class)
    fun constantMaskFails() { normalizedDisMask(FloatArray(4)) }
    @Test(expected=IllegalArgumentException::class)
    fun nonfiniteMaskFails() { normalizedDisMask(floatArrayOf(0f,Float.NaN)) }
    @Test fun disConditionsKeepFramesSeparate() {
        assertEquals("full-image",BaseCondition.parse(row(7)).queryFrame)
        assertEquals("bottle-crop-white",BaseCondition.parse(row(8)).queryFrame)
        try { BaseCondition.parse(row(7).put("query_frame","bottle-crop-white"));fail() }
        catch(expected: IllegalArgumentException) { }
    }
    @Test fun disConditionsRejectWrongModelOrAccelerator() {
        for(change in listOf("segmenter_model" to "YOLO","segmenter" to "CPU",
            "reference_policy" to "production-standard")) {
            try { BaseCondition.parse(row(7).put(change.first,change.second));fail() }
            catch(expected: IllegalArgumentException) { }
        }
    }
}
