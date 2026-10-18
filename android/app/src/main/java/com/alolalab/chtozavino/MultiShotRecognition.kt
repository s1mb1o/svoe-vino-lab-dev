package com.alolalab.chtozavino

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
