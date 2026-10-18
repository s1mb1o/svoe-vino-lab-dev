import XCTest

@MainActor
final class AccessibilityUITests: XCTestCase {
    override func setUp() {
        super.setUp()
        continueAfterFailure = false
    }

    func testAgeGateAccessibility() throws {
        let application = XCUIApplication()
        application.launchArguments = [
            "-reset_accessibility_test_state",
            "-UIPreferredContentSizeCategoryName",
            "UICTContentSizeCategoryL",
        ]
        application.launch()

        XCTAssertTrue(application.buttons["age-accept-button"].waitForExistence(timeout: 10))
        try application.performAccessibilityAudit()
    }

    func testRecognitionScreenAccessibilityAtLargestTextSize() throws {
        let application = XCUIApplication()
        application.launchArguments = [
            "-accept_age_for_accessibility_test",
            "-UIPreferredContentSizeCategoryName",
            "UICTContentSizeCategoryAccessibilityExtraExtraExtraLarge",
        ]
        application.launch()

        XCTAssertTrue(application.buttons["recognize-button"].waitForExistence(timeout: 10))
        for identifier in ["Камера-button", "photo-library-button", "Код-button", "recognize-button"] {
            let control = application.buttons[identifier]
            XCTAssertTrue(control.exists, "Missing control: \(identifier)")
            XCTAssertGreaterThanOrEqual(control.frame.width, 44, "Control is too narrow: \(identifier)")
            XCTAssertGreaterThanOrEqual(control.frame.height, 44, "Control is too short: \(identifier)")
        }

        let auditTypes: XCUIAccessibilityAuditType = [
            .contrast,
            .elementDetection,
            .hitRegion,
            .sufficientElementDescription,
            .textClipped,
            .trait,
        ]
        try application.performAccessibilityAudit(for: auditTypes)
    }

    func testSettingsAccessibility() throws {
        let application = XCUIApplication()
        application.launchArguments = [
            "-accept_age_for_accessibility_test",
            "-show_settings",
            "-UIPreferredContentSizeCategoryName",
            "UICTContentSizeCategoryL",
        ]
        application.launch()

        XCTAssertTrue(application.navigationBars["Настройки"].waitForExistence(timeout: 10))
        try application.performAccessibilityAudit()
    }

    func testHistoryAccessibilityAtLargestTextSize() throws {
        let application = XCUIApplication()
        application.launchArguments = [
            "-accept_age_for_accessibility_test",
            "-show_history",
            "-UIPreferredContentSizeCategoryName",
            "UICTContentSizeCategoryAccessibilityExtraExtraExtraLarge",
        ]
        application.launch()

        XCTAssertTrue(application.navigationBars["История"].waitForExistence(timeout: 10))
        try application.performAccessibilityAudit()
    }

    func testCodeScannerAccessibility() throws {
        let application = XCUIApplication()
        application.launchArguments = [
            "-accept_age_for_accessibility_test",
            "-show_scanner",
            "-UIPreferredContentSizeCategoryName",
            "UICTContentSizeCategoryL",
        ]
        application.launch()

        XCTAssertTrue(application.navigationBars["Сканировать код"].waitForExistence(timeout: 10))
        XCTAssertGreaterThanOrEqual(application.textFields["manual-code-field"].frame.height, 44)
        try application.performAccessibilityAudit()
    }

    func testUnavailableCameraAccessibility() throws {
        let application = XCUIApplication()
        application.launchArguments = [
            "-accept_age_for_accessibility_test",
            "-show_camera",
            "-force_unavailable_camera_for_accessibility_test",
            "-UIPreferredContentSizeCategoryName",
            "UICTContentSizeCategoryL",
        ]
        application.launch()

        XCTAssertTrue(application.buttons["Закрыть"].waitForExistence(timeout: 10))
        try application.performAccessibilityAudit()
    }
}
