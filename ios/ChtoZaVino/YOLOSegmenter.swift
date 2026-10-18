import CoreML
import Foundation
import UIKit

struct SegmentationMask: Sendable {
    let values: [Float]
    let width: Int
    let height: Int
}

struct YOLOBottleDetection: Sendable {
    let centerX: Float
    let centerY: Float
    let width: Float
    let height: Float
    let confidence: Float
    let maskCoefficients: [Float]
}

enum YOLOBottleMask {
    static let inputSize = 640
    static let classCount = 80
    static let bottleClass = 39
    static let coefficientCount = 32
    static let anchorCount = 8_400
    static let detectionFeatureCount = 4 + classCount + coefficientCount
    static let prototypeSize = 160
    static let confidenceThreshold: Float = 0.25

    static func select(
        detections: [Float],
        anchorCount: Int = anchorCount,
        classCount: Int = classCount,
        bottleClass: Int = bottleClass,
        coefficientCount: Int = coefficientCount,
        inputSize: Int = inputSize,
        confidenceThreshold: Float = confidenceThreshold
    ) throws -> YOLOBottleDetection? {
        let featureCount = 4 + classCount + coefficientCount
        guard detections.count == featureCount * anchorCount else {
            throw AppError.message(
                "YOLO26n-seg вернул \(detections.count) detection values вместо \(featureCount * anchorCount)."
            )
        }
        guard (0..<classCount).contains(bottleClass) else {
            throw AppError.message("YOLO26n-seg использует некорректный индекс класса bottle.")
        }

        var selected: YOLOBottleDetection?
        var selectedRank = -Float.infinity
        let classBase = 4 * anchorCount
        let coefficientBase = (4 + classCount) * anchorCount
        for anchor in 0..<anchorCount {
            let bottleConfidence = detections[classBase + bottleClass * anchorCount + anchor]
            guard bottleConfidence.isFinite, bottleConfidence >= confidenceThreshold else { continue }

            var bestClass = 0
            var bestConfidence = -Float.infinity
            for classIndex in 0..<classCount {
                let confidence = detections[classBase + classIndex * anchorCount + anchor]
                if confidence > bestConfidence {
                    bestClass = classIndex
                    bestConfidence = confidence
                }
            }
            guard bestClass == bottleClass else { continue }

            var centerX = detections[anchor]
            var centerY = detections[anchorCount + anchor]
            var width = detections[2 * anchorCount + anchor]
            var height = detections[3 * anchorCount + anchor]
            guard centerX.isFinite, centerY.isFinite, width.isFinite, height.isFinite,
                  width > 0, height > 0 else { continue }
            if max(max(abs(centerX), abs(centerY)), max(abs(width), abs(height))) <= 2 {
                centerX *= Float(inputSize)
                centerY *= Float(inputSize)
                width *= Float(inputSize)
                height *= Float(inputSize)
            }

            let half = Float(inputSize) / 2
            let distance = hypot(centerX - half, centerY - half)
            let centrality = min(1, max(0, 1 - distance / hypot(half, half)))
            let rank = min(Float(inputSize), width) * min(Float(inputSize), height) *
                (0.8 + 0.2 * centrality) * (0.5 + 0.5 * bottleConfidence)
            guard rank > selectedRank else { continue }

            let coefficients = (0..<coefficientCount).map {
                detections[coefficientBase + $0 * anchorCount + anchor]
            }
            selectedRank = rank
            selected = YOLOBottleDetection(
                centerX: centerX,
                centerY: centerY,
                width: width,
                height: height,
                confidence: bottleConfidence,
                maskCoefficients: coefficients
            )
        }
        return selected
    }

    static func build(
        prototypes: [Float],
        detection: YOLOBottleDetection,
        contentLeft: Int,
        contentTop: Int,
        contentRight: Int,
        contentBottom: Int,
        prototypeWidth: Int = prototypeSize,
        prototypeHeight: Int = prototypeSize,
        modelInputSize: Int = inputSize
    ) throws -> SegmentationMask {
        let coefficientCount = detection.maskCoefficients.count
        let planeSize = prototypeWidth * prototypeHeight
        guard prototypes.count == coefficientCount * planeSize else {
            throw AppError.message("YOLO26n-seg вернул маску неизвестного размера.")
        }
        guard contentLeft >= 0, contentLeft < contentRight, contentRight <= prototypeWidth,
              contentTop >= 0, contentTop < contentBottom, contentBottom <= prototypeHeight else {
            throw AppError.message("YOLO26n-seg вернул некорректную область изображения.")
        }

        let scaleX = Float(prototypeWidth) / Float(modelInputSize)
        let scaleY = Float(prototypeHeight) / Float(modelInputSize)
        let boxLeft = min(prototypeWidth, max(0, Int(floor((detection.centerX - detection.width / 2) * scaleX))))
        let boxTop = min(prototypeHeight, max(0, Int(floor((detection.centerY - detection.height / 2) * scaleY))))
        let boxRight = min(prototypeWidth, max(0, Int(ceil((detection.centerX + detection.width / 2) * scaleX))))
        let boxBottom = min(prototypeHeight, max(0, Int(ceil((detection.centerY + detection.height / 2) * scaleY))))
        let outputWidth = contentRight - contentLeft
        let outputHeight = contentBottom - contentTop
        var values = [Float](repeating: 0, count: outputWidth * outputHeight)
        let left = max(boxLeft, contentLeft)
        let top = max(boxTop, contentTop)
        let right = min(boxRight, contentRight)
        let bottom = min(boxBottom, contentBottom)
        guard left < right, top < bottom else { return SegmentationMask(values: values, width: outputWidth, height: outputHeight) }

        for y in top..<bottom {
            for x in left..<right {
                let pixel = y * prototypeWidth + x
                var logit: Float = 0
                for coefficient in 0..<coefficientCount {
                    logit += detection.maskCoefficients[coefficient] * prototypes[coefficient * planeSize + pixel]
                }
                let probability: Float
                if logit >= 0 {
                    probability = 1 / (1 + exp(-logit))
                } else {
                    let exponent = exp(logit)
                    probability = exponent / (1 + exponent)
                }
                values[(y - contentTop) * outputWidth + x - contentLeft] = probability
            }
        }
        return SegmentationMask(values: values, width: outputWidth, height: outputHeight)
    }
}

final class YOLOSegmenter {
    private let model: CoreMLTensorModel

    init() throws {
        model = try CoreMLTensorModel(resourceName: "YOLO26nSeg", computeMode: .cpu)
    }

    func mask(image: UIImage) throws -> SegmentationMask {
        let source = image.normalizedOrientation()
        let scale = min(
            CGFloat(YOLOBottleMask.inputSize) / source.size.width,
            CGFloat(YOLOBottleMask.inputSize) / source.size.height
        )
        let resizedWidth = max(1, Int((source.size.width * scale).rounded()))
        let resizedHeight = max(1, Int((source.size.height * scale).rounded()))
        let padLeft = (YOLOBottleMask.inputSize - resizedWidth) / 2
        let padTop = (YOLOBottleMask.inputSize - resizedHeight) / 2
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let inputImage = UIGraphicsImageRenderer(
            size: CGSize(width: YOLOBottleMask.inputSize, height: YOLOBottleMask.inputSize),
            format: format
        ).image { context in
            UIColor(red: 114 / 255, green: 114 / 255, blue: 114 / 255, alpha: 1).setFill()
            context.fill(CGRect(x: 0, y: 0, width: YOLOBottleMask.inputSize, height: YOLOBottleMask.inputSize))
            source.draw(in: CGRect(x: padLeft, y: padTop, width: resizedWidth, height: resizedHeight))
        }
        let input = try TensorImage.nchw(image: inputImage, size: YOLOBottleMask.inputSize) { $0 }
        let outputs = try model.predictAll(input)
        guard let detectionOutput = outputs.first(where: {
            $0.values.count == YOLOBottleMask.detectionFeatureCount * YOLOBottleMask.anchorCount
        }), let prototypeOutput = outputs.first(where: {
            $0.values.count == YOLOBottleMask.coefficientCount * YOLOBottleMask.prototypeSize * YOLOBottleMask.prototypeSize
        }) else {
            throw AppError.message("YOLO26n-seg вернул неизвестные tensor outputs: \(outputs.map(\.shape)).")
        }
        guard detectionOutput.values.allSatisfy(\.isFinite), prototypeOutput.values.allSatisfy(\.isFinite) else {
            throw AppError.message("YOLO26n-seg вернул нечисловое значение.")
        }
        guard let bottle = try YOLOBottleMask.select(detections: detectionOutput.values) else {
            throw AppError.message("YOLO не нашёл бутылку. Поместите всю бутылку в центр кадра.")
        }
        let prototypeScale = Float(YOLOBottleMask.prototypeSize) / Float(YOLOBottleMask.inputSize)
        let contentLeft = min(
            YOLOBottleMask.prototypeSize - 1,
            max(0, Int(floor(Float(padLeft) * prototypeScale)))
        )
        let contentTop = min(
            YOLOBottleMask.prototypeSize - 1,
            max(0, Int(floor(Float(padTop) * prototypeScale)))
        )
        let contentRight = min(
            YOLOBottleMask.prototypeSize,
            max(contentLeft + 1, Int(ceil(Float(padLeft + resizedWidth) * prototypeScale)))
        )
        let contentBottom = min(
            YOLOBottleMask.prototypeSize,
            max(contentTop + 1, Int(ceil(Float(padTop + resizedHeight) * prototypeScale)))
        )
        return try YOLOBottleMask.build(
            prototypes: prototypeOutput.values,
            detection: bottle,
            contentLeft: contentLeft,
            contentTop: contentTop,
            contentRight: contentRight,
            contentBottom: contentBottom
        )
    }
}
