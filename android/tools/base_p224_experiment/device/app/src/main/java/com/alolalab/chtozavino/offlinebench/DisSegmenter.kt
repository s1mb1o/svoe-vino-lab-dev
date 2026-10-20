package com.alolalab.chtozavino.offlinebench

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import com.google.ai.edge.litert.CompiledModel
import com.google.ai.edge.litert.Accelerator
import com.google.ai.edge.litert.Environment
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.json.JSONObject

internal fun normalizedDisMask(values: FloatArray): FloatArray {
    require(values.isNotEmpty() && values.all { it.isFinite() }) { "DIS вернул некорректную маску." }
    val low=values.min();val range=values.max()-low
    require(range.isFinite() && range>1e-6f) { "Сегментация не нашла объект." }
    return FloatArray(values.size) { ((values[it]-low)/range).coerceIn(0f,1f) }
}

internal fun disOptions()=CompiledModel.Options(Accelerator.GPU).apply {
    gpuOptions=CompiledModel.GpuOptions(precision=CompiledModel.GpuOptions.Precision.FP32,
        bufferStorageType=CompiledModel.GpuOptions.BufferStorageType.DEFAULT,
        serializeProgramCache=false,serializeExternalTensors=false)
}

internal fun disInputSize(metadata: JSONObject): Int {
    val input=metadata.getJSONArray("input_shape");val output=metadata.getJSONArray("output_shape")
    require(input.length()==4 && output.length()==4)
    val size=input.getInt(2)
    require(size in setOf(512,768,1024) && metadata.getString("precision")=="float32")
    require((0..3).map { input.getInt(it) }==listOf(1,3,size,size))
    require((0..3).map { output.getInt(it) }==listOf(1,1,size,size))
    return size
}

internal class DisSegmenter(file: File,environment: Environment,private val size: Int=1024): AutoCloseable {
    private val owner=Thread.currentThread()
    private val modelSha=sha256(file)
    // Keep exact mask arithmetic without forcing the encoder's BUFFER storage onto DIS.
    private val model=CompiledModel.create(file.path,disOptions(),environment)
    private val inputs=model.createInputBuffers()
    private val outputs=model.createOutputBuffers()
    init { require(size in setOf(512,768,1024) && inputs.size==1 && outputs.size==1) }
    fun segment(source: Bitmap,capture: File?): Segmented {
        check(Thread.currentThread()===owner)
        val started=System.nanoTime();val plane=size*size
        val image=Bitmap.createBitmap(size,size,Bitmap.Config.ARGB_8888)
        val pixels=IntArray(plane)
        try {
            Canvas(image).drawBitmap(source,null,RectF(0f,0f,size.toFloat(),size.toFloat()),
                Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
            image.getPixels(pixels,0,size,0,0,size,size)
        } finally { image.recycle() }
        val input=FloatArray(plane*3)
        for(i in pixels.indices) {
            input[i]=((pixels[i] ushr 16) and 255)/255f-.5f
            input[plane+i]=((pixels[i] ushr 8) and 255)/255f-.5f
            input[2*plane+i]=(pixels[i] and 255)/255f-.5f
        }
        inputs.single().writeFloat(input);val ready=System.nanoTime()
        model.run(inputs,outputs);val raw=outputs.single().readFloat();val inferred=System.nanoTime()
        require(raw.size==plane) { "DIS вернул некорректный размер маски." }
        val mask=normalizedDisMask(raw)
        require(mask.count { it>=.5f }>=4) { "Сегментация не нашла объект." }
        if(capture!=null) {
            capture.mkdirs()
            fun save(name: String,array: FloatArray) {
                val bytes=ByteBuffer.allocate(array.size*4).order(ByteOrder.LITTLE_ENDIAN)
                bytes.asFloatBuffer().put(array);File(capture,name).writeBytes(bytes.array())
            }
            save("input.f32",input);save("raw-mask.f32",raw);save("normalized-mask.f32",mask)
        }
        return Segmented(DenseMask(mask,size,size,source.width,source.height),null,
            JSONObject().put("model","DIS").put("accelerator","GPU").put("label_present",false)
                .put("input_size",size).put("model_sha256",modelSha)
                .put("preprocess_ms",(ready-started)/1_000_000.0)
                .put("inference_ms",(inferred-ready)/1_000_000.0)
                .put("total_ms",(System.nanoTime()-started)/1_000_000.0))
    }
    override fun close() {
        check(Thread.currentThread()===owner)
        inputs.forEach { it.close() };outputs.forEach { it.close() };model.close()
    }
}
