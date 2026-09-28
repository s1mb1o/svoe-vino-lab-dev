@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.alolalab.chtozavino

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.io.File
import java.text.DateFormat
import java.util.Date
import java.util.Locale

data class AppActions(
    val acceptAge: () -> Unit,
    val declineAge: () -> Unit,
    val takePhoto: () -> Unit,
    val chooseImage: () -> Unit,
    val scanCode: () -> Unit,
    val installPack: () -> Unit,
    val recognize: () -> Unit,
    val openUrl: (String) -> Unit,
    val clearHistory: () -> Unit,
    val dismissError: () -> Unit,
)

private enum class AppPage { RECOGNITION, HISTORY }

private val LightColors = lightColorScheme(
    primary = androidx.compose.ui.graphics.Color(0xff7c2638),
    onPrimary = androidx.compose.ui.graphics.Color.White,
    primaryContainer = androidx.compose.ui.graphics.Color(0xffffd9df),
    surface = androidx.compose.ui.graphics.Color(0xfffff8f3),
    surfaceVariant = androidx.compose.ui.graphics.Color(0xfff4dde1),
)

private val DarkColors = darkColorScheme(
    primary = androidx.compose.ui.graphics.Color(0xffffb1c0),
    onPrimary = androidx.compose.ui.graphics.Color(0xff4a071b),
    primaryContainer = androidx.compose.ui.graphics.Color(0xff641529),
    surface = androidx.compose.ui.graphics.Color(0xff1c1114),
    surfaceVariant = androidx.compose.ui.graphics.Color(0xff514347),
)

@Composable
fun ChtoZaVinoApp(state: UiState, actions: AppActions) {
    val dark = androidx.compose.foundation.isSystemInDarkTheme()
    MaterialTheme(colorScheme = if (dark) DarkColors else LightColors) {
        var page by remember { mutableStateOf(AppPage.RECOGNITION) }
        Surface(modifier = Modifier.fillMaxSize()) {
            Scaffold(
                topBar = {
                    TopAppBar(
                        title = {
                            Column {
                                Text("Что за вино?", fontWeight = FontWeight.SemiBold)
                                Text(
                                    "Распознавание на устройстве",
                                    style = MaterialTheme.typography.labelSmall,
                                )
                            }
                        },
                    )
                },
                bottomBar = {
                    NavigationBar {
                        NavigationBarItem(
                            selected = page == AppPage.RECOGNITION,
                            onClick = { page = AppPage.RECOGNITION },
                            icon = { Text("◎") },
                            label = { Text("Распознать") },
                        )
                        NavigationBarItem(
                            selected = page == AppPage.HISTORY,
                            onClick = { page = AppPage.HISTORY },
                            icon = { Text("◷") },
                            label = { Text("История") },
                        )
                    }
                },
            ) { padding ->
                when (page) {
                    AppPage.RECOGNITION -> RecognitionPage(
                        state,
                        actions,
                        Modifier.padding(padding),
                    )
                    AppPage.HISTORY -> HistoryPage(
                        state.history,
                        actions,
                        Modifier.padding(padding),
                    )
                }
            }
            if (!state.ageAccepted) {
                AgeGate(actions.acceptAge, actions.declineAge)
            }
        }
    }
}

@Composable
private fun AgeGate(accept: () -> Unit, decline: () -> Unit) {
    AlertDialog(
        onDismissRequest = {},
        title = { Text("Вам уже исполнилось 18 лет?") },
        text = {
            Text(
                "Приложение содержит информацию об алкогольной продукции. " +
                    "Она предназначена только для совершеннолетних пользователей.",
            )
        },
        confirmButton = { Button(onClick = accept) { Text("Мне есть 18 лет") } },
        dismissButton = { TextButton(onClick = decline) { Text("Выйти") } },
    )
}

@Composable
private fun RecognitionPage(state: UiState, actions: AppActions, modifier: Modifier = Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { Spacer(Modifier.height(4.dp)) }
        item { ModelPackCard(state.modelPack, state.isBusy, actions.installPack) }
        if (state.error != null) {
            item { ErrorCard(state.error, actions.dismissError) }
        }
        item {
            Text(
                "Выберите один способ",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Button(
                        onClick = actions.takePhoto,
                        enabled = !state.isBusy,
                        modifier = Modifier.weight(1f),
                    ) { Text("Сфотографировать") }
                    OutlinedButton(
                        onClick = actions.chooseImage,
                        enabled = !state.isBusy,
                        modifier = Modifier.weight(1f),
                    ) { Text("Из галереи") }
                }
                OutlinedButton(
                    onClick = actions.scanCode,
                    enabled = !state.isBusy && state.modelPack != null,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Сканировать штрихкод или QR") }
            }
        }
        if (state.selectedImage != null) {
            item {
                ImageCard("Исходное изображение", state.selectedImage)
            }
            item {
                Button(
                    onClick = actions.recognize,
                    enabled = !state.isBusy && state.modelPack != null,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Начать распознавание") }
            }
        }
        if (state.isBusy) {
            item {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    CircularProgressIndicator(modifier = Modifier.size(28.dp))
                    Text(state.progressText ?: "Выполняется обработка…")
                }
            }
        }
        if (state.scannedCode != null) {
            item {
                Text(
                    "Считанный код: ${state.scannedCode}",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        if (state.matches.isNotEmpty()) {
            item {
                Text(
                    "Результаты",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
            }
            items(state.matches) { match -> ResultCard(match, actions.openUrl) }
        }
        if (state.technicalText != null) {
            item { Text(state.technicalText, style = MaterialTheme.typography.bodySmall) }
        }
        if (state.debugImages != null) {
            item { DebugSection(state.debugImages) }
        }
        item { Spacer(Modifier.height(16.dp)) }
    }
}

@Composable
private fun ModelPackCard(pack: ModelPackInfo?, busy: Boolean, install: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Локальные модели", fontWeight = FontWeight.Bold)
            if (pack == null) {
                Text("Для распознавания установите проверенный пакет моделей и каталога.")
            } else {
                Text("Версия ${pack.version}: ${pack.vectorCount} изображений, ${pack.wineCount} вин.")
            }
            OutlinedButton(onClick = install, enabled = !busy) {
                Text(if (pack == null) "Установить пакет моделей" else "Заменить пакет моделей")
            }
        }
    }
}

@Composable
private fun ErrorCard(message: String, dismiss: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Text(message, color = MaterialTheme.colorScheme.onErrorContainer)
            TextButton(onClick = dismiss, modifier = Modifier.align(Alignment.End)) {
                Text("Закрыть")
            }
        }
    }
}

@Composable
private fun ImageCard(title: String, bitmap: android.graphics.Bitmap) {
    Card {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, fontWeight = FontWeight.SemiBold)
            Image(
                bitmap = bitmap.asImageBitmap(),
                contentDescription = title,
                modifier = Modifier.fillMaxWidth().height(280.dp)
                    .background(androidx.compose.ui.graphics.Color.White, RoundedCornerShape(8.dp)),
                contentScale = ContentScale.Fit,
            )
        }
    }
}

@Composable
private fun ResultCard(match: WineMatch, openUrl: (String) -> Unit) {
    Card {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(match.wine.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            match.wine.producer?.let { Text(it) }
            val details = listOfNotNull(match.wine.category, match.wine.color, match.wine.region)
                .joinToString(" · ")
            if (details.isNotEmpty()) Text(details, style = MaterialTheme.typography.bodySmall)
            Text(
                "Косинус: ${String.format(Locale.forLanguageTag("ru-RU"), "%.3f", match.score)}",
                style = MaterialTheme.typography.labelMedium,
            )
            Button(onClick = { openUrl(match.wine.pageUrl) }) {
                Text("Открыть на «Своё Вино»")
            }
        }
    }
}

@Composable
private fun DebugSection(images: DebugImages) {
    var expanded by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedButton(onClick = { expanded = !expanded }, modifier = Modifier.fillMaxWidth()) {
            Text(if (expanded) "Скрыть этапы обработки" else "Показать этапы обработки")
        }
        if (expanded) {
            ImageCard("После DIS: маска", images.disMask)
            ImageCard("Обрезанное изображение", images.crop)
            ImageCard("Белый фон и квадрат", images.whiteBackground)
        }
    }
}

@Composable
private fun HistoryPage(history: List<HistoryEntry>, actions: AppActions, modifier: Modifier = Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("История", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                if (history.isNotEmpty()) {
                    TextButton(onClick = actions.clearHistory) { Text("Очистить") }
                }
            }
        }
        if (history.isEmpty()) {
            item { Text("Распознанных вин пока нет.") }
        }
        items(history, key = { it.id }) { row ->
            HistoryCard(row, actions.openUrl)
        }
        item { Spacer(Modifier.height(16.dp)) }
    }
}

@Composable
private fun HistoryCard(entry: HistoryEntry, openUrl: (String) -> Unit) {
    val preview = remember(entry.previewPath) {
        entry.previewPath?.takeIf { File(it).isFile }?.let(BitmapFactory::decodeFile)
    }
    val formatter = remember {
        DateFormat.getDateTimeInstance(
            DateFormat.MEDIUM,
            DateFormat.SHORT,
            Locale.forLanguageTag("ru-RU"),
        )
    }
    Card(onClick = { openUrl(entry.pageUrl) }) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (preview != null) {
                Image(
                    bitmap = preview.asImageBitmap(),
                    contentDescription = "Изображение из истории",
                    modifier = Modifier.size(76.dp).background(androidx.compose.ui.graphics.Color.White),
                    contentScale = ContentScale.Fit,
                )
            } else {
                Box(
                    modifier = Modifier.size(76.dp)
                        .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(8.dp)),
                    contentAlignment = Alignment.Center,
                ) { Text(if (entry.source == RecognitionSource.CODE) "▦" else "◎") }
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(entry.wineName, fontWeight = FontWeight.SemiBold)
                Text(formatter.format(Date(entry.timestamp)), style = MaterialTheme.typography.bodySmall)
                Text(
                    if (entry.source == RecognitionSource.CODE) "Штрихкод или QR" else
                        "Фото · ${String.format(Locale.forLanguageTag("ru-RU"), "%.3f", entry.score)}",
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}
