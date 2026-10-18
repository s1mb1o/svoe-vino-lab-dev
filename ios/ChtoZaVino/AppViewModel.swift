import Foundation
import UIKit

@MainActor
final class AppViewModel: ObservableObject {
    @Published var selectedImage: UIImage?
    @Published var matches: [WineMatch] = []
    @Published var debugImages: DebugImages?
    @Published var isBusy = false
    @Published var progressText: String?
    @Published var technicalText: String?
    @Published var errorText: String?
    @Published var packManifest: ResourcePackManifest?
    @Published var currentTab = 0
    @Published var showsSettings = false
    @Published var showsCamera = false
    @Published var showsScanner = false
    @Published var isAcceleratorProbeRunning = false
    private(set) var forceUnavailableCamera = false

    let preferences: AppPreferences
    let history: HistoryStore
    private let packManager: ResourcePackManager
    private var engine: RecognitionEngine?
    private var debugServer: DebugHTTPServer?

    convenience init() {
        self.init(
            preferences: AppPreferences(),
            history: HistoryStore(),
            packManager: ResourcePackManager()
        )
    }

    init(
        preferences: AppPreferences,
        history: HistoryStore,
        packManager: ResourcePackManager
    ) {
        self.preferences = preferences
        self.history = history
        self.packManager = packManager
#if DEBUG
        let arguments = ProcessInfo.processInfo.arguments
        if arguments.contains("-reset_accessibility_test_state") {
            preferences.ageAccepted = false
        } else if arguments.contains("-accept_age_for_accessibility_test") {
            preferences.ageAccepted = true
        }
        showsSettings = arguments.contains("-show_settings")
        showsScanner = arguments.contains("-show_scanner")
        showsCamera = arguments.contains("-show_camera")
        forceUnavailableCamera = arguments.contains("-force_unavailable_camera_for_accessibility_test")
        currentTab = arguments.contains("-show_history") ? 1 : 0
#endif
        Task { await preparePack() }
    }

    var canRecognize: Bool { selectedImage != nil && engine != nil && !isBusy }

    func engineImageURL(for wine: WineCard) -> URL? {
        engine?.catalogue.imageURL(for: wine)
    }

    func acceptAge() { preferences.ageAccepted = true }

    func selectImage(_ image: UIImage) {
        selectedImage = image.normalizedOrientation()
        matches = []
        debugImages = nil
        technicalText = nil
        errorText = nil
        currentTab = 0
    }

    func recognize() {
        guard let image = selectedImage, let engine, !isBusy else { return }
        let encoder = preferences.encoder
        let segmenter = preferences.segmenter
        let disMode = preferences.disComputeMode
        let encoderMode = preferences.encoderComputeMode
        isBusy = true
        progressText = "Выделяем главный объект с помощью \(segmenter.technicalTitle)…"
        matches = []
        debugImages = nil
        technicalText = nil
        errorText = nil
        Task {
            do {
                let output = try await Task.detached(priority: .userInitiated) {
                    try engine.recognize(
                        image: image,
                        encoderID: encoder,
                        segmenterID: segmenter,
                        disComputeMode: disMode,
                        encoderComputeMode: encoderMode
                    )
                }.value
                matches = output.matches
                debugImages = output.debugImages
                technicalText = "\(output.segmenter.technicalTitle): \(output.segmentationMilliseconds) мс. \(encoder.title): " +
                    "\(output.embeddingMilliseconds) мс. Поиск: \(output.searchMilliseconds) мс."
                if let first = output.matches.first {
                    history.add(
                        source: .image,
                        encoder: output.encoder,
                        match: first,
                        preview: output.debugImages.whiteBackground
                    )
                }
            } catch {
                errorText = "Распознавание не выполнено: \(error.localizedDescription)"
            }
            isBusy = false
            progressText = nil
        }
    }

    func resolveCode(_ raw: String) {
        guard let engine, !isBusy else { return }
        isBusy = true
        progressText = "Ищем код в локальном каталоге…"
        matches = []
        debugImages = nil
        errorText = nil
        let values = engine.findCode(raw)
        if let first = values.first {
            matches = values
            history.add(source: .code, encoder: nil, match: first, preview: nil)
            technicalText = "Результат получен по локальному коду."
            showsScanner = false
        } else {
            errorText = "Код не найден в локальном каталоге."
        }
        isBusy = false
        progressText = nil
    }

    func setDebugServerEnabled(_ enabled: Bool) {
        preferences.debugServerEnabled = enabled
        if enabled {
            startDebugServer()
        } else {
            debugServer?.stop()
            debugServer = nil
        }
    }

    func redetectAccelerators() {
        guard !isAcceleratorProbeRunning else { return }
        isAcceleratorProbeRunning = true
        Task {
            preferences.acceleratorProbeStatus = await Self.acceleratorProbeStatus()
            isAcceleratorProbeRunning = false
        }
    }

    func dismissError() { errorText = nil }

    private func preparePack() async {
        isBusy = true
        progressText = "Готовим встроенный каталог…"
        do {
            let pack = try await Task.detached(priority: .utility) { [packManager] in
                try packManager.installBuiltIn()
            }.value
            packManifest = pack.manifest
            engine = try RecognitionEngine(pack: pack)
            if preferences.debugServerEnabled { startDebugServer() }
            if preferences.acceleratorProbeStatus.isEmpty {
                preferences.acceleratorProbeStatus = await Self.acceleratorProbeStatus()
            }
        } catch {
            errorText = "Не удалось подготовить каталог: \(error.localizedDescription)"
        }
        isBusy = false
        progressText = nil
    }


    private static func acceleratorProbeStatus() async -> String {
        await Task.detached(priority: .utility) {
            do {
                return try AcceleratorProbe.run()
            } catch {
                return "CPU + ANE недоступен: \(error.localizedDescription). Режим «Авто» использует выбор Core ML."
            }
        }.value
    }

    private func startDebugServer() {
        guard debugServer == nil, let engine, let manifest = packManifest else { return }
        do {
            let server = try DebugHTTPServer(
                packVersion: manifest.version,
                wineCount: manifest.wineCount,
                configuration: { [weak self] in
                    guard let self else { return (.dis, .siglip2) }
                    let segmenter = await self.preferences.segmenter
                    let encoder = await self.preferences.encoder
                    return (segmenter, encoder)
                },
                recognition: { [weak self] data, limit in
                    guard let self, let image = UIImage(data: data) else {
                        throw AppError.message("Некорректное изображение.")
                    }
                    let encoder = await self.preferences.encoder
                    let segmenter = await self.preferences.segmenter
                    let dis = await self.preferences.disComputeMode
                    let embedding = await self.preferences.encoderComputeMode
                    return try engine.recognize(
                        image: image,
                        encoderID: encoder,
                        segmenterID: segmenter,
                        disComputeMode: dis,
                        encoderComputeMode: embedding,
                        limit: limit
                    )
                }
            )
            server.start()
            debugServer = server
        } catch {
            preferences.debugServerEnabled = false
            errorText = "HTTP-сервер не запущен: \(error.localizedDescription)"
        }
    }
}
