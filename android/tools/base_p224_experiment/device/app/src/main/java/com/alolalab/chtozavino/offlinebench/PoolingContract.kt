package com.alolalab.chtozavino.offlinebench

import kotlin.math.ln
import org.json.JSONObject

internal data class BaseCondition(val number: Int,val name: String,val budget: Int,
    val pooling: String,val modelManifest: String,val vectors: String,val modelSha: String,
    val queryFrame: String="bottle-crop-white",val segmenter: String="CPU",val referencePolicy: String="matched",
    val segmenterModel: String="YOLO") {
    companion object {
        fun parse(row: JSONObject): BaseCondition {
            val number=row.getInt("number")
            val budget=row.getInt("budget")
            val pooling=row.getString("pooling")
            require(number in 1..8)
            require(budget==if(number>=3)512 else 224)
            require(pooling==if(number in setOf(2,4,6,7,8))"fractional-bg010" else "standard")
            val frame=row.optString("query_frame","bottle-crop-white")
            val segmenter=row.optString("segmenter","CPU")
            val references=row.optString("reference_policy","matched")
            val segmenterModel=row.optString("segmenter_model","YOLO")
            if(number>=7) {
                require(frame==if(number==7)"full-image" else "bottle-crop-white")
                require(segmenter=="GPU" && segmenterModel=="DIS" && references=="previous-matched-custom")
            } else if(number>=5) {
                require(frame=="full-image")
                require(segmenter==if(number==5)"NONE" else "CPU")
                require(references==if(number==5)"production-standard" else "previous-matched-custom")
            } else require(frame=="bottle-crop-white" && segmenter=="CPU" && references=="matched")
            val profile=row.getJSONObject("effective_profile").getJSONObject("parameters")
            require(profile.getInt("max_num_patches")==budget && profile.getString("pooling")==pooling)
            return BaseCondition(number,row.getString("name"),budget,pooling,
                row.getString("model_manifest"),row.getString("vectors"),row.getString("model_sha256"),frame,segmenter,references,segmenterModel)
        }
    }
}

internal fun bottleLogWeights(foreground: FloatArray,budget: Int,custom: Boolean): FloatArray {
    require(foreground.isNotEmpty() && foreground.size<=budget)
    require(foreground.all { it.isFinite() && it in 0f..1f })
    return FloatArray(budget) { index ->
        if(!custom || index>=foreground.size)0f
        else ln(.1f*(1-foreground[index])+foreground[index])
    }
}
