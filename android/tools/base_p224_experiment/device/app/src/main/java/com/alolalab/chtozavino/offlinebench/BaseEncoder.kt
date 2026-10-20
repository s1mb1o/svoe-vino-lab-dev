package com.alolalab.chtozavino.offlinebench

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

internal data class BaseEmbedding(val vector: FloatArray,val trace: JSONObject,val weights: FloatArray)

internal class BaseEncoder(private val directory: File,tableFile: File,
    private val environment: Environment): AutoCloseable {
    private val owner=Thread.currentThread()
    private val preprocessor=NaFlexPreprocessor()
    private val table=tableFile.readBytes().let { bytes ->
        require(bytes.size==256*768*4)
        FloatArray(256*768).also { ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(it) }
    }
    private var session: EncoderSession?=null
    private var inputs: List<TensorBuffer> = emptyList()
    private var outputs: List<TensorBuffer> = emptyList()
    private var contract: JSONObject?=null
    private var modelSha=""
    var accelerator=""
        private set
    fun select(condition: BaseCondition,requested: String) {
        check(Thread.currentThread()===owner)
        require(requested in setOf("CPU","GPU"))
        if(session!=null && modelSha==condition.modelSha && accelerator==requested)return
        close()
        val metadata=JSONObject(child(directory,condition.modelManifest).readText())
        val profile=metadata.getJSONObject("profile")
        require(metadata.getString("model_sha256")==condition.modelSha)
        require(profile.getInt("max_num_patches")==condition.budget && profile.getInt("embedding_dimension")==768)
        require(profile.getString("model_id")=="google/siglip2-base-patch16-naflex")
        require(profile.getString("model_revision")=="b53b807d3a2d5e2b3911292f2d69e5341cdc064c")
        session=EncoderSession.create(directory,metadata,encoderOptions(requested),environment) {}
        inputs=session!!.createInputBuffers();outputs=session!!.createOutputBuffers()
        contract=metadata;modelSha=condition.modelSha;accelerator=requested
    }
    fun encode(frame: MattingFrame,condition: BaseCondition,capture: File?): BaseEmbedding {
        check(Thread.currentThread()===owner);checkNotNull(session)
        val started=System.nanoTime()
        val image=preprocessor.prepare(frame.bitmap,table,budget=condition.budget,dimension=768)
        val foreground=MaskCoverage.exact(frame.foreground,frame.bitmap.width,frame.bitmap.height,image.width,image.height)
        val weights=bottleLogWeights(foreground,condition.budget,condition.pooling!="standard")
        val values=mapOf("patch_pixels" to image.pixels,"position_values" to image.positions,
            "valid_patches" to image.mask,"pooling_log_weights" to weights)
        val metadata=contract!!.getJSONArray("inputs")
        require(inputs.size==metadata.length())
        for(index in inputs.indices)inputs[index].writeFloat(checkNotNull(values[metadata.getJSONObject(index).getString("logical_name")]))
        val inferStarted=System.nanoTime();session!!.run(inputs,outputs)
        val vector=outputs.single().readFloat()
        require(vector.size==768 && vector.all { it.isFinite() }) { "Некорректный вектор Base NaFlex" }
        val norm=sqrt(vector.sumOf { it.toDouble()*it });require(abs(norm-1)<.001)
        val finished=System.nanoTime()
        if(capture!=null) {
            capture.mkdirs()
            fun save(name: String,array: FloatArray) {
                val bytes=ByteBuffer.allocate(array.size*4).order(ByteOrder.LITTLE_ENDIAN)
                bytes.asFloatBuffer().put(array);File(capture,name).writeBytes(bytes.array())
            }
            for((name,array)in values)save(name+".f32",array)
            save("embedding.f32",vector);save("foreground.f32",frame.foreground)
        }
        return BaseEmbedding(vector,JSONObject().put("accelerator",accelerator).put("budget",condition.budget)
            .put("profile",condition.pooling).put("dimension",768).put("norm",norm)
            .put("model_sha256",modelSha).put("grid_rows",image.height).put("grid_columns",image.width)
            .put("frame_width",frame.bitmap.width).put("frame_height",frame.bitmap.height)
            .put("preprocess_ms",(inferStarted-started)/1_000_000.0)
            .put("inference_ms",(finished-inferStarted)/1_000_000.0),weights)
    }
    override fun close() {
        check(Thread.currentThread()===owner)
        inputs.forEach { it.close() };outputs.forEach { it.close() }
        inputs=emptyList();outputs=emptyList();session?.close();session=null
        contract=null;modelSha="";accelerator=""
    }
}
