package com.alolalab.chtozavino.offlinebench

import kotlin.math.exp
import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject

class PoolingContractTest {
    @Test fun fractionalBottleAreaHasDeclaredWeights() {
        val values=bottleLogWeights(floatArrayOf(0f,.5f,1f),224,true)
        assertEquals(.1f,exp(values[0]),1e-7f);assertEquals(.55f,exp(values[1]),1e-7f)
        assertEquals(1f,exp(values[2]),1e-7f);assertTrue(values.drop(3).all { it==0f })
    }
    @Test fun standardAndPaddingKeepZeroBias() {
        assertTrue(bottleLogWeights(floatArrayOf(0f,1f),224,false).all { it==0f })
    }
    @Test fun invalidCoverageIsRejected() {
        for(values in listOf(floatArrayOf(),floatArrayOf(Float.NaN),floatArrayOf(-.1f),floatArrayOf(1.1f))) {
            try { bottleLogWeights(values,224,true);fail("Expected invalid coverage") }
            catch(expected: IllegalArgumentException) { }
        }
    }
    private fun condition(number: Int,budget: Int,pooling: String)=JSONObject()
        .put("number",number).put("name","test").put("budget",budget).put("pooling",pooling)
        .put("model_manifest","model.json").put("vectors","vectors.f32").put("model_sha256","sha")
        .put("effective_profile",JSONObject().put("parameters",JSONObject()
            .put("max_num_patches",budget).put("pooling",pooling)))
    @Test fun budgetsAreTiedToConditionIdentity() {
        assertEquals(224,BaseCondition.parse(condition(1,224,"standard")).budget)
        assertEquals(512,BaseCondition.parse(condition(3,512,"standard")).budget)
        assertThrows(IllegalArgumentException::class.java) { BaseCondition.parse(condition(1,512,"standard")) }
    }
    @Test fun customPoolingCannotUseStandardIdentity() {
        assertThrows(IllegalArgumentException::class.java) { BaseCondition.parse(condition(2,224,"standard")) }
        assertThrows(IllegalArgumentException::class.java) { BaseCondition.parse(condition(3,512,"fractional-bg010")) }
    }
    @Test fun emptyBottleCannotProduceAFullImageFallback() {
        assertThrows(IllegalArgumentException::class.java) { DenseMask(FloatArray(16),4,4,40,40).hull() }
    }
    @Test fun p512CustomUsesConditionFour() {
        val custom=BaseCondition.parse(condition(4,512,"fractional-bg010"))
        assertEquals(512,custom.budget)
        assertThrows(IllegalArgumentException::class.java) { BaseCondition.parse(condition(4,224,"fractional-bg010")) }
        assertThrows(IllegalArgumentException::class.java) { BaseCondition.parse(condition(4,512,"standard")) }
    }
    @Test fun p512CoverageHasTheSameFormulaAndZeroPadding() {
        val actual=bottleLogWeights(floatArrayOf(0f,.5f,1f),512,true)
        assertEquals(512,actual.size)
        assertEquals(.1f,exp(actual[0]),1e-7f);assertEquals(.55f,exp(actual[1]),1e-7f)
        assertEquals(1f,exp(actual[2]),1e-7f);assertTrue(actual.drop(3).all { it==0f })
    }
}
