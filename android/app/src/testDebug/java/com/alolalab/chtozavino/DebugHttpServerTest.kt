package com.alolalab.chtozavino

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Test

class DebugHttpServerTest {
    @Test
    fun serverIsDisabledByDefault() {
        assertFalse(DEBUG_HTTP_SERVER_DEFAULT_ENABLED)
    }

    @Test
    fun validatesMatchLimit() {
        assertEquals(20, matchLimit(null))
        assertEquals(1, matchLimit("1"))
        assertEquals(20, matchLimit("20"))
        assertThrows(IllegalArgumentException::class.java) { matchLimit("0") }
        assertThrows(IllegalArgumentException::class.java) { matchLimit("21") }
        assertThrows(IllegalArgumentException::class.java) { matchLimit("many") }
    }

    @Test
    fun writesMatcherCompatibleResponses() {
        val wine = WineCard(
            slug = "wine-a",
            name = "Wine A",
            pageUrl = "https://vino-svoe.ru/wines/wine-a",
            producer = "Producer",
        )
        val matches = listOf(WineMatch(wine, 0.91f))
        assertEquals("wine-a", predictionJson(matches).getString("slug"))
        val match = matchJson(matches, 31.5)
        assertEquals(PIPELINE_NAME, match.getString("pipeline"))
        assertEquals("wine-a", match.getJSONArray("candidates").getJSONObject(0)
            .getString("slug"))
        assertEquals(0.91, match.getJSONArray("candidates").getJSONObject(0)
            .getDouble("score"), 0.0001)
    }
}
