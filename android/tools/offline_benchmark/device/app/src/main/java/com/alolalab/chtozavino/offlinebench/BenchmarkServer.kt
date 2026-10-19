package com.alolalab.chtozavino.offlinebench

import android.content.Context
import android.app.ActivityManager
import android.os.Process
import android.util.Log
import fi.iki.elonen.NanoHTTPD
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.ExecutionException
import org.json.JSONObject

/** USB transport only. The application never sends images to an upstream service. */
internal class BenchmarkServer(context: Context,private val status: (String)->Unit) : NanoHTTPD(18088),AutoCloseable {
    private val directory=File(context.filesDir,"bench")
    companion object {
        // Keep creation and cleanup ordered even when HTTP is disabled and enabled.
        private val worker=Executors.newSingleThreadExecutor { task -> Thread(task,"offline-inference") }
    }
    private var engine: BenchmarkEngine?=null
    @Volatile private var health=JSONObject().put("status","not_initialized").put("pid",Process.myPid())
    @Volatile private var active=false
    @Volatile private var closed=false
    override fun serve(session: IHTTPSession): Response = try {
        if(session.method==Method.GET && session.uri=="/healthz") {
            val process=ActivityManager.RunningAppProcessInfo()
            ActivityManager.getMyMemoryState(process)
            respond(Response.Status.OK,JSONObject(health.toString()).put("active",active)
                .put("foreground_service",BenchmarkRuntime.foregroundService)
                .put("wake_lock_held",BenchmarkRuntime.wakeLockHeld)
                .put("process_importance",process.importance)
                .put("pack_present",File(directory,"manifest.json").isFile)
                .put("reranking",false).put("barcode",false))
        } else if(session.method==Method.POST && session.uri in setOf("/v1/match","/v1/eval/predict","/v1/debug/embedding")) {
            require(session.headers["content-type"].orEmpty().startsWith("multipart/form-data")) { "multipart/form-data required" }
            val contentLength=session.headers["content-length"]?.toLongOrNull() ?: error("Content-Length required")
            require(contentLength in 1..(20*1024*1024L+65536)) { "Image exceeds 20 MiB" }
            val files=hashMapOf<String,String>()
            session.parseBody(files)
            require(files.keys==setOf("image")) { "Supply exactly one image. Masks and answers are forbidden." }
            val allowed=setOf("image","variant","k","accelerator")
            require(session.parameters.keys.all { it in allowed }) { "Unexpected request field" }
            val image=File(checkNotNull(files["image"]))
            require(image.isFile && image.length() in 1..20*1024*1024L)
            val selection=session.parameters["variant"]?.singleOrNull() ?: "1"
            val k=session.parameters["k"]?.singleOrNull()?.toInt() ?: 20
            require(k in 1..20)
            val accelerator=session.parameters["accelerator"]?.singleOrNull() ?: "GPU"
            require(accelerator in setOf("CPU","GPU"))
            val result=worker.submit<JSONObject> {
                check(!closed) { "Benchmark HTTP server is closed" }
                active=true
                try {
                    if(engine==null) {
                        status("Проверка пакета и загрузка моделей…")
                        engine=BenchmarkEngine(directory)
                    }
                    engine!!.predict(image,selection,k,accelerator,session.uri=="/v1/debug/embedding").also {
                        health=engine!!.health()
                        status("Готово · ${it.getInt("encoder_passes")} проходов · ${it.getDouble("latency_ms").toInt()} мс")
                    }
                } finally { active=false }
            }.get()
            respond(Response.Status.OK,result)
        } else respond(Response.Status.NOT_FOUND,JSONObject().put("error","not found"))
    } catch(error: Exception) {
        val cause=if(error is ExecutionException)error.cause ?: error else error
        Log.e("OfflineBench","Request failed",cause)
        respond(if(cause is IllegalArgumentException)Response.Status.BAD_REQUEST else Response.Status.INTERNAL_ERROR,
            JSONObject().put("error",cause.message ?: cause.javaClass.simpleName).put("pid",Process.myPid())
                .put("reranking",false).put("barcode",false))
    }
    private fun respond(status: Response.Status,body: JSONObject)=newFixedLengthResponse(status,"application/json",body.toString())
    override fun close() {
        close {}
    }
    fun close(afterClosed: () -> Unit) {
        if(closed)return
        closed=true
        stop()
        worker.execute {
            try { engine?.close() }
            finally { engine=null;afterClosed() }
        }
    }
}
