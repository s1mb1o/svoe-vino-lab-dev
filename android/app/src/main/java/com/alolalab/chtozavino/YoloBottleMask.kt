package com.alolalab.chtozavino

import kotlin.math.ceil
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

internal const val YOLO_INPUT_SIZE = 640
internal const val YOLO_CLASS_COUNT = 80
internal const val YOLO_BOTTLE_CLASS = 39
internal const val YOLO_MASK_COEFFICIENT_COUNT = 32
internal const val YOLO_ANCHOR_COUNT = 8400
internal const val YOLO_DETECTION_FEATURE_COUNT =
    4 + YOLO_CLASS_COUNT + YOLO_MASK_COEFFICIENT_COUNT
internal const val YOLO_PROTO_SIZE = 160
internal const val YOLO_CONFIDENCE_THRESHOLD = 0.25f

internal data class YoloBottleDetection(
    val centerX: Float,
    val centerY: Float,
    val width: Float,
    val height: Float,
    val confidence: Float,
    val maskCoefficients: FloatArray,
)

internal data class SegmentationMask(
    val values: FloatArray,
    val width: Int,
    val height: Int,
)

internal fun selectYoloBottleDetection(
    detections: FloatArray,
    anchorCount: Int = YOLO_ANCHOR_COUNT,
    classCount: Int = YOLO_CLASS_COUNT,
    bottleClass: Int = YOLO_BOTTLE_CLASS,
    coefficientCount: Int = YOLO_MASK_COEFFICIENT_COUNT,
    inputSize: Int = YOLO_INPUT_SIZE,
    confidenceThreshold: Float = YOLO_CONFIDENCE_THRESHOLD,
): YoloBottleDetection? {
    val featureCount = 4 + classCount + coefficientCount
    require(detections.size == featureCount * anchorCount) {
        "YOLO detection output has ${detections.size} values; expected ${featureCount * anchorCount}."
    }
    require(bottleClass in 0 until classCount)

    var selected: YoloBottleDetection? = null
    var selectedRank = Float.NEGATIVE_INFINITY
    val classBase = 4 * anchorCount
    for (anchor in 0 until anchorCount) {
        val bottleConfidence = detections[classBase + bottleClass * anchorCount + anchor]
        if (!bottleConfidence.isFinite() || bottleConfidence < confidenceThreshold) continue

        var bestClass = 0
        var bestConfidence = Float.NEGATIVE_INFINITY
        for (classIndex in 0 until classCount) {
            val confidence = detections[classBase + classIndex * anchorCount + anchor]
            if (confidence > bestConfidence) {
                bestClass = classIndex
                bestConfidence = confidence
            }
        }
        if (bestClass != bottleClass) continue

        var centerX = detections[anchor]
        var centerY = detections[anchorCount + anchor]
        var width = detections[2 * anchorCount + anchor]
        var height = detections[3 * anchorCount + anchor]
        if (!centerX.isFinite() || !centerY.isFinite() ||
            !width.isFinite() || !height.isFinite() || width <= 0f || height <= 0f
        ) {
            continue
        }
        if (max(max(abs(centerX), abs(centerY)), max(abs(width), abs(height))) <= 2f) {
            centerX *= inputSize
            centerY *= inputSize
            width *= inputSize
            height *= inputSize
        }

        val half = inputSize / 2f
        val centrality = (1f - hypot(centerX - half, centerY - half) / hypot(half, half))
            .coerceIn(0f, 1f)
        val clippedWidth = min(inputSize.toFloat(), width)
        val clippedHeight = min(inputSize.toFloat(), height)
        val rank = clippedWidth * clippedHeight *
            (0.8f + 0.2f * centrality) * (0.5f + 0.5f * bottleConfidence)
        if (rank <= selectedRank) continue

        val coefficients = FloatArray(coefficientCount)
        val coefficientBase = (4 + classCount) * anchorCount
        for (coefficient in 0 until coefficientCount) {
            coefficients[coefficient] =
                detections[coefficientBase + coefficient * anchorCount + anchor]
        }
        selectedRank = rank
        selected = YoloBottleDetection(
            centerX = centerX,
            centerY = centerY,
            width = width,
            height = height,
            confidence = bottleConfidence,
            maskCoefficients = coefficients,
        )
    }
    return selected
}

internal fun buildYoloBottleMask(
    prototypes: FloatArray,
    detection: YoloBottleDetection,
    contentLeft: Int,
    contentTop: Int,
    contentRight: Int,
    contentBottom: Int,
    protoWidth: Int = YOLO_PROTO_SIZE,
    protoHeight: Int = YOLO_PROTO_SIZE,
    modelInputSize: Int = YOLO_INPUT_SIZE,
): SegmentationMask {
    val coefficientCount = detection.maskCoefficients.size
    val planeSize = protoWidth * protoHeight
    require(prototypes.size == coefficientCount * planeSize) {
        "YOLO mask output has ${prototypes.size} values; expected ${coefficientCount * planeSize}."
    }
    require(contentLeft in 0 until contentRight && contentRight <= protoWidth)
    require(contentTop in 0 until contentBottom && contentBottom <= protoHeight)

    val scaleX = protoWidth.toFloat() / modelInputSize
    val scaleY = protoHeight.toFloat() / modelInputSize
    val boxLeft = floor((detection.centerX - detection.width / 2f) * scaleX)
        .toInt().coerceIn(0, protoWidth)
    val boxTop = floor((detection.centerY - detection.height / 2f) * scaleY)
        .toInt().coerceIn(0, protoHeight)
    val boxRight = ceil((detection.centerX + detection.width / 2f) * scaleX)
        .toInt().coerceIn(0, protoWidth)
    val boxBottom = ceil((detection.centerY + detection.height / 2f) * scaleY)
        .toInt().coerceIn(0, protoHeight)

    val outputWidth = contentRight - contentLeft
    val outputHeight = contentBottom - contentTop
    val values = FloatArray(outputWidth * outputHeight)
    val left = max(boxLeft, contentLeft)
    val top = max(boxTop, contentTop)
    val right = min(boxRight, contentRight)
    val bottom = min(boxBottom, contentBottom)
    for (y in top until bottom) {
        for (x in left until right) {
            val pixel = y * protoWidth + x
            var logit = 0f
            for (coefficient in 0 until coefficientCount) {
                logit += detection.maskCoefficients[coefficient] *
                    prototypes[coefficient * planeSize + pixel]
            }
            val probability = if (logit >= 0f) {
                1f / (1f + exp(-logit))
            } else {
                val expLogit = exp(logit)
                expLogit / (1f + expLogit)
            }
            values[(y - contentTop) * outputWidth + x - contentLeft] = probability
        }
    }
    return SegmentationMask(values, outputWidth, outputHeight)
}
