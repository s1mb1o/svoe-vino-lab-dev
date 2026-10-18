import Foundation
import UIKit

final class RecognitionEngine: @unchecked Sendable {
    let catalogue: CatalogueIndex
    private let inferenceLock = NSLock()
    private var disSegmenters: [ComputeMode: DISSegmenter] = [:]
    private var yoloSegmenter: YOLOSegmenter?
    private var encoders: [String: ImageEncoder] = [:]

    init(pack: InstalledResourcePack) throws {
        catalogue = try CatalogueIndex(pack: pack)
    }

    func findCode(_ raw: String) -> [WineMatch] {
        catalogue.findCode(raw)
    }

    func recognize(
        image: UIImage,
        encoderID: ImageEncoderID,
        segmenterID: SegmenterID,
        disComputeMode: ComputeMode,
        encoderComputeMode: ComputeMode,
        limit: Int = 5
    ) throws -> RecognitionOutput {
        inferenceLock.lock()
        defer { inferenceLock.unlock() }
        guard (1...20).contains(limit) else { throw AppError.message("k должен быть от 1 до 20.") }
        let source = image.limited(longSide: 2048)
        let segmentationStart = ContinuousClock.now
        let mask: SegmentationMask
        switch segmenterID {
        case .dis:
            let segmenter: DISSegmenter
            if let cached = disSegmenters[disComputeMode] {
                segmenter = cached
            } else {
                segmenter = try DISSegmenter(computeMode: disComputeMode)
                disSegmenters[disComputeMode] = segmenter
            }
            mask = try segmenter.mask(image: source)
        case .yolo:
            let segmenter: YOLOSegmenter
            if let cached = yoloSegmenter {
                segmenter = cached
            } else {
                segmenter = try YOLOSegmenter()
                yoloSegmenter = segmenter
            }
            mask = try segmenter.mask(image: source)
        }
        let prepared = try ImagePipeline.prepare(
            source: source,
            segmentationMask: mask,
            segmenter: segmenterID
        )
        let segmentationDuration = segmentationStart.duration(to: .now)

        let encoderStart = ContinuousClock.now
        let encoderKey = "\(encoderID.rawValue):\(encoderComputeMode.rawValue)"
        let encoder: ImageEncoder
        if let cached = encoders[encoderKey] {
            encoder = cached
        } else {
            encoder = try ImageEncoder(id: encoderID, computeMode: encoderComputeMode)
            encoders[encoderKey] = encoder
        }
        let vector = try encoder.encode(square: prepared.modelInput)
        let encoderDuration = encoderStart.duration(to: .now)

        let searchStart = ContinuousClock.now
        let matches = try catalogue.search(vector: vector, encoder: encoderID, limit: limit)
        let searchDuration = searchStart.duration(to: .now)
        guard !matches.isEmpty else { throw AppError.message("В локальном каталоге нет результата.") }
        return RecognitionOutput(
            matches: matches,
            debugImages: prepared.debug,
            segmentationMilliseconds: Self.milliseconds(segmentationDuration),
            embeddingMilliseconds: Self.milliseconds(encoderDuration),
            searchMilliseconds: Self.milliseconds(searchDuration),
            encoder: encoderID,
            segmenter: segmenterID
        )
    }

    private static func milliseconds(_ duration: Duration) -> Int {
        let components = duration.components
        return Int(components.seconds * 1_000 + components.attoseconds / 1_000_000_000_000_000)
    }
}
