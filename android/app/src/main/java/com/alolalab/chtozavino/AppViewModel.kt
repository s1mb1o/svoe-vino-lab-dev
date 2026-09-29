package com.alolalab.chtozavino

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val preferences = application.getSharedPreferences(SETTINGS_PREFERENCES, 0)
    private val packManager = ModelPackManager(application)
    private val historyStore = HistoryStore(application)
    private var installedPack: InstalledModelPack? = packManager.current()
    private var engine: RecognitionEngine? = null
    private var acceleratorCheckRunning = false

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

    private val mutableState = MutableStateFlow(
        UiState(
            ageAccepted = preferences.getBoolean("age_accepted", false),
            modelPack = installedPack?.info,
            disAcceleratorMode = disAcceleratorMode,
            sigLip2AcceleratorMode = sigLip2AcceleratorMode,
            automaticDisAccelerator = automaticDisAccelerator,
            automaticSigLip2Accelerator = automaticSigLip2Accelerator,
            isAcceleratorCheckRunning = installedPack != null && needsInitialAcceleratorCheck,
            debugHttpServerAvailable = BuildConfig.DEBUG,
            debugHttpServerEnabled = BuildConfig.DEBUG && isDebugHttpServerEnabled(application),
            history = historyStore.list(),
            isBusy = installedPack == null || needsInitialAcceleratorCheck,
            progressText = when {
                installedPack == null -> "Готовим встроенный каталог…"
                needsInitialAcceleratorCheck -> "Проверяем совместимость GPU…"
                else -> null
            },
        ),
    )
    val state: StateFlow<UiState> = mutableState.asStateFlow()

    init {
        viewModelScope.launch {
            val pack = installedPack ?: runCatching {
                withContext(Dispatchers.IO) { packManager.installBuiltIn() }
            }.getOrElse {
                showError("Встроенный каталог не установлен: ${friendlyMessage(it)}.")
                return@launch
            }.also {
                installedPack = it
                engine = null
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

    fun setDisAcceleratorMode(mode: AcceleratorMode) {
        disAcceleratorMode = mode
        preferences.edit().putString(KEY_DIS_ACCELERATOR_MODE, mode.name).apply()
        mutableState.update { it.copy(disAcceleratorMode = mode) }
    }

    fun setSigLip2AcceleratorMode(mode: AcceleratorMode) {
        sigLip2AcceleratorMode = mode
        preferences.edit().putString(KEY_SIGLIP2_ACCELERATOR_MODE, mode.name).apply()
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
        viewModelScope.launch {
            mutableState.update {
                it.copy(
                    isBusy = true,
                    progressText = "Открываем изображение…",
                    error = null,
                    matches = emptyList(),
                    debugImages = null,
                    scannedCode = null,
                )
            }
            runCatching { withContext(Dispatchers.IO) { BitmapLoader.decode(getApplication(), uri) } }
                .onSuccess { bitmap ->
                    mutableState.update {
                        it.copy(
                            selectedImage = bitmap,
                            isBusy = false,
                            progressText = null,
                            technicalText = null,
                        )
                    }
                }
                .onFailure { showError("Не удалось открыть изображение: ${friendlyMessage(it)}") }
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
                    engine = null
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
        val bitmap = mutableState.value.selectedImage ?: return
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
                    progressText = "Выделяем главный объект с помощью DIS…",
                    error = null,
                    matches = emptyList(),
                    debugImages = null,
                    technicalText = null,
                    scannedCode = null,
                )
            }
            runCatching {
                withContext(Dispatchers.Default) {
                    val activeEngine = engine ?: RecognitionEngine(pack).also { engine = it }
                    activeEngine.recognize(bitmap, accelerators)
                }
            }.onSuccess { output ->
                saveAutomaticCpuFallbacks(output)
                val history = withContext(Dispatchers.IO) {
                    historyStore.add(
                        RecognitionSource.IMAGE,
                        output.matches.first(),
                        output.debugImages.whiteBackground,
                    )
                }
                mutableState.update {
                    it.copy(
                        matches = output.matches,
                        debugImages = output.debugImages,
                        history = history,
                        isBusy = false,
                        progressText = null,
                        technicalText = buildString {
                            append("DIS: ${output.disMs} мс (${output.disAccelerator}). ")
                            append("SigLIP2: ${output.embeddingMs} мс ")
                            append("(${output.embeddingAccelerator}). ")
                            append("Поиск: ${output.searchMs} мс.")
                        },
                    )
                }
            }.onFailure { showError("Распознавание не выполнено: ${friendlyMessage(it)}") }
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
            disAcceleratorMode == AcceleratorMode.AUTO &&
            automaticDisAccelerator == ModelAccelerator.GPU &&
            output.disAccelerator == ModelAccelerator.CPU.name
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
