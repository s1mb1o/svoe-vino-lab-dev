package com.alolalab.chtozavino

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

internal const val MAX_SELECTED_IMAGES = 3

private data class RecognizedShot(
    val originalIndex: Int,
    val output: RecognitionOutput,
)

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val preferences = application.getSharedPreferences(SETTINGS_PREFERENCES, 0)
    private val packManager = ModelPackManager(application)
    private val historyStore = HistoryStore(application)
    private var installedPack: InstalledModelPack? = packManager.current()
    private var engine: RecognitionEngine? = null
    private var acceleratorCheckRunning = false

    private var segmenterMode = SegmenterMode.fromPreference(
        preferences.getString(KEY_SEGMENTER_MODE, null),
    )

    private var disAcceleratorMode = AcceleratorMode.fromPreference(
        preferences.getString(KEY_DIS_ACCELERATOR_MODE, null),
    )
    private var sigLip2AcceleratorMode = AcceleratorMode.fromPreference(
        preferences.getString(KEY_SIGLIP2_ACCELERATOR_MODE, null),
    )
    private var automaticDisAccelerator = ModelAccelerator.fromPreference(
        preferences.getString(KEY_AUTOMATIC_DIS_ACCELERATOR, null),
    )
    private var automaticSigLip2Accelerator = ModelAccelerator.fromPreference(
        preferences.getString(KEY_AUTOMATIC_SIGLIP2_ACCELERATOR, null),
    )
    private val needsInitialAcceleratorCheck =
        preferences.getInt(KEY_ACCELERATOR_CHECK_VERSION, 0) != ACCELERATOR_CHECK_VERSION ||
            automaticDisAccelerator == null || automaticSigLip2Accelerator == null
    private val needsBuiltInPack = installedPack?.hasYolo() != true

    private val mutableState = MutableStateFlow(
        UiState(
            ageAccepted = preferences.getBoolean("age_accepted", false),
            modelPack = installedPack?.info,
            segmenterMode = segmenterMode,
            disAcceleratorMode = disAcceleratorMode,
            sigLip2AcceleratorMode = sigLip2AcceleratorMode,
            automaticDisAccelerator = automaticDisAccelerator,
            automaticSigLip2Accelerator = automaticSigLip2Accelerator,
            isAcceleratorCheckRunning = !needsBuiltInPack && needsInitialAcceleratorCheck,
            debugHttpServerAvailable = BuildConfig.DEBUG,
            debugHttpServerEnabled = BuildConfig.DEBUG && isDebugHttpServerEnabled(application),
            history = historyStore.list(),
            isBusy = needsBuiltInPack || needsInitialAcceleratorCheck,
            progressText = when {
                needsBuiltInPack -> "Готовим встроенный каталог…"
                needsInitialAcceleratorCheck -> "Проверяем совместимость GPU…"
                else -> null
            },
        ),
    )
    val state: StateFlow<UiState> = mutableState.asStateFlow()

    init {
        viewModelScope.launch {
            val pack = installedPack?.takeIf(InstalledModelPack::hasYolo) ?: runCatching {
                withContext(Dispatchers.IO) { packManager.installBuiltIn() }
            }.getOrElse {
                showError("Встроенный каталог не установлен: ${friendlyMessage(it)}.")
                return@launch
            }.also {
                installedPack = it
                replaceEngine(null)
                mutableState.update { state -> state.copy(modelPack = it.info) }
            }
            if (needsInitialAcceleratorCheck) {
                runAcceleratorCheck(pack)
            } else {
                mutableState.update {
                    it.copy(isBusy = false, progressText = null)
                }
            }
        }
    }

    fun acceptAge() {
        preferences.edit().putBoolean("age_accepted", true).apply()
        mutableState.update { it.copy(ageAccepted = true) }
    }

    fun setSegmenterMode(mode: SegmenterMode) {
        segmenterMode = mode
        preferences.edit().putString(KEY_SEGMENTER_MODE, mode.name).apply()
        replaceEngine(null)
        mutableState.update { it.copy(segmenterMode = mode) }
    }

    fun setDisAcceleratorMode(mode: AcceleratorMode) {
        disAcceleratorMode = mode
        preferences.edit().putString(KEY_DIS_ACCELERATOR_MODE, mode.name).apply()
        replaceEngine(null)
        mutableState.update { it.copy(disAcceleratorMode = mode) }
    }

    fun setSigLip2AcceleratorMode(mode: AcceleratorMode) {
        sigLip2AcceleratorMode = mode
        preferences.edit().putString(KEY_SIGLIP2_ACCELERATOR_MODE, mode.name).apply()
        replaceEngine(null)
        mutableState.update { it.copy(sigLip2AcceleratorMode = mode) }
    }

    fun setDebugHttpServerEnabled(enabled: Boolean) {
        if (!BuildConfig.DEBUG) return
        val application = getApplication<Application>()
        val control = application as? DebugHttpServerControl ?: return
        runCatching { control.setDebugHttpServerEnabled(enabled) }
            .onSuccess {
                saveDebugHttpServerEnabled(application, enabled)
                mutableState.update {
                    it.copy(debugHttpServerEnabled = enabled, error = null)
                }
            }
            .onFailure {
                saveDebugHttpServerEnabled(application, false)
                mutableState.update { state ->
                    state.copy(
                        debugHttpServerEnabled = false,
                        error = "HTTP-сервер не запущен: ${friendlyMessage(it)}",
                    )
                }
            }
    }

    fun redetectAccelerators() {
        val pack = installedPack ?: return
        if (acceleratorCheckRunning) return
        viewModelScope.launch { runAcceleratorCheck(pack) }
    }

    fun selectImage(uri: Uri) {
        selectImages(listOf(uri))
    }

    fun selectImages(uris: List<Uri>) {
        val currentState = mutableState.value
        if (currentState.isBusy || uris.isEmpty()) return
        val availableSlots = MAX_SELECTED_IMAGES - currentState.selectedImages.size
        if (availableSlots <= 0) {
            mutableState.update {
                it.copy(error = "Можно выбрать не более трёх фотографий.")
            }
            return
        }
        val acceptedUris = uris.take(availableSlots)
        viewModelScope.launch {
            mutableState.update {
                it.copy(
                    isBusy = true,
                    progressText = if (acceptedUris.size == 1) {
                        "Открываем изображение…"
                    } else {
                        "Открываем изображения…"
                    },
                    error = null,
                    matches = emptyList(),
                    debugImages = null,
                    scannedCode = null,
                )
            }
            runCatching {
                withContext(Dispatchers.IO) {
                    acceptedUris.mapNotNull { uri ->
                        runCatching { BitmapLoader.decode(getApplication(), uri) }.getOrNull()
                    }
                }
            }.onSuccess { bitmaps ->
                if (bitmaps.isEmpty()) {
                    showError("Не удалось открыть выбранные изображения.")
                } else {
                    mutableState.update {
                        it.copy(
                            selectedImages = it.selectedImages + bitmaps,
                            isBusy = false,
                            progressText = null,
                            technicalText = when {
                                uris.size > acceptedUris.size ->
                                    "Можно выбрать не более трёх фотографий. Добавлены первые ${acceptedUris.size}."
                                bitmaps.size < acceptedUris.size ->
                                    "Некоторые изображения не удалось открыть."
                                else -> null
                            },
                        )
                    }
                }
            }.onFailure { showError("Не удалось открыть изображение: ${friendlyMessage(it)}") }
        }
    }

    fun removeImage(index: Int) {
        if (mutableState.value.isBusy) return
        mutableState.update { state ->
            if (index !in state.selectedImages.indices) return@update state
            state.copy(
                selectedImages = state.selectedImages.filterIndexed { itemIndex, _ ->
                    itemIndex != index
                },
                matches = emptyList(),
                debugImages = null,
                technicalText = null,
                scannedCode = null,
                error = null,
            )
        }
    }

    fun clearImages() {
        if (mutableState.value.isBusy) return
        mutableState.update {
            it.copy(
                selectedImages = emptyList(),
                matches = emptyList(),
                debugImages = null,
                technicalText = null,
                scannedCode = null,
                error = null,
            )
        }
    }

    fun installModelPack(uri: Uri) {
        viewModelScope.launch {
            mutableState.update {
                it.copy(
                    isBusy = true,
                    progressText = "Проверяем и устанавливаем пакет моделей…",
                    error = null,
                )
            }
            runCatching { withContext(Dispatchers.IO) { packManager.install(uri) } }
                .onSuccess { pack ->
                    installedPack = pack
                    replaceEngine(null)
                    mutableState.update {
                        it.copy(
                            modelPack = pack.info,
                            isBusy = false,
                            progressText = null,
                            technicalText = "Пакет моделей установлен.",
                        )
                    }
                }
                .onFailure { showError("Не удалось установить пакет: ${friendlyMessage(it)}") }
        }
    }

    fun recognize() {
        val bitmaps = mutableState.value.selectedImages.toList()
        if (bitmaps.isEmpty()) return
        val pack = installedPack ?: run {
            showError("Сначала установите пакет моделей.")
            return
        }
        val currentState = mutableState.value
        if (currentState.isBusy) return
        val accelerators = recognitionAccelerators(
            disMode = currentState.disAcceleratorMode,
            sigLip2Mode = currentState.sigLip2AcceleratorMode,
            automaticDis = currentState.automaticDisAccelerator,
            automaticSigLip2 = currentState.automaticSigLip2Accelerator,
        )
        viewModelScope.launch {
            mutableState.update {
                it.copy(
                    isBusy = true,
                    progressText = "Готовим распознавание…",
                    error = null,
                    matches = emptyList(),
                    debugImages = null,
                    technicalText = null,
                    scannedCode = null,
                )
            }
            val recognizedShots = mutableListOf<RecognizedShot>()
            val failures = mutableListOf<String>()
            try {
                bitmaps.forEachIndexed { index, bitmap ->
                    mutableState.update {
                        it.copy(progressText = "Обрабатываем фото ${index + 1} из ${bitmaps.size}…")
                    }
                    try {
                        val output = withContext(Dispatchers.Default) {
                            val activeEngine = engine ?: RecognitionEngine(pack).also { engine = it }
                            activeEngine.recognize(bitmap, accelerators, currentState.segmenterMode)
                        }
                        recognizedShots += RecognizedShot(index, output)
                    } catch (error: Throwable) {
                        if (error is CancellationException) throw error
                        failures += "Фото ${index + 1}: ${friendlyMessage(error)}"
                    }
                }

                if (recognizedShots.isEmpty()) {
                    val details = failures.firstOrNull()?.let { " $it" }.orEmpty()
                    throw ImageRecognitionException("Ни одно фото не обработано.$details")
                }

                recognizedShots.forEach { saveAutomaticCpuFallbacks(it.output) }
                val merged = mergeMultiShotMatches(recognizedShots.map { it.output.matches })
                val bestShot = recognizedShots[merged.bestShotIndex]
                val history = withContext(Dispatchers.IO) {
                    historyStore.add(
                        RecognitionSource.IMAGE,
                        merged.matches.first(),
                        bestShot.output.debugImages.whiteBackground,
                    )
                }
                recognizedShots.forEachIndexed { index, shot ->
                    if (index != merged.bestShotIndex) recycleDebugImages(shot.output.debugImages)
                }
                mutableState.update {
                    it.copy(
                        matches = merged.matches,
                        debugImages = bestShot.output.debugImages,
                        history = history,
                        isBusy = false,
                        progressText = null,
                        technicalText = buildString {
                            append("Обработано фото: ${recognizedShots.size} из ${bitmaps.size}. ")
                            append("Лучший результат: фото ${bestShot.originalIndex + 1}. ")
                            append("${bestShot.output.segmenterName}: ")
                            append("${recognizedShots.sumOf { shot -> shot.output.segmentationMs }} мс ")
                            append("(${bestShot.output.segmentationAccelerator}). ")
                            append("SigLIP2: ")
                            append("${recognizedShots.sumOf { shot -> shot.output.embeddingMs }} мс ")
                            append("(${bestShot.output.embeddingAccelerator}). ")
                            append("Поиск: ${recognizedShots.sumOf { shot -> shot.output.searchMs }} мс.")
                            if (failures.isNotEmpty()) append(" Не обработано: ${failures.size}.")
                        },
                    )
                }
            } catch (error: Throwable) {
                recognizedShots.forEach { recycleDebugImages(it.output.debugImages) }
                if (error is CancellationException) throw error
                showError("Распознавание не выполнено: ${friendlyMessage(error)}")
            }
        }
    }

    fun resolveCode(raw: String) {
        val pack = installedPack ?: run {
            showError("Сначала установите пакет моделей.")
            return
        }
        if (mutableState.value.isBusy) return
        viewModelScope.launch {
            mutableState.update {
                it.copy(
                    isBusy = true,
                    progressText = "Ищем код в локальном каталоге…",
                    error = null,
                    matches = emptyList(),
                    debugImages = null,
                    technicalText = null,
                    scannedCode = raw,
                )
            }
            runCatching {
                withContext(Dispatchers.Default) {
                    val activeEngine = engine ?: RecognitionEngine(pack).also { engine = it }
                    activeEngine.findCode(raw)
                }
            }.onSuccess { matches ->
                if (matches.isEmpty()) {
                    showError("Код не найден в локальном каталоге.")
                } else {
                    val history = withContext(Dispatchers.IO) {
                        historyStore.add(RecognitionSource.CODE, matches.first(), null)
                    }
                    mutableState.update {
                        it.copy(
                            matches = matches,
                            history = history,
                            isBusy = false,
                            progressText = null,
                            technicalText = "Результат получен по локальному коду.",
                        )
                    }
                }
            }.onFailure { showError("Поиск кода не выполнен: ${friendlyMessage(it)}") }
        }
    }

    fun clearHistory() {
        viewModelScope.launch(Dispatchers.IO) {
            historyStore.clear()
            mutableState.update { it.copy(history = emptyList()) }
        }
    }

    fun dismissError() {
        mutableState.update { it.copy(error = null) }
    }

    fun reportScannerError(message: String) {
        showError("Сканер не запущен: $message")
    }

    fun startCodeScan() {
        mutableState.update {
            it.copy(
                error = null,
                technicalText = "Наведите камеру на EAN-13, штрихкод или QR. " +
                    "Для ручного ввода нажмите значок клавиатуры в сканере.",
                scannedCode = null,
            )
        }
    }

    fun reportScannerCanceled() {
        mutableState.update {
            it.copy(technicalText = "Сканирование отменено.")
        }
    }

    private suspend fun runAcceleratorCheck(pack: InstalledModelPack) {
        if (acceleratorCheckRunning) return
        acceleratorCheckRunning = true
        mutableState.update {
            it.copy(
                isBusy = true,
                isAcceleratorCheckRunning = true,
                progressText = "Проверяем совместимость GPU…",
                error = null,
            )
        }
        runCatching {
            withContext(Dispatchers.Default) { AcceleratorDetector.detect(pack) }
        }.onSuccess { result ->
            automaticDisAccelerator = result.dis
            automaticSigLip2Accelerator = result.sigLip2
            preferences.edit()
                .putInt(KEY_ACCELERATOR_CHECK_VERSION, ACCELERATOR_CHECK_VERSION)
                .putString(KEY_AUTOMATIC_DIS_ACCELERATOR, result.dis.name)
                .putString(KEY_AUTOMATIC_SIGLIP2_ACCELERATOR, result.sigLip2.name)
                .apply()
            mutableState.update {
                it.copy(
                    automaticDisAccelerator = result.dis,
                    automaticSigLip2Accelerator = result.sigLip2,
                    isBusy = false,
                    isAcceleratorCheckRunning = false,
                    progressText = null,
                    technicalText = "Автопроверка: DIS — ${result.dis.name}, " +
                        "SigLIP2 — ${result.sigLip2.name}.",
                )
            }
        }.onFailure {
            mutableState.update { state ->
                state.copy(
                    isBusy = false,
                    isAcceleratorCheckRunning = false,
                    progressText = null,
                    error = "Проверка ускорителей не выполнена: ${friendlyMessage(it)}. " +
                        "Выберите CPU в настройках.",
                )
            }
        }
        acceleratorCheckRunning = false
    }

    private fun saveAutomaticCpuFallbacks(output: RecognitionOutput) {
        var changed = false
        if (
            output.segmenterName == SegmenterMode.DIS.name &&
            disAcceleratorMode == AcceleratorMode.AUTO &&
            automaticDisAccelerator == ModelAccelerator.GPU &&
            output.segmentationAccelerator == ModelAccelerator.CPU.name
        ) {
            automaticDisAccelerator = ModelAccelerator.CPU
            changed = true
        }
        if (
            sigLip2AcceleratorMode == AcceleratorMode.AUTO &&
            automaticSigLip2Accelerator == ModelAccelerator.GPU &&
            output.embeddingAccelerator == ModelAccelerator.CPU.name
        ) {
            automaticSigLip2Accelerator = ModelAccelerator.CPU
            changed = true
        }
        if (!changed) return
        preferences.edit()
            .putString(KEY_AUTOMATIC_DIS_ACCELERATOR, automaticDisAccelerator?.name)
            .putString(KEY_AUTOMATIC_SIGLIP2_ACCELERATOR, automaticSigLip2Accelerator?.name)
            .apply()
        mutableState.update {
            it.copy(
                automaticDisAccelerator = automaticDisAccelerator,
                automaticSigLip2Accelerator = automaticSigLip2Accelerator,
            )
        }
    }

    private fun showError(message: String) {
        mutableState.update {
            it.copy(isBusy = false, progressText = null, error = message)
        }
    }

    private fun recycleDebugImages(images: DebugImages) {
        images.disMask.recycle()
        images.crop.recycle()
        images.whiteBackground.recycle()
    }

    private fun replaceEngine(replacement: RecognitionEngine?) {
        if (engine === replacement) return
        engine?.close()
        engine = replacement
    }

    override fun onCleared() {
        replaceEngine(null)
        super.onCleared()
    }

    private fun friendlyMessage(error: Throwable): String {
        var current: Throwable? = error
        while (current != null) {
            val text = current.message?.trim()
            if (!text.isNullOrEmpty()) return text
            current = current.cause
        }
        return "неизвестная ошибка"
    }

    companion object {
        private const val ACCELERATOR_CHECK_VERSION = 1
        private const val KEY_ACCELERATOR_CHECK_VERSION = "accelerator_check_version"
    }
}
