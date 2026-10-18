import Foundation
import UIKit

struct PreparedImage: @unchecked Sendable {
    let source: UIImage
    let debug: DebugImages
    let modelInput: UIImage
}

enum ImagePipeline {
    static func prepare(
        source original: UIImage,
        segmentationMask: SegmentationMask,
        segmenter: SegmenterID
    ) throws -> PreparedImage {
        let source = original.limited(longSide: 2048)
        let mask = segmentationMask.values
        let maskWidth = segmentationMask.width
        let maskHeight = segmentationMask.height
        guard maskWidth > 0, maskHeight > 0, mask.count == maskWidth * maskHeight else {
            throw AppError.message("Размер маски \(segmenter.technicalTitle) некорректен.")
        }

        var minX = maskWidth
        var minY = maskHeight
        var maxX = -1
        var maxY = -1
        var foreground = 0
        for y in 0..<maskHeight {
            for x in 0..<maskWidth where mask[y * maskWidth + x] >= 0.5 {
                foreground += 1
                minX = min(minX, x)
                minY = min(minY, y)
                maxX = max(maxX, x)
                maxY = max(maxY, y)
            }
        }
        let fraction = Float(foreground) / Float(mask.count)
        guard maxX >= minX, fraction >= 0.005 else {
            throw AppError.message("\(segmenter.technicalTitle) не нашёл главный объект. Поместите бутылку в центр кадра.")
        }
        guard fraction <= 0.995 else {
            throw AppError.message("\(segmenter.technicalTitle) выделил весь кадр. Снимите бутылку на более простом фоне.")
        }

        guard let sourceCG = source.cgImage else { throw AppError.message("Не удалось прочитать изображение.") }
        var left = Int(Float(minX) / Float(maskWidth) * Float(sourceCG.width))
        var top = Int(Float(minY) / Float(maskHeight) * Float(sourceCG.height))
        var right = Int(ceil(Float(maxX + 1) / Float(maskWidth) * Float(sourceCG.width)))
        var bottom = Int(ceil(Float(maxY + 1) / Float(maskHeight) * Float(sourceCG.height)))
        let marginX = Int((Float(right - left) * 0.04).rounded())
        let marginY = Int((Float(bottom - top) * 0.04).rounded())
        left = max(0, left - marginX)
        top = max(0, top - marginY)
        right = min(sourceCG.width, right + marginX)
        bottom = min(sourceCG.height, bottom + marginY)
        guard right > left, bottom > top else {
            throw AppError.message("\(segmenter.technicalTitle) вернул пустую область объекта.")
        }

        let width = right - left
        let height = bottom - top
        guard let cropCG = sourceCG.cropping(to: CGRect(x: left, y: top, width: width, height: height)) else {
            throw AppError.message("Не удалось обрезать объект.")
        }
        let crop = UIImage(cgImage: cropCG)
        let cropPixels = try RGBAImage(image: crop)
        var composite = cropPixels.bytes
        for y in 0..<height {
            let sourceY = top + y
            let maskY = min(maskHeight - 1, sourceY * maskHeight / sourceCG.height)
            for x in 0..<width {
                let sourceX = left + x
                let maskX = min(maskWidth - 1, sourceX * maskWidth / sourceCG.width)
                let alpha = min(1, max(0, mask[maskY * maskWidth + maskX]))
                let offset = (y * width + x) * 4
                for channel in 0..<3 {
                    let value = Float(composite[offset + channel])
                    composite[offset + channel] = UInt8(min(255, max(0, (255 + (value - 255) * alpha).rounded())))
                }
                composite[offset + 3] = 255
            }
        }
        let whiteCrop = try RGBAImage(bytes: composite, width: width, height: height).uiImage()
        let squareSide = max(width, height)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let square = UIGraphicsImageRenderer(
            size: CGSize(width: squareSide, height: squareSide),
            format: format
        ).image { context in
            UIColor.white.setFill()
            context.fill(CGRect(x: 0, y: 0, width: squareSide, height: squareSide))
            whiteCrop.draw(in: CGRect(
                x: (squareSide - width) / 2,
                y: (squareSide - height) / 2,
                width: width,
                height: height
            ))
        }

        let previewWidth: Int
        let previewHeight: Int
        if sourceCG.width >= sourceCG.height {
            previewWidth = 512
            previewHeight = max(1, Int((512 * Double(sourceCG.height) / Double(sourceCG.width)).rounded()))
        } else {
            previewHeight = 512
            previewWidth = max(1, Int((512 * Double(sourceCG.width) / Double(sourceCG.height)).rounded()))
        }
        var maskBytes = [UInt8](repeating: 255, count: previewWidth * previewHeight * 4)
        for y in 0..<previewHeight {
            let maskY = y * maskHeight / previewHeight
            for x in 0..<previewWidth {
                let maskX = x * maskWidth / previewWidth
                let value = UInt8((min(1, max(0, mask[maskY * maskWidth + maskX])) * 255).rounded())
                let offset = (y * previewWidth + x) * 4
                maskBytes[offset] = value
                maskBytes[offset + 1] = value
                maskBytes[offset + 2] = value
            }
        }
        let maskPreview = try RGBAImage(bytes: maskBytes, width: previewWidth, height: previewHeight).uiImage()
        return PreparedImage(
            source: source,
            debug: DebugImages(mask: maskPreview, crop: crop, whiteBackground: square, segmenter: segmenter),
            modelInput: square
        )
    }
}
