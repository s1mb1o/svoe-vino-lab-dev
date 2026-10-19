package com.alolalab.chtozavino

import android.graphics.Bitmap
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.max
import kotlin.math.min

internal const val NAFLEX_PATCH_SIZE = 16
internal const val NAFLEX_PATCH_VALUES = 3 * NAFLEX_PATCH_SIZE * NAFLEX_PATCH_SIZE

internal data class NaFlexGrid(
    val height: Int,
    val width: Int,
) {
    val patchCount: Int get() = height * width
}

internal data class NaFlexInput(
    val patches: FloatArray,
    val positionalEmbeddings: FloatArray,
    val attentionMask: LongArray,
    val backboneAttentionMask: FloatArray,
    val foregroundWeights: FloatArray,
    val grid: NaFlexGrid,
)

internal data class NaFlexForegroundMask(
    val values: FloatArray,
    val width: Int,
    val height: Int,
) {
    init {
        require(width > 0 && height > 0)
        require(values.size == width * height)
    }
}

internal fun naFlexGridForImage(
    imageHeight: Int,
    imageWidth: Int,
    maxNumPatches: Int,
): NaFlexGrid {
    require(imageHeight > 0 && imageWidth > 0)
    require(maxNumPatches > 0)
    val epsilon = 1e-5
    var minimum = epsilon / 10.0
    var maximum = 100.0
    while (maximum - minimum >= epsilon) {
        val scale = (minimum + maximum) / 2.0
        val height = scaledPatchCount(imageHeight, scale)
        val width = scaledPatchCount(imageWidth, scale)
        if (height.toLong() * width <= maxNumPatches) {
            minimum = scale
        } else {
            maximum = scale
        }
    }
    return NaFlexGrid(
        height = scaledPatchCount(imageHeight, minimum),
        width = scaledPatchCount(imageWidth, minimum),
    )
}

private fun scaledPatchCount(size: Int, scale: Double): Int = max(
    1,
    ceil(size * scale / NAFLEX_PATCH_SIZE).toInt(),
)

internal class NaFlexPreprocessor(
    private val maxNumPatches: Int,
    private val positionEmbeddingGrid: Int,
    private val hiddenSize: Int,
    private val positionEmbeddings: FloatArray,
) {
    init {
        require(maxNumPatches in setOf(256, 512, 1024))
        require(positionEmbeddingGrid > 0)
        require(hiddenSize > 0)
        require(
            positionEmbeddings.size ==
                positionEmbeddingGrid * positionEmbeddingGrid * hiddenSize,
        )
    }

    fun prepare(bitmap: Bitmap, foregroundMask: NaFlexForegroundMask? = null): NaFlexInput {
        if (foregroundMask != null) {
            require(foregroundMask.width == bitmap.width && foregroundMask.height == bitmap.height)
        }
        val grid = naFlexGridForImage(bitmap.height, bitmap.width, maxNumPatches)
        check(grid.patchCount <= maxNumPatches)
        val targetWidth = grid.width * NAFLEX_PATCH_SIZE
        val targetHeight = grid.height * NAFLEX_PATCH_SIZE
        val resized = Bitmap.createScaledBitmap(bitmap, targetWidth, targetHeight, true)
        val pixels = IntArray(targetWidth * targetHeight)
        resized.getPixels(pixels, 0, targetWidth, 0, 0, targetWidth, targetHeight)
        if (resized !== bitmap) resized.recycle()

        val patches = packNaFlexPixels(pixels, targetWidth, grid, maxNumPatches)
        val mask = naFlexAttentionMask(grid, maxNumPatches)
        return NaFlexInput(
            patches = patches,
            positionalEmbeddings = resizePositionEmbeddings(
                source = positionEmbeddings,
                sourceGrid = positionEmbeddingGrid,
                target = grid,
                maxNumPatches = maxNumPatches,
                hiddenSize = hiddenSize,
            ),
            attentionMask = mask,
            backboneAttentionMask = naFlexBackboneAttentionMask(grid, maxNumPatches),
            foregroundWeights = naFlexForegroundWeights(
                mask = foregroundMask,
                grid = grid,
                maxNumPatches = maxNumPatches,
            ),
            grid = grid,
        )
    }
}

internal fun naFlexForegroundWeights(
    mask: NaFlexForegroundMask?,
    grid: NaFlexGrid,
    maxNumPatches: Int,
): FloatArray {
    require(grid.patchCount <= maxNumPatches)
    val result = FloatArray(maxNumPatches)
    if (mask == null) {
        for (index in 0 until grid.patchCount) result[index] = 1f
        return result
    }
    val targetWidth = grid.width * NAFLEX_PATCH_SIZE
    val targetHeight = grid.height * NAFLEX_PATCH_SIZE
    var patch = 0
    for (patchY in 0 until grid.height) {
        for (patchX in 0 until grid.width) {
            var sum = 0f
            for (pixelY in 0 until NAFLEX_PATCH_SIZE) {
                val targetY = patchY * NAFLEX_PATCH_SIZE + pixelY
                for (pixelX in 0 until NAFLEX_PATCH_SIZE) {
                    val targetX = patchX * NAFLEX_PATCH_SIZE + pixelX
                    sum += sampleMaskBilinear(mask, targetX, targetY, targetWidth, targetHeight)
                }
            }
            val mean = sum / (NAFLEX_PATCH_SIZE * NAFLEX_PATCH_SIZE)
            result[patch++] = 0.1f + 0.9f * mean.coerceIn(0f, 1f)
        }
    }
    return result
}

private fun sampleMaskBilinear(
    mask: NaFlexForegroundMask,
    targetX: Int,
    targetY: Int,
    targetWidth: Int,
    targetHeight: Int,
): Float {
    val sourceX = ((targetX + 0.5f) * mask.width / targetWidth - 0.5f)
        .coerceIn(0f, (mask.width - 1).toFloat())
    val sourceY = ((targetY + 0.5f) * mask.height / targetHeight - 0.5f)
        .coerceIn(0f, (mask.height - 1).toFloat())
    val x0 = sourceX.toInt()
    val y0 = sourceY.toInt()
    val x1 = min(x0 + 1, mask.width - 1)
    val y1 = min(y0 + 1, mask.height - 1)
    val xWeight = sourceX - x0
    val yWeight = sourceY - y0
    val top = mask.values[y0 * mask.width + x0] * (1f - xWeight) +
        mask.values[y0 * mask.width + x1] * xWeight
    val bottom = mask.values[y1 * mask.width + x0] * (1f - xWeight) +
        mask.values[y1 * mask.width + x1] * xWeight
    return (top * (1f - yWeight) + bottom * yWeight).coerceIn(0f, 1f)
}

internal fun packNaFlexPixels(
    pixels: IntArray,
    width: Int,
    grid: NaFlexGrid,
    maxNumPatches: Int,
): FloatArray {
    val height = grid.height * NAFLEX_PATCH_SIZE
    require(width == grid.width * NAFLEX_PATCH_SIZE)
    require(pixels.size == width * height)
    require(grid.patchCount <= maxNumPatches)
    val patches = FloatArray(maxNumPatches * NAFLEX_PATCH_VALUES)
    var target = 0
    for (patchY in 0 until grid.height) {
        for (patchX in 0 until grid.width) {
            for (pixelY in 0 until NAFLEX_PATCH_SIZE) {
                val sourceRow = (patchY * NAFLEX_PATCH_SIZE + pixelY) * width
                for (pixelX in 0 until NAFLEX_PATCH_SIZE) {
                    val pixel = pixels[sourceRow + patchX * NAFLEX_PATCH_SIZE + pixelX]
                    patches[target++] = (((pixel ushr 16) and 0xff) / 127.5f) - 1f
                    patches[target++] = (((pixel ushr 8) and 0xff) / 127.5f) - 1f
                    patches[target++] = ((pixel and 0xff) / 127.5f) - 1f
                }
            }
        }
    }
    return patches
}

internal fun naFlexAttentionMask(grid: NaFlexGrid, maxNumPatches: Int): LongArray {
    require(grid.patchCount <= maxNumPatches)
    return LongArray(maxNumPatches) { if (it < grid.patchCount) 1L else 0L }
}

internal fun naFlexBackboneAttentionMask(
    grid: NaFlexGrid,
    maxNumPatches: Int,
): FloatArray {
    require(grid.patchCount <= maxNumPatches)
    val result = FloatArray(maxNumPatches * maxNumPatches)
    for (row in 0 until maxNumPatches) {
        val offset = row * maxNumPatches
        for (column in grid.patchCount until maxNumPatches) {
            result[offset + column] = -Float.MAX_VALUE
        }
    }
    return result
}

internal fun resizePositionEmbeddings(
    source: FloatArray,
    sourceGrid: Int,
    target: NaFlexGrid,
    maxNumPatches: Int,
    hiddenSize: Int,
): FloatArray {
    require(source.size == sourceGrid * sourceGrid * hiddenSize)
    require(target.patchCount in 1..maxNumPatches)
    val yWeights = interpolationWeights(sourceGrid, target.height)
    val xWeights = interpolationWeights(sourceGrid, target.width)
    val result = FloatArray(maxNumPatches * hiddenSize)
    for (targetY in 0 until target.height) {
        val y = yWeights[targetY]
        for (targetX in 0 until target.width) {
            val x = xWeights[targetX]
            val outputOffset = (targetY * target.width + targetX) * hiddenSize
            for (dimension in 0 until hiddenSize) {
                var value = 0f
                for (yIndex in y.indices.indices) {
                    val sourceRow = y.indices[yIndex] * sourceGrid
                    val yWeight = y.weights[yIndex]
                    for (xIndex in x.indices.indices) {
                        val sourceOffset =
                            (sourceRow + x.indices[xIndex]) * hiddenSize + dimension
                        value += source[sourceOffset] * yWeight * x.weights[xIndex]
                    }
                }
                result[outputOffset + dimension] = value
            }
        }
    }
    val first = result.copyOfRange(0, hiddenSize)
    for (patch in target.patchCount until maxNumPatches) {
        first.copyInto(result, patch * hiddenSize)
    }
    return result
}

private data class AxisWeights(
    val indices: IntArray,
    val weights: FloatArray,
)

private fun interpolationWeights(inputSize: Int, outputSize: Int): List<AxisWeights> {
    val scale = inputSize.toDouble() / outputSize
    val support = if (scale >= 1.0) scale else 1.0
    val inverseScale = if (scale >= 1.0) 1.0 / scale else 1.0
    return List(outputSize) { outputIndex ->
        val center = scale * (outputIndex + 0.5)
        val minimum = max((center - support + 0.5).toInt(), 0)
        val maximum = min((center + support + 0.5).toInt(), inputSize)
        val count = maximum - minimum
        check(count > 0)
        val indices = IntArray(count)
        val weights = FloatArray(count)
        var total = 0.0
        for (index in 0 until count) {
            indices[index] = minimum + index
            val distance = abs((index + minimum - center + 0.5) * inverseScale)
            val weight = if (distance < 1.0) 1.0 - distance else 0.0
            weights[index] = weight.toFloat()
            total += weight
        }
        check(total > 0.0)
        for (index in weights.indices) weights[index] = (weights[index] / total).toFloat()
        AxisWeights(indices, weights)
    }
}
