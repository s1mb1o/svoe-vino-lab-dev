package com.alolalab.chtozavino

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class ModelPackUpgradeTest {
    @get:Rule val temporary = TemporaryFolder()

    @Test
    fun `old fixed and split packs require the new built in pack`() {
        val directory = temporary.newFolder()
        directory.resolve("yolo26n-seg_w8a32.tflite").writeText("fixture")
        for (version in 1..6) {
            assertTrue(InstalledModelPack(directory, manifest(version)).needsBuiltInUpgrade())
        }
        assertFalse(InstalledModelPack(directory, manifest(7)).needsBuiltInUpgrade())
    }

    @Test
    fun `an incomplete version six pack requires repair`() {
        assertTrue(InstalledModelPack(temporary.newFolder(), manifest(6)).needsBuiltInUpgrade())
    }

    private fun manifest(version: Int) = ModelPackManifest(
        formatVersion = version, versionName = "fixture", vectorCount = 1,
        wineCount = 1, imageCount = 1, installedAt = 0, files = emptyMap(),
    )
}
