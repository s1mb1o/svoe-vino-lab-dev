package com.alolalab.chtozavino

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.io.path.createTempDirectory

class CatalogueIndexTest {
    @Test
    fun searchUsesMaximumImageCosinePerWine() {
        val index = makeIndex()
        val query = FloatArray(VECTOR_DIMENSION).also { it[0] = 1f }

        val results = index.search(query, limit = 2)

        assertEquals(listOf("first", "second"), results.map { it.wine.slug })
        assertEquals(1f, results[0].score, 0.00001f)
        assertTrue(results[1].score in 0.70f..0.71f)
    }

    @Test
    fun ean13MatchesGtin14() {
        val results = makeIndex().findCode("4631168664979")

        assertEquals(listOf("first"), results.map { it.wine.slug })
    }

    @Test
    fun urlNormalizationRemovesFragmentAndDefaultPort() {
        assertEquals(
            CatalogueIndex.normalizeCode("https://example.org/path?a=1"),
            CatalogueIndex.normalizeCode("HTTPS://EXAMPLE.ORG:443/path?a=1#label"),
        )
    }

    private fun makeIndex(): CatalogueIndex {
        val directory = createTempDirectory("catalogue-index-test").toFile()
        val vectors = Array(3) { FloatArray(VECTOR_DIMENSION) }
        vectors[0][0] = 1f
        vectors[1][1] = 1f
        val diagonal = (1.0 / kotlin.math.sqrt(2.0)).toFloat()
        vectors[2][0] = diagonal
        vectors[2][1] = diagonal
        writeVectors(File(directory, "vectors.f32"), vectors)
        File(directory, "wines.jsonl").writeText(
            """{"wine_slug":"first","name":"Первое","page_url":"https://vino-svoe.ru/wines/first"}
{"wine_slug":"second","name":"Второе","page_url":"https://vino-svoe.ru/wines/second"}
""",
        )
        File(directory, "candidates.jsonl").writeText(
            """{"vector_row":0,"wine_slug":"first","view":"full"}
{"vector_row":1,"wine_slug":"first","view":"full"}
{"vector_row":2,"wine_slug":"second","view":"full"}
""",
        )
        File(directory, "codes.jsonl").writeText(
            """{"wine_slug":"first","kind":"gtin","value":"04631168664979"}
""",
        )
        val pack = InstalledModelPack(
            directory,
            ModelPackManifest(
                versionName = "test",
                vectorCount = 3,
                wineCount = 2,
                installedAt = 0,
                files = emptyMap(),
            ),
        )
        return CatalogueIndex.load(pack)
    }

    private fun writeVectors(file: File, vectors: Array<FloatArray>) {
        val buffer = ByteBuffer.allocate(vectors.size * VECTOR_DIMENSION * Float.SIZE_BYTES)
            .order(ByteOrder.LITTLE_ENDIAN)
        vectors.forEach { vector -> vector.forEach(buffer::putFloat) }
        file.writeBytes(buffer.array())
    }
}
