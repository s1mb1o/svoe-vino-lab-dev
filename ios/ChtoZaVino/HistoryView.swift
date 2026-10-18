import SwiftUI

struct HistoryView: View {
    @ObservedObject var viewModel: AppViewModel
    @ObservedObject private var history: HistoryStore

    init(viewModel: AppViewModel) {
        self.viewModel = viewModel
        history = viewModel.history
    }

    var body: some View {
        Group {
            if history.entries.isEmpty {
                AccessibleUnavailableView(
                    title: "История пока пуста",
                    systemImage: "clock.arrow.circlepath",
                    description: "Здесь появятся результаты распознавания."
                )
            } else {
                List {
                    ForEach(history.entries) { entry in
                        HistoryRow(entry: entry, previewURL: history.previewURL(for: entry))
                    }
                    Section {
                        Button("Очистить историю", action: history.clear)
                            .buttonStyle(.plain)
                            .foregroundStyle(AppAccessibility.destructiveTint)
                            .frame(minHeight: 44)
                            .accessibilityHint("Безвозвратно удаляет локальную историю распознавания")
                    }
                }
                .accessibilityIdentifier("history-list")
            }
        }
        .navigationTitle("История")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct HistoryRow: View {
    let entry: HistoryEntry
    let previewURL: URL?
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        Group {
            if dynamicTypeSize.isAccessibilitySize {
                VStack(alignment: .leading, spacing: 10) {
                    preview
                    details
                    resultLink
                }
            } else {
                HStack(spacing: 14) {
                    preview
                    details
                    Spacer(minLength: 0)
                    resultLink
                }
            }
        }
        .accessibilityElement(children: .contain)
    }

    @ViewBuilder
    private var preview: some View {
        if let previewURL, let image = UIImage(contentsOfFile: previewURL.path) {
            Image(uiImage: image)
                .resizable()
                .scaledToFill()
                .frame(width: 64, height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .accessibilityHidden(true)
        }
    }

    private var details: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(entry.wine.name)
                .font(.headline)
                .accessibilityHeading(.h3)
            Text(historySubtitle)
                .font(.caption)
            Text(entry.createdAt, format: .dateTime.day().month().year().hour().minute())
                .font(.caption2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private var resultLink: some View {
        if let url = URL(string: entry.wine.pageURL) {
            Link(destination: url) {
                if dynamicTypeSize.isAccessibilitySize {
                    Label("Открыть на сайте", systemImage: "arrow.up.right.square")
                        .labelStyle(.titleAndIcon)
                        .frame(minHeight: 44)
                } else {
                    Label("Открыть на сайте", systemImage: "arrow.up.right.square")
                        .labelStyle(.iconOnly)
                        .frame(minWidth: 44, minHeight: 44)
                }
            }
            .tint(AppAccessibility.actionTint)
            .contentShape(Rectangle())
            .accessibilityLabel("Открыть \(entry.wine.name) на сайте")
            .accessibilityHint("Открывает страницу вина в браузере")
        }
    }

    private var historySubtitle: String {
        let source = entry.source.rawValue
        let score = "сходство \(Int((entry.score * 100).rounded()))%"
        if let encoder = entry.encoder { return "\(source) · \(encoder.title) · \(score)" }
        return "\(source) · \(score)"
    }
}
