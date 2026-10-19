package com.alolalab.chtozavino.offlinebench

import android.content.Context
import android.os.Handler
import android.os.Looper

/** Process lifetime. An Activity recreation must not close a running USB evaluation. */
internal object BenchmarkRuntime {
    private var server: BenchmarkServer? = null
    @Volatile var stopping = false
        private set
    @Volatile var foregroundService = false
    @Volatile var wakeLockHeld = false
    @Volatile var listener: ((String)->Unit)? = null
    @Volatile var message: String = "HTTP-сервер выключен"
        private set
    val running get() = server!=null
    private fun publish(value: String) {
        message=value
        listener?.invoke(value)
    }
    fun start(context: Context) {
        check(!stopping) { "Previous benchmark shutdown is still active" }
        if(server!=null)return
        server=BenchmarkServer(context.applicationContext) { publish(it) }.also { it.start() }
        publish("HTTP-сервер включён · порт 18088")
    }
    fun stop(afterClosed: () -> Unit = {}) {
        val previous=server
        server=null
        if(previous==null) { afterClosed();return }
        stopping=true
        publish("Остановка HTTP-сервера и освобождение моделей…")
        previous.close {
            Handler(Looper.getMainLooper()).post {
                stopping=false
                publish("HTTP-сервер выключен")
                afterClosed()
            }
        }
    }
    fun failed(error: Exception) {
        publish("Ошибка: ${error.message}")
    }
}
