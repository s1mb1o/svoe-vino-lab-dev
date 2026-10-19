package com.alolalab.chtozavino.offlinebench

import org.junit.Assert.*
import org.junit.Test

class ReferenceSearchTest {
    @Test fun meanKeepsDistinctEqualScoringReferences() {
        val result = TopMean(3,3)
        listOf(.8f,.8f,.1f,-.5f).forEach { result.add(0,it) }
        result.add(1,-.4f)
        assertEquals((.8f+.8f+.1f)/3,result.result()[0],.000001f)
        assertEquals(-.4f,result.result()[1],0f)
        assertEquals(Float.NEGATIVE_INFINITY,result.result()[2],0f)
    }
    @Test fun meanUsesAvailableReferencesWhenFewerThanKExist() {
        val result = TopMean(1,3)
        result.add(0,.6f)
        result.add(0,.4f)
        assertEquals(.5f,result.result()[0],.000001f)
    }
    @Test fun fusionUsesAllWineScoresAndKeepsMissingSpaceFallback() {
        val bottle = floatArrayOf(.8f,.7f,Float.NEGATIVE_INFINITY)
        val label = floatArrayOf(.2f,Float.NEGATIVE_INFINITY,.9f)
        val result = fuse(bottle,label,.75)
        assertEquals(.65,result[0],.000001)
        assertEquals(.7,result[1],.000001)
        assertEquals(.9,result[2],.000001)
        assertArrayEquals(bottle.map { it.toDouble() }.toDoubleArray(),fuse(bottle,null,.75),0.0)
    }
    @Test fun scoreTiesUseLexicalSlugOrder() {
        val result = ranked(doubleArrayOf(.5,.5,.5),listOf("wine-z","wine-a","wine-m"),3)
        assertEquals(listOf("wine-a","wine-m","wine-z"),
            (0 until result.length()).map { result.getJSONObject(it).getString("slug") })
    }
}
