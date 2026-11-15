import IntuyeKit
import SwiftUI

/// Which lesson to open, and the learner's sentence that triggered it (shown as "You said").
struct LessonRef: Identifiable, Hashable { let id: String; var youSaid: String? = nil }

/// A 60-second grammar lesson: the pattern, one plain rule, three examples, one check.
/// Opened from a review card ("Why it's built this way") or from Progress.
struct LessonView: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    let ref: LessonRef
    var asSheet = false
    @State private var lesson: Lesson?
    @State private var picked: Int?
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Space.m) {
                if let error { ErrorBanner(message: error) { Task { await load() } } }
                if let l = lesson { content(l) } else if error == nil { ProgressView().frame(maxWidth: .infinity).padding(.top, Space.xxxl) }
            }
            .padding(.horizontal, Space.margin)
            .padding(.bottom, Space.xxl)
        }
        .background(AmbientBackground(.plum, .sand))
        .navigationTitle("Lesson")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { if asSheet { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } } }
        .task { await load() }
    }

    @ViewBuilder private func content(_ l: Lesson) -> some View {
        VStack(alignment: .leading, spacing: Space.xs) {
            Text(l.title).font(.title.weight(.bold))
            Text(l.pattern).font(.system(.title2, design: .serif)).foregroundStyle(Tint.plum.fg)
        }
        Text(l.rule).font(.lcBody)
        if let said = ref.youSaid {
            VStack(alignment: .leading, spacing: Space.xs) {
                TintChip(tint: .sand, text: "You said")
                Text(said).font(.lcSource).foregroundStyle(LC.Color.textSecondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .lcCard(wash: .sand)
        }
        VStack(spacing: 0) {
            ForEach(Array(l.examples.enumerated()), id: \.offset) { i, x in
                if i > 0 { Divider().overlay(LC.Color.hairline) }
                Button { app.speaker.say(x.target, voice: app.tts) } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(x.target).font(.system(.title3, design: .serif)).foregroundStyle(LC.Color.textPrimary)
                            Text(x.en).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                        }
                        Spacer()
                        Image(systemName: "speaker.wave.2").foregroundStyle(LC.Color.accent)
                    }
                    .padding(.vertical, Space.s)
                }
                .accessibilityLabel("\(x.target). \(x.en)")
                .accessibilityHint("Plays the \(app.lang.name)")
            }
        }
        .lcCard()
        Text("Your turn").font(.lcCaption).foregroundStyle(LC.Color.textSecondary).padding(.top, Space.s)
        check(l.check).lcCard(wash: .plum)
    }

    private func check(_ c: LessonCheck) -> some View {
        VStack(alignment: .leading, spacing: Space.s) {
            Text("Which is right?").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            Text(c.prompt).font(.lcHeadline)
            ForEach(Array(c.options.enumerated()), id: \.offset) { i, option in
                let right = picked != nil && i == c.answer, wrong = picked == i && i != c.answer
                Button {
                    guard picked == nil else { return }
                    picked = i
                    if i == c.answer { app.speaker.say(option, voice: app.tts) }
                } label: {
                    HStack {
                        Text(option).font(.system(.body, design: .serif)).foregroundStyle(LC.Color.textPrimary)
                        Spacer()
                        if right { Image(systemName: "checkmark").foregroundStyle(Tint.sage.fg) }
                    }
                    .padding(.horizontal, Space.m).padding(.vertical, 11)
                    .background(right ? Tint.sage.wash : wrong ? Tint.rose.wash : LC.Color.surface,
                                in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .strokeBorder(right ? Tint.sage.fg : wrong ? Tint.rose.fg : LC.Color.hairline))
                    .opacity(picked != nil && !right && !wrong ? 0.55 : 1)
                }
                .disabled(picked != nil)
                .accessibilityAddTraits(picked == i ? .isSelected : [])
            }
            .sensoryFeedback(trigger: picked) { _, new in new == c.answer ? .success : .error }
            if let p = picked {
                Text(p == c.answer ? "That's the one." : "Not quite. The green one follows the pattern above.")
                    .font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
        }
    }

    private func load() async {
        do { lesson = try await app.api.lesson(ref.id); error = nil } catch { self.error = error.localizedDescription }
    }
}
