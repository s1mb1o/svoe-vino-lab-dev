package com.alolalab.chtozavino

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class MultiShotRecognitionTest {
    @Test
    fun keepsMaximumScoreForEachWine() {
        val result = mergeMultiShotMatches(
            listOf(
                listOf(match("wine-a", 0.72f), match("wine-b", 0.80f)),
                listOf(match("wine-a", 0.91f), match("wine-c", 0.75f)),
            ),
        )

        assertEquals(listOf("wine-a", "wine-b", "wine-c"), result.matches.map { it.wine.slug })
        assertEquals(listOf(0.91f, 0.80f, 0.75f), result.matches.map(WineMatch::score))
        assertEquals(1, result.bestShotIndex)
    }

    @Test
    fun keepsEarlierShotWhenTheSameWineHasEqualScores() {
        val result = mergeMultiShotMatches(
            listOf(listOf(match("wine-a", 0.9f)), listOf(match("wine-a", 0.9f))),
        )

        assertEquals(0, result.bestShotIndex)
    }

    @Test
    fun sortsScoreTiesBySlugAndAppliesLimit() {
        val result = mergeMultiShotMatches(
            listOf(
                listOf(
                    match("wine-c", 0.8f),
                    match("wine-a", 0.8f),
                    match("wine-b", 0.8f),
                ),
            ),
            limit = 2,
        )

        assertEquals(listOf("wine-a", "wine-b"), result.matches.map { it.wine.slug })
    }

    @Test
    fun rejectsEmptyInputs() {
        assertThrows(IllegalArgumentException::class.java) {
            mergeMultiShotMatches(emptyList())
        }
        assertThrows(IllegalArgumentException::class.java) {
            mergeMultiShotMatches(listOf(emptyList()))
        }
    }

    private fun match(slug: String, score: Float): WineMatch = WineMatch(
        wine = WineCard(slug = slug, name = slug, pageUrl = "https://vino-svoe.ru/wines/$slug"),
        score = score,
    )
}
