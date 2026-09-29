package com.alolalab.chtozavino

import android.content.Context

internal const val DEBUG_HTTP_SERVER_DEFAULT_ENABLED = false
private const val KEY_DEBUG_HTTP_SERVER_ENABLED = "debug_http_server_enabled"

interface DebugHttpServerControl {
    fun setDebugHttpServerEnabled(enabled: Boolean)
}

internal fun isDebugHttpServerEnabled(context: Context): Boolean =
    context.getSharedPreferences(SETTINGS_PREFERENCES, Context.MODE_PRIVATE)
        .getBoolean(KEY_DEBUG_HTTP_SERVER_ENABLED, DEBUG_HTTP_SERVER_DEFAULT_ENABLED)

internal fun saveDebugHttpServerEnabled(context: Context, enabled: Boolean) {
    context.getSharedPreferences(SETTINGS_PREFERENCES, Context.MODE_PRIVATE)
        .edit()
        .putBoolean(KEY_DEBUG_HTTP_SERVER_ENABLED, enabled)
        .apply()
}
