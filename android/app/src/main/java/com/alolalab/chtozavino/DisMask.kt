package com.alolalab.chtozavino

internal fun validateDisOutput(
    mask: FloatArray,
    expectedSize: Int,
): FloatArray {
    if (mask.size != expectedSize) {
        throw ImageRecognitionException(
            "DIS вернул ${mask.size} значений вместо $expectedSize.",
        )
    }
    return normalizeDisMask(mask)
}

internal fun normalizeDisMask(mask: FloatArray): FloatArray {
    var low = Float.POSITIVE_INFINITY
    var high = Float.NEGATIVE_INFINITY
    for (value in mask) {
        if (!value.isFinite()) {
            throw ImageRecognitionException("DIS вернул некорректную маску.")
        }
        if (value < low) low = value
        if (value > high) high = value
    }
    val range = high - low
    if (!range.isFinite() || range <= 1e-6f) {
        throw ImageRecognitionException("DIS вернул однотонную маску.")
    }
    for (index in mask.indices) {
        mask[index] = ((mask[index] - low) / range).coerceIn(0f, 1f)
    }
    return mask
}
