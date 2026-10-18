import Foundation
import UIKit

@MainActor
final class HistoryStore: ObservableObject {
    @Published private(set) var entries: [HistoryEntry] = []
    private let fileManager: FileManager
    private let root: URL
    private let file: URL

    init(fileManager: FileManager = .default) {
        self.fileManager = fileManager
        let base = (try? fileManager.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )) ?? fileManager.temporaryDirectory
        root = base.appending(path: "ChtoZaVino/history")
        file = root.appending(path: "history.json")
        try? fileManager.createDirectory(at: root, withIntermediateDirectories: true)
        entries = Self.read(file: file)
    }

    func add(source: RecognitionSource, encoder: ImageEncoderID?, match: WineMatch, preview: UIImage?) {
        let id = UUID()
        var previewName: String?
        if let preview, let data = preview.jpegData(compressionQuality: 0.82) {
            let name = id.uuidString + ".jpg"
            try? data.write(to: root.appending(path: name), options: .atomic)
            previewName = name
        }
        entries.insert(HistoryEntry(
            id: id,
            createdAt: Date(),
            source: source,
            encoder: encoder,
            wine: match.wine,
            score: match.score,
            previewFileName: previewName
        ), at: 0)
        if entries.count > 50 {
            for old in entries.dropFirst(50) {
                if let name = old.previewFileName { try? fileManager.removeItem(at: root.appending(path: name)) }
            }
            entries = Array(entries.prefix(50))
        }
        save()
    }

    func previewURL(for entry: HistoryEntry) -> URL? {
        entry.previewFileName.map { root.appending(path: $0) }
    }

    func clear() {
        for entry in entries {
            if let name = entry.previewFileName { try? fileManager.removeItem(at: root.appending(path: name)) }
        }
        entries = []
        save()
    }

    private func save() {
        guard let data = try? JSONEncoder().encode(entries) else { return }
        try? data.write(to: file, options: .atomic)
    }

    private static func read(file: URL) -> [HistoryEntry] {
        guard let data = try? Data(contentsOf: file),
              let values = try? JSONDecoder().decode([HistoryEntry].self, from: data) else { return [] }
        return Array(values.prefix(50))
    }
}
