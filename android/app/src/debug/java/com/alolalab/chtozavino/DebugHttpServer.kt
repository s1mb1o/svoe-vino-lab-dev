package com.alolalab.chtozavino

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import fi.iki.elonen.NanoHTTPD
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

const val DEBUG_HTTP_PORT = 18088
private const val MAX_IMAGE_BYTES = 20L * 1024L * 1024L
internal const val PIPELINE_NAME = "android-dis-siglip2-base-224"

object DebugHttpServer {
    private var server: AndroidMatcherServer? = null

    @Synchronized
    fun start(context: Context) {
        if (server != null) return
        val instance = AndroidMatcherServer(context.applicationContext)
        instance.start(NanoHTTPD.SOCKET_READ_TIMEOUT, false)
        server = instance
        Log.i("ChtoZaVino", "Debug HTTP server listens on 0.0.0.0:$DEBUG_HTTP_PORT")
    }

    @Synchronized
    fun stop() {
        server?.stop()
        server = null
    }
}

internal fun matchLimit(raw: String?): Int {
    if (raw.isNullOrBlank()) return 20
    val value = raw.toIntOrNull() ?: throw IllegalArgumentException("k must be an integer")
    require(value in 1..20) { "k must be from 1 through 20" }
    return value
}

internal fun predictionJson(matches: List<WineMatch>): JSONObject = JSONObject()
    .put("slug", matches.firstOrNull()?.wine?.slug.orEmpty())

internal fun matchJson(matches: List<WineMatch>, latencyMs: Double): JSONObject = JSONObject()
    .put("pipeline", PIPELINE_NAME)
    .put("latency_ms", latencyMs)
    .put("candidates", JSONArray().apply {
        matches.forEachIndexed { index, match ->
            put(JSONObject()
                .put("rank", index + 1)
                .put("slug", match.wine.slug)
                .put("score", match.score.toDouble())
                .put("wine", wineJson(match.wine)))
        }
    })

private fun wineJson(wine: WineCard): JSONObject = JSONObject()
    .put("name", wine.name)
    .put("page_url", wine.pageUrl)
    .put("producer", wine.producer ?: JSONObject.NULL)
    .put("category", wine.category ?: JSONObject.NULL)
    .put("region", wine.region ?: JSONObject.NULL)
    .put("color", wine.color ?: JSONObject.NULL)
    .put("grapes", wine.grapes ?: JSONObject.NULL)
    .put("sugar", JSONObject.NULL)
    .put("image_url", JSONObject.NULL)
    .put("qr_urls", JSONArray())

private class AndroidMatcherServer(
    private val context: Context,
) : NanoHTTPD(DEBUG_HTTP_PORT) {
    private val inferenceLock = ReentrantLock()
    private var engineKey: String? = null
    private var engine: RecognitionEngine? = null

    override fun serve(session: IHTTPSession): Response = try {
        when {
            session.uri == "/healthz" && session.method == Method.GET -> health()
            session.uri == "/v1/eval/predict" && session.method == Method.POST -> {
                recognize(session, null)
            }
            session.uri == "/v1/match" && session.method == Method.POST -> {
                val k = matchLimit(session.parameters["k"]?.firstOrNull())
                recognize(session, k)
            }
            session.uri in setOf("/v1/eval/predict", "/v1/match") -> {
                error(ApiStatus.METHOD_NOT_ALLOWED, "method not allowed")
            }
            else -> error(Response.Status.NOT_FOUND, "not found")
        }
    } catch (error: IllegalArgumentException) {
        error(Response.Status.BAD_REQUEST, error.message ?: "invalid request")
    } catch (error: Exception) {
        Log.e("ChtoZaVino", "Debug HTTP request failed.", error)
        error(ApiStatus.BAD_GATEWAY, friendlyMessage(error))
    }

    private fun health(): Response {
        val pack = ModelPackManager(context).current()
        val body = JSONObject()
            .put("status", if (pack == null) "loading" else "ok")
            .put("port", DEBUG_HTTP_PORT)
            .put("pack_version", pack?.manifest?.versionName ?: JSONObject.NULL)
            .put("wine_count", pack?.manifest?.wineCount ?: 0)
        return json(if (pack == null) Response.Status.SERVICE_UNAVAILABLE else Response.Status.OK, body)
    }

    private fun recognize(session: IHTTPSession, k: Int?): Response {
        val contentLength = session.headers["content-length"]?.toLongOrNull()
        if (contentLength != null && contentLength > MAX_IMAGE_BYTES + 64 * 1024L) {
            return error(ApiStatus.PAYLOAD_TOO_LARGE, "image exceeds 20 MiB")
        }
        if (!session.headers["content-type"].orEmpty().startsWith("multipart/form-data")) {
            return error(ApiStatus.UNSUPPORTED_MEDIA_TYPE, "multipart/form-data is required")
        }
        val files = hashMapOf<String, String>()
        session.parseBody(files)
        val path = files["image"] ?: return error(ApiStatus.UNPROCESSABLE_ENTITY, "image is required")
        val image = File(path)
        if (!image.isFile || image.length() == 0L) {
            return error(Response.Status.BAD_REQUEST, "image is empty")
        }
        if (image.length() > MAX_IMAGE_BYTES) {
            return error(ApiStatus.PAYLOAD_TOO_LARGE, "image exceeds 20 MiB")
        }

        val bitmap = try {
            BitmapLoader.decode(image)
        } catch (decodeError: Exception) {
            return error(ApiStatus.UNSUPPORTED_MEDIA_TYPE, "image cannot be decoded")
        }
        return try {
            val started = System.nanoTime()
            val output = inferenceLock.withLock {
                val pack = ModelPackManager(context).current()
                    ?: return error(Response.Status.SERVICE_UNAVAILABLE, "model pack is not ready")
                val key = "${pack.directory.absolutePath}:${pack.manifest.versionName}:${pack.manifest.installedAt}"
                if (engine == null || engineKey != key) {
                    engine = RecognitionEngine(pack)
                    engineKey = key
                }
                engine!!.recognize(bitmap, savedRecognitionAccelerators(context), k ?: 1)
            }
            val latencyMs = (System.nanoTime() - started) / 1_000_000.0
            val body = if (k == null) {
                predictionJson(output.matches)
            } else {
                matchJson(output.matches, latencyMs)
            }
            recycle(output)
            json(Response.Status.OK, body)
        } finally {
            bitmap.recycle()
        }
    }

    private fun recycle(output: RecognitionOutput) {
        output.debugImages.disMask.recycle()
        output.debugImages.crop.recycle()
        output.debugImages.whiteBackground.recycle()
    }

    private fun json(status: Response.IStatus, body: JSONObject): Response =
        newFixedLengthResponse(status, "application/json; charset=utf-8", body.toString()).apply {
            addHeader("Cache-Control", "no-store")
        }

    private fun error(status: Response.IStatus, detail: String): Response =
        json(status, JSONObject().put("detail", detail))

    private fun friendlyMessage(error: Throwable): String {
        var current: Throwable? = error
        while (current != null) {
            current.message?.trim()?.takeIf(String::isNotEmpty)?.let { return it }
            current = current.cause
        }
        return error.javaClass.simpleName
    }
}

private enum class ApiStatus(
    private val code: Int,
    private val description: String,
) : NanoHTTPD.Response.IStatus {
    UNPROCESSABLE_ENTITY(422, "Unprocessable Entity"),
    BAD_GATEWAY(502, "Bad Gateway"),
    METHOD_NOT_ALLOWED(405, "Method Not Allowed"),
    PAYLOAD_TOO_LARGE(413, "Payload Too Large"),
    UNSUPPORTED_MEDIA_TYPE(415, "Unsupported Media Type");

    override fun getRequestStatus(): Int = code
    override fun getDescription(): String = "$code $description"
}
