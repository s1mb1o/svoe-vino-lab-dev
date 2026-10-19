package com.alolalab.chtozavino.offlinebench

import android.util.Log
import com.google.ai.edge.litert.Environment
import com.google.ai.edge.litert.TensorBuffer
import dev.naflex.litert.EncoderSession
import dev.naflex.litert.NaFlexPreprocessor
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.sqrt
import org.json.JSONObject

internal data class Embedded(val vector: FloatArray, val weights: FloatArray,
                             val trace: JSONObject)

internal class WeightedEncoder(private val directory: File, private val manifest: JSONObject,
                              positionsFile: File, private val environment: Environment) : AutoCloseable {
    private val owner = Thread.currentThread()
    private val preprocessor = NaFlexPreprocessor()
    private val table = positionsFile.readBytes().let { bytes ->
        require(bytes.size == 256 * 1152 * 4)
        FloatArray(bytes.size/4).also { ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(it) }
    }
    private var session: EncoderSession? = null
    private var inputs: List<TensorBuffer> = emptyList()
    private var outputs: List<TensorBuffer> = emptyList()
    var accelerator: String = ""
        private set

    fun select(accelerator: String) {
        check(Thread.currentThread() === owner)
        require(accelerator in setOf("GPU","CPU"))
        if (session != null && this.accelerator == accelerator) return
        close()
        val options = encoderOptions(accelerator)
        Log.i("OfflineBench", "Encoder compilation started: $accelerator; GPU options=${options.gpuOptions}")
        session = EncoderSession.create(directory,manifest,options,environment) {}
        inputs = session!!.createInputBuffers()
        outputs = session!!.createOutputBuffers()
        this.accelerator = accelerator
        Log.i("OfflineBench", "Encoder compilation finished: $accelerator")
    }

    fun encode(frame: MattingFrame, profile: String, capture: File? = null): Embedded {
        check(Thread.currentThread() === owner)
        checkNotNull(session)
        val started = System.nanoTime()
        val image = preprocessor.prepare(frame.bitmap,table,budget=512,dimension=1152)
        val preprocessed = System.nanoTime()
        val weights = if (profile == "u") FloatArray(512) else {
            require(profile in setOf("g1-bg010-l2-legacy","g1-bg000-l2-legacy","g1-bg000-l3-exact"))
            val exact = profile.endsWith("-exact")
            fun coverage(mask: FloatArray) = if(exact) MaskCoverage.exact(mask,frame.bitmap.width,
                frame.bitmap.height,image.width,image.height) else MaskCoverage.legacy(mask,
                frame.bitmap.width,frame.bitmap.height,image.width,image.height)
            val foreground = coverage(frame.foreground)
            val label = frame.label?.let(::coverage)
            MaskCoverage.logWeights(foreground,label,512,if(profile.contains("bg010")) .1f else 0f,
                if(profile.contains("-l3-")) 3f else 2f)
        }
        val weighted = System.nanoTime()
        val contract = manifest.getJSONArray("inputs")
        require(inputs.size == 4 && contract.length() == 4)
        for (index in inputs.indices) inputs[index].writeFloat(when(contract.getJSONObject(index).getString("logical_name")) {
            "patch_pixels" -> image.pixels
            "position_values" -> image.positions
            "valid_patches" -> image.mask
            "pooling_log_weights" -> weights
            else -> error("Unknown encoder input.")
        })
        val inferenceStarted = System.nanoTime()
        session!!.run(inputs,outputs)
        val vector = outputs.single().readFloat()
        require(vector.size == 1152 && vector.all { it.isFinite() }) { "Некорректный вектор SO400M." }
        val norm = sqrt(vector.sumOf { it.toDouble() * it })
        require(abs(norm-1)<.001) { "Некорректная норма SO400M: $norm." }
        val finished = System.nanoTime()
        if(capture!=null) {
            capture.mkdirs()
            fun save(name: String,values: FloatArray) {
                val buffer=ByteBuffer.allocate(values.size*4).order(ByteOrder.LITTLE_ENDIAN)
                buffer.asFloatBuffer().put(values)
                File(capture,name).writeBytes(buffer.array())
            }
            save("patch_pixels.f32",image.pixels);save("position_values.f32",image.positions)
            save("valid_patches.f32",image.mask);save("pooling_log_weights.f32",weights)
            save("embedding.f32",vector)
            save("foreground.f32",frame.foreground)
            if(frame.label!=null)save("label.f32",frame.label) else File(capture,"label.f32").delete()
            File(capture,"image.png").outputStream().use { frame.bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it) }
        }
        fun ms(a: Long,b: Long) = (b-a)/1_000_000.0
        return Embedded(vector,weights,JSONObject()
            .put("accelerator",accelerator).put("profile",profile)
            .put("gpu_constant_tensor_sharing",accelerator=="GPU")
            .put("gpu_source_quantization",false)
            .put("grid_rows",image.height).put("grid_columns",image.width)
            .put("valid_patches",image.height*image.width).put("norm",norm)
            .put("preprocess_ms",ms(started,preprocessed)).put("mask_weights_ms",ms(preprocessed,weighted))
            .put("inference_ms",ms(inferenceStarted,finished)).put("total_ms",ms(started,finished))
            .put("rotation_degrees",frame.angle).put("frame_width",frame.bitmap.width)
            .put("frame_height",frame.bitmap.height).put("large_crop_render_scale",frame.renderScale))
    }
    override fun close() {
        check(Thread.currentThread() === owner)
        inputs.forEach { it.close() };inputs=emptyList()
        outputs.forEach { it.close() };outputs=emptyList()
        session?.close();session=null
        accelerator=""
    }
}
