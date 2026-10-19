package com.alolalab.chtozavino

import android.graphics.Bitmap
import android.util.Log
import com.google.ai.edge.litert.Accelerator
import com.google.ai.edge.litert.CompiledModel
import com.google.ai.edge.litert.Environment
import dev.naflex.litert.EncoderSession
import dev.naflex.litert.NaFlexPreprocessor as VerifiedPreprocessor
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.json.JSONObject

/** Use the released v0.2.0 preprocessor and graph on the engine worker thread. */
internal class VerifiedNaFlexEncoder(
    private val pack: InstalledModelPack,
    requested: ModelAccelerator,
    private val allowCpuFallback: Boolean,
    private val environment: Environment?,
) : SigLipImageEncoder {
    private val owner = Thread.currentThread()
    private val metadata = JSONObject(pack.file(COMPLETE_NAFLEX_MANIFEST_FILE).readText())
    private val preprocessor = VerifiedPreprocessor()
    private val positions = pack.file(COMPLETE_NAFLEX_POSITIONS_FILE).readBytes().let { bytes ->
        FloatArray(bytes.size / Float.SIZE_BYTES).also {
            ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(it)
        }
    }
    private val ownedEnvironment = environment ?: Environment.create()
    private var selected = requested
    private var session: EncoderSession? = null
    private var inputs: List<com.google.ai.edge.litert.TensorBuffer> = emptyList()
    private var outputs: List<com.google.ai.edge.litert.TensorBuffer> = emptyList()
    private var closed = false

    init {
        try {
            session = try {
                open(selected)
            } catch (error: Exception) {
                if (!allowCpuFallback || selected != ModelAccelerator.GPU) throw error
                selected = ModelAccelerator.CPU
                open(selected)
            }
            allocateBuffers()
        } catch (error: Throwable) {
            closeSession()
            if (environment == null) ownedEnvironment.close()
            throw error
        }
    }

    override val accelerator: String get() = selected.name

    override fun encode(bitmap: Bitmap, foregroundMask: NaFlexForegroundMask?): FloatArray {
        check(Thread.currentThread() === owner)
        check(!closed)
        val image = preprocessor.prepare(bitmap, positions, budget = 512, dimension = 768)
        fun run(): FloatArray {
            val contract = metadata.getJSONArray("inputs")
            for (index in inputs.indices) {
                inputs[index].writeFloat(when (contract.getJSONObject(index).getString("logical_name")) {
                    "patch_pixels" -> image.pixels
                    "position_values" -> image.positions
                    "valid_patches" -> image.mask
                    else -> throw ImageRecognitionException("Неизвестный вход Base NaFlex p512.")
                })
            }
            checkNotNull(session).run(inputs, outputs)
            return normalizeSigLipVector(outputs.single().readFloat(), BASE_NAFLEX_VECTOR_DIMENSION)
        }
        return try {
            run()
        } catch (error: Exception) {
            if (!allowCpuFallback || selected != ModelAccelerator.GPU) throw error
            Log.w("ChtoZaVino", "Base NaFlex p512 GPU failed. Retrying on CPU.", error)
            closeSession()
            selected = ModelAccelerator.CPU
            session = open(selected)
            allocateBuffers()
            run()
        }
    }

    private fun open(accelerator: ModelAccelerator): EncoderSession {
        val options = CompiledModel.Options(
            if (accelerator == ModelAccelerator.GPU) Accelerator.GPU else Accelerator.CPU,
        )
        if (accelerator == ModelAccelerator.GPU) {
            options.gpuOptions = CompiledModel.GpuOptions(
                precision = CompiledModel.GpuOptions.Precision.FP32,
                bufferStorageType = CompiledModel.GpuOptions.BufferStorageType.BUFFER,
                serializeProgramCache = false,
                serializeExternalTensors = false,
            )
        }
        return EncoderSession.create(pack.directory, metadata, options, ownedEnvironment) {}
    }

    private fun closeSession() {
        inputs.forEach { it.close() }
        inputs = emptyList()
        outputs.forEach { it.close() }
        outputs = emptyList()
        session?.close()
        session = null
    }

    private fun allocateBuffers() {
        inputs = checkNotNull(session).createInputBuffers()
        outputs = checkNotNull(session).createOutputBuffers()
    }

    override fun close() {
        check(Thread.currentThread() === owner)
        if (closed) return
        closed = true
        closeSession()
        if (environment == null) ownedEnvironment.close()
    }
}
