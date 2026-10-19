package com.alolalab.chtozavino

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class NaFlexPreprocessorTest {
    @Test
    fun `p512 keeps a square image below the patch limit`() {
        val grid = naFlexGridForImage(1024, 1024, 512)

        assertEquals(NaFlexGrid(22, 22), grid)
        assertEquals(484, grid.patchCount)
    }

    @Test
    fun `p512 preserves a two to one aspect ratio`() {
        val grid = naFlexGridForImage(512, 1024, 512)

        assertEquals(NaFlexGrid(16, 32), grid)
        assertEquals(512, grid.patchCount)
    }

    @Test
    fun `position resize copies the first token into padding`() {
        val source = FloatArray(2 * 2 * 2) { it.toFloat() }
        val resized = resizePositionEmbeddings(
            source = source,
            sourceGrid = 2,
            target = NaFlexGrid(1, 2),
            maxNumPatches = 4,
            hiddenSize = 2,
        )

        assertEquals(8, resized.size)
        assertArrayEquals(resized.copyOfRange(0, 2), resized.copyOfRange(4, 6), 0f)
        assertArrayEquals(resized.copyOfRange(0, 2), resized.copyOfRange(6, 8), 0f)
        assertTrue(resized.all(Float::isFinite))
    }

    @Test
    fun `patch packing uses patch row pixel row and RGB order`() {
        val width = 2 * NAFLEX_PATCH_SIZE
        val pixels = IntArray(width * NAFLEX_PATCH_SIZE)
        pixels[0] = 0xffff8000.toInt()
        pixels[NAFLEX_PATCH_SIZE] = 0xff0040ff.toInt()

        val patches = packNaFlexPixels(
            pixels = pixels,
            width = width,
            grid = NaFlexGrid(1, 2),
            maxNumPatches = 3,
        )

        assertEquals(1f, patches[0], 1e-6f)
        assertEquals(128f / 127.5f - 1f, patches[1], 1e-6f)
        assertEquals(-1f, patches[2], 1e-6f)
        assertEquals(-1f, patches[NAFLEX_PATCH_VALUES], 1e-6f)
        assertEquals(64f / 127.5f - 1f, patches[NAFLEX_PATCH_VALUES + 1], 1e-6f)
        assertEquals(1f, patches[NAFLEX_PATCH_VALUES + 2], 1e-6f)
        assertTrue(patches.copyOfRange(2 * NAFLEX_PATCH_VALUES, patches.size).all { it == 0f })
    }

    @Test
    fun `attention mask marks real patches and padding`() {
        assertArrayEquals(
            longArrayOf(1, 1, 1, 1, 1, 1, 0, 0),
            naFlexAttentionMask(NaFlexGrid(2, 3), 8),
        )
    }

    @Test
    fun `backbone mask blocks padded keys for each query`() {
        val mask = naFlexBackboneAttentionMask(NaFlexGrid(1, 2), 4)

        assertArrayEquals(
            floatArrayOf(0f, 0f, -Float.MAX_VALUE, -Float.MAX_VALUE),
            mask.copyOfRange(0, 4),
            0f,
        )
        assertArrayEquals(mask.copyOfRange(0, 4), mask.copyOfRange(12, 16), 0f)
    }

    @Test
    fun `position resize matches the PyTorch antialias reference`() {
        val source = FloatArray(4 * 4) { it.toFloat() }
        val resized = resizePositionEmbeddings(
            source = source,
            sourceGrid = 4,
            target = NaFlexGrid(2, 3),
            maxNumPatches = 6,
            hiddenSize = 1,
        )

        val expected = floatArrayOf(
            3.1571431f,
            4.357143f,
            5.557143f,
            9.442858f,
            10.642858f,
            11.842857f,
        )
        assertArrayEquals(expected, resized, 1e-5f)
    }

    @Test
    fun `foreground weights map zero to point one and one to one`() {
        val values = FloatArray(2 * NAFLEX_PATCH_SIZE * NAFLEX_PATCH_SIZE)
        for (y in 0 until NAFLEX_PATCH_SIZE) {
            for (x in NAFLEX_PATCH_SIZE until 2 * NAFLEX_PATCH_SIZE) {
                values[y * 2 * NAFLEX_PATCH_SIZE + x] = 1f
            }
        }

        val weights = naFlexForegroundWeights(
            mask = NaFlexForegroundMask(
                values,
                width = 2 * NAFLEX_PATCH_SIZE,
                height = NAFLEX_PATCH_SIZE,
            ),
            grid = NaFlexGrid(1, 2),
            maxNumPatches = 4,
        )

        assertArrayEquals(floatArrayOf(0.1f, 1f, 0f, 0f), weights, 1e-6f)
    }
}
