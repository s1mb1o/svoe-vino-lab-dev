package com.alolalab.chtozavino

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.ImageDecoder
import android.graphics.Paint
import android.graphics.RectF
import android.net.Uri
import android.util.Log
import com.google.ai.edge.litert.Accelerator
import com.google.ai.edge.litert.CompiledModel
import com.google.ai.edge.litert.TensorBuffer
import java.io.File
import kotlin.math.ceil
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

private const val DIS_SIZE = 1024
private const val SIGLIP_SIZE = 224
private const val SIGLIP_TIMM_RESIZE_SIZE = 248
private const val MASK_THRESHOLD = 0.5f
private const val MAX_SOURCE_SIDE = 2048

class ImageRecognitionException(message: String, cause: Throwable? = null) :
    IllegalStateException(message, cause)

private class LiteRtRunner private constructor(
    private val model: CompiledModel,
    val accelerator: String,
) : AutoCloseable {
    private val inputs: List<TensorBuffer> = model.createInputBuffers()
    private val outputs: List<TensorBuffer> = model.createOutputBuffers()

    companion object {
        fun open(path: String, accelerator: ModelAccelerator): LiteRtRunner =
            when (accelerator) {
                ModelAccelerator.GPU -> openGpu(path)
                ModelAccelerator.CPU -> openCpu(path)
            }

        fun openGpu(path: String): LiteRtRunner = try {
            LiteRtRunner(
                CompiledModel.create(
                    path,
                    CompiledModel.Options(Accelerator.GPU),
                    null,
                ),
                "GPU",
            )
        } catch (error: Exception) {
            throw ImageRecognitionException("LiteRT не смог загрузить модель на GPU.", error)
        }

        fun openCpu(path: String): LiteRtRunner = try {
            LiteRtRunner(
                CompiledModel.create(
                    path,
                    CompiledModel.Options(Accelerator.CPU),
                    null,
                ),
                "CPU",
            )
        } catch (error: Exception) {
            throw ImageRecognitionException("LiteRT не смог загрузить модель на CPU.", error)
        }
    }

    fun run(input: FloatArray): FloatArray {
        inputs[0].writeFloat(input)
        model.run(inputs, outputs)
        return outputs[0].readFloat()
    }

    override fun close() {
        inputs.forEach(TensorBuffer::close)
        outputs.forEach(TensorBuffer::close)
        model.close()
    }
}

private class DisSegmenter(
    private val modelPath: String,
    accelerator: ModelAccelerator,
    private val allowCpuFallback: Boolean,
) : AutoCloseable {
    private var runner = openRunner(modelPath, accelerator, allowCpuFallback, "DIS")
    val accelerator: String get() = runner.accelerator

    fun mask(bitmap: Bitmap): FloatArray {
        val resized = Bitmap.createBitmap(DIS_SIZE, DIS_SIZE, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(resized)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        canvas.drawBitmap(
            bitmap,
            null,
            RectF(0f, 0f, DIS_SIZE.toFloat(), DIS_SIZE.toFloat()),
            paint,
        )
        val pixels = IntArray(DIS_SIZE * DIS_SIZE)
        resized.getPixels(pixels, 0, DIS_SIZE, 0, 0, DIS_SIZE, DIS_SIZE)
        resized.recycle()

        val input = FloatArray(3 * DIS_SIZE * DIS_SIZE)
        val plane = DIS_SIZE * DIS_SIZE
        for (index in pixels.indices) {
            val pixel = pixels[index]
            input[index] = ((pixel ushr 16) and 0xff) / 255f - 0.5f
            input[plane + index] = ((pixel ushr 8) and 0xff) / 255f - 0.5f
            input[2 * plane + index] = (pixel and 0xff) / 255f - 0.5f
        }
        return runWithCpuFallback(input, plane)
    }

    override fun close() = runner.close()

    private fun runWithCpuFallback(input: FloatArray, expectedSize: Int): FloatArray {
        try {
            return validateDisOutput(runner.run(input), expectedSize)
        } catch (gpuError: Exception) {
            if (!allowCpuFallback || runner.accelerator != "GPU") throw gpuError
            Log.w(
                "ChtoZaVino",
                "DIS GPU inference returned an invalid result. Retrying on CPU.",
                gpuError,
            )
            runner.close()
            runner = try {
                LiteRtRunner.openCpu(modelPath)
            } catch (cpuOpenError: Exception) {
                cpuOpenError.addSuppressed(gpuError)
                throw cpuOpenError
            }
            return try {
                validateDisOutput(runner.run(input), expectedSize)
            } catch (cpuError: Exception) {
                cpuError.addSuppressed(gpuError)
                throw cpuError
            }
        }
    }
}

private class SigLip2Encoder(
    private val modelPath: String,
    accelerator: ModelAccelerator,
    private val allowCpuFallback: Boolean,
) : AutoCloseable {
    private var runner = openRunner(modelPath, accelerator, allowCpuFallback, "SigLIP2")
    val accelerator: String get() = runner.accelerator

    fun encode(bitmap: Bitmap): FloatArray {
        // The GX10 timm image processor first receives the saved 224 px square.
        // It then applies crop_pct=0.9: resize to 248 px and center-crop to 224 px.
        // Keep both resize operations here so Android and the catalogue use the same input.
        val square224 = Bitmap.createScaledBitmap(bitmap, SIGLIP_SIZE, SIGLIP_SIZE, true)
        val expanded = Bitmap.createScaledBitmap(
            square224,
            SIGLIP_TIMM_RESIZE_SIZE,
            SIGLIP_TIMM_RESIZE_SIZE,
            true,
        )
        if (square224 !== bitmap) square224.recycle()
        val pixels = IntArray(SIGLIP_SIZE * SIGLIP_SIZE)
        val cropOffset = (SIGLIP_TIMM_RESIZE_SIZE - SIGLIP_SIZE) / 2
        expanded.getPixels(
            pixels,
            0,
            SIGLIP_SIZE,
            cropOffset,
            cropOffset,
            SIGLIP_SIZE,
            SIGLIP_SIZE,
        )
        if (expanded !== bitmap) expanded.recycle()

        val plane = SIGLIP_SIZE * SIGLIP_SIZE
        val input = FloatArray(3 * plane)
        for (index in pixels.indices) {
            val pixel = pixels[index]
            input[index] = (((pixel ushr 16) and 0xff) / 127.5f) - 1f
            input[plane + index] = (((pixel ushr 8) and 0xff) / 127.5f) - 1f
            input[2 * plane + index] = ((pixel and 0xff) / 127.5f) - 1f
        }
        return runWithCpuFallback(input)
    }

    override fun close() = runner.close()

    private fun runWithCpuFallback(input: FloatArray): FloatArray {
        try {
            return normalizeSigLipVector(runner.run(input))
        } catch (gpuError: Exception) {
            if (!allowCpuFallback || runner.accelerator != "GPU") throw gpuError
            Log.w(
                "ChtoZaVino",
                "SigLIP2 GPU inference returned an invalid result. Retrying on CPU.",
                gpuError,
            )
            runner.close()
            runner = try {
                LiteRtRunner.openCpu(modelPath)
            } catch (cpuOpenError: Exception) {
                cpuOpenError.addSuppressed(gpuError)
                throw cpuOpenError
            }
            return try {
                normalizeSigLipVector(runner.run(input))
            } catch (cpuError: Exception) {
                cpuError.addSuppressed(gpuError)
                throw cpuError
            }
        }
    }
}

private fun openRunner(
    modelPath: String,
    accelerator: ModelAccelerator,
    allowCpuFallback: Boolean,
    modelName: String,
): LiteRtRunner = try {
    LiteRtRunner.open(modelPath, accelerator)
} catch (gpuError: Exception) {
    if (!allowCpuFallback || accelerator != ModelAccelerator.GPU) throw gpuError
    Log.w(
        "ChtoZaVino",
        "$modelName GPU initialization failed. Retrying on CPU.",
        gpuError,
    )
    try {
        LiteRtRunner.openCpu(modelPath)
    } catch (cpuError: Exception) {
        cpuError.addSuppressed(gpuError)
        throw cpuError
    }
}

object AcceleratorDetector {
    fun detect(pack: InstalledModelPack): AcceleratorProbeResult {
        val disInput = createDisProbeInput()
        val disPath = pack.file("dis.tflite").absolutePath
        var disGpuFailure: String? = null
        val dis = try {
            LiteRtRunner.openGpu(disPath).use { runner ->
                validateDisOutput(runner.run(disInput), DIS_SIZE * DIS_SIZE)
            }
            ModelAccelerator.GPU
        } catch (error: Exception) {
            disGpuFailure = probeMessage(error)
            LiteRtRunner.openCpu(disPath).use { runner ->
                validateDisOutput(runner.run(disInput), DIS_SIZE * DIS_SIZE)
            }
            ModelAccelerator.CPU
        }

        val sigLip2Input = FloatArray(3 * SIGLIP_SIZE * SIGLIP_SIZE)
        val sigLip2Path = pack.file("siglip2_base_224_fp16.tflite").absolutePath
        var sigLip2GpuFailure: String? = null
        val sigLip2 = try {
            LiteRtRunner.openGpu(sigLip2Path).use { runner ->
                normalizeSigLipVector(runner.run(sigLip2Input))
            }
            ModelAccelerator.GPU
        } catch (error: Exception) {
            sigLip2GpuFailure = probeMessage(error)
            LiteRtRunner.openCpu(sigLip2Path).use { runner ->
                normalizeSigLipVector(runner.run(sigLip2Input))
            }
            ModelAccelerator.CPU
        }
        return AcceleratorProbeResult(
            dis = dis,
            sigLip2 = sigLip2,
            disGpuFailure = disGpuFailure,
            sigLip2GpuFailure = sigLip2GpuFailure,
        )
    }

    private fun createDisProbeInput(): FloatArray {
        val plane = DIS_SIZE * DIS_SIZE
        val input = FloatArray(3 * plane)
        for (y in 0 until DIS_SIZE) {
            for (x in 0 until DIS_SIZE) {
                val index = y * DIS_SIZE + x
                input[index] = x.toFloat() / (DIS_SIZE - 1) - 0.5f
                input[plane + index] = y.toFloat() / (DIS_SIZE - 1) - 0.5f
                input[2 * plane + index] = (x + y).toFloat() / (2 * (DIS_SIZE - 1)) - 0.5f
            }
        }
        return input
    }

    private fun probeMessage(error: Throwable): String {
        var current: Throwable? = error
        while (current != null) {
            val message = current.message?.trim()
            if (!message.isNullOrEmpty()) return message
            current = current.cause
        }
        return error.javaClass.simpleName
    }
}

private data class PreparedImage(
    val debug: DebugImages,
    val modelInput: Bitmap,
)

private object DisImageProcessor {
    fun prepare(source: Bitmap, mask: FloatArray): PreparedImage {
        var minX = DIS_SIZE
        var minY = DIS_SIZE
        var maxX = -1
        var maxY = -1
        var foregroundCount = 0
        for (y in 0 until DIS_SIZE) {
            val row = y * DIS_SIZE
            for (x in 0 until DIS_SIZE) {
                if (mask[row + x] >= MASK_THRESHOLD) {
                    foregroundCount += 1
                    minX = min(minX, x)
                    minY = min(minY, y)
                    maxX = max(maxX, x)
                    maxY = max(maxY, y)
                }
            }
        }
        val fraction = foregroundCount.toFloat() / mask.size
        if (maxX < minX || fraction < 0.005f) {
            throw ImageRecognitionException(
                "DIS не нашёл главный объект. Поместите бутылку в центр кадра.",
            )
        }
        if (fraction > 0.995f) {
            throw ImageRecognitionException(
                "DIS выделил весь кадр. Снимите бутылку на более простом фоне.",
            )
        }

        var left = (minX.toFloat() / DIS_SIZE * source.width).toInt()
        var top = (minY.toFloat() / DIS_SIZE * source.height).toInt()
        var right = ceil((maxX + 1f) / DIS_SIZE * source.width).toInt()
        var bottom = ceil((maxY + 1f) / DIS_SIZE * source.height).toInt()
        val marginX = ((right - left) * 0.04f).roundToInt()
        val marginY = ((bottom - top) * 0.04f).roundToInt()
        left = (left - marginX).coerceAtLeast(0)
        top = (top - marginY).coerceAtLeast(0)
        right = (right + marginX).coerceAtMost(source.width)
        bottom = (bottom + marginY).coerceAtMost(source.height)
        if (right <= left || bottom <= top) {
            throw ImageRecognitionException("DIS вернул пустую область объекта.")
        }

        val width = right - left
        val height = bottom - top
        val crop = Bitmap.createBitmap(source, left, top, width, height)
        val cropPixels = IntArray(width * height)
        crop.getPixels(cropPixels, 0, width, 0, 0, width, height)
        val compositePixels = IntArray(cropPixels.size)
        for (y in 0 until height) {
            val sourceY = top + y
            val maskY = (sourceY * DIS_SIZE / source.height).coerceIn(0, DIS_SIZE - 1)
            for (x in 0 until width) {
                val sourceX = left + x
                val maskX = (sourceX * DIS_SIZE / source.width).coerceIn(0, DIS_SIZE - 1)
                val alpha = mask[maskY * DIS_SIZE + maskX].coerceIn(0f, 1f)
                val pixel = cropPixels[y * width + x]
                val red = (255f + (((pixel ushr 16) and 0xff) - 255f) * alpha).roundToInt()
                val green = (255f + (((pixel ushr 8) and 0xff) - 255f) * alpha).roundToInt()
                val blue = (255f + ((pixel and 0xff) - 255f) * alpha).roundToInt()
                compositePixels[y * width + x] = Color.rgb(red, green, blue)
            }
        }
        val composite = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        composite.setPixels(compositePixels, 0, width, 0, 0, width, height)

        val squareSide = max(width, height)
        val square = Bitmap.createBitmap(squareSide, squareSide, Bitmap.Config.ARGB_8888)
        Canvas(square).apply {
            drawColor(Color.WHITE)
            drawBitmap(composite, ((squareSide - width) / 2f), ((squareSide - height) / 2f), null)
        }
        composite.recycle()

        val previewWidth: Int
        val previewHeight: Int
        if (source.width >= source.height) {
            previewWidth = 512
            previewHeight = max(1, (512f * source.height / source.width).roundToInt())
        } else {
            previewHeight = 512
            previewWidth = max(1, (512f * source.width / source.height).roundToInt())
        }
        val maskPixels = IntArray(previewWidth * previewHeight)
        for (y in 0 until previewHeight) {
            val maskY = y * DIS_SIZE / previewHeight
            for (x in 0 until previewWidth) {
                val maskX = x * DIS_SIZE / previewWidth
                val value = (mask[maskY * DIS_SIZE + maskX].coerceIn(0f, 1f) * 255f).roundToInt()
                maskPixels[y * previewWidth + x] = Color.rgb(value, value, value)
            }
        }
        val maskPreview = Bitmap.createBitmap(previewWidth, previewHeight, Bitmap.Config.ARGB_8888)
        maskPreview.setPixels(maskPixels, 0, previewWidth, 0, 0, previewWidth, previewHeight)

        return PreparedImage(
            debug = DebugImages(maskPreview, crop, square),
            modelInput = square,
        )
    }
}

class RecognitionEngine(private val pack: InstalledModelPack) {
    private val index = CatalogueIndex.load(pack)

    fun findCode(raw: String): List<WineMatch> = index.findCode(raw)

    fun recognize(
        bitmap: Bitmap,
        accelerators: RecognitionAccelerators,
        limit: Int = 5,
    ): RecognitionOutput {
        require(limit in 1..20)
        val disStart = System.nanoTime()
        val mask: FloatArray
        val disAccelerator: String
        DisSegmenter(
            modelPath = pack.file("dis.tflite").absolutePath,
            accelerator = accelerators.dis,
            allowCpuFallback = accelerators.allowDisCpuFallback,
        ).use { dis ->
            mask = dis.mask(bitmap)
            disAccelerator = dis.accelerator
        }
        val prepared = DisImageProcessor.prepare(bitmap, mask)
        val disMs = elapsedMs(disStart)

        val embeddingStart = System.nanoTime()
        val embedding: FloatArray
        val embeddingAccelerator: String
        SigLip2Encoder(
            modelPath = pack.file("siglip2_base_224_fp16.tflite").absolutePath,
            accelerator = accelerators.sigLip2,
            allowCpuFallback = accelerators.allowSigLip2CpuFallback,
        ).use { encoder ->
            embedding = encoder.encode(prepared.modelInput)
            embeddingAccelerator = encoder.accelerator
        }
        val embeddingMs = elapsedMs(embeddingStart)

        val searchStart = System.nanoTime()
        val matches = index.search(embedding, limit)
        val searchMs = elapsedMs(searchStart)
        if (matches.isEmpty()) {
            throw ImageRecognitionException("В локальном каталоге нет результата.")
        }
        return RecognitionOutput(
            matches = matches,
            debugImages = prepared.debug,
            disMs = disMs,
            embeddingMs = embeddingMs,
            searchMs = searchMs,
            disAccelerator = disAccelerator,
            embeddingAccelerator = embeddingAccelerator,
        )
    }

    private fun elapsedMs(start: Long): Long = (System.nanoTime() - start) / 1_000_000L
}

object BitmapLoader {
    fun decode(context: Context, uri: Uri): Bitmap {
        return decode(ImageDecoder.createSource(context.contentResolver, uri))
    }

    fun decode(file: File): Bitmap = decode(ImageDecoder.createSource(file))

    private fun decode(source: ImageDecoder.Source): Bitmap {
        val decoded = ImageDecoder.decodeBitmap(source) { decoder, info, _ ->
            decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            val width = info.size.width
            val height = info.size.height
            val longest = max(width, height)
            if (longest > MAX_SOURCE_SIDE) {
                val scale = MAX_SOURCE_SIDE.toFloat() / longest
                decoder.setTargetSize(
                    max(1, (width * scale).roundToInt()),
                    max(1, (height * scale).roundToInt()),
                )
            }
        }
        return if (decoded.config == Bitmap.Config.ARGB_8888) decoded else decoded.copy(
            Bitmap.Config.ARGB_8888,
            false,
        ).also { decoded.recycle() }
    }
}
