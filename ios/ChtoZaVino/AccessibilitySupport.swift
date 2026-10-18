import SwiftUI
import UIKit

enum AppAccessibility {
    static let actionTint = Color(red: 0, green: 0.25, blue: 0.5)
    static let destructiveTint = Color(red: 0.62, green: 0, blue: 0.08)

    @MainActor
    static func announce(_ message: String) {
        guard UIAccessibility.isVoiceOverRunning else { return }
        UIAccessibility.post(notification: .announcement, argument: message)
    }

    static func resultCount(_ count: Int) -> String {
        "Результатов: \(count)"
    }
}

struct AccessibleUnavailableView: View {
    let title: String
    let systemImage: String
    let description: String

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.largeTitle)
                .accessibilityHidden(true)
            Text(title)
                .font(.title3.bold())
                .multilineTextAlignment(.center)
            Text(description)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .accessibilityElement(children: .combine)
    }
}

struct HighContrastButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .opacity(configuration.isPressed ? 0.8 : 1)
    }
}

private struct AccessibleCardBackground: ViewModifier {
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    func body(content: Content) -> some View {
        let style = reduceTransparency
            ? AnyShapeStyle(Color(uiColor: .secondarySystemBackground))
            : AnyShapeStyle(.thinMaterial)
        content.background(style, in: RoundedRectangle(cornerRadius: 16))
    }
}

extension View {
    func accessibleCardBackground() -> some View {
        modifier(AccessibleCardBackground())
    }
}
