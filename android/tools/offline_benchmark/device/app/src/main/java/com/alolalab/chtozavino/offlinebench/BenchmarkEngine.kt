package com.alolalab.chtozavino.offlinebench

import android.graphics.Bitmap
import android.graphics.ColorSpace
import android.graphics.ImageDecoder
import android.os.Process
import com.google.ai.edge.litert.Environment
import java.io.File
import java.security.MessageDigest
import kotlin.math.sqrt
import org.json.JSONArray
import org.json.JSONObject

internal fun sha256(file: File): String {
    val digest=MessageDigest.getInstance("SHA-256")
    file.inputStream().buffered(1024*1024).use { stream ->
        val buffer=ByteArray(1024*1024)
        while(true) { val count=stream.read(buffer);if(count<0)break;digest.update(buffer,0,count) }
    }
    return digest.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
}

internal fun unitMean(first: FloatArray,second: FloatArray): FloatArray {
    require(first.size==second.size)
    val result=FloatArray(first.size) { first[it]+second[it] }
    val norm=sqrt(result.sumOf { it.toDouble()*it })
    require(norm>1e-9 && norm.isFinite())
    return FloatArray(result.size) { (result[it]/norm).toFloat() }
}

/** All model operations, including cleanup, run on the single inference worker. */
internal class BenchmarkEngine(private val directory: File) : AutoCloseable {
    private val owner=Thread.currentThread()
    val manifest=JSONObject(child(directory,"manifest.json").readText())
    private val slugs=manifest.getJSONArray("slugs").let { a -> (0 until a.length()).map { a.getString(it) } }
    private val variants=manifest.getJSONArray("variants").let { a -> (0 until a.length()).map { a.getJSONObject(it) } }
    private val environment: Environment
    private val segmenter: BottleLabelSegmenter
    private val encoder: WeightedEncoder
    private val indices=mutableMapOf<String,ReferenceIndex>()
    init {
        require(manifest.getString("format")=="chtozavino-offline-device-benchmark")
        require(!manifest.getBoolean("reranking") && !manifest.getBoolean("barcode"))
        require(manifest.getInt("dimension")==1152 && manifest.getInt("max_num_patches")==512)
        require(slugs.size==slugs.distinct().size && slugs==slugs.sorted() && variants.size==10)
        val files=manifest.getJSONObject("files")
        for (name in files.keys()) {
            val specification=files.getJSONObject(name)
            val file=child(directory,name)
            require(file.isFile && file.length()==specification.getLong("bytes")) { "Wrong pack file size: $name" }
            require(sha256(file)==specification.getString("sha256")) { "Wrong pack checksum: $name" }
        }
        val encoderMetadata=JSONObject(child(directory,manifest.getString("encoder_manifest")).readText())
        val profile=encoderMetadata.getJSONObject("profile")
        require(profile.getString("model_id")==manifest.getString("model"))
        require(profile.getString("model_revision")==manifest.getString("revision"))
        require(profile.getInt("embedding_dimension")==1152 && profile.getInt("max_num_patches")==512)
        val segmentationMetadata=JSONObject(child(directory,manifest.getString("segmenter_manifest")).readText())
        require(segmentationMetadata.getJSONObject("numerical_validation").getBoolean("passed"))
        environment=Environment.create()
        try {
            segmenter=BottleLabelSegmenter(child(directory,segmentationMetadata.getString("model_file")),segmentationMetadata,environment)
            encoder=WeightedEncoder(directory,encoderMetadata,child(directory,manifest.getString("position_table")),environment)
        } catch(error: Throwable) { environment.close();throw error }
    }
    fun health(): JSONObject=JSONObject().put("status","ok").put("pid",Process.myPid())
        .put("model",manifest.getString("model")).put("revision",manifest.getString("revision"))
        .put("dimension",1152).put("max_num_patches",512).put("wine_count",slugs.size)
        .put("pack_version",manifest.getString("version")).put("reranking",false).put("barcode",false)
        .put("encoder_accelerator",encoder.accelerator).put("segmenter_accelerator","CPU")
        .put("query_masks","on-device-mobile-segmenter").put("offline",true)

    fun predict(image: File,selection: String,k: Int,accelerator: String,debug: Boolean): JSONObject {
        check(Thread.currentThread()===owner)
        val started=System.nanoTime()
        val selected=if(selection=="all")variants else variants.filter { it.getInt("number").toString()==selection }
        require(selected.isNotEmpty()) { "variant must be 1 through 10 or all" }
        encoder.select(accelerator)
        val bitmap=ImageDecoder.decodeBitmap(ImageDecoder.createSource(image)) { decoder,info,_ ->
            require(info.size.width.toLong()*info.size.height<=24_000_000) { "Image exceeds 24 megapixels" }
            decoder.allocator=ImageDecoder.ALLOCATOR_SOFTWARE
            decoder.setTargetColorSpace(ColorSpace.get(ColorSpace.Named.SRGB))
        }
        try { return recognize(bitmap,selected,k,debug,started).put("image_sha256",sha256(image)) }
        finally { bitmap.recycle() }
    }
    private fun recognize(source: Bitmap,selected: List<JSONObject>,k: Int,debug: Boolean,started: Long): JSONObject {
        val segmentation=segmenter.segment(source,if(debug)File(directory.parentFile,"bench-diagnostics/segmenter") else null)
        val best=MaskGeometry.bestAngle(segmentation.bottle)
        val guarded=MaskGeometry.guarded(best)
        // Cache only inside one request. Never reuse an embedding between query images.
        val embeddings=linkedMapOf<String,Embedded>()
        val derived=mutableMapOf<String,FloatArray>()
        val scores=mutableMapOf<String,FloatArray>()
        var renderMs=0.0
        fun embed(profile: String,kind: String,angle: Double,margin: Double): Embedded {
            val key="$kind:$profile:$angle:$margin"
            return embeddings.getOrPut(key) {
                val before=System.nanoTime()
                val matte=if(kind=="label")checkNotNull(segmentation.label) else segmentation.bottle
                renderFrame(source,matte,if(kind=="label")null else segmentation.label,angle,margin).use { frame ->
                    renderMs+=(System.nanoTime()-before)/1_000_000.0
                    val capture=if(debug)File(directory.parentFile,"bench-diagnostics/pass-${embeddings.size}") else null
                    encoder.encode(frame,profile,capture).also { it.trace.put("key",key).put("space",kind)
                        if(capture!=null)it.trace.put("diagnostic_directory",capture.path) }
                }
            }
        }
        fun bottle(recipe: JSONObject): FloatArray {
            val profile=recipe.getString("query_pool")
            val geometry=recipe.getString("query_geometry")
            val key="$profile:$geometry"
            return derived.getOrPut(key) {
                fun original()=embed(profile,"bottle",0.0,.04).vector
                fun rotated(angle: Double)=embed(profile,"bottle",angle,0.0).vector
                when(geometry) {
                    "crop" -> rotated(0.0)
                    "iou" -> rotated(best)
                    "card5" -> rotated(guarded)
                    "mean-iou" -> unitMean(original(),rotated(best))
                    "mean-card5" -> unitMean(original(),rotated(guarded))
                    "original" -> original()
                    else -> error("Unknown query geometry: $geometry")
                }
            }
        }
        fun score(index: String,key: String,vector: FloatArray,aggregation: String): FloatArray =
            scores.getOrPut("$index:$key:$aggregation") {
                indices.getOrPut(index) {
                    ReferenceIndex(directory,manifest.getJSONObject("indices").getJSONObject(index),slugs.size)
                }.score(vector,aggregation)
            }
        val results=JSONArray()
        for(specification in selected) {
            val before=System.nanoTime()
            val recipe=specification.getJSONObject("recipe")
            val vector=bottle(recipe)
            val queryKey=recipe.getString("query_pool")+":"+recipe.getString("query_geometry")
            val searchStarted=System.nanoTime()
            val bs=score(specification.getString("bottle_index"),queryKey,vector,recipe.getString("aggregation"))
            val bottleSearchEnd=System.nanoTime()
            var labelVector: FloatArray?=null
            val ls=if(specification.has("label_index") && !specification.isNull("label_index") && segmentation.label!=null) {
                labelVector=embed("u","label",0.0,0.0).vector
                score(specification.getString("label_index"),"label:u",labelVector!!,"max")
            } else null
            val weight=specification.optJSONObject("fusion")?.getDouble("bottle_weight") ?: 1.0
            val candidates=ranked(fuse(bs,ls,weight),slugs,k)
            val finished=System.nanoTime()
            val result=JSONObject().put("variant",specification.getInt("number"))
                .put("desktop_variant_id",specification.getString("desktop_variant_id"))
                .put("slug",candidates.optJSONObject(0)?.getString("slug").orEmpty()).put("candidates",candidates)
                .put("recipe",recipe).put("label_used",ls!=null).put("bottle_weight",weight)
                .put("variant_incremental_ms",(finished-before)/1_000_000.0)
                .put("bottle_search_ms",(bottleSearchEnd-searchStarted)/1_000_000.0)
                .put("timing_mode",if(selected.size==1)"independent" else "shared-query-work")
            if(debug) {
                result.put("embedding",JSONArray(vector.toList()))
                if(labelVector!=null)result.put("label_embedding",JSONArray(labelVector!!.toList()))
                result.put("bottle_scores",JSONArray(bs.map { if(it.isFinite())it else JSONObject.NULL }))
            }
            results.put(result)
        }
        val traces=JSONArray(embeddings.values.map { it.trace })
        val response=health().put("variants",results).put("encoder_passes",embeddings.size)
            .put("encoders",traces).put("segmentation",segmentation.trace)
            .put("best_angle",best).put("guarded_angle",guarded).put("render_ms",renderMs)
            .put("latency_ms",(System.nanoTime()-started)/1_000_000.0)
            .put("timing_mode",if(selected.size==1)"independent" else "shared-query-work")
        if(debug)response.put("pooling_log_weights",JSONArray(embeddings.values.map { JSONArray(it.weights.toList()) }))
        return response
    }
    override fun close() {
        check(Thread.currentThread()===owner)
        encoder.close();segmenter.close();environment.close()
    }
}
