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

class MainActivity : ComponentActivity() {
    private val viewModel: AppViewModel by viewModels()
    private var pendingCameraUri: Uri? = null

    private val galleryLauncher = registerForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri ->
        if (uri != null) viewModel.selectImage(uri)
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
            ChtoZaVinoApp(
                state = state,
                actions = AppActions(
                    acceptAge = viewModel::acceptAge,
                    declineAge = ::finishAffinity,
                    takePhoto = ::takePhoto,
                    chooseImage = { galleryLauncher.launch(arrayOf("image/jpeg", "image/png", "image/webp")) },
                    scanCode = ::scanCode,
                    recognize = viewModel::recognize,
                    openUrl = ::openUrl,
                    clearHistory = viewModel::clearHistory,
                    dismissError = viewModel::dismissError,
                    setDisAcceleratorMode = viewModel::setDisAcceleratorMode,
                    setSigLip2AcceleratorMode = viewModel::setSigLip2AcceleratorMode,
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
