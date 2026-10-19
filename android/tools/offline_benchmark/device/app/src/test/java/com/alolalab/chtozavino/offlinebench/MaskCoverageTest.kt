package com.alolalab.chtozavino.offlinebench

import kotlin.math.exp
import org.junit.Assert.*
import org.junit.Test

class MaskCoverageTest {
    @Test fun legacyMatchesPillow113FixedCoefficientFixture() {
        val mask=FloatArray(17*13) { ((it*37+it/7*11)%256)/255f }
        val expected=intArrayOf(126,120,120,147,125,151,120,115,125,130,120,114,
            140,128,134,129,107,133,134,129,107,138,134,128)
        assertArrayEquals(FloatArray(expected.size) { expected[it]/255f },MaskCoverage.legacy(mask,17,13,4,6),0f)
    }
    @Test fun legacyBoxIncludesUpperBoundaryAndExcludesLowerBoundary() {
        val mask=FloatArray(6) { (it*37)/255f }
        val expected=intArrayOf(19,74,130,185)
        assertArrayEquals(FloatArray(4) { expected[it]/255f },MaskCoverage.legacy(mask,6,1,4,1),0f)
    }
    @Test fun fullCoverageStaysFullWithBothResizePaths() {
        val mask=FloatArray(49*113) { 1f }
        assertArrayEquals(FloatArray(7*11) { 1f },MaskCoverage.exact(mask,49,113,7,11),1e-6f)
        assertArrayEquals(FloatArray(7*11) { 1f },MaskCoverage.legacy(mask,49,113,7,11),1e-6f)
    }
    @Test fun labelIsClippedToForeground() {
        val bias=MaskCoverage.logWeights(floatArrayOf(0f,.5f,1f),floatArrayOf(1f,1f,1f),5,.1f,2f)
        assertArrayEquals(floatArrayOf(.1f,1.05f,2f),FloatArray(3) { exp(bias[it]) },1e-6f)
        assertEquals(0f,bias[3],0f)
    }
    @Test fun zeroSumUsesValidPatchesOnly() {
        assertArrayEquals(floatArrayOf(0f,0f,0f,0f),MaskCoverage.logWeights(floatArrayOf(0f,0f),null,4,0f,3f),0f)
    }
    @Test fun zeroWeightExcludesOnlyThatValidPatch() {
        val bias=MaskCoverage.logWeights(floatArrayOf(0f,1f),null,3,0f,2f)
        assertEquals(-10000f,bias[0],0f)
        assertEquals(0f,bias[1],0f)
        assertEquals(0f,bias[2],0f)
    }
    @Test fun exactOnePatchAveragesFloatCoverage() {
        val mask=FloatArray(16*16) { if(it%16<8)1f else 0f }
        assertEquals(.5f,MaskCoverage.exact(mask,16,16,1,1).single(),1e-6f)
    }
}
