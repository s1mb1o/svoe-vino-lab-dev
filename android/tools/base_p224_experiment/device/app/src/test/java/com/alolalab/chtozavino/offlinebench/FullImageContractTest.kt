package com.alolalab.chtozavino.offlinebench

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject

class FullImageContractTest {
    @Test fun alphaDiscardPreservesRgbAndRowPadding() {
        val raw=byteArrayOf(1,2,3,0,4,5,6,127,99,98,97,96,7,8,9,0,10,11,12,127,95,94,93,92)
        val expected=raw.copyOf()
        for(index in listOf(3,7,15,19))expected[index]=0xff.toByte()
        discardAlpha(raw,2,2,12)
        assertArrayEquals(expected,raw)
    }
    @Test(expected=IllegalArgumentException::class)
    fun alphaDiscardRejectsInvalidStride() { discardAlpha(ByteArray(16),2,2,4) }
    private fun row(number: Int)=JSONObject().put("number",number).put("name","full-image")
        .put("budget",512).put("pooling",if(number==5)"standard" else "fractional-bg010")
        .put("query_frame","full-image").put("segmenter",if(number==5)"NONE" else "CPU")
        .put("reference_policy",if(number==5)"production-standard" else "previous-matched-custom")
        .put("model_manifest","model.json").put("vectors","vectors.f32").put("model_sha256","sha")
        .put("effective_profile",JSONObject().put("parameters",JSONObject().put("max_num_patches",512)
            .put("pooling",if(number==5)"standard" else "fractional-bg010")))
    @Test fun fullImageProfilesRejectCropping() {
        for(n in listOf(5,6)) {
            assertEquals("full-image",BaseCondition.parse(row(n)).queryFrame)
            try { BaseCondition.parse(row(n).put("query_frame","bottle-crop-white"));fail() }
            catch(expected: IllegalArgumentException) { }
        }
    }
    @Test fun fullImageProfilesKeepReferencePoliciesSeparate() {
        assertEquals("NONE",BaseCondition.parse(row(5)).segmenter)
        assertEquals("CPU",BaseCondition.parse(row(6)).segmenter)
        try { BaseCondition.parse(row(6).put("reference_policy","production-standard"));fail() }
        catch(expected: IllegalArgumentException) { }
    }
    @Test fun fullMaskCoordinatesAreNotCropped() {
        val mask=DenseMask(floatArrayOf(0f,1f,0f,1f),2,2,2,2)
        assertArrayEquals(floatArrayOf(0f,1f,0f,1f),fullImageCoverage(mask,2,2),1e-7f)
        assertArrayEquals(FloatArray(6) { 1f },fullImageCoverage(null,3,2),1e-7f)
    }
    @Test(expected=IllegalArgumentException::class)
    fun rejectsMaskFromDifferentGeometry() {
        fullImageCoverage(DenseMask(floatArrayOf(1f),1,1,2,2),3,2)
    }
}
