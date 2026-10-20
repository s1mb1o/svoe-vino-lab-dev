package com.alolalab.chtozavino.offlinebench

import android.graphics.Bitmap
import android.graphics.ColorSpace
import android.graphics.ImageDecoder
import android.os.Process
import com.google.ai.edge.litert.Environment
import java.io.File
import org.json.JSONArray
import org.json.JSONObject

internal class BenchmarkEngine(private val directory: File): AutoCloseable {
    private val owner=Thread.currentThread()
    private val manifest=JSONObject(child(directory,"manifest.json").readText())
    private val slugs=manifest.getJSONArray("slugs").let { a -> (0 until a.length()).map { a.getString(it) } }
    private val conditions=manifest.getJSONArray("conditions").let { a -> (0 until a.length()).map { BaseCondition.parse(a.getJSONObject(it)) } }
    private val environment: Environment
    private var segmenter: BottleLabelSegmenter?=null
    private var disSegmenter: DisSegmenter?=null
    private val segmentationMetadata=JSONObject(child(directory,manifest.getString("segmenter_manifest")).readText())
    private val disSize=if(manifest.getInt("format_version")==4)disInputSize(segmentationMetadata) else 0
    private val encoder: BaseEncoder
    private val indices=mutableMapOf<Int,BaseIndex>()
    private var current: BaseCondition?=null
    init {
        require(manifest.getString("format")=="chtozavino-base-p224-comparison")
        require(manifest.getInt("format_version") in 2..4)
        require(manifest.getInt("dimension")==768 && manifest.getInt("wine_count")==slugs.size && slugs.size==2093)
        require(slugs==slugs.sorted() && slugs.size==slugs.distinct().size)
        require(conditions.map { it.number }==when(manifest.getInt("format_version")) {
            2 -> listOf(1,2,3,4);3 -> listOf(5,6);else -> listOf(5,7,8) })
        require(!manifest.getBoolean("reranking") && !manifest.getBoolean("barcode"))
        require(manifest.getInt("reference_views")==1)
        val files=manifest.getJSONObject("files")
        for(name in files.keys()) {
            val row=files.getJSONObject(name);val file=child(directory,name)
            require(file.isFile && file.length()==row.getLong("bytes") && sha256(file)==row.getString("sha256"))
        }
        for(condition in conditions) {
            require(files.has(condition.modelManifest) && files.has(condition.vectors))
            val model=JSONObject(child(directory,condition.modelManifest).readText())
            val name=model.getString("model_file")
            require(files.has(name) && model.getString("model_sha256")==condition.modelSha)
            require(files.getJSONObject(name).getString("sha256")==condition.modelSha)
            require(files.getJSONObject(condition.vectors).getLong("bytes")==slugs.size.toLong()*768*4)
        }
        for(condition in conditions) {
            val name=manifest.getJSONObject("validations").getString(condition.budget.toString())
            require(files.has(name))
            val validation=JSONObject(child(directory,name).readText())
            require(validation.getBoolean("passed"))
            require(validation.getString(if(condition.number in setOf(3,5))"source_sha256" else "candidate_sha256")==condition.modelSha)
        }
        val segmentation=JSONObject(child(directory,manifest.getString("segmenter_manifest")).readText())
        require(segmentation.getJSONObject(if(manifest.getInt("format_version")==4)"source_verification" else "numerical_validation").getBoolean("passed"))
        environment=Environment.create()
        try {
            encoder=BaseEncoder(directory,child(directory,manifest.getString("position_table")),environment)
        } catch(error: Throwable) { environment.close();throw error }
    }
    fun health(): JSONObject=JSONObject().put("status","ok").put("pid",Process.myPid())
        .put("model",manifest.getString("model")).put("revision",manifest.getString("revision"))
        .put("dimension",768).put("max_num_patches",current?.budget ?: 224)
        .put("condition",current?.number ?: 0).put("wine_count",slugs.size)
        .put("pack_version",manifest.getString("version")).put("reranking",false).put("barcode",false)
        .put("encoder_accelerator",encoder.accelerator).put("segmenter_accelerator",current?.segmenter ?: "NONE").put("offline",true)
        .put("query_frame",current?.queryFrame ?: "not-selected").put("reference_policy",current?.referencePolicy ?: "not-selected")
        .put("dis_input_size",disSize)
    fun predict(image: File,selection: String,k: Int,accelerator: String,debug: Boolean): JSONObject {
        check(Thread.currentThread()===owner)
        // Keep blocks independent. Avoid model-budget recreation on every query.
        val number=selection.toIntOrNull();require(conditions.any { it.number==number }) { "Specify an installed variant" }
        val condition=conditions.single { it.number==number };current=condition
        val started=System.nanoTime();encoder.select(condition,accelerator)
        val bitmap=if(condition.number>=5)decodeFullImage(image)
        else ImageDecoder.decodeBitmap(ImageDecoder.createSource(image)) { decoder,info,_ ->
            require(info.size.width.toLong()*info.size.height<=24_000_000)
            decoder.allocator=ImageDecoder.ALLOCATOR_SOFTWARE
            decoder.setTargetColorSpace(ColorSpace.get(ColorSpace.Named.SRGB))
        }
        try { return recognize(bitmap,condition,k,debug,started).put("image_sha256",sha256(image)) }
        finally { bitmap.recycle() }
    }
    private fun recognize(source: Bitmap,condition: BaseCondition,k: Int,debug: Boolean,started: Long): JSONObject {
        val segmentation=if(condition.segmenter=="NONE") {
            segmenter?.close();segmenter=null;disSegmenter?.close();disSegmenter=null;null
        } else if(condition.segmenterModel=="DIS") {
            val active=disSegmenter ?: DisSegmenter(child(directory,segmentationMetadata.getString("model_file")),environment,disSize).also { disSegmenter=it }
            active.segment(source,if(debug)File(directory.parentFile,"bench-diagnostics/segmenter") else null)
        } else {
            val active=segmenter ?: BottleLabelSegmenter(child(directory,segmentationMetadata.getString("model_file")),segmentationMetadata,environment).also { segmenter=it }
            active.segment(source,if(debug)File(directory.parentFile,"bench-diagnostics/segmenter") else null)
        }
        val capture=if(debug)File(directory.parentFile,"bench-diagnostics/pass-0") else null
        val frame=if(condition.queryFrame=="full-image")fullImageFrame(source,segmentation?.bottle)
            else renderFrame(source,checkNotNull(segmentation).bottle,null,0.0,.04)
        val embedded=frame.use {
            val result=encoder.encode(it,condition,capture)
            result.trace.put("query_frame",condition.queryFrame).put("source_width",source.width).put("source_height",source.height)
            if(debug && condition.queryFrame=="full-image") {
                val sourceSha=bitmapPixelSha(source);val frameSha=bitmapPixelSha(it.bitmap)
                check(source.width==it.bitmap.width && source.height==it.bitmap.height && sourceSha==frameSha)
                result.trace.put("source_pixel_sha256",sourceSha).put("frame_pixel_sha256",frameSha)
                result.trace.put("source_color_space",source.colorSpace?.name)
                    .put("pixel_contract","raw-rgb-ignore-alpha")
                File(checkNotNull(capture),"frame.rgb").writeBytes(bitmapRgb(it.bitmap))
                File(checkNotNull(capture),"frame.png").outputStream().use { stream ->
                    check(it.bitmap.compress(Bitmap.CompressFormat.PNG,100,stream))
                }
            }
            result
        }
        val searchStarted=System.nanoTime()
        val scores=indices.getOrPut(condition.number) { BaseIndex(child(directory,condition.vectors),slugs) }.scores(embedded.vector)
        val candidates=ranked(scores,slugs,k)
        val result=JSONObject().put("variant",condition.number).put("name",condition.name)
            .put("slug",candidates.getJSONObject(0).getString("slug")).put("candidates",candidates)
            .put("budget",condition.budget).put("pooling",condition.pooling).put("timing_mode","independent")
            .put("query_frame",condition.queryFrame).put("reference_policy",condition.referencePolicy)
        if(debug)result.put("embedding",JSONArray(embedded.vector.toList())).put("bottle_scores",JSONArray(scores.toList()))
        return health().put("variants",JSONArray().put(result)).put("encoder_passes",1)
            .put("encoders",JSONArray().put(embedded.trace)).put("segmentation",segmentation?.trace ?: JSONObject().put("skipped",true))
            .put("label_used",false).put("search_ms",(System.nanoTime()-searchStarted)/1_000_000.0)
            .put("latency_ms",(System.nanoTime()-started)/1_000_000.0).put("timing_mode","independent")
    }
    override fun close() {
        check(Thread.currentThread()===owner);encoder.close();segmenter?.close();disSegmenter?.close();environment.close()
    }
}
