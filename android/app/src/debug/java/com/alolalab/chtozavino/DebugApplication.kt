package com.alolalab.chtozavino

import android.app.Application

class DebugApplication : Application(), DebugHttpServerControl {
    // AppViewModel restores the saved server setting after pack migration and probes.

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
