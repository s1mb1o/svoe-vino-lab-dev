package com.alolalab.chtozavino

internal const val MULTI_SHOT_EARLY_EXIT_SCORE = 0.93f
internal const val MULTI_SHOT_EARLY_EXIT_MARGIN = 0.08f

private const val SCORE_EPSILON = 0.000001f

internal data class MultiShotMergeResult(
    val matches: List<WineMatch>,
    val bestShotIndex: Int,
)

private data class ShotMatch(
    val match: WineMatch,
    val shotIndex: Int,
)

internal fun mergeMultiShotMatches(
    shots: List<List<WineMatch>>,
    limit: Int = 5,
): MultiShotMergeResult {
    require(shots.isNotEmpty()) { "At least one shot is required." }
    require(limit > 0) { "The result limit must be positive." }

    val bestBySlug = linkedMapOf<String, ShotMatch>()
    shots.forEachIndexed { shotIndex, matches ->
        matches.forEach { match ->
            val current = bestBySlug[match.wine.slug]
            if (current == null || match.score > current.match.score) {
                bestBySlug[match.wine.slug] = ShotMatch(match, shotIndex)
            }
        }
    }
    require(bestBySlug.isNotEmpty()) { "At least one match is required." }

    val merged = bestBySlug.values.sortedWith(
        compareByDescending<ShotMatch> { it.match.score }
            .thenBy { it.match.wine.slug },
    ).take(limit)
    return MultiShotMergeResult(
        matches = merged.map(ShotMatch::match),
        bestShotIndex = merged.first().shotIndex,
    )
}

internal fun shouldStopMultiShot(matches: List<WineMatch>): Boolean {
    if (matches.size < 2) return false
    val ranked = matches.sortedWith(
        compareByDescending<WineMatch>(WineMatch::score)
            .thenBy { it.wine.slug },
    )
    val topScore = ranked[0].score
    val scoreMargin = topScore - ranked[1].score
    return topScore + SCORE_EPSILON >= MULTI_SHOT_EARLY_EXIT_SCORE &&
        scoreMargin + SCORE_EPSILON >= MULTI_SHOT_EARLY_EXIT_MARGIN
}
