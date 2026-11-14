import Charts
import IntuyeKit
import SwiftUI

struct ProgressScreen: View {
    @Environment(AppModel.self) private var app
    @State private var data: ProgressDTO?
    @State private var lessons: [LessonSummary] = []
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Space.m) {
                if let error { ErrorBanner(message: error) { Task { await load() } } }
                if let d = data {
                    if let r = d.reflection { ReflectionCard(reflection: r) }
                    spanglish(d.spanglishRatio)
                    if let est = d.levelEstimate { level(est) }
                    confidence(d.confidence)
                    words(d.words)
                    lessonList
                } else if error == nil {
                    ProgressView().frame(maxWidth: .infinity).padding(.top, Space.xxxl)
                }
            }
            .padding(.horizontal, Space.margin)
            .padding(.bottom, Space.xxl)
        }
        .background(AmbientBackground(.plum, .sea))
        .navigationTitle("Progress")
        .refreshable { await load() }
        .task(id: app.refreshToken) { await load() }
        .navigationDestination(for: LessonRef.self) { LessonView(ref: $0) }
    }

    private func level(_ est: LevelEstimate) -> some View {
        let b = est.basis
        let why = ["\(b.wordsKept) \(b.wordsKept == 1 ? "word" : "words") kept",
                   b.spanishShare.map { "\($0.formatted(.percent.precision(.fractionLength(0)))) Spanish in what you tried this month" },
                   b.avgSpanishWords.map { "about \(Int($0.rounded())) words a sentence" }].compactMap { $0 }.joined(separator: ", ")
        return VStack(alignment: .leading, spacing: Space.xs) {
            Text("Your level, roughly").font(.lcHeadline)
            HStack(alignment: .firstTextBaseline) {
                Text(est.band).font(.system(.largeTitle, weight: .bold))
                Spacer()
                Text(Levels.name(est.level)).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
            Text("From \(why).").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            if est.level == est.currentSetting {
                Text("Matches your setting.").font(.lcCaption).foregroundStyle(LC.Color.textSecondary).padding(.top, Space.xs)
            } else {
                Button("Use this level (you're set to \(Levels.name(est.currentSetting)))") { Task { await useLevel(est.level) } }
                    .buttonStyle(.lcSubtle).padding(.top, Space.s)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .lcCard(wash: .sand)
    }

    @ViewBuilder private var lessonList: some View {
        if !lessons.isEmpty {
            Text("Grammar from your sentences").font(.lcCaption).foregroundStyle(LC.Color.textSecondary).padding(.top, Space.s)
            VStack(spacing: 0) {
                ForEach(lessons) { l in
                    NavigationLink(value: LessonRef(id: l.id, youSaid: l.youSaid)) {
                        HStack(spacing: Space.m) {
                            TintTile(tint: .plum, symbol: "sparkles", size: 28)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(l.title).font(.lcBody).foregroundStyle(LC.Color.textPrimary)
                                Text(l.pattern).font(.system(.footnote, design: .serif)).foregroundStyle(LC.Color.textSecondary)
                            }
                            Spacer()
                            Image(systemName: "chevron.right").font(.footnote.weight(.semibold)).foregroundStyle(LC.Color.textTertiary)
                        }
                        .padding(.vertical, Space.s)
                    }
                    if l.id != lessons.last?.id { Divider().overlay(LC.Color.hairline) }
                }
            }
            .lcCard()
        }
    }

    private func useLevel(_ level: Int) async {
        do { _ = try await app.api.updateLevel(level); await app.loadMe(); await load() } catch { self.error = error.localizedDescription }
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
        .lcCard(wash: .plum)
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
        do {
            async let p = app.api.progress()
            async let l = app.api.lessons()
            (data, lessons) = (try await p, (try? await l) ?? [])
            error = nil
        } catch { self.error = error.localizedDescription }
    }
}

/// Level names shared by Settings, onboarding and Progress (same 0–5 scale as the estimate).
enum Levels {
    static let names = ["Just starting", "Beginner", "I get by", "Intermediate", "Conversational", "Fluent"]
    static func name(_ i: Int) -> String { names[max(0, min(i, names.count - 1))] }
}

/// The weekly reflection: one calm card. On Progress always, on Today on Mondays.
struct ReflectionCard: View {
    let reflection: Reflection

    var body: some View {
        let r = reflection
        VStack(alignment: .leading, spacing: Space.s) {
            HStack(spacing: Space.m) {
                TintTile(tint: .sage, symbol: "calendar", size: 34)
                VStack(alignment: .leading, spacing: 1) {
                    Text("Your week").font(.lcHeadline)
                    Text("The last seven days").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                }
            }
            Text(r.line).font(.lcBody)
            if let best = r.bestSpanish {
                TintChip(tint: .sage, text: "Your best Spanish this week")
                Text(best).font(.system(.title3, design: .serif))
            }
            HStack(alignment: .top) {
                fact("\(r.sentences)", r.sentences == 1 ? "sentence" : "sentences")
                fact(r.spanishShare.map { $0.formatted(.percent.precision(.fractionLength(0))) } ?? "–", "in Spanish")
                fact("\(r.wordsKept)", r.wordsKept == 1 ? "word stuck" : "words stuck")
                fact("\(r.scenesRehearsed)", r.scenesRehearsed == 1 ? "scene rehearsed" : "scenes rehearsed")
            }
            .padding(.top, Space.xs)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .lcCard(wash: .sage)
    }

    private func fact(_ n: String, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(n).font(.title3.weight(.bold)).monospacedDigit()
            Text(label).font(.caption).foregroundStyle(LC.Color.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }
}
