import CoreML
import Foundation
import UIKit

enum SegmenterID: String, Codable, CaseIterable, Identifiable, Sendable {
    case dis
    case yolo

    var id: String { rawValue }

    var title: String {
        switch self {
        case .dis: "DIS"
        case .yolo: "YOLO"
        }
    }

    var technicalTitle: String {
        switch self {
        case .dis: "DIS"
        case .yolo: "YOLO26n-seg"
        }
    }
}

enum ImageEncoderID: String, Codable, CaseIterable, Identifiable, Sendable {
    case siglip2BaseNaFlexP512 = "siglip2-base-naflex-p512"
    case siglip2
    case mobileclip2S2 = "mobileclip2-s2"

    var id: String { rawValue }

    var title: String {
        switch self {
        case .siglip2BaseNaFlexP512: "SigLIP2 Base NaFlex p512"
        case .siglip2: "SigLIP2 Base 224"
        case .mobileclip2S2: "MobileCLIP2-S2"
        }
    }

    var vectorDimension: Int {
        switch self {
        case .siglip2BaseNaFlexP512: 768
        case .siglip2: 768
        case .mobileclip2S2: 512
        }
    }

    var inputSize: Int {
        switch self {
        case .siglip2BaseNaFlexP512: 352
        case .siglip2: 224
        case .mobileclip2S2: 256
        }
    }

    var modelResourceName: String {
        switch self {
        case .siglip2BaseNaFlexP512: "SigLIP2BaseNaFlexP512ImageEncoder"
        case .siglip2: "SigLIP2ImageEncoder"
        case .mobileclip2S2: "MobileCLIP2S2ImageEncoder"
        }
    }
}

enum ComputeMode: String, Codable, CaseIterable, Identifiable, Sendable {
    case automatic
    case ane
    case cpu

    var id: String { rawValue }

    var title: String {
        switch self {
        case .automatic: "Авто"
        case .ane: "ANE"
        case .cpu: "CPU"
        }
    }

    var computeUnits: MLComputeUnits {
#if targetEnvironment(simulator)
        return .cpuOnly
#else
        switch self {
        case .automatic: .all
        case .ane: .cpuAndNeuralEngine
        case .cpu: .cpuOnly
        }
#endif
    }
}

struct WineCard: Codable, Identifiable, Hashable, Sendable {
    let wineSlug: String
    let name: String
    let pageURL: String
    let producer: String?
    let category: String?
    let region: String?
    let color: String?
    let grapes: String?
    let imagePath: String
    let imageSHA256: String

    var id: String { wineSlug }

    enum CodingKeys: String, CodingKey {
        case wineSlug = "wine_slug"
        case name
        case pageURL = "page_url"
        case producer
        case category
        case region
        case color
        case grapes
        case imagePath = "image_path"
        case imageSHA256 = "image_sha256"
    }
}

struct WineMatch: Identifiable, Hashable, Sendable {
    let wine: WineCard
    let score: Float

    var id: String { wine.wineSlug }
}

struct DebugImages: @unchecked Sendable {
    let mask: UIImage
    let crop: UIImage
    let whiteBackground: UIImage
    let segmenter: SegmenterID
}

struct RecognitionOutput: @unchecked Sendable {
    let matches: [WineMatch]
    let debugImages: DebugImages
    let segmentationMilliseconds: Int
    let embeddingMilliseconds: Int
    let searchMilliseconds: Int
    let encoder: ImageEncoderID
    let segmenter: SegmenterID
}

enum RecognitionSource: String, Codable, Sendable {
    case image = "Фото"
    case code = "Код"
}

struct HistoryEntry: Codable, Identifiable, Sendable {
    let id: UUID
    let createdAt: Date
    let source: RecognitionSource
    let encoder: ImageEncoderID?
    let wine: WineCard
    let score: Float
    let previewFileName: String?
}

struct PackFileRecord: Codable, Sendable {
    let bytes: Int64
    let sha256: String
}

struct EncoderIndexManifest: Codable, Sendable {
    let model: String
    let pipeline: String
    let vectorDimension: Int
    let vectorCount: Int
    let vectorsPath: String
    let candidatesPath: String

    enum CodingKeys: String, CodingKey {
        case model
        case pipeline
        case vectorDimension = "vector_dimension"
        case vectorCount = "vector_count"
        case vectorsPath = "vectors_path"
        case candidatesPath = "candidates_path"
    }
}

struct ResourcePackManifest: Codable, Sendable {
    let format: String
    let formatVersion: Int
    let version: String
    let wineCount: Int
    let imageCount: Int
    let files: [String: PackFileRecord]
    let encoderIndexes: [String: EncoderIndexManifest]

    enum CodingKeys: String, CodingKey {
        case format
        case formatVersion = "format_version"
        case version
        case wineCount = "wine_count"
        case imageCount = "image_count"
        case files
        case encoderIndexes = "encoder_indexes"
    }
}

struct InstalledResourcePack: Sendable {
    let directory: URL
    let manifest: ResourcePackManifest

    func file(_ relativePath: String) -> URL {
        directory.appending(path: relativePath)
    }
}

enum AppError: LocalizedError {
    case message(String)

    var errorDescription: String? {
        switch self {
        case let .message(text): text
        }
    }
}

func similarityText(_ score: Float) -> String {
    "Сходство: \(Int((score * 100).rounded()))%"
}
