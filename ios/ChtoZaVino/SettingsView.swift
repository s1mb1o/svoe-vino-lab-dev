import CoreML
import SwiftUI

struct SettingsView: View {
    @ObservedObject var viewModel: AppViewModel
    @ObservedObject private var preferences: AppPreferences
    @Environment(\.dismiss) private var dismiss

    init(viewModel: AppViewModel) {
        self.viewModel = viewModel
        preferences = viewModel.preferences
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    sectionTitle("Сегментация")
                    Picker("Модель", selection: $preferences.segmenter) {
                        ForEach(SegmenterID.allCases) { segmenter in
                            Text(segmenter.title).tag(segmenter)
                        }
                    }
                    .pickerStyle(.menu)
                    .tint(AppAccessibility.actionTint)
                    .foregroundStyle(.primary)
                    .accessibilityHint("Выбирает модель для выделения бутылки")
                    modelStatus(name: "DIS", title: "DIS")
                    modelStatus(name: "YOLO26nSeg", title: "YOLO26n-seg")
                    if preferences.segmenter == .yolo {
                        Text("YOLO26n-seg использует CPU и ищет класс bottle.")
                            .font(.caption)
                    }
                }
                Section {
                    sectionTitle("Энкодер изображения")
                    Picker("Модель", selection: $preferences.encoder) {
                        ForEach(ImageEncoderID.allCases) { encoder in
                            Text(encoder.title).tag(encoder)
                        }
                    }
                    .pickerStyle(.menu)
                    .tint(AppAccessibility.actionTint)
                    .foregroundStyle(.primary)
                    .accessibilityHint("Выбирает модель для сравнения изображения с каталогом")
                    modelStatus(name: "SigLIP2BaseNaFlexP512ImageEncoder", title: "SigLIP2 Base NaFlex p512")
                    modelStatus(name: "SigLIP2ImageEncoder", title: "SigLIP2 Base 224")
                    modelStatus(name: "MobileCLIP2S2ImageEncoder", title: "MobileCLIP2-S2")
                }
                if preferences.segmenter == .dis {
                    Section {
                        sectionTitle("DIS")
                        Picker("Ускоритель", selection: $preferences.disComputeMode) {
                            ForEach(ComputeMode.allCases) { mode in Text(mode.title).tag(mode) }
                        }
                        .pickerStyle(.menu)
                        .tint(AppAccessibility.actionTint)
                        .foregroundStyle(.primary)
                        .accessibilityHint("Выбирает вычислительный модуль для DIS")
                    }
                }
                Section {
                    sectionTitle("Энкодер")
                    Picker("Ускоритель", selection: $preferences.encoderComputeMode) {
                        ForEach(ComputeMode.allCases) { mode in Text(mode.title).tag(mode) }
                    }
                    .pickerStyle(.menu)
                    .tint(AppAccessibility.actionTint)
                    .foregroundStyle(.primary)
                    .accessibilityHint("Выбирает вычислительный модуль для энкодера")
#if targetEnvironment(simulator)
                    Text("Симулятор выполняет Core ML на CPU.")
                        .font(.caption)
#endif
                    let status = preferences.acceleratorProbeStatus.isEmpty
                        ? "Ускоритель ещё не проверен."
                        : preferences.acceleratorProbeStatus
                    Text(status)
                        .font(.caption)
                        .accessibilityLabel("Статус ускорителя")
                        .accessibilityValue(status)
                    Button {
                        viewModel.redetectAccelerators()
                    } label: {
                        if viewModel.isAcceleratorProbeRunning {
                            HStack {
                                ProgressView().accessibilityHidden(true)
                                Text("Проверяем…")
                            }
                        } else {
                            Text("Проверить ускоритель снова")
                        }
                    }
                    .frame(minHeight: 44)
                    .disabled(viewModel.isAcceleratorProbeRunning)
                    .accessibilityLabel(viewModel.isAcceleratorProbeRunning
                        ? "Проверка ускорителя выполняется"
                        : "Проверить ускоритель снова")
                    .accessibilityHint("Проверяет совместимость моделей с CPU и Neural Engine")
                }
                Section {
                    sectionTitle("Встроенный каталог")
                    primaryLabeledContent("Версия", value: viewModel.packManifest?.version ?? "Готовим…")
                    primaryLabeledContent("Вина", value: "\(viewModel.packManifest?.wineCount ?? 0)")
                    primaryLabeledContent("Изображения", value: "\(viewModel.packManifest?.imageCount ?? 0)")
                }
#if DEBUG
                Section {
                    sectionTitle("Отладка")
                    Toggle("HTTP-сервер для тестов", isOn: Binding(
                        get: { preferences.debugServerEnabled },
                        set: viewModel.setDebugServerEnabled
                    ))
                    Text("Порт 18088. Сервер обрабатывает запросы последовательно.")
                        .font(.caption)
                }
#endif
                Section {
                    sectionTitle("Приложение")
                    primaryLabeledContent("Версия", value: appVersion)
                    Link("Сайт «Что за вино?»", destination: URL(string: "https://vino-svoe.ru")!)
                        .tint(AppAccessibility.actionTint)
                        .frame(minHeight: 44)
                        .accessibilityHint("Открывает сайт в браузере")
                }
            }
            .accessibilityIdentifier("settings-form")
            .navigationTitle("Настройки")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title3)
                    }
                        .frame(minWidth: 44, minHeight: 44)
                        .accessibilityLabel("Готово")
                        .accessibilityHint("Закрывает настройки")
                }
            }
            .onChange(of: viewModel.isAcceleratorProbeRunning) { wasRunning, isRunning in
                if isRunning {
                    AppAccessibility.announce("Проверка ускорителя началась")
                } else if wasRunning {
                    AppAccessibility.announce("Проверка ускорителя завершена. \(statusText)")
                }
            }
        }
    }

    private func modelStatus(name: String, title: String) -> some View {
        let available = Bundle.main.url(forResource: name, withExtension: "mlmodelc") != nil
        return LabeledContent(title) {
            Label(
                available ? "Готова" : "Нет модели",
                systemImage: available ? "checkmark.circle.fill" : "exclamationmark.triangle.fill"
            )
            .foregroundStyle(.primary)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title). \(available ? "Готова" : "Нет модели")")
    }

    private func sectionTitle(_ title: String) -> some View {
        Text(title)
            .font(.headline)
            .foregroundStyle(.primary)
            .accessibilityHeading(.h2)
    }

    private func primaryLabeledContent(_ title: String, value: String) -> some View {
        LabeledContent(title) {
            Text(value).foregroundStyle(.primary)
        }
    }

    private var statusText: String {
        preferences.acceleratorProbeStatus.isEmpty
            ? "Статус недоступен"
            : preferences.acceleratorProbeStatus
    }

    private var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—"
    }
}
