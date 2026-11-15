import IntuyeKit
import SwiftUI

/// Rescue drill (see the English, say it in the target language) and shadowing (hear it, say it back), scored
/// phoneme by phoneme from what on-device recognition heard.
struct PracticeView: View {
    enum Mode { case drill, shadow }
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    let scene: ScenarioDTO
    let mode: Mode
    @State private var index = 0
    @State private var result: PracticeResult?
    @State private var heard = ""
    @State private var typed = ""
    @State private var correct = 0
    @State private var error: String?

    private var items: [PhraseDTO] { Array((mode == .drill ? scene.phrases?.rescue : scene.phrases?.key)?.prefix(8) ?? []) }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Space.m) {
                if index >= items.count {
                    VStack(spacing: Space.s) {
                        Text("Done").font(.lcHeadline)
                        Text("\(correct) of \(items.count) sounded right.").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                    }
                    .frame(maxWidth: .infinity).lcCard(wash: .sage)
                    Button("Go again") { index = 0; correct = 0; result = nil }.buttonStyle(.lcPrimary)
                    Button("Back to the scene") { dismiss() }.buttonStyle(.lcSubtle)
                } else {
                    prompt(items[index])
                    if let result { feedback(result, items[index]) }
                    if let error { ErrorBanner(message: error) { self.error = nil } }
                    HoldToTalkButton(isRecording: app.transcriber.isRunning, level: app.transcriber.level,
                                     onBegin: { Task { await begin() } }, onEnd: { Task { await end() } })
                        .frame(maxWidth: .infinity)
                    TextField("Or type what you'd say", text: $typed)
                        .textFieldStyle(.roundedBorder).submitLabel(.done)
                        .onSubmit { Task { await check(typed) } }
                    if result != nil {
                        HStack {
                            Button("Try again") { result = nil }.buttonStyle(.lcSubtle)
                            Button(index == items.count - 1 ? "Finish" : "Next") { index += 1; result = nil; heard = "" }.buttonStyle(.lcPrimary)
                        }
                    }
                }
            }
            .padding(.horizontal, Space.margin).padding(.bottom, Space.xxl)
        }
        .background(AmbientBackground(mode == .drill ? .rose : .sea, mode == .drill ? .sand : .plum))
        .navigationTitle(mode == .drill ? "Rescue drill" : "Shadowing")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func prompt(_ p: PhraseDTO) -> some View {
        VStack(spacing: Space.s) {
            Text("\(index + 1) of \(items.count)").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            if mode == .drill {
                Text(p.en).font(.title2.weight(.bold)).multilineTextAlignment(.center)
                Text("Say it in \(app.lang.name)").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            } else {
                Text(p.target).font(.system(.title, design: .serif)).multilineTextAlignment(.center)
                Text(p.en).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                HStack {
                    Button { app.speaker.say(p.target, voice: app.tts) } label: { Label("Listen", systemImage: "speaker.wave.2") }
                    Button("Slowly") { app.speaker.say(p.target, voice: app.tts, slow: true) }
                }
                .buttonStyle(.bordered)
            }
        }
        .frame(maxWidth: .infinity)
        .lcCard(wash: mode == .drill ? .rose : .sea)
    }

    private func feedback(_ r: PracticeResult, _ p: PhraseDTO) -> some View {
        VStack(alignment: .leading, spacing: Space.s) {
            TintChip(tint: r.ok ? .sage : .rose, text: r.ok ? "Sounded right" : "Close. Listen and try again")
            FlowLayout(spacing: 8, lineSpacing: 8) {
                ForEach(Array(r.words.enumerated()), id: \.offset) { _, w in
                    VStack(spacing: 0) {
                        Text(w.word).font(.lcTargetBody)
                        Text(w.phonemes.map { $0.ok ? $0.p : "[\($0.p)]" }.joined()).font(.caption2).foregroundStyle(LC.Color.textSecondary)
                    }
                    .padding(.horizontal, 6).padding(.vertical, 2)
                    .background((w.ok ? Tint.sage : Tint.rose).bg, in: RoundedRectangle(cornerRadius: 8))
                    .accessibilityLabel(w.ok ? "\(w.word), right" : "\(w.word), \(w.heard.map { "heard \($0)" } ?? "not heard")")
                }
            }
            if !heard.isEmpty { Text("Heard: “\(heard)”").font(.lcCaption).foregroundStyle(LC.Color.textSecondary) }
            ForEach(r.tips, id: \.self) { Text($0).font(.lcCaption).foregroundStyle(LC.Color.textSecondary) }
            if mode == .drill {
                Button { app.speaker.say(p.target, voice: app.tts, slow: true) } label: {
                    Label(p.target, systemImage: "speaker.wave.2").font(.lcTarget)
                }
            }
        }
        .lcCard()
    }

    private func begin() async {
        await app.holdToTalkBegan()
        do { try await app.transcriber.start(locale: app.sttLocale(target: true)) }
        catch { self.error = error.localizedDescription; await app.holdToTalkEnded() }
    }

    private func end() async {
        let text = await app.transcriber.stop()
        await app.holdToTalkEnded()
        await check(text)
    }

    private func check(_ text: String) async {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty, index < items.count else { return }
        heard = t
        do {
            let r = try await app.api.practiceCompare(expected: items[index].target, heard: t)
            result = r; typed = ""
            if r.ok { correct += 1 }
        } catch { self.error = error.localizedDescription }
    }
}
