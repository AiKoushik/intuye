import Charts
import LangCoachKit
import SwiftUI

struct ProgressScreen: View {
    @Environment(AppModel.self) private var app
    @State private var data: ProgressDTO?
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Space.m) {
                if let error { ErrorBanner(message: error) { Task { await load() } } }
                if let d = data {
                    spanglish(d.spanglishRatio)
                    confidence(d.confidence)
                    words(d.words)
                } else if error == nil {
                    ProgressView().frame(maxWidth: .infinity).padding(.top, Space.xxxl)
                }
            }
            .padding(.horizontal, Space.margin)
            .padding(.bottom, Space.xxl)
        }
        .background(LC.Color.canvas.ignoresSafeArea())
        .navigationTitle("Progress")
        .refreshable { await load() }
        .task(id: app.refreshToken) { await load() }
    }

    private func spanglish(_ weeks: [WeekRatio]) -> some View {
        VStack(alignment: .leading, spacing: Space.s) {
            Text("English in your Spanish").font(.lcHeadline)
            if let last = weeks.last {
                HStack(alignment: .firstTextBaseline) {
                    Text(last.ratio, format: .percent.precision(.fractionLength(0)))
                        .font(.system(.largeTitle, weight: .bold)).monospacedDigit()
                    Spacer()
                    if weeks.count > 1 {
                        let prev = weeks[weeks.count - 2].ratio
                        Text("\(last.ratio <= prev ? "down" : "up") from \(prev.formatted(.percent.precision(.fractionLength(0)))) last week")
                            .font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                    }
                }
                Chart(weeks, id: \.week) { w in
                    LineMark(x: .value("Week", w.week), y: .value("English share", w.ratio))
                        .foregroundStyle(LC.Color.plum)
                        .lineStyle(StrokeStyle(lineWidth: 2.5, lineCap: .round, lineJoin: .round))
                    PointMark(x: .value("Week", w.week), y: .value("English share", w.ratio))
                        .foregroundStyle(LC.Color.plum)
                }
                .chartYScale(domain: 0...1)
                .chartYAxis { AxisMarks(values: [0, 0.5, 1]) { v in AxisGridLine(); AxisValueLabel(format: .percent) } }
                .frame(height: 120)
                .accessibilityLabel("Weekly share of English in your Spanish sentences")
            } else {
                Text("Try saying things in Spanish, even mixed with English. This shows how much English is left in them, week by week.")
                    .font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
        }
        .lcCard()
    }

    private func confidence(_ rows: [ConfidenceRow]) -> some View {
        VStack(alignment: .leading, spacing: Space.s) {
            Text("Confidence by scene").font(.lcHeadline)
            if rows.isEmpty {
                Text("Rate how ready you feel before and after rehearsing a scene.").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
            ForEach(rows, id: \.scenarioId) { r in
                HStack {
                    TintTile(tint: Tint.topic(nil, title: r.title), size: 28)
                    Text(r.title).font(.lcBody)
                    Spacer()
                    Text(r.before.map(String.init) ?? "–").foregroundStyle(LC.Color.textSecondary)
                    Image(systemName: "arrow.right").font(.caption).foregroundStyle(LC.Color.textSecondary)
                    Text(r.after.map(String.init) ?? "–").fontWeight(.semibold)
                        .foregroundStyle((r.after ?? 0) > (r.before ?? 0) ? LC.Color.success : LC.Color.textPrimary)
                }
                .monospacedDigit()
                .padding(.vertical, 4)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("\(r.title): \(r.before.map { "\($0)" } ?? "not rated") before, \(r.after.map { "\($0)" } ?? "not rated") after")
            }
        }
        .lcCard()
    }

    private func words(_ w: WordStats) -> some View {
        HStack(spacing: Space.s) {
            stat(w.met, "words met", .sea)
            stat(w.kept, "kept", .sage)
            stat(w.due, "due now", .sand)
        }
    }

    private func stat(_ n: Int, _ label: String, _ tint: Tint) -> some View {
        VStack(spacing: 2) {
            Text("\(n)").font(.title2.weight(.bold)).monospacedDigit()
            Text(label).font(.lcCaption)
        }
        .foregroundStyle(tint.fg)
        .frame(maxWidth: .infinity)
        .padding(.vertical, Space.m)
        .background(tint.bg, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .accessibilityElement(children: .combine)
    }

    private func load() async {
        do { data = try await app.api.progress(); error = nil } catch { self.error = error.localizedDescription }
    }
}
