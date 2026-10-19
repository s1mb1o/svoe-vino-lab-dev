package com.alolalab.chtozavino.offlinebench

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import com.google.ai.edge.litert.Accelerator
import com.google.ai.edge.litert.CompiledModel
import com.google.ai.edge.litert.Environment
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.*
import org.json.JSONObject

internal data class Segmented(val bottle: DenseMask, val label: DenseMask?,
                              val trace: JSONObject)

internal class BottleLabelSegmenter(file: File, private val metadata: JSONObject,
                                    environment: Environment) : AutoCloseable {
    private val owner = Thread.currentThread()
    private val model = CompiledModel.create(file.path,CompiledModel.Options(Accelerator.CPU),environment)
    private val inputs = model.createInputBuffers()
    private val outputs = model.createOutputBuffers()
    private val size = 640
    private val proto = 160
    private val anchors = 8400
    private data class Detection(val cx: Float,val cy: Float,val w: Float,val h: Float,
                                 val confidence: Float,val coefficients: FloatArray) {
        val left get() = cx-w/2
        val top get() = cy-h/2
        val right get() = cx+w/2
        val bottom get() = cy+h/2
    }
    init {
        require(metadata.getString("input_layout")=="NCHW" && metadata.getString("coordinate_units")=="pixels")
        require(metadata.getJSONArray("classes").toString()=="[\"bottle\",\"label\"]")
        require(inputs.size==1 && outputs.size==2)
    }
    fun segment(source: Bitmap,capture: File? = null): Segmented {
        check(Thread.currentThread()===owner)
        val started=System.nanoTime()
        val scale=min(size.toDouble()/source.width,size.toDouble()/source.height)
        val width=round(source.width*scale).toInt().coerceAtLeast(1)
        val height=round(source.height*scale).toInt().coerceAtLeast(1)
        val left=(size-width)/2
        val top=(size-height)/2
        val image=Bitmap.createBitmap(size,size,Bitmap.Config.ARGB_8888)
        val pixels=IntArray(size*size)
        try {
            Canvas(image).apply {
                drawColor(Color.rgb(114,114,114))
                drawBitmap(source,null,Rect(left,top,left+width,top+height),Paint(Paint.FILTER_BITMAP_FLAG))
            }
            image.getPixels(pixels,0,size,0,0,size,size)
        } finally { image.recycle() }
        val plane=size*size
        val tensor=FloatArray(plane*3)
        for (i in pixels.indices) {
            tensor[i]=((pixels[i] ushr 16) and 255)/255f
            tensor[plane+i]=((pixels[i] ushr 8) and 255)/255f
            tensor[plane*2+i]=(pixels[i] and 255)/255f
        }
        inputs.single().writeFloat(tensor)
        val ready=System.nanoTime()
        model.run(inputs,outputs)
        val values=outputs.map { it.readFloat() }
        require(values.all { a -> a.all { it.isFinite() } }) { "Некорректный выход сегментатора." }
        val detections=values.single { it.size==38*anchors }
        val prototypes=values.single { it.size==32*proto*proto }
        val inferred=System.nanoTime()
        if(capture!=null) {
            capture.mkdirs()
            fun save(name: String,values: FloatArray) {
                val bytes=ByteBuffer.allocate(values.size*4).order(ByteOrder.LITTLE_ENDIAN)
                bytes.asFloatBuffer().put(values)
                File(capture,name).writeBytes(bytes.array())
            }
            save("input.f32",tensor);save("detections.f32",detections);save("prototypes.f32",prototypes)
        }
        fun candidates(classId: Int): List<Detection> = (0 until anchors).mapNotNull { anchor ->
            val confidence=detections[(4+classId)*anchors+anchor]
            val other=detections[(4+1-classId)*anchors+anchor]
            val cx=detections[anchor];val cy=detections[anchors+anchor]
            val w=detections[2*anchors+anchor];val h=detections[3*anchors+anchor]
            if (confidence<.25f || confidence<other || w<=0 || h<=0 || cx<left ||
                cy<top || cx>=left+width || cy>=top+height) null
            else Detection(cx,cy,w,h,confidence,FloatArray(32) { detections[(6+it)*anchors+anchor] })
        }
        val bottleDetection=candidates(0).maxByOrNull {
            val central=(1-hypot(it.cx-size/2f,it.cy-size/2f)/hypot(size/2f,size/2f)).coerceIn(0f,1f)
            min(size.toFloat(),it.w)*min(size.toFloat(),it.h)*(.8f+.2f*central)*(.5f+.5f*it.confidence)
        } ?: error("Сегментатор не нашёл бутылку.")
        fun mask(detection: Detection): DenseMask {
            val output=FloatArray(proto*proto)
            for (y in 0 until proto) for (x in 0 until proto) {
                val xx=(x+.5)*4;val yy=(y+.5)*4
                if(xx<detection.left || xx>=detection.right || yy<detection.top || yy>=detection.bottom ||
                    xx<left || xx>=left+width || yy<top || yy>=top+height) continue
                val index=y*proto+x
                var logit=0f
                for (c in 0 until 32) logit+=detection.coefficients[c]*prototypes[c*proto*proto+index]
                output[index]=1f/(1+exp(-logit.coerceIn(-30f,30f)))
            }
            return DenseMask(output,proto,proto,source.width,source.height,
                -left/scale,-top/scale,4/scale,4/scale)
        }
        val bottle=mask(bottleDetection)
        require(bottle.values.count { it>=.5f }>=4) { "Сегментатор вернул пустую маску бутылки." }
        var label: DenseMask?=null
        var labelConfidence: Float?=null
        val labels=candidates(1).filter {
            it.cx>=bottleDetection.left && it.cx<=bottleDetection.right &&
                it.cy>=bottleDetection.top && it.cy<=bottleDetection.bottom &&
                it.w*it.h<.95*bottleDetection.w*bottleDetection.h
        }.sortedByDescending { it.w*it.h*it.confidence }.take(10)
        for (detection in labels) {
            val candidate=mask(detection)
            val active=candidate.values.indices.filter { candidate.values[it]>=.5f }
            if(active.size<4 || active.count { bottle.values[it]>=.5f }<.6*active.size) continue
            label=candidate;labelConfidence=detection.confidence;break
        }
        val finished=System.nanoTime()
        return Segmented(bottle,label,JSONObject().put("accelerator","CPU")
            .put("model","YOLO11n-seg-bottle-label").put("bottle_confidence",bottleDetection.confidence)
            .put("label_present",label!=null).put("label_confidence",labelConfidence ?: JSONObject.NULL)
            .put("preprocess_ms",(ready-started)/1_000_000.0)
            .put("inference_ms",(inferred-ready)/1_000_000.0)
            .put("postprocess_ms",(finished-inferred)/1_000_000.0)
            .put("total_ms",(finished-started)/1_000_000.0))
    }
    override fun close() {
        check(Thread.currentThread()===owner)
        inputs.forEach { it.close() };outputs.forEach { it.close() };model.close()
    }
}
