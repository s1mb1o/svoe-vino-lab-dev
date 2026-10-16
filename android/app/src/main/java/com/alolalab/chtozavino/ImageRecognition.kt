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
import com.google.ai.edge.litert.Environment
import com.google.ai.edge.litert.TensorBuffer
import java.io.File
import kotlin.math.ceil
import kotlin.math.floor
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
        fun open(
            path: String,
            accelerator: ModelAccelerator,
            environment: Environment? = null,
        ): LiteRtRunner =
            when (accelerator) {
                ModelAccelerator.GPU -> openGpu(path, environment)
                ModelAccelerator.CPU -> openCpu(path, environment)
            }

        fun openGpu(path: String, environment: Environment? = null): LiteRtRunner = try {
            LiteRtRunner(
                CompiledModel.create(
                    path,
                    CompiledModel.Options(Accelerator.GPU),
                    environment,
                ),
                "GPU",
            )
        } catch (error: Exception) {
            throw ImageRecognitionException("LiteRT не смог загрузить модель на GPU.", error)
        }

        fun openCpu(path: String, environment: Environment? = null): LiteRtRunner = try {
            LiteRtRunner(
                CompiledModel.create(
                    path,
                    CompiledModel.Options(Accelerator.CPU),
                    environment,
                ),
                "CPU",
            )
        } catch (error: Exception) {
            throw ImageRecognitionException("LiteRT не смог загрузить модель на CPU.", error)
        }
    }

    fun run(input: FloatArray): FloatArray {
        return runAll(input).first()
    }

    fun runAll(input: FloatArray): List<FloatArray> {
        inputs[0].writeFloat(input)
        model.run(inputs, outputs)
        return outputs.map(TensorBuffer::readFloat)
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
    private val environment: Environment? = null,
) : AutoCloseable {
    private var runner = openRunner(
        modelPath,
        accelerator,
        allowCpuFallback,
        "DIS",
        environment,
    )
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
                LiteRtRunner.openCpu(modelPath, environment)
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

private class YoloBottleSegmenter(
    modelPath: String,
    environment: Environment? = null,
) : AutoCloseable {
    private val runner = LiteRtRunner.openCpu(modelPath, environment)
    val accelerator: String get() = runner.accelerator

    fun mask(bitmap: Bitmap): SegmentationMask {
        val scale = min(
            YOLO_INPUT_SIZE.toFloat() / bitmap.width,
            YOLO_INPUT_SIZE.toFloat() / bitmap.height,
        )
        val resizedWidth = max(1, (bitmap.width * scale).roundToInt())
        val resizedHeight = max(1, (bitmap.height * scale).roundToInt())
        val padLeft = (YOLO_INPUT_SIZE - resizedWidth) / 2
        val padTop = (YOLO_INPUT_SIZE - resizedHeight) / 2
        val inputBitmap = Bitmap.createBitmap(
            YOLO_INPUT_SIZE,
            YOLO_INPUT_SIZE,
            Bitmap.Config.ARGB_8888,
        )
        Canvas(inputBitmap).apply {
            drawColor(Color.rgb(114, 114, 114))
            drawBitmap(
                bitmap,
                null,
                RectF(
                    padLeft.toFloat(),
                    padTop.toFloat(),
                    (padLeft + resizedWidth).toFloat(),
                    (padTop + resizedHeight).toFloat(),
                ),
                Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG),
            )
        }

        val pixels = IntArray(YOLO_INPUT_SIZE * YOLO_INPUT_SIZE)
        inputBitmap.getPixels(
            pixels,
            0,
            YOLO_INPUT_SIZE,
            0,
            0,
            YOLO_INPUT_SIZE,
            YOLO_INPUT_SIZE,
        )
        inputBitmap.recycle()
        val plane = YOLO_INPUT_SIZE * YOLO_INPUT_SIZE
        val input = FloatArray(3 * plane)
        for (index in pixels.indices) {
            val pixel = pixels[index]
            input[index] = ((pixel ushr 16) and 0xff) / 255f
            input[plane + index] = ((pixel ushr 8) and 0xff) / 255f
            input[2 * plane + index] = (pixel and 0xff) / 255f
        }

        val outputs = runner.runAll(input)
        val detections = outputs.singleOrNull {
            it.size == YOLO_DETECTION_FEATURE_COUNT * YOLO_ANCHOR_COUNT
        } ?: throw ImageRecognitionException(
            "YOLO26n-seg вернул неизвестный detection tensor: ${outputs.map(FloatArray::size)}.",
        )
        val prototypes = outputs.singleOrNull {
            it.size == YOLO_MASK_COEFFICIENT_COUNT * YOLO_PROTO_SIZE * YOLO_PROTO_SIZE
        } ?: throw ImageRecognitionException(
            "YOLO26n-seg вернул неизвестный mask tensor: ${outputs.map(FloatArray::size)}.",
        )
        val bottle = selectYoloBottleDetection(detections)
            ?: throw ImageRecognitionException(
                "YOLO не нашёл бутылку. Поместите всю бутылку в центр кадра.",
            )
        val protoScale = YOLO_PROTO_SIZE.toFloat() / YOLO_INPUT_SIZE
        val contentLeft = floor(padLeft * protoScale).toInt().coerceIn(0, YOLO_PROTO_SIZE - 1)
        val contentTop = floor(padTop * protoScale).toInt().coerceIn(0, YOLO_PROTO_SIZE - 1)
        val contentRight = ceil((padLeft + resizedWidth) * protoScale)
            .toInt().coerceIn(contentLeft + 1, YOLO_PROTO_SIZE)
        val contentBottom = ceil((padTop + resizedHeight) * protoScale)
            .toInt().coerceIn(contentTop + 1, YOLO_PROTO_SIZE)
        return buildYoloBottleMask(
            prototypes = prototypes,
            detection = bottle,
            contentLeft = contentLeft,
            contentTop = contentTop,
            contentRight = contentRight,
            contentBottom = contentBottom,
        )
    }

    override fun close() = runner.close()
}

private class SigLip2Encoder(
    private val modelPath: String,
    accelerator: ModelAccelerator,
    private val allowCpuFallback: Boolean,
    private val environment: Environment? = null,
) : AutoCloseable {
    private var runner = openRunner(
        modelPath,
        accelerator,
        allowCpuFallback,
        "SigLIP2",
        environment,
    )
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
                LiteRtRunner.openCpu(modelPath, environment)
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
    environment: Environment? = null,
): LiteRtRunner = try {
    LiteRtRunner.open(modelPath, accelerator, environment)
} catch (gpuError: Exception) {
    if (!allowCpuFallback || accelerator != ModelAccelerator.GPU) throw gpuError
    Log.w(
        "ChtoZaVino",
        "$modelName GPU initialization failed. Retrying on CPU.",
        gpuError,
    )
    try {
        LiteRtRunner.openCpu(modelPath, environment)
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

private object ForegroundImageProcessor {
    fun prepare(
        source: Bitmap,
        segmentationMask: SegmentationMask,
        segmenterName: String,
    ): PreparedImage {
        val mask = segmentationMask.values
        val maskWidth = segmentationMask.width
        val maskHeight = segmentationMask.height
        require(mask.size == maskWidth * maskHeight)
        var minX = maskWidth
        var minY = maskHeight
        var maxX = -1
        var maxY = -1
        var foregroundCount = 0
        for (y in 0 until maskHeight) {
            val row = y * maskWidth
            for (x in 0 until maskWidth) {
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
                "$segmenterName не нашёл главный объект. Поместите бутылку в центр кадра.",
            )
        }
        if (fraction > 0.995f) {
            throw ImageRecognitionException(
                "$segmenterName выделил весь кадр. Снимите бутылку на более простом фоне.",
            )
        }

        var left = (minX.toFloat() / maskWidth * source.width).toInt()
        var top = (minY.toFloat() / maskHeight * source.height).toInt()
        var right = ceil((maxX + 1f) / maskWidth * source.width).toInt()
        var bottom = ceil((maxY + 1f) / maskHeight * source.height).toInt()
        val marginX = ((right - left) * 0.04f).roundToInt()
        val marginY = ((bottom - top) * 0.04f).roundToInt()
        left = (left - marginX).coerceAtLeast(0)
        top = (top - marginY).coerceAtLeast(0)
        right = (right + marginX).coerceAtMost(source.width)
        bottom = (bottom + marginY).coerceAtMost(source.height)
        if (right <= left || bottom <= top) {
            throw ImageRecognitionException("$segmenterName вернул пустую область объекта.")
        }

        val width = right - left
        val height = bottom - top
        val crop = Bitmap.createBitmap(source, left, top, width, height)
        val cropPixels = IntArray(width * height)
        crop.getPixels(cropPixels, 0, width, 0, 0, width, height)
        val compositePixels = IntArray(cropPixels.size)
        for (y in 0 until height) {
            val sourceY = top + y
            val maskY = (sourceY * maskHeight / source.height).coerceIn(0, maskHeight - 1)
            for (x in 0 until width) {
                val sourceX = left + x
                val maskX = (sourceX * maskWidth / source.width).coerceIn(0, maskWidth - 1)
                val alpha = mask[maskY * maskWidth + maskX].coerceIn(0f, 1f)
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
            val maskY = y * maskHeight / previewHeight
            for (x in 0 until previewWidth) {
                val maskX = x * maskWidth / previewWidth
                val value = (mask[maskY * maskWidth + maskX].coerceIn(0f, 1f) * 255f)
                    .roundToInt()
                maskPixels[y * previewWidth + x] = Color.rgb(value, value, value)
            }
        }
        val maskPreview = Bitmap.createBitmap(previewWidth, previewHeight, Bitmap.Config.ARGB_8888)
        maskPreview.setPixels(maskPixels, 0, previewWidth, 0, 0, previewWidth, previewHeight)

        return PreparedImage(
            debug = DebugImages(maskPreview, crop, square, segmenterName),
            modelInput = square,
        )
    }
}

class RecognitionEngine(private val pack: InstalledModelPack) : AutoCloseable {
    private val index = CatalogueIndex.load(pack)
    private val environment = Environment.create()
    private var disSegmenter: DisSegmenter? = null
    private var disAccelerator: ModelAccelerator? = null
    private var disAllowsFallback: Boolean? = null
    private var yoloSegmenter: YoloBottleSegmenter? = null
    private var encoder: SigLip2Encoder? = null
    private var encoderAccelerator: ModelAccelerator? = null
    private var encoderAllowsFallback: Boolean? = null

    fun findCode(raw: String): List<WineMatch> = index.findCode(raw)

    @Synchronized
    fun recognize(
        bitmap: Bitmap,
        accelerators: RecognitionAccelerators,
        segmenterMode: SegmenterMode = SegmenterMode.DIS,
        limit: Int = 5,
    ): RecognitionOutput {
        require(limit in 1..20)
        val segmentationStart = System.nanoTime()
        val mask: SegmentationMask
        val segmenterName: String
        val actualSegmentationAccelerator: String
        if (segmenterMode == SegmenterMode.YOLO) {
            if (!pack.hasYolo()) {
                throw ImageRecognitionException("В пакете моделей нет YOLO26n-seg.")
            }
            closeDisSegmenter()
            val yolo = yoloSegmenter ?: YoloBottleSegmenter(
                pack.file("yolo26n-seg_w8a32.tflite").absolutePath,
                environment,
            ).also { yoloSegmenter = it }
            mask = yolo.mask(bitmap)
            segmenterName = SegmenterMode.YOLO.name
            actualSegmentationAccelerator = yolo.accelerator
        } else {
            closeYoloSegmenter()
            val dis = getDisSegmenter(accelerators)
            mask = SegmentationMask(dis.mask(bitmap), DIS_SIZE, DIS_SIZE)
            segmenterName = SegmenterMode.DIS.name
            actualSegmentationAccelerator = dis.accelerator
        }
        val prepared = ForegroundImageProcessor.prepare(bitmap, mask, segmenterName)
        val segmentationMs = elapsedMs(segmentationStart)

        val embeddingStart = System.nanoTime()
        val effectiveEmbeddingAccelerator = if (
            segmenterMode == SegmenterMode.DIS &&
            actualSegmentationAccelerator == ModelAccelerator.GPU.name &&
            accelerators.sigLip2 == ModelAccelerator.GPU
        ) {
            // LiteRT GPU can abort when two CompiledModel instances live in one process.
            // Keep DIS on GPU and use CPU for the smaller SigLIP2 model.
            ModelAccelerator.CPU
        } else {
            accelerators.sigLip2
        }
        val activeEncoder = getEncoder(
            accelerator = effectiveEmbeddingAccelerator,
            allowCpuFallback = accelerators.allowSigLip2CpuFallback,
        )
        val embedding = activeEncoder.encode(prepared.modelInput)
        val embeddingAccelerator = activeEncoder.accelerator
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
            segmentationMs = segmentationMs,
            embeddingMs = embeddingMs,
            searchMs = searchMs,
            segmenterName = segmenterName,
            segmentationAccelerator = actualSegmentationAccelerator,
            embeddingAccelerator = embeddingAccelerator,
        )
    }

    private fun getDisSegmenter(accelerators: RecognitionAccelerators): DisSegmenter {
        if (
            disSegmenter == null ||
            disAccelerator != accelerators.dis ||
            disAllowsFallback != accelerators.allowDisCpuFallback
        ) {
            closeDisSegmenter()
            if (accelerators.dis == ModelAccelerator.GPU && encoder?.accelerator == "GPU") {
                closeEncoder()
            }
            disSegmenter = DisSegmenter(
                modelPath = pack.file("dis.tflite").absolutePath,
                accelerator = accelerators.dis,
                allowCpuFallback = accelerators.allowDisCpuFallback,
                environment = environment,
            )
            disAccelerator = accelerators.dis
            disAllowsFallback = accelerators.allowDisCpuFallback
        }
        return checkNotNull(disSegmenter)
    }

    private fun getEncoder(
        accelerator: ModelAccelerator,
        allowCpuFallback: Boolean,
    ): SigLip2Encoder {
        if (
            encoder == null || encoderAccelerator != accelerator ||
            encoderAllowsFallback != allowCpuFallback
        ) {
            closeEncoder()
            encoder = SigLip2Encoder(
                modelPath = pack.file("siglip2_base_224_fp16.tflite").absolutePath,
                accelerator = accelerator,
                allowCpuFallback = allowCpuFallback,
                environment = environment,
            )
            encoderAccelerator = accelerator
            encoderAllowsFallback = allowCpuFallback
        }
        return checkNotNull(encoder)
    }

    private fun closeDisSegmenter() {
        disSegmenter?.close()
        disSegmenter = null
        disAccelerator = null
        disAllowsFallback = null
    }

    private fun closeYoloSegmenter() {
        yoloSegmenter?.close()
        yoloSegmenter = null
    }

    private fun closeEncoder() {
        encoder?.close()
        encoder = null
        encoderAccelerator = null
        encoderAllowsFallback = null
    }

    @Synchronized
    override fun close() {
        closeDisSegmenter()
        closeYoloSegmenter()
        closeEncoder()
        environment.close()
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
