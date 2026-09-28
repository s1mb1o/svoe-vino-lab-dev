package com.alolalab.chtozavino

import android.content.Context
import android.net.Uri
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.zip.ZipInputStream

private const val PACK_FORMAT = "svoe-vino-android-model-pack"
private const val PACK_VERSION = 1
private const val PIPELINE_ID = "dis-white-square-v1"
private const val SIGLIP_MODEL = "vit_base_patch16_siglip_224.v2_webli"
const val VECTOR_DIMENSION = 768

private val REQUIRED_PAYLOADS = setOf(
    "dis.tflite",
    "siglip2_base_224_fp16.tflite",
    "vectors.f32",
    "candidates.jsonl",
    "wines.jsonl",
    "codes.jsonl",
)
private val ALLOWED_ENTRIES = REQUIRED_PAYLOADS + "manifest.json"
private const val MAX_PACK_BYTES = 700L * 1024L * 1024L

class ModelPackException(message: String) : IllegalArgumentException(message)

data class PackFile(val bytes: Long, val sha256: String)

data class ModelPackManifest(
    val versionName: String,
    val vectorCount: Int,
    val wineCount: Int,
    val installedAt: Long,
    val files: Map<String, PackFile>,
)

data class InstalledModelPack(
    val directory: File,
    val manifest: ModelPackManifest,
) {
    val info: ModelPackInfo
        get() = ModelPackInfo(
            version = manifest.versionName,
            vectorCount = manifest.vectorCount,
            wineCount = manifest.wineCount,
            installedAt = manifest.installedAt,
        )

    fun file(name: String): File = File(directory, name)
}

class ModelPackManager(private val context: Context) {
    private val modelRoot = File(context.filesDir, "models")
    private val currentDir = File(modelRoot, "current")

    fun current(): InstalledModelPack? {
        if (!currentDir.isDirectory) return null
        return runCatching { validateDirectory(currentDir, verifyHashes = false) }.getOrNull()
    }

    fun install(uri: Uri): InstalledModelPack {
        modelRoot.mkdirs()
        val staging = File(modelRoot, ".staging-${System.currentTimeMillis()}")
        if (staging.exists()) staging.deleteRecursively()
        check(staging.mkdirs()) { "Не удалось создать временный каталог пакета." }

        try {
            extract(uri, staging)
            val installed = validateDirectory(staging, verifyHashes = true)
            // Parse all catalogue payloads before replacing a working pack.
            CatalogueIndex.load(installed)

            val previous = File(modelRoot, ".previous")
            if (previous.exists()) previous.deleteRecursively()
            if (currentDir.exists() && !currentDir.renameTo(previous)) {
                throw ModelPackException("Не удалось подготовить замену пакета моделей.")
            }
            if (!staging.renameTo(currentDir)) {
                previous.renameTo(currentDir)
                throw ModelPackException("Не удалось установить пакет моделей.")
            }
            previous.deleteRecursively()
            return validateDirectory(currentDir, verifyHashes = false)
        } catch (error: Exception) {
            staging.deleteRecursively()
            throw error
        }
    }

    private fun extract(uri: Uri, target: File) {
        val found = mutableSetOf<String>()
        var total = 0L
        val source = context.contentResolver.openInputStream(uri)
            ?: throw ModelPackException("Не удалось открыть пакет моделей.")
        ZipInputStream(source.buffered()).use { zip ->
            while (true) {
                val entry = zip.nextEntry ?: break
                val name = entry.name
                if (entry.isDirectory || name !in ALLOWED_ENTRIES || '/' in name || '\\' in name) {
                    throw ModelPackException("Пакет содержит недопустимый файл: $name")
                }
                if (!found.add(name)) {
                    throw ModelPackException("Пакет содержит файл два раза: $name")
                }
                FileOutputStream(File(target, name)).use { output ->
                    val buffer = ByteArray(1024 * 1024)
                    while (true) {
                        val count = zip.read(buffer)
                        if (count < 0) break
                        total += count
                        if (total > MAX_PACK_BYTES) {
                            throw ModelPackException("Пакет моделей превышает 700 МБ.")
                        }
                        output.write(buffer, 0, count)
                    }
                }
                zip.closeEntry()
            }
        }
        val missing = ALLOWED_ENTRIES - found
        if (missing.isNotEmpty()) {
            throw ModelPackException("В пакете нет файлов: ${missing.sorted().joinToString()}.")
        }
    }

    private fun validateDirectory(directory: File, verifyHashes: Boolean): InstalledModelPack {
        val manifestFile = File(directory, "manifest.json")
        val json = runCatching { JSONObject(manifestFile.readText()) }
            .getOrElse { throw ModelPackException("Некорректный manifest.json: ${it.message}") }
        if (json.optString("format") != PACK_FORMAT || json.optInt("format_version") != PACK_VERSION) {
            throw ModelPackException("Версия формата пакета не поддерживается.")
        }
        if (json.optString("pipeline") != PIPELINE_ID) {
            throw ModelPackException("Пакет использует другой конвейер обработки изображения.")
        }
        if (json.optString("model") != SIGLIP_MODEL) {
            throw ModelPackException("Пакет использует другую модель SigLIP2.")
        }
        if (json.optInt("vector_dim") != VECTOR_DIMENSION) {
            throw ModelPackException("Размерность векторов должна быть $VECTOR_DIMENSION.")
        }
        val vectorCount = json.optInt("vector_count", -1)
        val wineCount = json.optInt("wine_count", -1)
        if (vectorCount <= 0 || wineCount <= 0) {
            throw ModelPackException("Пакет содержит некорректные счётчики каталога.")
        }

        val fileJson = json.optJSONObject("files")
            ?: throw ModelPackException("В manifest.json нет объекта files.")
        if (fileJson.keys().asSequence().toSet() != REQUIRED_PAYLOADS) {
            throw ModelPackException("Список файлов в manifest.json не совпадает с контрактом.")
        }
        val files = REQUIRED_PAYLOADS.associateWith { name ->
            val record = fileJson.optJSONObject(name)
                ?: throw ModelPackException("В manifest.json нет записи $name.")
            val bytes = record.optLong("bytes", -1)
            val sha256 = record.optString("sha256")
            if (bytes < 0 || !sha256.matches(Regex("[0-9a-f]{64}"))) {
                throw ModelPackException("Некорректная запись файла $name.")
            }
            val file = File(directory, name)
            if (!file.isFile || file.length() != bytes) {
                throw ModelPackException("Размер файла $name не совпадает с manifest.json.")
            }
            if (verifyHashes && sha256(file) != sha256) {
                throw ModelPackException("SHA-256 файла $name не совпадает с manifest.json.")
            }
            PackFile(bytes, sha256)
        }
        val expectedVectorBytes = vectorCount.toLong() * VECTOR_DIMENSION * Float.SIZE_BYTES
        if (files.getValue("vectors.f32").bytes != expectedVectorBytes) {
            throw ModelPackException("Размер vectors.f32 не совпадает с числом векторов.")
        }
        val installedAt = json.optLong("created_at_epoch_ms", manifestFile.lastModified())
        return InstalledModelPack(
            directory,
            ModelPackManifest(
                versionName = json.optString("version", "1"),
                vectorCount = vectorCount,
                wineCount = wineCount,
                installedAt = installedAt,
                files = files,
            ),
        )
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { source ->
            val buffer = ByteArray(1024 * 1024)
            while (true) {
                val count = source.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
