import CryptoKit
import Foundation

final class ResourcePackManager {
    static let expectedFormat = "svoe-vino-ios-resource-pack"
    static let expectedVersion = 1
    private static let receiptVersion = 1

    private struct ValidationReceipt: Codable {
        let receiptVersion: Int
        let packVersion: String
        let manifestSHA256: String
    }

    private let fileManager: FileManager
    private let bundle: Bundle

    init(fileManager: FileManager = .default, bundle: Bundle = .main) {
        self.fileManager = fileManager
        self.bundle = bundle
    }

    func current() throws -> InstalledResourcePack? {
        let target = try installedDirectory()
        guard fileManager.fileExists(atPath: target.path) else { return nil }
        let manifest = try readManifest(directory: target)
        if try hasValidReceipt(directory: target, manifest: manifest) {
            try validateManifest(manifest)
            return InstalledResourcePack(directory: target, manifest: manifest)
        }
        let installed = try validate(directory: target)
        try writeReceipt(directory: target, manifest: installed.manifest)
        return installed
    }

    func installBuiltIn() throws -> InstalledResourcePack {
        guard let source = bundle.url(forResource: "BuiltinPack", withExtension: nil) else {
            throw AppError.message("Встроенный каталог не найден.")
        }
        let bundledManifest = try readManifest(directory: source)
        if let installed = try? current(), installed.manifest.version == bundledManifest.version {
            return installed
        }
        let target = try installedDirectory()
        let parent = target.deletingLastPathComponent()
        try fileManager.createDirectory(at: parent, withIntermediateDirectories: true)
        let temporary = parent.appending(path: "resource-pack-install-\(UUID().uuidString)")
        do {
            try fileManager.copyItem(at: source, to: temporary)
            let validated = try validate(directory: temporary)
            if fileManager.fileExists(atPath: target.path) {
                try fileManager.removeItem(at: target)
            }
            try fileManager.moveItem(at: temporary, to: target)
            try writeReceipt(directory: target, manifest: validated.manifest)
            return InstalledResourcePack(directory: target, manifest: validated.manifest)
        } catch {
            try? fileManager.removeItem(at: temporary)
            throw error
        }
    }

    func validate(directory: URL) throws -> InstalledResourcePack {
        let manifest = try readManifest(directory: directory)
        try validateManifest(manifest)
        for (relativePath, record) in manifest.files {
            let file = try safeFile(root: directory, relativePath: relativePath)
            let attributes = try fileManager.attributesOfItem(atPath: file.path)
            let size = (attributes[.size] as? NSNumber)?.int64Value ?? -1
            guard size == record.bytes else {
                throw AppError.message("Размер файла \(relativePath) не совпадает с manifest.json.")
            }
            guard try sha256(file) == record.sha256.lowercased() else {
                throw AppError.message("SHA-256 файла \(relativePath) не совпадает с manifest.json.")
            }
        }
        let wineRows = try String(contentsOf: safeFile(root: directory, relativePath: "wines.jsonl"), encoding: .utf8)
        let decoder = JSONDecoder()
        for line in wineRows.split(whereSeparator: \.isNewline) {
            let wine = try decoder.decode(WineCard.self, from: Data(line.utf8))
            let image = try safeFile(root: directory, relativePath: wine.imagePath)
            guard try sha256(image) == wine.imageSHA256.lowercased() else {
                throw AppError.message("SHA-256 изображения \(wine.wineSlug) не совпадает с каталогом.")
            }
        }
        return InstalledResourcePack(directory: directory, manifest: manifest)
    }

    private func validateManifest(_ manifest: ResourcePackManifest) throws {
        guard manifest.format == Self.expectedFormat, manifest.formatVersion == Self.expectedVersion else {
            throw AppError.message("Формат встроенного каталога не поддерживается.")
        }
        guard manifest.wineCount > 0, manifest.imageCount == manifest.wineCount else {
            throw AppError.message("Число вин и изображений в каталоге не совпадает.")
        }
        for encoder in ImageEncoderID.allCases {
            try validateEncoder(encoder, manifest: manifest)
        }
    }

    private func hasValidReceipt(directory: URL, manifest: ResourcePackManifest) throws -> Bool {
        let url = validationReceiptURL(directory: directory)
        guard let data = try? Data(contentsOf: url),
              let receipt = try? JSONDecoder().decode(ValidationReceipt.self, from: data) else { return false }
        let manifestSHA256 = try sha256(directory.appending(path: "manifest.json"))
        return receipt.receiptVersion == Self.receiptVersion
            && receipt.packVersion == manifest.version
            && receipt.manifestSHA256 == manifestSHA256
    }

    private func writeReceipt(directory: URL, manifest: ResourcePackManifest) throws {
        let receipt = ValidationReceipt(
            receiptVersion: Self.receiptVersion,
            packVersion: manifest.version,
            manifestSHA256: try sha256(directory.appending(path: "manifest.json"))
        )
        let data = try JSONEncoder().encode(receipt)
        try data.write(to: validationReceiptURL(directory: directory), options: .atomic)
    }

    private func validationReceiptURL(directory: URL) -> URL {
        directory.deletingLastPathComponent().appending(path: "resource-pack.validation.json")
    }

    private func readManifest(directory: URL) throws -> ResourcePackManifest {
        let data = try Data(contentsOf: directory.appending(path: "manifest.json"))
        return try JSONDecoder().decode(ResourcePackManifest.self, from: data)
    }

    private func validateEncoder(_ encoder: ImageEncoderID, manifest: ResourcePackManifest) throws {
        guard let index = manifest.encoderIndexes[encoder.rawValue] else {
            throw AppError.message("В каталоге нет индекса \(encoder.title).")
        }
        guard index.vectorDimension == encoder.vectorDimension, index.vectorCount > 0 else {
            throw AppError.message("Индекс \(encoder.title) несовместим с приложением.")
        }
    }

    private func safeFile(root: URL, relativePath: String) throws -> URL {
        guard !relativePath.hasPrefix("/"), !relativePath.split(separator: "/").contains("..") else {
            throw AppError.message("Каталог содержит небезопасный путь.")
        }
        let rootPath = root.standardizedFileURL.path + "/"
        let file = root.appending(path: relativePath).standardizedFileURL
        guard file.path.hasPrefix(rootPath), fileManager.fileExists(atPath: file.path) else {
            throw AppError.message("Файл \(relativePath) отсутствует в каталоге.")
        }
        return file
    }

    private func installedDirectory() throws -> URL {
        let base = try fileManager.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        return base.appending(path: "ChtoZaVino/resource-pack")
    }

    private func sha256(_ url: URL) throws -> String {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        var digest = SHA256()
        while true {
            let data = try handle.read(upToCount: 1_048_576) ?? Data()
            if data.isEmpty { break }
            digest.update(data: data)
        }
        return digest.finalize().map { String(format: "%02x", $0) }.joined()
    }
}
