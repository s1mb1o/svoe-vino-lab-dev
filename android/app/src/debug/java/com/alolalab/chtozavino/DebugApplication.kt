package com.alolalab.chtozavino

import android.app.Application
import android.util.Log

class DebugApplication : Application(), DebugHttpServerControl {
    override fun onCreate() {
        super.onCreate()
        if (isDebugHttpServerEnabled(this)) {
            runCatching { DebugHttpServer.start(this) }
                .onFailure {
                    saveDebugHttpServerEnabled(this, false)
                    Log.e("ChtoZaVino", "Cannot start the debug HTTP server.", it)
                }
        }
    }

    override fun setDebugHttpServerEnabled(enabled: Boolean) {
        if (enabled) {
            DebugHttpServer.start(this)
        } else {
            DebugHttpServer.stop()
        }
    }

    override fun onTerminate() {
        DebugHttpServer.stop()
        super.onTerminate()
    }
}
