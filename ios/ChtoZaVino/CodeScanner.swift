import SwiftUI
import UIKit
import Vision
import VisionKit

struct CodeScannerSheet: View {
    let completion: (String) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var manualCode = ""
    @AccessibilityFocusState private var codeFieldFocused: Bool

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 18) {
                    if DataScannerViewController.isSupported && DataScannerViewController.isAvailable {
                        Text("Наведите камеру на код. При использовании VoiceOver распознанное значение появится в поле ручного ввода.")
                            .font(.callout)
                            .frame(maxWidth: .infinity, alignment: .leading)
                        LiveCodeScanner(
                            completion: completion,
                            accessibilityDetection: acceptAccessibilityDetection
                        )
                        .frame(minHeight: 280)
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                        .accessibilityIdentifier("live-code-scanner")
                    } else {
                        AccessibleUnavailableView(
                            title: "Сканер недоступен",
                            systemImage: "barcode.viewfinder",
                            description: "Введите код вручную."
                        )
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Ручной ввод")
                            .font(.headline)
                            .accessibilityHeading(.h2)
                        TextField("Введите код", text: $manualCode)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 11)
                            .background(
                                Color(uiColor: .secondarySystemBackground),
                                in: RoundedRectangle(cornerRadius: 8)
                            )
                            .overlay {
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color(uiColor: .separator), lineWidth: 1)
                            }
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .submitLabel(.search)
                            .onSubmit(submitManualCode)
                            .accessibilityLabel("Код")
                            .accessibilityHint("Введите EAN-13, штрихкод или адрес из QR-кода")
                            .accessibilityFocused($codeFieldFocused)
                            .accessibilityIdentifier("manual-code-field")
                        Button(action: submitManualCode) {
                            Text("Найти код")
                                .foregroundStyle(
                                    trimmedCode.isEmpty ? Color(uiColor: .label) : Color.white
                                )
                                .frame(maxWidth: .infinity, minHeight: 44)
                                .padding(.horizontal, 16)
                                .background(
                                    trimmedCode.isEmpty
                                        ? Color(uiColor: .secondarySystemBackground)
                                        : AppAccessibility.actionTint,
                                    in: RoundedRectangle(cornerRadius: 10)
                                )
                        }
                            .buttonStyle(HighContrastButtonStyle())
                            .disabled(trimmedCode.isEmpty)
                            .accessibilityHint("Ищет код во встроенном каталоге")
                            .accessibilityIdentifier("find-code-button")
                    }
                }
                .padding()
            }
            .navigationTitle("Сканировать код")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title3)
                    }
                        .frame(minWidth: 44, minHeight: 44)
                        .accessibilityLabel("Отмена")
                        .accessibilityHint("Закрывает сканер")
                }
            }
        }
    }

    private var trimmedCode: String {
        manualCode.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func submitManualCode() {
        guard !trimmedCode.isEmpty else { return }
        completion(trimmedCode)
    }

    private func acceptAccessibilityDetection(_ value: String) {
        manualCode = value
        codeFieldFocused = true
        AppAccessibility.announce("Код распознан и добавлен в поле ручного ввода: \(value)")
    }
}

private struct LiveCodeScanner: UIViewControllerRepresentable {
    let completion: (String) -> Void
    let accessibilityDetection: (String) -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(completion: completion, accessibilityDetection: accessibilityDetection)
    }

    func makeUIViewController(context: Context) -> DataScannerViewController {
        let controller = DataScannerViewController(
            recognizedDataTypes: [.barcode(symbologies: [.ean8, .ean13, .upce, .code128, .dataMatrix, .qr])],
            qualityLevel: .balanced,
            recognizesMultipleItems: false,
            isHighFrameRateTrackingEnabled: false,
            isPinchToZoomEnabled: true,
            isGuidanceEnabled: true,
            isHighlightingEnabled: true
        )
        controller.delegate = context.coordinator
        try? controller.startScanning()
        return controller
    }

    func updateUIViewController(_ uiViewController: DataScannerViewController, context: Context) {}

    static func dismantleUIViewController(_ uiViewController: DataScannerViewController, coordinator: Coordinator) {
        uiViewController.stopScanning()
    }

    final class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let completion: (String) -> Void
        let accessibilityDetection: (String) -> Void
        private var lastAccessibilityValue: String?

        init(completion: @escaping (String) -> Void, accessibilityDetection: @escaping (String) -> Void) {
            self.completion = completion
            self.accessibilityDetection = accessibilityDetection
        }

        func dataScanner(_ dataScanner: DataScannerViewController, didTapOn item: RecognizedItem) {
            guard let value = barcodeValue(from: item) else { return }
            completion(value)
        }

        func dataScanner(
            _ dataScanner: DataScannerViewController,
            didAdd addedItems: [RecognizedItem],
            allItems: [RecognizedItem]
        ) {
            guard UIAccessibility.isVoiceOverRunning,
                  let value = addedItems.lazy.compactMap(barcodeValue).first,
                  value != lastAccessibilityValue else { return }
            lastAccessibilityValue = value
            accessibilityDetection(value)
        }

        private func barcodeValue(from item: RecognizedItem) -> String? {
            guard case let .barcode(barcode) = item,
                  let value = barcode.payloadStringValue,
                  !value.isEmpty else { return nil }
            return value
        }
    }
}
