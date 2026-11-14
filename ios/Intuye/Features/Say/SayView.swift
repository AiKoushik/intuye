import IntuyeKit
import SwiftUI

@MainActor
@Observable
final class SayModel {
    struct Item: Identifiable { let id = UUID(); let result: CoachResult }
    var results: [Item] = []
    var draft = ""
    var busy = false
    var error: String?
    var listenSpanish = false  // on-device speech is one language at a time; Spanglish works best with English

    func send(_ text: String, api: APIClient, direction: CoachDirection = .auto) async {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return }
        busy = true; error = nil
        defer { busy = false }
        do {
            let r = try await api.coach(t, direction: direction)
            results.append(Item(result: r))
            draft = ""
        } catch {
            self.error = (error as? APIError) == .offline
                ? "Couldn't reach your coach. Your sentence is still here; retry when you're back online."
                : error.localizedDescription
            draft = t
        }
    }
}

struct SayView: View {
    @Environment(AppModel.self) private var app
    @State private var model = SayModel()
    @FocusState private var focused: Bool

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: Space.m) {
                    if model.results.isEmpty && !model.busy {
                        EmptyState(message: "Say anything in English, Spanish or a mix — like “me gusta escuchar esto en mi mind” or “what does cómo te va mean?”",
                                   actionTitle: nil)
                    }
                    ForEach(model.results) { item in
                        Group {
                            if item.result.intent == .ask { AnswerCard(result: item.result) } else { ResultCard(result: item.result) }
                        }
                        .id(item.id)
                        .transition(.opacity.combined(with: .move(edge: .bottom)))
                    }
                    if model.busy { PendingCard(source: app.transcriber.isRunning ? app.transcriber.text : model.draft) }
                    if let e = model.error { ErrorBanner(message: e) { Task { await model.send(model.draft, api: app.api) } } }
                }
                .padding(.horizontal, Space.margin)
                .padding(.bottom, Space.xl)
                .animation(Motion.spring, value: model.results.count)
            }
            .onChange(of: model.results.count) { _, _ in
                if let last = model.results.last { withAnimation { proxy.scrollTo(last.id, anchor: .bottom) } }
            }
        }
        .background(AmbientBackground(.sea, .plum))
        .navigationTitle("Say")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Picker("I'll speak", selection: $model.listenSpanish) {
                        Text("English or Spanglish").tag(false)
                        Text("Spanish").tag(true)
                    }
                } label: { Image(systemName: "globe").accessibilityLabel("Speech language") }
            }
            ToolbarItem(placement: .topBarTrailing) {
                NavigationLink { PhrasebookView() } label: { Image(systemName: "star").accessibilityLabel("Phrasebook") }
            }
        }
        .safeAreaInset(edge: .bottom) { inputBar }
    }

    private var inputBar: some View {
        HStack(spacing: Space.m) {
            TextField(app.transcriber.isRunning ? "Listening…" : "Say or type anything",
                      text: app.transcriber.isRunning ? .constant(app.transcriber.text) : $model.draft, axis: .vertical)
                .lineLimit(1...4)
                .focused($focused)
                .submitLabel(.send)
                .onSubmit { Task { await model.send(model.draft, api: app.api) } }
                .padding(.horizontal, Space.l).padding(.vertical, 13)
                .background(LC.Color.surface, in: RoundedRectangle(cornerRadius: 25, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 25, style: .continuous).strokeBorder(LC.Color.borderStrong, lineWidth: 1))
            HoldToTalkButton(isRecording: app.transcriber.isRunning, level: app.transcriber.level,
                             onBegin: { Task { await beginTalking() } }, onEnd: { Task { await endTalking() } })
        }
        .padding(.horizontal, Space.margin)
        .padding(.vertical, Space.s)
        .background(LC.Color.canvas)
    }

    private func beginTalking() async {
        focused = false
        await app.holdToTalkBegan()
        do {
            try await app.transcriber.start(locale: Locale(identifier: model.listenSpanish ? (app.dialect == "es-ES" ? "es-ES" : "es-MX") : "en-US"))
        } catch {
            model.error = error.localizedDescription
            await app.holdToTalkEnded()
        }
    }

    private func endTalking() async {
        let text = await app.transcriber.stop()
        await app.holdToTalkEnded()
        await model.send(text, api: app.api)
    }
}

struct ResultCard: View {
    @Environment(AppModel.self) private var app
    let result: CoachResult
    @State private var showNatural = false
    @State private var saved = false

    var body: some View {
        VStack(alignment: .leading, spacing: Space.m) {
            HStack {
                DirectionChip(intent: result.intent)
                Spacer()
                Button { app.speaker.say(result.intent == .toEs ? result.close : result.source, dialect: app.dialect) } label: {
                    Image(systemName: "speaker.wave.2")
                }
                .accessibilityLabel("Play Spanish")
                Button {
                    saved.toggle()
                    Phrasebook.shared.toggle(result)
                } label: { Image(systemName: saved ? "star.fill" : "star") }
                .accessibilityLabel(saved ? "Remove from phrasebook" : "Save to phrasebook")
                .sensoryFeedback(.selection, trigger: saved)
            }
            .foregroundStyle(LC.Color.accent)
            InterlinearLine(pairs: result.alignment, bottomIsEnglish: result.intent == .toEn)
            if let natural = result.natural {
                DisclosureGroup("More natural", isExpanded: $showNatural) {
                    Text(natural).font(.lcSpanishBody).frame(maxWidth: .infinity, alignment: .leading).padding(.top, Space.xs)
                }
                .font(.lcCaption)
                .foregroundStyle(LC.Color.textSecondary)
            }
        }
        .lcCard()
        .onAppear { saved = Phrasebook.shared.contains(result) }
    }
}

struct AnswerCard: View {
    let result: CoachResult
    var body: some View {
        VStack(alignment: .leading, spacing: Space.s) {
            HStack(spacing: Space.s) {
                DirectionChip(intent: .ask)
                Text(result.source).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
            Text(result.answer ?? "").font(.lcBody)
        }
        .lcCard(wash: .sand)
    }
}

struct PendingCard: View {
    let source: String
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        VStack(alignment: .leading, spacing: Space.s) {
            Text(source.isEmpty ? " " : source).font(.lcSource).foregroundStyle(LC.Color.textSecondary)
            RoundedRectangle(cornerRadius: 6).fill(LC.Color.sunken).frame(height: 24).frame(maxWidth: 240)
                .opacity(reduceMotion ? 1 : 0.6)
                .phaseAnimator(reduceMotion ? [1.0] : [0.5, 1.0]) { v, phase in v.opacity(phase) }
        }
        .lcCard()
        .accessibilityLabel("Translating")
    }
}
