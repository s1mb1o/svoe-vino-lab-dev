import PhotosUI
import SwiftUI

struct ContentView: View {
    @ObservedObject var viewModel: AppViewModel
    @State private var declined = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Group {
            if viewModel.preferences.ageAccepted {
                application
            } else {
                AgeGate(declined: $declined, accept: viewModel.acceptAge)
            }
        }
        .transaction { transaction in
            if reduceMotion { transaction.animation = nil }
        }
        .onChange(of: viewModel.progressText) { _, text in
            if let text { AppAccessibility.announce(text) }
        }
        .alert("Ошибка", isPresented: Binding(
            get: { viewModel.errorText != nil },
            set: { if !$0 { viewModel.dismissError() } }
        )) {
            Button("Закрыть", role: .cancel, action: viewModel.dismissError)
        } message: {
            Text(viewModel.errorText ?? "")
        }
        .sheet(isPresented: $viewModel.showsSettings) {
            SettingsView(viewModel: viewModel)
        }
        .sheet(isPresented: $viewModel.showsCamera) {
            CameraPicker(forceUnavailable: viewModel.forceUnavailableCamera) { image in
                viewModel.showsCamera = false
                if let image { viewModel.selectImage(image) }
            }
        }
        .sheet(isPresented: $viewModel.showsScanner) {
            CodeScannerSheet { code in viewModel.resolveCode(code) }
        }
    }

    private var application: some View {
        TabView(selection: $viewModel.currentTab) {
            NavigationStack {
                RecognitionView(viewModel: viewModel)
                    .toolbar { toolbar }
            }
            .tabItem { Label("Распознавание", systemImage: "viewfinder") }
            .tag(0)

            NavigationStack {
                HistoryView(viewModel: viewModel)
                    .toolbar { toolbar }
            }
            .tabItem { Label("История", systemImage: "clock.arrow.circlepath") }
            .tag(1)
        }
    }

    @ToolbarContentBuilder
    private var toolbar: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            Button { viewModel.showsSettings = true } label: {
                Image(systemName: "gearshape")
            }
            .accessibilityLabel("Настройки")
            .accessibilityHint("Открывает настройки моделей и приложения")
            .accessibilityIdentifier("settings-button")
        }
    }
}

private struct AgeGate: View {
    @Binding var declined: Bool
    let accept: () -> Void
    @AccessibilityFocusState private var declinedMessageFocused: Bool

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                Image("ProductLogo")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 120, height: 120)
                    .clipShape(RoundedRectangle(cornerRadius: 24))
                    .accessibilityHidden(true)
                Text("Что за вино?")
                    .font(.largeTitle.bold())
                    .multilineTextAlignment(.center)
                    .accessibilityHeading(.h1)
                Text(declined ? "Доступ к приложению закрыт." : "Подтвердите, что вам уже исполнилось 18 лет.")
                    .multilineTextAlignment(.center)
                    .accessibilityFocused($declinedMessageFocused)
                if !declined {
                    Button("Мне есть 18 лет", action: accept)
                        .buttonStyle(.borderedProminent)
                        .tint(AppAccessibility.actionTint)
                        .controlSize(.large)
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .accessibilityHint("Открывает приложение")
                        .accessibilityIdentifier("age-accept-button")
                    Button("Мне нет 18 лет") { declined = true }
                        .buttonStyle(.plain)
                        .foregroundStyle(AppAccessibility.destructiveTint)
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .accessibilityHint("Закрывает доступ к приложению")
                }
            }
            .frame(maxWidth: 480)
            .padding(32)
            .frame(maxWidth: .infinity)
        }
        .onChange(of: declined) { _, isDeclined in
            guard isDeclined else { return }
            declinedMessageFocused = true
            AppAccessibility.announce("Доступ к приложению закрыт")
        }
    }
}

private struct RecognitionView: View {
    private enum FocusTarget: Hashable {
        case recognizeButton
        case results
    }

    @ObservedObject var viewModel: AppViewModel
    @State private var photoItem: PhotosPickerItem?
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @AccessibilityFocusState private var focusedTarget: FocusTarget?

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 16) {
                Label("Не требует интернета", systemImage: "wifi.slash")
                    .font(.subheadline)
                    .frame(maxWidth: .infinity, alignment: .leading)

                sourceActions
                    .disabled(viewModel.isBusy)

                if let image = viewModel.selectedImage {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 360)
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                        .accessibilityLabel("Выбранная фотография бутылки")
                        .accessibilityHint("Фотография используется для распознавания вина на устройстве")
                } else {
                    AccessibleUnavailableView(
                        title: "Выберите фотографию бутылки",
                        systemImage: "wineglass",
                        description: "Фотография останется на устройстве."
                    )
                    .frame(minHeight: 260)
                }

                Button(action: viewModel.recognize) {
                    Label("Начать распознавание", systemImage: "sparkle.magnifyingglass")
                        .foregroundStyle(
                            viewModel.canRecognize ? Color.white : Color(uiColor: .label)
                        )
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .padding(.horizontal, 16)
                        .background(
                            viewModel.canRecognize
                                ? AppAccessibility.actionTint
                                : Color(uiColor: .secondarySystemBackground),
                            in: RoundedRectangle(cornerRadius: 10)
                        )
                }
                .buttonStyle(HighContrastButtonStyle())
                .controlSize(.large)
                .disabled(!viewModel.canRecognize)
                .accessibilityHint(viewModel.canRecognize
                    ? "Распознаёт выбранную бутылку на устройстве"
                    : "Сначала выберите фотографию и дождитесь подготовки каталога")
                .accessibilityFocused($focusedTarget, equals: .recognizeButton)
                .accessibilityIdentifier("recognize-button")

                if viewModel.isBusy {
                    let progress = viewModel.progressText ?? "Работаем…"
                    ProgressView(progress)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .accessibilityElement(children: .ignore)
                        .accessibilityLabel("Состояние")
                        .accessibilityValue(progress)
                }
                if let text = viewModel.technicalText {
                    Text(text)
                        .font(.caption)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .accessibilityLabel("Техническая информация. \(text)")
                }
                if !viewModel.matches.isEmpty {
                    Text("Результаты")
                        .font(.title2.bold())
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .accessibilityHeading(.h2)
                        .accessibilityValue(AppAccessibility.resultCount(viewModel.matches.count))
                        .accessibilityFocused($focusedTarget, equals: .results)
                        .accessibilityIdentifier("recognition-results-heading")
                }
                ForEach(viewModel.matches) { match in
                    ResultCard(match: match, imageURL: viewModel.engineImageURL(for: match.wine))
                }
                if let debug = viewModel.debugImages {
                    DebugSection(images: debug)
                }
            }
            .padding()
        }
        .navigationTitle("Что за вино?")
        .navigationBarTitleDisplayMode(.inline)
        .onChange(of: viewModel.selectedImage != nil) { _, hasImage in
            guard hasImage else { return }
            focusedTarget = .recognizeButton
        }
        .onChange(of: viewModel.matches.count) { oldCount, newCount in
            guard newCount > 0, newCount != oldCount else { return }
            focusedTarget = .results
        }
    }

    @ViewBuilder
    private var sourceActions: some View {
        if dynamicTypeSize.isAccessibilitySize {
            VStack(spacing: 12) { sourceActionControls }
        } else {
            HStack(spacing: 12) { sourceActionControls }
        }
    }

    @ViewBuilder
    private var sourceActionControls: some View {
        ActionButton(
            title: "Камера",
            icon: "camera",
            hint: "Открывает камеру для фотографии бутылки"
        ) { viewModel.showsCamera = true }
        PhotosPicker(selection: $photoItem, matching: .images) {
            CompactActionLabel(title: "Галерея", icon: "photo.on.rectangle")
        }
        .buttonStyle(.bordered)
        .tint(AppAccessibility.actionTint)
        .accessibilityLabel("Галерея")
        .accessibilityHint("Открывает фототеку для выбора фотографии бутылки")
        .accessibilityIdentifier("photo-library-button")
        ActionButton(
            title: "Код",
            icon: "barcode.viewfinder",
            hint: "Открывает сканер и ручной ввод кода"
        ) { viewModel.showsScanner = true }
        .onChange(of: photoItem) { _, item in
            Task {
                if let data = try? await item?.loadTransferable(type: Data.self),
                   let image = UIImage(data: data) {
                    viewModel.selectImage(image)
                } else if item != nil {
                    AppAccessibility.announce("Не удалось открыть выбранную фотографию")
                }
            }
        }
    }
}

private struct ActionButton: View {
    let title: String
    let icon: String
    let hint: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            CompactActionLabel(title: title, icon: icon)
        }
        .buttonStyle(.bordered)
        .tint(AppAccessibility.actionTint)
        .accessibilityLabel(title)
        .accessibilityHint(hint)
        .accessibilityIdentifier("\(title)-button")
    }
}

private struct CompactActionLabel: View {
    let title: String
    let icon: String

    var body: some View {
        VStack(spacing: 5) {
            Image(systemName: icon)
                .font(.title3)
                .accessibilityHidden(true)
            Text(title)
                .font(.body)
                .multilineTextAlignment(.center)
                .accessibilityHidden(true)
        }
        .frame(maxWidth: .infinity, minHeight: 44)
        .contentShape(Rectangle())
    }
}

private struct ResultCard: View {
    let match: WineMatch
    let imageURL: URL?
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        Group {
            if dynamicTypeSize.isAccessibilitySize {
                VStack(alignment: .leading, spacing: 12) {
                    wineImage
                    details
                }
            } else {
                HStack(spacing: 16) {
                    wineImage
                    details
                    Spacer(minLength: 0)
                }
            }
        }
        .padding()
        .accessibleCardBackground()
        .accessibilityElement(children: .contain)
    }

    @ViewBuilder
    private var wineImage: some View {
        if let imageURL, let image = UIImage(contentsOfFile: imageURL.path) {
            Image(uiImage: image)
                .resizable()
                .scaledToFit()
                .frame(width: 90, height: 130)
                .accessibilityHidden(true)
        }
    }

    private var details: some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(match.wine.name)
                .font(.headline)
                .accessibilityHeading(.h3)
            if let producer = match.wine.producer {
                Text(producer)
            }
            Text(similarityText(match.score))
                .font(.subheadline.bold())
                .accessibilityLabel(similarityText(match.score))
            if let url = URL(string: match.wine.pageURL) {
                Link("Открыть на vino-svoe.ru", destination: url)
                    .tint(AppAccessibility.actionTint)
                    .frame(minHeight: 44, alignment: .leading)
                    .contentShape(Rectangle())
                    .accessibilityHint("Открывает страницу вина в браузере")
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct DebugSection: View {
    let images: DebugImages

    var body: some View {
        DisclosureGroup("Этапы обработки") {
            DebugImage(title: "Маска \(images.segmenter.technicalTitle)", image: images.mask)
            DebugImage(title: "Обрезка", image: images.crop)
            DebugImage(title: "Белый фон", image: images.whiteBackground)
        }
        .padding()
        .accessibleCardBackground()
        .accessibilityHint("Показывает диагностические изображения распознавания")
    }
}

private struct DebugImage: View {
    let title: String
    let image: UIImage

    var body: some View {
        VStack(alignment: .leading) {
            Text(title).font(.caption.bold())
            Image(uiImage: image)
                .resizable()
                .scaledToFit()
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .accessibilityHidden(true)
        }
        .padding(.top, 8)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Диагностическое изображение: \(title)")
    }
}
