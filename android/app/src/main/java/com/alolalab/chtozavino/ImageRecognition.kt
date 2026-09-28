package com.alolalab.chtozavino

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.ImageDecoder
import android.graphics.Paint
import android.graphics.RectF
import android.net.Uri
import com.google.ai.edge.litert.Accelerator
import com.google.ai.edge.litert.CompiledModel
import com.google.ai.edge.litert.TensorBuffer
import kotlin.math.ceil
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sqrt

private const val DIS_SIZE = 1024
private const val SIGLIP_SIZE = 224
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
        fun open(path: String): LiteRtRunner {
            return try {
                LiteRtRunner(
                    CompiledModel.create(
                        path,
                        CompiledModel.Options(Accelerator.GPU),
                        null,
                    ),
                    "GPU",
                )
            } catch (gpuError: Exception) {
                try {
                    LiteRtRunner(
                        CompiledModel.create(
                            path,
                            CompiledModel.Options(Accelerator.CPU),
                            null,
                        ),
                        "CPU",
                    )
                } catch (cpuError: Exception) {
                    cpuError.addSuppressed(gpuError)
                    throw ImageRecognitionException(
                        "LiteRT не смог загрузить модель на GPU или CPU.",
                        cpuError,
                    )
                }
            }
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

private class DisSegmenter(modelPath: String) : AutoCloseable {
    private val runner = LiteRtRunner.open(modelPath)
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
        val output = runner.run(input)
        if (output.size != plane) {
            throw ImageRecognitionException("DIS вернул маску неизвестного размера.")
        }
        return output
    }

    override fun close() = runner.close()
}

private class SigLip2Encoder(modelPath: String) : AutoCloseable {
    private val runner = LiteRtRunner.open(modelPath)
    val accelerator: String get() = runner.accelerator

    fun encode(bitmap: Bitmap): FloatArray {
        val resized = Bitmap.createScaledBitmap(bitmap, SIGLIP_SIZE, SIGLIP_SIZE, true)
        val pixels = IntArray(SIGLIP_SIZE * SIGLIP_SIZE)
        resized.getPixels(pixels, 0, SIGLIP_SIZE, 0, 0, SIGLIP_SIZE, SIGLIP_SIZE)
        if (resized !== bitmap) resized.recycle()

        val plane = SIGLIP_SIZE * SIGLIP_SIZE
        val input = FloatArray(3 * plane)
        for (index in pixels.indices) {
            val pixel = pixels[index]
            input[index] = (((pixel ushr 16) and 0xff) / 127.5f) - 1f
            input[plane + index] = (((pixel ushr 8) and 0xff) / 127.5f) - 1f
            input[2 * plane + index] = ((pixel and 0xff) / 127.5f) - 1f
        }
        val output = runner.run(input)
        if (output.size != VECTOR_DIMENSION) {
            throw ImageRecognitionException(
                "SigLIP2 вернул ${output.size} значений вместо $VECTOR_DIMENSION.",
            )
        }
        var normSquared = 0.0
        for (value in output) normSquared += value * value
        val norm = sqrt(normSquared).toFloat()
        if (!norm.isFinite() || norm <= 0f) {
            throw ImageRecognitionException("SigLIP2 вернул пустой вектор.")
        }
        for (index in output.indices) output[index] /= norm
        return output
    }

    override fun close() = runner.close()
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

    fun recognize(bitmap: Bitmap): RecognitionOutput {
        val disStart = System.nanoTime()
        val mask: FloatArray
        val disAccelerator: String
        DisSegmenter(pack.file("dis.tflite").absolutePath).use { dis ->
            disAccelerator = dis.accelerator
            mask = dis.mask(bitmap)
        }
        val prepared = DisImageProcessor.prepare(bitmap, mask)
        val disMs = elapsedMs(disStart)

        val embeddingStart = System.nanoTime()
        val embedding: FloatArray
        val embeddingAccelerator: String
        SigLip2Encoder(pack.file("siglip2_base_224_fp16.tflite").absolutePath).use { encoder ->
            embeddingAccelerator = encoder.accelerator
            embedding = encoder.encode(prepared.modelInput)
        }
        val embeddingMs = elapsedMs(embeddingStart)

        val searchStart = System.nanoTime()
        val matches = index.search(embedding)
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
        val source = ImageDecoder.createSource(context.contentResolver, uri)
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
