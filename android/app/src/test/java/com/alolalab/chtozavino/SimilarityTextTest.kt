package com.alolalab.chtozavino

import org.junit.Assert.assertEquals
import org.junit.Test

class SimilarityTextTest {
    @Test
    fun roundsCosineToWholePercent() {
        assertEquals("91%", formatSimilarityPercent(0.9096f))
    }

    @Test
    fun clampsScoreToDisplayRange() {
        assertEquals("0%", formatSimilarityPercent(-0.2f))
        assertEquals("100%", formatSimilarityPercent(1.0001f))
    }
}
