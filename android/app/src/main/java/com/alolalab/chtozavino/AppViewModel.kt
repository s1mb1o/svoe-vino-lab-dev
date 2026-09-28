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
    private val preferences = application.getSharedPreferences("settings", 0)
    private val packManager = ModelPackManager(application)
    private val historyStore = HistoryStore(application)
    private var installedPack: InstalledModelPack? = packManager.current()
    private var engine: RecognitionEngine? = null

    private val mutableState = MutableStateFlow(
        UiState(
            ageAccepted = preferences.getBoolean("age_accepted", false),
            modelPack = installedPack?.info,
            history = historyStore.list(),
        ),
    )
    val state: StateFlow<UiState> = mutableState.asStateFlow()

    fun acceptAge() {
        preferences.edit().putBoolean("age_accepted", true).apply()
        mutableState.update { it.copy(ageAccepted = true) }
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
        if (mutableState.value.isBusy) return
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
                    activeEngine.recognize(bitmap)
                }
            }.onSuccess { output ->
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
}
