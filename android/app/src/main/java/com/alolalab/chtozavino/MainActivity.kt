package com.alolalab.chtozavino

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.FileProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import java.io.File

internal val GALLERY_MIME_TYPES = listOf(
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
)

class MainActivity : ComponentActivity() {
    private val viewModel: AppViewModel by viewModels()
    private var pendingCameraUri: Uri? = null

    private val galleryLauncher = registerForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments(),
    ) { uris ->
        if (uris.isNotEmpty()) viewModel.selectImages(uris)
    }

    private val cameraLauncher = registerForActivityResult(
        ActivityResultContracts.TakePicture(),
    ) { saved ->
        val uri = pendingCameraUri
        if (saved && uri != null) viewModel.selectImage(uri)
        pendingCameraUri = null
    }

    private val codeScanner by lazy {
        val options = GmsBarcodeScannerOptions.Builder()
            .setBarcodeFormats(
                Barcode.FORMAT_EAN_8,
                Barcode.FORMAT_EAN_13,
                Barcode.FORMAT_UPC_A,
                Barcode.FORMAT_UPC_E,
                Barcode.FORMAT_CODE_128,
                Barcode.FORMAT_DATA_MATRIX,
                Barcode.FORMAT_QR_CODE,
            )
            .enableAutoZoom()
            .allowManualInput()
            .build()
        GmsBarcodeScanning.getClient(this, options)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val state = viewModel.state.collectAsStateWithLifecycle().value
            androidx.compose.runtime.DisposableEffect(BuildConfig.DEBUG && state.debugHttpServerEnabled) {
                if (BuildConfig.DEBUG && state.debugHttpServerEnabled) {
                    window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                }
                onDispose { window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
            }
            ChtoZaVinoApp(
                state = state,
                actions = AppActions(
                    acceptAge = viewModel::acceptAge,
                    declineAge = ::finishAffinity,
                    takePhoto = ::takePhoto,
                    chooseImage = {
                        galleryLauncher.launch(GALLERY_MIME_TYPES.toTypedArray())
                    },
                    scanCode = ::scanCode,
                    recognize = viewModel::recognize,
                    removeImage = viewModel::removeImage,
                    clearImages = viewModel::clearImages,
                    openUrl = ::openUrl,
                    clearHistory = viewModel::clearHistory,
                    dismissError = viewModel::dismissError,
                    setSegmenterMode = viewModel::setSegmenterMode,
                    setRecognitionPipeline = viewModel::setRecognitionPipeline,
                    setDisAcceleratorMode = viewModel::setDisAcceleratorMode,
                    setSigLip2AcceleratorMode = viewModel::setSigLip2AcceleratorMode,
                    setDebugHttpServerEnabled = viewModel::setDebugHttpServerEnabled,
                    redetectAccelerators = viewModel::redetectAccelerators,
                ),
            )
        }
    }

    private fun takePhoto() {
        val directory = File(cacheDir, "camera").apply { mkdirs() }
        val file = File(directory, "photo-${System.currentTimeMillis()}.jpg")
        val uri = FileProvider.getUriForFile(this, "$packageName.files", file)
        pendingCameraUri = uri
        cameraLauncher.launch(uri)
    }

    private fun scanCode() {
        viewModel.startCodeScan()
        codeScanner.startScan()
            .addOnSuccessListener { barcode ->
                val value = barcode.rawValue
                if (value.isNullOrBlank()) {
                    viewModel.reportScannerError("Google Code Scanner вернул пустое значение")
                } else {
                    viewModel.resolveCode(value)
                }
            }
            .addOnFailureListener { error ->
                viewModel.reportScannerError(error.message ?: "ошибка Google Play services")
            }
            .addOnCanceledListener(viewModel::reportScannerCanceled)
    }

    private fun openUrl(url: String) {
        runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
    }
}
