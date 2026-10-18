import Foundation
import UIKit
import XCTest
@testable import ChtoZaVino

final class CoreTests: XCTestCase {
    func testGTINNormalizationMatchesAndroid() {
        XCTAssertEqual(CatalogueIndex.normalizeCode("4630037250909"), "gtin:04630037250909")
        XCTAssertEqual(CatalogueIndex.normalizeCode(" 12345678 "), "gtin:00000012345678")
    }

    func testURLNormalizationRemovesFragmentAndDefaultPort() {
        XCTAssertEqual(
            CatalogueIndex.normalizeCode("HTTPS://VINO-SVOE.RU:443/wines/test#label"),
            "url:https://vino-svoe.ru/wines/test"
        )
    }

    func testSimilarityUsesWholePercent() {
        XCTAssertEqual(similarityText(0.909), "Сходство: 91%")
    }

    func testAccessibilityResultCount() {
        XCTAssertEqual(AppAccessibility.resultCount(1), "Результатов: 1")
        XCTAssertEqual(AppAccessibility.resultCount(20), "Результатов: 20")
    }

    func testTensorPixelsKeepTopToBottomOrder() throws {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let image = UIGraphicsImageRenderer(size: CGSize(width: 1, height: 2), format: format).image { context in
            context.cgContext.setFillColor(UIColor.red.cgColor)
            context.cgContext.fill(CGRect(x: 0, y: 0, width: 1, height: 1))
            context.cgContext.setFillColor(UIColor.blue.cgColor)
            context.cgContext.fill(CGRect(x: 0, y: 1, width: 1, height: 1))
        }
        let pixels = try RGBAImage(image: image)
        XCTAssertGreaterThan(pixels.bytes[0], 240)
        XCTAssertLessThan(pixels.bytes[2], 15)
        XCTAssertLessThan(pixels.bytes[4], 15)
        XCTAssertGreaterThan(pixels.bytes[6], 240)
    }

    func testNaFlexPatchOrderIsPixelThenRGB() throws {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let image = UIGraphicsImageRenderer(size: CGSize(width: 1, height: 1), format: format).image { context in
            context.cgContext.setFillColor(red: 1, green: 0.5, blue: 0, alpha: 1)
            context.cgContext.fill(CGRect(x: 0, y: 0, width: 1, height: 1))
        }
        let patches = try TensorImage.naflexPatches(image: image, gridSide: 1, patchSize: 1)
        XCTAssertEqual(patches.shape.map(\.intValue), [1, 1, 3])
        XCTAssertEqual(patches[0].floatValue, 1, accuracy: 0.01)
        XCTAssertEqual(patches[1].floatValue, 0, accuracy: 0.02)
        XCTAssertEqual(patches[2].floatValue, -1, accuracy: 0.01)
    }

    func testNCHWStoresChannelsInSeparatePlanes() throws {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let image = UIGraphicsImageRenderer(size: CGSize(width: 1, height: 1), format: format).image { context in
            context.cgContext.setFillColor(red: 1, green: 0.5, blue: 0, alpha: 1)
            context.cgContext.fill(CGRect(x: 0, y: 0, width: 1, height: 1))
        }
        let tensor = try TensorImage.nchw(image: image, size: 1) { $0 }
        XCTAssertEqual(tensor.shape.map(\.intValue), [1, 3, 1, 1])
        XCTAssertEqual(tensor[0].floatValue, 1, accuracy: 0.01)
        XCTAssertEqual(tensor[1].floatValue, 0.5, accuracy: 0.02)
        XCTAssertEqual(tensor[2].floatValue, 0, accuracy: 0.01)
    }

    func testYOLOSelectsLargestCentralBottleAndReadsCoefficients() throws {
        let anchors = 2
        let classes = 3
        let coefficients = 2
        var values = [Float](repeating: 0, count: (4 + classes + coefficients) * anchors)
        writeYOLODetection(
            target: &values, anchors: anchors, classes: classes, anchor: 0,
            centerX: 50, centerY: 50, width: 80, height: 80, classIndex: 1, confidence: 0.9
        )
        writeYOLODetection(
            target: &values, anchors: anchors, classes: classes, anchor: 1,
            centerX: 50, centerY: 50, width: 20, height: 20, classIndex: 1, confidence: 0.99
        )
        values[(4 + classes) * anchors] = 2
        values[(4 + classes + 1) * anchors] = -1

        let selected = try YOLOBottleMask.select(
            detections: values,
            anchorCount: anchors,
            classCount: classes,
            bottleClass: 1,
            coefficientCount: coefficients,
            inputSize: 100
        )
        XCTAssertEqual(selected?.width, 80)
        XCTAssertEqual(selected?.maskCoefficients, [2, -1])
    }

    func testYOLORejectsBottleWhenAnotherClassWins() throws {
        let anchors = 1
        let classes = 3
        var values = [Float](repeating: 0, count: (4 + classes + 1) * anchors)
        writeYOLODetection(
            target: &values, anchors: anchors, classes: classes, anchor: 0,
            centerX: 50, centerY: 50, width: 40, height: 40, classIndex: 1, confidence: 0.8
        )
        values[4] = 0.9
        XCTAssertNil(try YOLOBottleMask.select(
            detections: values,
            anchorCount: anchors,
            classCount: classes,
            bottleClass: 1,
            coefficientCount: 1,
            inputSize: 100
        ))
    }

    func testYOLOConvertsNormalizedBoxCoordinates() throws {
        let anchors = 1
        let classes = 2
        var values = [Float](repeating: 0, count: (4 + classes + 1) * anchors)
        writeYOLODetection(
            target: &values, anchors: anchors, classes: classes, anchor: 0,
            centerX: 0.5, centerY: 0.5, width: 0.25, height: 0.75,
            classIndex: 1, confidence: 0.8
        )
        let selected = try YOLOBottleMask.select(
            detections: values,
            anchorCount: anchors,
            classCount: classes,
            bottleClass: 1,
            coefficientCount: 1,
            inputSize: 640
        )
        XCTAssertEqual(selected?.centerX, 320)
        XCTAssertEqual(selected?.width, 160)
        XCTAssertEqual(selected?.height, 480)
    }

    func testYOLOBuildsMaskAndRemovesLetterbox() throws {
        let detection = YOLOBottleDetection(
            centerX: 4,
            centerY: 4,
            width: 8,
            height: 8,
            confidence: 0.9,
            maskCoefficients: [2]
        )
        let mask = try YOLOBottleMask.build(
            prototypes: [Float](repeating: 1, count: 16),
            detection: detection,
            contentLeft: 1,
            contentTop: 0,
            contentRight: 3,
            contentBottom: 4,
            prototypeWidth: 4,
            prototypeHeight: 4,
            modelInputSize: 8
        )
        XCTAssertEqual(mask.width, 2)
        XCTAssertEqual(mask.height, 4)
        XCTAssertTrue(mask.values.allSatisfy { $0 > 0.8 })
    }

    private func writeYOLODetection(
        target: inout [Float],
        anchors: Int,
        classes: Int,
        anchor: Int,
        centerX: Float,
        centerY: Float,
        width: Float,
        height: Float,
        classIndex: Int,
        confidence: Float
    ) {
        target[anchor] = centerX
        target[anchors + anchor] = centerY
        target[2 * anchors + anchor] = width
        target[3 * anchors + anchor] = height
        target[(4 + classIndex) * anchors + anchor] = confidence
        for index in 0..<classes where index != classIndex {
            target[(4 + index) * anchors + anchor] = 0.1
        }
    }

#if DEBUG
    func testDebugMatchLimit() throws {
        XCTAssertEqual(try DebugHTTPServer.matchLimit(nil), 20)
        XCTAssertEqual(try DebugHTTPServer.matchLimit("1"), 1)
        XCTAssertThrowsError(try DebugHTTPServer.matchLimit("0"))
        XCTAssertThrowsError(try DebugHTTPServer.matchLimit("text"))
    }
#endif
}
