import CoreML
import Foundation
import UIKit

final class CoreMLTensorModel {
    private let model: MLModel
    private let inputName: String

    init(resourceName: String, computeMode: ComputeMode, bundle: Bundle = .main) throws {
        guard let url = bundle.url(forResource: resourceName, withExtension: "mlmodelc") else {
            throw AppError.message("Core ML модель \(resourceName) не найдена.")
        }
        let configuration = MLModelConfiguration()
        configuration.computeUnits = computeMode.computeUnits
        model = try MLModel(contentsOf: url, configuration: configuration)
        guard let name = model.modelDescription.inputDescriptionsByName.first(where: {
            $0.value.type == .multiArray
        })?.key else {
            throw AppError.message("Core ML модель \(resourceName) не имеет tensor input.")
        }
        inputName = name
    }

    func predict(_ input: MLMultiArray) throws -> [Float] {
        let outputs = try predictAll(input)
        guard let array = outputs.first else {
            throw AppError.message("Core ML модель не вернула tensor output.")
        }
        return array.values
    }

    func predictAll(_ input: MLMultiArray) throws -> [(shape: [Int], values: [Float])] {
        let provider = try MLDictionaryFeatureProvider(dictionary: [inputName: input])
        let output = try model.prediction(from: provider)
        let arrays = output.featureNames.compactMap { output.featureValue(for: $0)?.multiArrayValue }
        guard !arrays.isEmpty else {
            throw AppError.message("Core ML модель не вернула tensor output.")
        }
        return arrays.map { array in
            (
                shape: array.shape.map(\.intValue),
                values: array.floatValues()
            )
        }
    }
}

private extension MLMultiArray {
    func floatValues() -> [Float] {
        guard dataType == .float32, isContiguous else {
            return (0..<count).map { self[$0].floatValue }
        }
        let values = dataPointer.assumingMemoryBound(to: Float.self)
        return Array(UnsafeBufferPointer(start: values, count: count))
    }

    var isContiguous: Bool {
        var expectedStride = 1
        for index in stride(from: shape.count - 1, through: 0, by: -1) {
            let length = shape[index].intValue
            if length > 1, strides[index].intValue != expectedStride { return false }
            expectedStride *= length
        }
        return true
    }
}

enum TensorImage {
    static func nchw(
        image: UIImage,
        size: Int,
        transform: (Float) -> Float
    ) throws -> MLMultiArray {
        let pixels = try RGBAImage(image: image, width: size, height: size).bytes
        let array = try MLMultiArray(shape: [1, 3, NSNumber(value: size), NSNumber(value: size)], dataType: .float32)
        let values = array.dataPointer.assumingMemoryBound(to: Float.self)
        let plane = size * size
        for index in 0..<plane {
            let pixel = index * 4
            values[index] = transform(Float(pixels[pixel]) / 255)
            values[plane + index] = transform(Float(pixels[pixel + 1]) / 255)
            values[2 * plane + index] = transform(Float(pixels[pixel + 2]) / 255)
        }
        return array
    }

    static func naflexPatches(image: UIImage, gridSide: Int = 22, patchSize: Int = 16) throws -> MLMultiArray {
        let imageSize = gridSide * patchSize
        let pixels = try RGBAImage(image: image, width: imageSize, height: imageSize).bytes
        let patchValues = patchSize * patchSize * 3
        let array = try MLMultiArray(
            shape: [1, NSNumber(value: gridSide * gridSide), NSNumber(value: patchValues)],
            dataType: .float32
        )
        let values = array.dataPointer.assumingMemoryBound(to: Float.self)
        var output = 0
        for patchY in 0..<gridSide {
            for patchX in 0..<gridSide {
                for y in 0..<patchSize {
                    for x in 0..<patchSize {
                        let pixel = (((patchY * patchSize + y) * imageSize) + patchX * patchSize + x) * 4
                        values[output] = Float(pixels[pixel]) / 127.5 - 1
                        values[output + 1] = Float(pixels[pixel + 1]) / 127.5 - 1
                        values[output + 2] = Float(pixels[pixel + 2]) / 127.5 - 1
                        output += 3
                    }
                }
            }
        }
        return array
    }
}

struct RGBAImage {
    let bytes: [UInt8]
    let width: Int
    let height: Int

    init(image: UIImage, width: Int? = nil, height: Int? = nil) throws {
        guard let cgImage = image.cgImage else { throw AppError.message("Не удалось прочитать изображение.") }
        self.width = width ?? cgImage.width
        self.height = height ?? cgImage.height
        var buffer = [UInt8](repeating: 0, count: self.width * self.height * 4)
        guard let context = CGContext(
            data: &buffer,
            width: self.width,
            height: self.height,
            bitsPerComponent: 8,
            bytesPerRow: self.width * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            throw AppError.message("Не удалось подготовить изображение.")
        }
        context.interpolationQuality = .high
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: self.width, height: self.height))
        bytes = buffer
    }

    init(bytes: [UInt8], width: Int, height: Int) {
        self.bytes = bytes
        self.width = width
        self.height = height
    }

    func uiImage() throws -> UIImage {
        let data = Data(bytes)
        guard let provider = CGDataProvider(data: data as CFData),
              let image = CGImage(
                width: width,
                height: height,
                bitsPerComponent: 8,
                bitsPerPixel: 32,
                bytesPerRow: width * 4,
                space: CGColorSpaceCreateDeviceRGB(),
                bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedLast.rawValue),
                provider: provider,
                decode: nil,
                shouldInterpolate: true,
                intent: .defaultIntent
              ) else {
            throw AppError.message("Не удалось создать изображение.")
        }
        return UIImage(cgImage: image)
    }
}

final class DISSegmenter {
    static let size = 1024
    private let model: CoreMLTensorModel

    init(computeMode: ComputeMode) throws {
        model = try CoreMLTensorModel(resourceName: "DIS", computeMode: computeMode)
    }

    func mask(image: UIImage) throws -> SegmentationMask {
        let input = try TensorImage.nchw(image: image, size: Self.size) { $0 - 0.5 }
        var values = try model.predict(input)
        let expected = Self.size * Self.size
        guard values.count == expected else {
            throw AppError.message("DIS вернул некорректную маску.")
        }
        var low = Float.infinity
        var high = -Float.infinity
        for value in values {
            guard value.isFinite else { throw AppError.message("DIS вернул некорректную маску.") }
            low = min(low, value)
            high = max(high, value)
        }
        guard high - low > 0.000001 else { throw AppError.message("DIS вернул некорректную маску.") }
        let range = high - low
        for index in values.indices { values[index] = min(1, max(0, (values[index] - low) / range)) }
        return SegmentationMask(values: values, width: Self.size, height: Self.size)
    }
}

final class ImageEncoder {
    private let id: ImageEncoderID
    private let model: CoreMLTensorModel

    init(id: ImageEncoderID, computeMode: ComputeMode) throws {
        self.id = id
        model = try CoreMLTensorModel(resourceName: id.modelResourceName, computeMode: computeMode)
    }

    func encode(square: UIImage) throws -> [Float] {
        let inputImage: UIImage
        let input: MLMultiArray
        switch id {
        case .siglip2BaseNaFlexP512:
            inputImage = square
            input = try TensorImage.naflexPatches(image: inputImage)
        case .siglip2:
            let square224 = square.resized(to: CGSize(width: 224, height: 224))
            let expanded = square224.resized(to: CGSize(width: 248, height: 248))
            inputImage = try expanded.centerCrop(size: 224)
            input = try TensorImage.nchw(image: inputImage, size: 224) { $0 * 2 - 1 }
        case .mobileclip2S2:
            inputImage = square.resized(to: CGSize(width: 256, height: 256))
            input = try TensorImage.nchw(image: inputImage, size: 256) { $0 }
        }
        let vector = try model.predict(input)
        guard vector.count == id.vectorDimension, vector.allSatisfy(\.isFinite) else {
            throw AppError.message("\(id.title) вернул некорректный вектор.")
        }
        let norm = Float(vector.reduce(0.0) { $0 + Double($1 * $1) }.squareRoot())
        guard norm.isFinite, norm > 0 else { throw AppError.message("\(id.title) вернул пустой вектор.") }
        return vector.map { $0 / norm }
    }
}

enum AcceleratorProbe {
    static func run() throws -> String {
#if targetEnvironment(simulator)
        return "Симулятор: Core ML использует CPU."
#else
        let models: [(String, [NSNumber], Int)] = [
            ("DIS", [1, 3, NSNumber(value: DISSegmenter.size), NSNumber(value: DISSegmenter.size)], DISSegmenter.size * DISSegmenter.size),
            (ImageEncoderID.siglip2BaseNaFlexP512.modelResourceName, [1, 484, 768], ImageEncoderID.siglip2BaseNaFlexP512.vectorDimension),
            (ImageEncoderID.siglip2.modelResourceName, [1, 3, 224, 224], ImageEncoderID.siglip2.vectorDimension),
            (ImageEncoderID.mobileclip2S2.modelResourceName, [1, 3, 256, 256], ImageEncoderID.mobileclip2S2.vectorDimension),
        ]
        for (name, shape, expectedCount) in models {
            let model = try CoreMLTensorModel(resourceName: name, computeMode: .ane)
            let input = try MLMultiArray(shape: shape, dataType: .float32)
            let output = try model.predict(input)
            guard output.count == expectedCount, output.allSatisfy(\.isFinite) else {
                throw AppError.message("\(name) не прошла проверку CPU + ANE.")
            }
        }
        return "DIS и все энкодеры совместимы с режимом CPU + ANE."
#endif
    }
}

extension UIImage {
    func normalizedOrientation() -> UIImage {
        guard imageOrientation != .up else { return self }
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: size, format: format).image { _ in
            draw(in: CGRect(origin: .zero, size: size))
        }
    }

    func limited(longSide: CGFloat) -> UIImage {
        let source = normalizedOrientation()
        let maximum = max(source.size.width, source.size.height)
        guard maximum > longSide else { return source }
        let scale = longSide / maximum
        return source.resized(to: CGSize(width: source.size.width * scale, height: source.size.height * scale))
    }

    func resized(to target: CGSize) -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: target, format: format).image { _ in
            draw(in: CGRect(origin: .zero, size: target))
        }
    }

    func centerCrop(size cropSize: Int) throws -> UIImage {
        guard let cgImage else { throw AppError.message("Не удалось обрезать изображение.") }
        let x = max(0, (cgImage.width - cropSize) / 2)
        let y = max(0, (cgImage.height - cropSize) / 2)
        guard let crop = cgImage.cropping(to: CGRect(x: x, y: y, width: cropSize, height: cropSize)) else {
            throw AppError.message("Не удалось обрезать изображение.")
        }
        return UIImage(cgImage: crop)
    }
}
