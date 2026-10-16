package com.alolalab.chtozavino

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class YoloBottleMaskTest {
    @Test
    fun selectsLargestCentralBottleAndReadsCoefficients() {
        val anchors = 2
        val classes = 3
        val coefficients = 2
        val values = FloatArray((4 + classes + coefficients) * anchors)
        writeDetection(values, anchors, classes, 0, 50f, 50f, 80f, 80f, 1, 0.9f)
        writeDetection(values, anchors, classes, 1, 50f, 50f, 20f, 20f, 1, 0.99f)
        values[(4 + classes) * anchors] = 2f
        values[(4 + classes + 1) * anchors] = -1f

        val selected = selectYoloBottleDetection(
            detections = values,
            anchorCount = anchors,
            classCount = classes,
            bottleClass = 1,
            coefficientCount = coefficients,
            inputSize = 100,
        )

        assertNotNull(selected)
        assertEquals(80f, selected!!.width)
        assertEquals(2f, selected.maskCoefficients[0])
        assertEquals(-1f, selected.maskCoefficients[1])
    }

    @Test
    fun rejectsCandidateWhenBottleIsNotBestClass() {
        val anchors = 1
        val classes = 3
        val values = FloatArray((4 + classes + 1) * anchors)
        writeDetection(values, anchors, classes, 0, 50f, 50f, 40f, 40f, 1, 0.8f)
        values[4] = 0.9f

        assertNull(
            selectYoloBottleDetection(
                values,
                anchorCount = anchors,
                classCount = classes,
                bottleClass = 1,
                coefficientCount = 1,
                inputSize = 100,
            ),
        )
    }

    @Test
    fun convertsNormalizedBoxCoordinatesToModelPixels() {
        val anchors = 1
        val classes = 2
        val values = FloatArray((4 + classes + 1) * anchors)
        writeDetection(values, anchors, classes, 0, 0.5f, 0.5f, 0.25f, 0.75f, 1, 0.8f)

        val selected = selectYoloBottleDetection(
            values,
            anchorCount = anchors,
            classCount = classes,
            bottleClass = 1,
            coefficientCount = 1,
            inputSize = 640,
        )

        assertEquals(320f, selected!!.centerX)
        assertEquals(160f, selected.width)
        assertEquals(480f, selected.height)
    }

    @Test
    fun buildsMaskAndRemovesLetterboxArea() {
        val detection = YoloBottleDetection(
            centerX = 4f,
            centerY = 4f,
            width = 8f,
            height = 8f,
            confidence = 0.9f,
            maskCoefficients = floatArrayOf(2f),
        )
        val prototypes = FloatArray(16) { 1f }

        val mask = buildYoloBottleMask(
            prototypes = prototypes,
            detection = detection,
            contentLeft = 1,
            contentTop = 0,
            contentRight = 3,
            contentBottom = 4,
            protoWidth = 4,
            protoHeight = 4,
            modelInputSize = 8,
        )

        assertEquals(2, mask.width)
        assertEquals(4, mask.height)
        assertTrue(mask.values.all { it > 0.8f })
    }

    private fun writeDetection(
        target: FloatArray,
        anchors: Int,
        classes: Int,
        anchor: Int,
        centerX: Float,
        centerY: Float,
        width: Float,
        height: Float,
        classIndex: Int,
        confidence: Float,
    ) {
        target[anchor] = centerX
        target[anchors + anchor] = centerY
        target[2 * anchors + anchor] = width
        target[3 * anchors + anchor] = height
        target[(4 + classIndex) * anchors + anchor] = confidence
        for (index in 0 until classes) {
            if (index != classIndex) target[(4 + index) * anchors + anchor] = 0.1f
        }
    }
}
