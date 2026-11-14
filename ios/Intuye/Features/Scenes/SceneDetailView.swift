import IntuyeKit
import SwiftUI

struct SceneDetailView: View {
    @Environment(AppModel.self) private var app
    let scenarioId: String
    @State private var scene: ScenarioDTO?
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Space.m) {
                if let s = scene {
                    let tint = Tint.topic(s.topic, title: s.title)
                    HStack(spacing: Space.s) {
                        TintChip(tint: tint, text: tint.topicLabel)
                        Text(whenLabel(s)).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                    }
                    Text(s.title).font(.lcDisplay)
                    readiness(s)
                    if let p = s.phrases {
                        header("Key phrases")
                        VStack(alignment: .leading, spacing: 0) {
                            ForEach(p.key) { phrase in
                                phraseRow(phrase)
                                if phrase.id != p.key.last?.id { Divider().overlay(LC.Color.hairline) }
                            }
                        }
                        .lcCard()
                        header("If you get stuck")
                        VStack(alignment: .leading, spacing: Space.s) {
                            ForEach(p.rescue) { r in spanishButton(r.es) }
                        }
                        .lcCard(wash: .rose)
                        header("You might hear")
                        VStack(alignment: .leading, spacing: Space.m) {
                            ForEach(p.hear) { h in
                                VStack(alignment: .leading, spacing: 2) {
                                    spanishButton(h.es)
                                    Text(h.en).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                                }
                            }
                        }
                        .lcCard(wash: .sea)
                    }
                    NavigationLink("Rehearse") { RehearseView(scene: s) }
                        .buttonStyle(.lcPrimary)
                        .padding(.top, Space.m)
                } else if let error {
                    ErrorBanner(message: error) { Task { await load() } }
                } else {
                    ProgressView().frame(maxWidth: .infinity).padding(.top, Space.xxxl)
                }
            }
            .padding(.horizontal, Space.margin)
            .padding(.bottom, Space.xxl)
        }
        .background(AmbientBackground(.sand, .sea))
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func header(_ t: String) -> some View {
        Text(t).font(.lcCaption).foregroundStyle(LC.Color.textSecondary).padding(.top, Space.l)
    }

    private func phraseRow(_ p: PhraseDTO) -> some View {
        HStack(alignment: .top) {
            InterlinearLine(pairs: p.alignment.map { AlignedPair(src: $0.src, tgt: $0.tgt, new: false) })
            Spacer(minLength: Space.s)
            Button { app.speaker.say(p.es, dialect: app.dialect) } label: { Image(systemName: "speaker.wave.2") }
                .accessibilityLabel("Play \(p.es)")
        }
        .padding(.vertical, Space.m)
    }

    private func spanishButton(_ es: String) -> some View {
        Button { app.speaker.say(es, dialect: app.dialect, slow: true) } label: {
            Text(es).font(.lcSpanish).foregroundStyle(LC.Color.textPrimary).frame(maxWidth: .infinity, alignment: .leading)
        }
        .buttonStyle(.plain)
        .accessibilityHint("Plays it slowly")
    }

    private func readiness(_ s: ScenarioDTO) -> some View {
        HStack {
            Text("How ready do you feel?").font(.lcBody)
            Spacer()
            HStack(spacing: 2) {
                ForEach(1...5, id: \.self) { v in
                    Button { Task { await rate(v) } } label: {
                        Image(systemName: v <= (s.readiness.current ?? 0) ? "circle.fill" : "circle")
                            .font(.footnote).foregroundStyle(Tint.topic(s.topic, title: s.title).fg).frame(width: 28, height: 44)
                    }
                    .accessibilityLabel("\(v) of 5")
                }
            }
        }
        .lcCard(padding: Space.m)
    }

    private func rate(_ value: Int) async {
        guard let s = scene else { return }
        let phase = s.readiness.before == nil ? "before" : "after"
        _ = try? await app.api.rate(s.id, value: value, phase: phase)
        await load()
    }

    private func load() async {
        do { scene = try await app.api.scenario(scenarioId); error = nil } catch { self.error = error.localizedDescription }
    }
}
