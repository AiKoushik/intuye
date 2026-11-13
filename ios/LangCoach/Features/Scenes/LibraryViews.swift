import LangCoachKit
import SwiftUI

/// "Find or add a scene": type, or tap the mic and say it. Speech is transcribed on the iPhone; only text is searched.
struct SceneSearchField: View {
    @Environment(AppModel.self) private var app
    @Binding var query: String
    var onSubmit: () -> Void
    @State private var listening = false
    @FocusState private var focused: Bool

    var body: some View {
        HStack(spacing: Space.s) {
            Image(systemName: "magnifyingglass").foregroundStyle(LC.Color.textTertiary)
            TextField(listening ? "Listening…" : "Find or add a scene",
                      text: listening ? .constant(app.transcriber.text) : $query)
                .focused($focused)
                .submitLabel(.search)
                .onSubmit(onSubmit)
                .font(.lcBody)
            Button { Task { await toggleMic() } } label: {
                Image(systemName: "mic.fill")
                    .frame(width: 40, height: 40)
                    .foregroundStyle(listening ? LC.Color.onAccent : LC.Color.accent)
                    .background(listening ? LC.Color.accentFill : .clear, in: Circle())
            }
            .accessibilityLabel(listening ? "Stop and search" : "Say a scene")
            .accessibilityAddTraits(listening ? .isSelected : [])
        }
        .padding(.leading, Space.m).padding(.trailing, Space.xs)
        .frame(minHeight: 48)
        .background(LC.Color.surface, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous)
            .stroke(focused || listening ? LC.Color.accent : LC.Color.borderStrong, lineWidth: 1))
        .onChange(of: app.transcriber.isRunning) { _, running in
            if !running && listening { Task { await toggleMic() } }  // recognizer stopped on its own
        }
    }

    private func toggleMic() async {
        if listening {
            listening = false
            let text = await app.transcriber.stop()
            await app.holdToTalkEnded()
            if !text.isEmpty { query = text; onSubmit() }
            return
        }
        focused = false
        await app.holdToTalkBegan()
        do {
            try await app.transcriber.start(locale: Locale(identifier: "en-US"))
            listening = true
        } catch {
            await app.holdToTalkEnded()
        }
    }
}

struct LibraryRow: View {
    let card: LibraryCard
    var body: some View {
        HStack(spacing: Space.m) {
            VStack(alignment: .leading, spacing: 2) {
                Text(card.title).font(.lcBody)
                Text(card.situation).font(.lcCaption).foregroundStyle(LC.Color.textSecondary).lineLimit(2)
            }
            Spacer(minLength: Space.s)
            Text(usesLabel(card.uses)).font(.lcCaption).foregroundStyle(LC.Color.textSecondary).monospacedDigit()
        }
        .padding(.vertical, 2)
        .accessibilityElement(children: .combine)
    }
}

func usesLabel(_ n: Int) -> String { n == 1 ? "1 use" : "\(n) uses" }

/// A library scene before you add it: what it covers, who shared it, its phrases.
struct LibrarySceneView: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    let templateId: String
    var onUsed: (ScenarioDTO) -> Void
    @State private var scene: LibraryScene?
    @State private var error: String?
    @State private var busy = false
    @State private var reporting = false
    @State private var reported = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Space.m) {
                if let t = scene {
                    Text(t.title).font(.lcDisplay)
                    Text(t.situation).font(.lcBody)
                    Label("\(usesLabel(t.uses)). \(t.credit.map { "Shared by \($0)" } ?? "Shared anonymously").",
                          systemImage: "person.2")
                        .font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                    Button(busy ? "Adding…" : "Use this scene") { Task { await use() } }
                        .buttonStyle(.lcPrimary).disabled(busy)
                    Text("Key phrases").font(.lcCaption).foregroundStyle(LC.Color.textSecondary).padding(.top, Space.l)
                    VStack(alignment: .leading, spacing: 0) {
                        ForEach(Array(t.phrases.key.enumerated()), id: \.offset) { i, p in
                            HStack(alignment: .top) {
                                InterlinearLine(pairs: p.alignment.map { $0.map { AlignedPair(src: $0.src, tgt: $0.tgt, new: false) } }
                                    ?? [AlignedPair(src: p.en, tgt: p.es, new: false)])
                                Spacer(minLength: Space.s)
                                Button { app.speaker.say(p.es, dialect: app.dialect) } label: { Image(systemName: "speaker.wave.2") }
                                    .accessibilityLabel("Play \(p.es)")
                            }
                            .padding(.vertical, Space.m)
                            if i < t.phrases.key.count - 1 { Divider().overlay(LC.Color.hairline) }
                        }
                    }
                    .lcCard()
                    Text("If you get stuck").font(.lcCaption).foregroundStyle(LC.Color.textSecondary).padding(.top, Space.l)
                    VStack(alignment: .leading, spacing: Space.s) {
                        ForEach(t.phrases.rescue, id: \.es) { r in
                            Button { app.speaker.say(r.es, dialect: app.dialect, slow: true) } label: {
                                Text(r.es).font(.lcSpanish).foregroundStyle(LC.Color.textPrimary).frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .lcCard()
                    Button { reporting = true } label: { Label(reported ? "Reported. Thanks." : "Report this scene", systemImage: "flag") }
                        .font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .disabled(reported)
                } else if let error {
                    ErrorBanner(message: error) { Task { await load() } }
                } else {
                    ProgressView().frame(maxWidth: .infinity).padding(.top, Space.xxxl)
                }
            }
            .padding(.horizontal, Space.margin)
            .padding(.bottom, Space.xxl)
        }
        .background(LC.Color.canvas.ignoresSafeArea())
        .navigationBarTitleDisplayMode(.inline)
        .confirmationDialog("What's wrong with this scene?", isPresented: $reporting, titleVisibility: .visible) {
            ForEach(LibraryReportReason.allCases, id: \.self) { reason in
                Button(reason.label) { Task { await report(reason) } }
            }
        } message: { Text("Scenes reported by three learners are hidden until we review them.") }
        .task { await load() }
    }

    private func load() async {
        do { scene = try await app.api.libraryScene(templateId); error = nil } catch { self.error = error.localizedDescription }
    }

    private func use() async {
        busy = true; defer { busy = false }
        do {
            let s = try await app.api.useLibraryScene(templateId)
            app.refreshToken += 1
            dismiss()
            onUsed(s)
        } catch { self.error = error.localizedDescription }
    }

    private func report(_ reason: LibraryReportReason) async {
        do { try await app.api.reportLibraryScene(templateId, reason: reason); reported = true } catch { self.error = error.localizedDescription }
    }
}
