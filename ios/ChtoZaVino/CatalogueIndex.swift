import Accelerate
import Foundation

private struct CandidateRow: Decodable {
    let vectorRow: Int
    let wineSlug: String
    let view: String

    enum CodingKeys: String, CodingKey {
        case vectorRow = "vector_row"
        case wineSlug = "wine_slug"
        case view
    }
}

private struct CodeRow: Decodable {
    let value: String
    let wineSlug: String

    enum CodingKeys: String, CodingKey {
        case value
        case wineSlug = "wine_slug"
    }
}

private struct CandidateRef: Sendable {
    let row: Int
    let slug: String
}

private struct EncoderIndex: Sendable {
    let vectors: [Float]
    let candidates: [CandidateRef]
    let vectorDimension: Int
}

final class CatalogueIndex: @unchecked Sendable {
    let pack: InstalledResourcePack
    let wines: [String: WineCard]
    private let codes: [String: Set<String>]
    private var indexes: [ImageEncoderID: EncoderIndex] = [:]
    private let lock = NSLock()

    init(pack: InstalledResourcePack) throws {
        self.pack = pack
        let wineRows: [WineCard] = try Self.readJSONLines(pack.file("wines.jsonl"))
        let mapped = Dictionary(uniqueKeysWithValues: wineRows.map { ($0.wineSlug, $0) })
        guard mapped.count == pack.manifest.wineCount else {
            throw AppError.message("Число вин в wines.jsonl не совпадает с manifest.json.")
        }
        for wine in wineRows {
            guard wine.pageURL.hasPrefix("https://vino-svoe.ru/wines/") else {
                throw AppError.message("Некорректная ссылка вина \(wine.wineSlug).")
            }
        }
        wines = mapped

        let codeRows: [CodeRow] = try Self.readJSONLines(pack.file("codes.jsonl"))
        var codeMap: [String: Set<String>] = [:]
        for row in codeRows where mapped[row.wineSlug] != nil {
            codeMap[Self.normalizeCode(row.value), default: []].insert(row.wineSlug)
        }
        codes = codeMap
    }

    func imageURL(for wine: WineCard) -> URL {
        pack.file(wine.imagePath)
    }

    func findCode(_ raw: String) -> [WineMatch] {
        codes[Self.normalizeCode(raw), default: []]
            .compactMap { wines[$0] }
            .sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
            .map { WineMatch(wine: $0, score: 1) }
    }

    func search(vector: [Float], encoder: ImageEncoderID, limit: Int = 5) throws -> [WineMatch] {
        guard (1...20).contains(limit), vector.count == encoder.vectorDimension else {
            throw AppError.message("Размер вектора \(encoder.title) не совпадает с индексом.")
        }
        let normalized = try Self.normalized(vector)
        let index = try loadIndex(encoder)
        let rowCount = index.vectors.count / index.vectorDimension
        var scores = [Float](repeating: 0, count: rowCount)
        normalized.withUnsafeBufferPointer { query in
            index.vectors.withUnsafeBufferPointer { matrix in
                scores.withUnsafeMutableBufferPointer { output in
                    vDSP_mmul(
                        matrix.baseAddress!,
                        1,
                        query.baseAddress!,
                        1,
                        output.baseAddress!,
                        1,
                        vDSP_Length(rowCount),
                        1,
                        vDSP_Length(index.vectorDimension)
                    )
                }
            }
        }
        var best: [String: Float] = [:]
        for candidate in index.candidates {
            let score = scores[candidate.row]
            if score > best[candidate.slug, default: -.infinity] {
                best[candidate.slug] = score
            }
        }
        return best.sorted { left, right in
            left.value == right.value ? left.key < right.key : left.value > right.value
        }.prefix(limit).compactMap { slug, score in
            wines[slug].map { WineMatch(wine: $0, score: score) }
        }
    }

    static func normalizeCode(_ raw: String) -> String {
        let text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.isEmpty, text.allSatisfy(\.isNumber) {
            switch text.count {
            case 8, 12, 13, 14: return "gtin:" + String(repeating: "0", count: 14 - text.count) + text
            default: return "raw:" + text
            }
        }
        if var components = URLComponents(string: text),
           let scheme = components.scheme?.lowercased(),
           let host = components.host?.lowercased(),
           ["http", "https"].contains(scheme) {
            components.scheme = scheme
            components.host = host
            components.fragment = nil
            if components.path.isEmpty { components.path = "/" }
            if (scheme == "http" && components.port == 80) || (scheme == "https" && components.port == 443) {
                components.port = nil
            }
            if let url = components.string { return "url:" + url }
        }
        return "raw:" + text
    }

    private func loadIndex(_ encoder: ImageEncoderID) throws -> EncoderIndex {
        lock.lock()
        defer { lock.unlock() }
        if let existing = indexes[encoder] { return existing }
        guard let manifest = pack.manifest.encoderIndexes[encoder.rawValue] else {
            throw AppError.message("Индекс \(encoder.title) отсутствует.")
        }
        let data = try Data(contentsOf: pack.file(manifest.vectorsPath), options: .mappedIfSafe)
        let expectedBytes = manifest.vectorCount * manifest.vectorDimension * MemoryLayout<Float>.size
        guard data.count == expectedBytes else {
            throw AppError.message("Размер vectors.f32 для \(encoder.title) некорректен.")
        }
        var vectors = [Float](repeating: 0, count: expectedBytes / 4)
        _ = vectors.withUnsafeMutableBytes { destination in data.copyBytes(to: destination) }
        guard vectors.allSatisfy(\.isFinite) else {
            throw AppError.message("Индекс \(encoder.title) содержит нечисловое значение.")
        }
        let rows: [CandidateRow] = try Self.readJSONLines(pack.file(manifest.candidatesPath))
        let candidates = try rows.filter { $0.view == "full" }.map { row -> CandidateRef in
            guard (0..<manifest.vectorCount).contains(row.vectorRow), wines[row.wineSlug] != nil else {
                throw AppError.message("Некорректная строка candidates.jsonl для \(encoder.title).")
            }
            return CandidateRef(row: row.vectorRow, slug: row.wineSlug)
        }
        guard !candidates.isEmpty else {
            throw AppError.message("Индекс \(encoder.title) не содержит векторов full.")
        }
        let loaded = EncoderIndex(vectors: vectors, candidates: candidates, vectorDimension: manifest.vectorDimension)
        indexes[encoder] = loaded
        return loaded
    }

    private static func normalized(_ vector: [Float]) throws -> [Float] {
        let sum = vector.reduce(0.0) { $0 + Double($1 * $1) }
        let norm = Float(sum.squareRoot())
        guard norm.isFinite, norm > 0 else {
            throw AppError.message("Энкодер вернул пустой вектор.")
        }
        return vector.map { $0 / norm }
    }

    private static func readJSONLines<T: Decodable>(_ url: URL) throws -> [T] {
        let text = try String(contentsOf: url, encoding: .utf8)
        let decoder = JSONDecoder()
        return try text.split(whereSeparator: \.isNewline).map { line in
            try decoder.decode(T.self, from: Data(line.utf8))
        }
    }
}
