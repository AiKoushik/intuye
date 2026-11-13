import LangCoachKit
import SwiftUI

struct TodayView: View {
    @Environment(AppModel.self) private var app
    @State private var today: TodayDTO?
    @State private var error: String?
    @State private var showReview = false
    @State private var showSettings = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Space.m) {
                Text(Date.now.formatted(.dateTime.weekday(.wide).day().month(.wide)))
                    .font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                Text(greeting).font(.lcDisplay).padding(.bottom, Space.s)

                if let error { ErrorBanner(message: error) { Task { await load() } } }

                if let scene = today?.nextScenario {
                    NavigationLink { SceneDetailView(scenarioId: scene.id) } label: { comingUp(scene) }.buttonStyle(.plain)
                } else if today != nil {
                    EmptyState(message: "Nothing coming up yet. Tell your coach about a situation you'd like to be ready for.",
                               actionTitle: "Add a scene") { app.selectedTab = .scenes }
                }
                if let n = today?.suggestedScenarios, n > 0 {
                    Button { app.selectedTab = .scenes } label: {
                        Label(n == 1 ? "1 scene suggested from what you talk about" : "\(n) scenes suggested from what you talk about",
                              systemImage: "sparkles").font(.lcCaption)
                    }
                }
                words
                if let recent = today?.recent, !recent.isEmpty {
                    Text("Recent sentences").font(.lcCaption).foregroundStyle(LC.Color.textSecondary).padding(.top, Space.l)
                    ForEach(recent) { r in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(r.text).font(.lcSource).foregroundStyle(LC.Color.textSecondary)
                            if let es = r.closeEs { Text(es).font(.lcSpanish) }
                        }
                        .lcCard()
                    }
                } else if today != nil {
                    EmptyState(message: "Say anything in English to get started.", actionTitle: "Open Say") { app.selectedTab = .say }
                }
            }
            .padding(.horizontal, Space.margin)
            .padding(.bottom, Space.xxl)
        }
        .background(LC.Color.canvas.ignoresSafeArea())
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { showSettings = true } label: { Image(systemName: "person.crop.circle") }.accessibilityLabel("Settings")
            }
        }
        .refreshable { await load() }
        .task(id: app.refreshToken) { await load() }
        .fullScreenCover(isPresented: $showReview, onDismiss: { Task { await load() } }) { ReviewSessionView() }
        .sheet(isPresented: $showSettings) { SettingsView() }
    }

    private var greeting: String {
        let h = Calendar.current.component(.hour, from: .now)
        let part = h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"
        return app.firstName.map { "\(part), \($0)" } ?? part
    }

    private func comingUp(_ s: ScenarioDTO) -> some View {
        VStack(alignment: .leading, spacing: Space.m) {
            let tint = Tint.topic(s.topic, title: s.title)
            HStack(alignment: .top, spacing: Space.m) {
                TintTile(tint: tint, size: 36)
                VStack(alignment: .leading, spacing: 2) {
                    Text(s.title).font(.lcHeadline).foregroundStyle(LC.Color.textPrimary)
                    Text(whenLabel(s)).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                }
                Spacer()
                ReadinessDots(value: s.readiness.current, tint: tint)
            }
            Text((s.readiness.after ?? 0) > 0 ? "Rehearse again" : "Prep").buttonLike()
        }
        .lcCard()
    }

    private var words: some View {
        VStack(alignment: .leading, spacing: Space.m) {
            let count = today?.wordsReady.count ?? 0
            HStack(spacing: Space.m) {
                TintTile(tint: .sea, symbol: "rectangle.stack", size: 36)
                VStack(alignment: .leading, spacing: 2) {
                    Text(count > 0 ? "\(count) words ready" : "Your words").font(.lcHeadline)
                    Text(count > 0 ? "From what you said and what's coming up" : "Get 5–10 words picked from your week")
                        .font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                }
            }
            if let items = today?.wordsReady.previewItems, !items.isEmpty {
                FlowLayout(spacing: 8, lineSpacing: 8) {
                    ForEach(items, id: \.es) { WordChip(text: $0.es, tint: Tint.reason($0.origin)) }
                }
            }
            Button(count > 0 ? "Start review" : "Get today's words") { showReview = true }.buttonStyle(.lcSubtle)
        }
        .lcCard()
    }

    private func load() async {
        do { today = try await app.api.today(); error = nil } catch { self.error = error.localizedDescription }
    }
}

func whenLabel(_ s: ScenarioDTO) -> String {
    guard let date = LCDate.parse(s.startsAt) else { return s.kind == "recurring" ? "Comes up often" : "Whenever you're ready" }
    let raw = date.formatted(.relative(presentation: .named))
    let rel = raw.prefix(1).uppercased() + raw.dropFirst()
    let time = date.formatted(date: .omitted, time: .shortened)
    return s.kind == "upcoming" ? "\(rel) at \(time), from your calendar" : "\(rel) at \(time)"
}

private extension Text {
    /// Looks like the primary button inside a tappable card (the card itself is the button).
    func buttonLike() -> some View {
        self.font(.headline).frame(maxWidth: .infinity, minHeight: 50)
            .foregroundStyle(LC.Color.onAccent)
            .background(LC.Color.accentFill, in: RoundedRectangle(cornerRadius: Radius.control, style: .continuous))
    }
}
