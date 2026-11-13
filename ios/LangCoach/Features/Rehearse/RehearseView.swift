import LangCoachKit
import SwiftUI

@MainActor
@Observable
final class RehearseModel {
    struct Bubble: Identifiable { let id = UUID(); let coach: Bool; let text: String; let en: String?; let native: String? }
    struct Ending: Identifiable { let id = UUID(); let end: RehearsalEnd }

    var bubbles: [Bubble] = []
    var rehearsalId: String?
    var difficulty = "gentle"
    var busy = false
    var done = false
    var error: String?
    var ending: Ending?
    var hintIndex = 0

    func start(scene: ScenarioDTO, api: APIClient, speak: (String) -> Void) async {
        busy = true; defer { busy = false }
        bubbles = []; done = false; ending = nil
        do {
            let r = try await api.startRehearsal(scenarioId: scene.id, difficulty: difficulty)
            rehearsalId = r.rehearsalId
            bubbles.append(Bubble(coach: true, text: r.coach.es, en: r.coach.en, native: nil))
            speak(r.coach.es)
        } catch { self.error = error.localizedDescription }
    }

    func say(_ text: String, api: APIClient, speak: (String) -> Void) async {
        guard let id = rehearsalId, !text.isEmpty else { return }
        busy = true; defer { busy = false }
        do {
            let r = try await api.rehearsalTurn(id, text: text)
            bubbles.append(Bubble(coach: false, text: text, en: nil, native: r.native))
            bubbles.append(Bubble(coach: true, text: r.coach.es, en: r.coach.en, native: nil))
            speak(r.coach.es)
            done = r.done
        } catch { self.error = error.localizedDescription }
    }

    func end(api: APIClient) async {
        guard let id = rehearsalId else { return }
        if let e = try? await api.endRehearsal(id) { ending = Ending(end: e) }
    }
}

/// Voice role-play: the coach plays the other person in Spanish. Tap a coach line for its English;
/// say anything in English to get the Spanish back.
struct RehearseView: View {
    @Environment(AppModel.self) private var app
    let scene: ScenarioDTO
    @State private var model = RehearseModel()
    @State private var englishMode = false
    @State private var shown: Set<UUID> = []

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: Space.s) {
                    ForEach(model.bubbles) { b in bubble(b).id(b.id) }
                    if model.busy { ProgressView().padding() }
                    if let e = model.error { ErrorBanner(message: e) }
                }
                .padding(.horizontal, Space.margin)
                .padding(.vertical, Space.m)
            }
            .onChange(of: model.bubbles.count) { _, _ in
                if let last = model.bubbles.last { withAnimation { proxy.scrollTo(last.id, anchor: .bottom) } }
            }
        }
        .background(AmbientBackground(.sage, .sand))
        .navigationTitle(scene.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Picker("Difficulty", selection: $model.difficulty) {
                        Text("Gentle").tag("gentle"); Text("Real").tag("real"); Text("Fast").tag("fast")
                    }
                    Button("Restart") { Task { await model.start(scene: scene, api: app.api, speak: speak) } }
                    Button("End rehearsal") { Task { await model.end(api: app.api) } }
                } label: { Image(systemName: "slider.horizontal.3").accessibilityLabel("Rehearsal options") }
            }
        }
        .safeAreaInset(edge: .bottom) { controls }
        .task { if model.rehearsalId == nil { await model.start(scene: scene, api: app.api, speak: speak) } }
        .onChange(of: model.done) { _, done in if done { Task { await model.end(api: app.api) } } }
        .sheet(item: $model.ending) { ending in
            RehearsalSummary(scene: scene, end: ending.end)
        }
    }

    private func bubble(_ b: RehearseModel.Bubble) -> some View {
        HStack {
            if !b.coach { Spacer(minLength: 48) }
            VStack(alignment: .leading, spacing: 4) {
                Text(b.text).font(b.coach ? .lcSpanish : .lcBody)
                if b.coach, shown.contains(b.id), let en = b.en {
                    Text(en).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                }
                if let native = b.native {
                    Text("A native would say \(Text(native).font(.lcSpanishBody).foregroundStyle(LC.Color.textPrimary))")
                        .font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                }
            }
            .padding(.horizontal, 14).padding(.vertical, 10)
            .background(b.coach ? Tint.topic(scene.topic, title: scene.title).bg : LC.Color.surface,
                        in: UnevenRoundedRectangle(topLeadingRadius: 20, bottomLeadingRadius: b.coach ? 6 : 20,
                                                   bottomTrailingRadius: b.coach ? 20 : 6, topTrailingRadius: 20, style: .continuous))
            .onTapGesture { if b.coach { if shown.contains(b.id) { shown.remove(b.id) } else { shown.insert(b.id) } } }
            .accessibilityHint(b.coach ? "Double-tap for English" : "")
            if b.coach { Spacer(minLength: 48) }
        }
    }

    private var controls: some View {
        HStack(spacing: Space.m) {
            Button("Hint") { hint() }.buttonStyle(.lcSubtle).frame(width: 96)
            HoldToTalkButton(isRecording: app.transcriber.isRunning, level: app.transcriber.level,
                             onBegin: { Task { await begin() } }, onEnd: { Task { await end() } })
            Button(englishMode ? "Spanish" : "In English") { englishMode.toggle() }
                .buttonStyle(.lcSubtle).frame(width: 96)
                .accessibilityHint("Switches what language the mic listens for")
        }
        .padding(.horizontal, Space.margin).padding(.vertical, Space.s)
        .background(LC.Color.canvas)
        .disabled(model.busy || model.done)
    }

    private func hint() {
        guard let keys = scene.phrases?.key, !keys.isEmpty else { return }
        let p = keys[model.hintIndex % keys.count]
        model.hintIndex += 1
        model.bubbles.append(.init(coach: false, text: "Try: \(p.es)", en: nil, native: nil))
    }

    private func speak(_ text: String) { app.speaker.say(text, dialect: app.dialect, slow: model.difficulty == "gentle") }

    private func begin() async {
        await app.holdToTalkBegan()
        let locale = englishMode ? "en-US" : (app.dialect == "es-ES" ? "es-ES" : "es-MX")
        do { try await app.transcriber.start(locale: Locale(identifier: locale)) } catch {
            model.error = error.localizedDescription; await app.holdToTalkEnded()
        }
    }

    private func end() async {
        let text = await app.transcriber.stop()
        await app.holdToTalkEnded()
        await model.say(text, api: app.api, speak: speak)
    }
}

struct RehearsalSummary: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    let scene: ScenarioDTO
    let end: RehearsalEnd
    @State private var rated: Int?

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: Space.l) {
                Text(end.summary).font(.lcBody)
                Text("Keep these").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                ForEach(end.keepPhrases, id: \.self) { p in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(p.es).font(.lcSpanish)
                        Text(p.en).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                    }
                }
                Text("How ready do you feel now?").font(.lcBody).padding(.top, Space.m)
                HStack {
                    ForEach(1...5, id: \.self) { v in
                        Button("\(v)") {
                            rated = v
                            Task { _ = try? await app.api.rate(scene.id, value: v, phase: "after"); app.refreshToken += 1 }
                        }
                        .buttonStyle(.bordered)
                        .tint(rated == v ? LC.Color.accent : LC.Color.borderStrong)
                    }
                }
                Spacer()
                Button("Done") { dismiss() }.buttonStyle(.lcPrimary)
            }
            .padding(Space.margin)
            .navigationTitle("Rehearsal done")
        }
        .presentationDetents([.large])
    }
}
