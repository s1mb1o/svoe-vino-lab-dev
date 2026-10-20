package com.alolalab.chtozavino.offlinebench

import java.io.File
import java.io.FileInputStream
import java.nio.channels.FileChannel
import java.security.MessageDigest
import org.json.JSONArray

internal fun child(directory: File,name: String): File {
    val file=File(directory,name).canonicalFile
    require(file.path.startsWith(directory.canonicalPath+File.separator)) { "Unsafe pack path" }
    return file
}
internal fun sha256(file: File): String {
    val digest=MessageDigest.getInstance("SHA-256")
    file.inputStream().buffered(1024*1024).use { stream ->
        val buffer=ByteArray(1024*1024)
        while(true) { val n=stream.read(buffer);if(n<0)break;digest.update(buffer,0,n) }
    }
    return digest.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
}
internal class BaseIndex(file: File,private val slugs: List<String>) {
    private val matrix=FileInputStream(file).channel.use {
        require(file.length()==slugs.size.toLong()*768*4)
        it.map(FileChannel.MapMode.READ_ONLY,0,file.length())
    }
    fun scores(vector: FloatArray): FloatArray {
        require(vector.size==768 && vector.all { it.isFinite() })
        return NativeDot.score(matrix,slugs.size,768,vector).also { require(it.all(Float::isFinite)) }
    }
}
internal fun ranked(scores: FloatArray,slugs: List<String>,k: Int): JSONArray {
    require(scores.size==slugs.size && k in 1..20)
    val order=scores.indices.sortedWith(compareByDescending<Int> { scores[it] }.thenBy { slugs[it] })
    return JSONArray().apply {
        order.take(k).forEachIndexed { rank,index -> put(org.json.JSONObject()
            .put("slug",slugs[index]).put("score",scores[index]).put("rank",rank+1)) }
    }
}
