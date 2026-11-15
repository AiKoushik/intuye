import IntuyeKit
import SwiftUI

@MainActor
@Observable
final class ReviewModel {
    var cards: [DueCard] = []
    var index = 0
    var revealed = false
    var loading = true
    var error: String?
    var pronunciation: PronunciationResult?
    var nextDue: Date?
    var reviewed = 0
    /// True once a rating had to be saved on the device because the server wasn't reachable.
    var savedOffline = false

    var current: DueCard? { cards.indices.contains(index) ? cards[index] : nil }
    var finished: Bool { !loading && current == nil }

    func load(api: APIClient, queue: ReviewQueue) async {
        loading = true; defer { loading = false }
        do {
            var due = try await api.dueCards()
            if due.isEmpty {
                _ = try await api.nextBatch()
                due = try await api.dueCards()
            }
            cards = due
            await queue.cache(due)
        } catch let e as APIError where e.status == 0 {
            cards = await queue.cachedDue()  // airplane mode: review what was due last time we were online
            if cards.isEmpty { self.error = e.message }
        } catch { self.error = error.localizedDescription }
    }

    func rate(_ rating: Rating, api: APIClient, queue: ReviewQueue) async {
        guard let card = current else { return }
        do {
            let r = try await api.review(card.lexemeId, rating)
            if let d = LCDate.parse(r.dueAt), rating != .forgot { nextDue = min(nextDue ?? d, d) }
        } catch let e as APIError where e.status == 0 {
            await queue.append(PendingReview(lexemeId: card.lexemeId, rating: rating.rawValue, reviewedAt: LCDate.string(.now)))
            savedOffline = true
        } catch { self.error = error.localizedDescription; return }
        reviewed += 1
        if rating == .forgot { cards.append(card) }  // see it again at the end of this session
        index += 1; revealed = false; pronunciation = nil
    }
}

struct ReviewSessionView: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var model = ReviewModel()
    @State private var ratingTrigger = 0
    @State private var lesson: LessonRef?

    var body: some View {
        VStack(spacing: Space.l) {
            HStack {
                Text(model.cards.isEmpty ? "" : "\(min(model.index + 1, model.cards.count)) of \(model.cards.count)")
                    .font(.lcCaption).foregroundStyle(LC.Color.textSecondary).monospacedDigit()
                Spacer()
                Button("Close") { dismiss() }
            }
            ProgressView(value: Double(model.index), total: Double(max(model.cards.count, 1))).tint(LC.Color.accent)

            if model.loading {
                Spacer(); ProgressView(); Spacer()
            } else if let e = model.error {
                ErrorBanner(message: e) { Task { model.error = nil; await model.load(api: app.api, queue: app.reviewQueue) } }
                Spacer()
            } else if let card = model.current {
                cardView(card)
                    .id(card.lexemeId + "\(model.index)")
                    .transition(reduceMotion ? .opacity : .asymmetric(insertion: .move(edge: .trailing), removal: .move(edge: .leading)))
                ratings
            } else {
                summary
            }
        }
        .padding(Space.margin)
        .background(AmbientBackground(.sea, .sage))
        .animation(reduceMotion ? .easeInOut(duration: 0.15) : Motion.spring, value: model.index)
        .animation(Motion.spring, value: model.revealed)
        .sensoryFeedback(.success, trigger: ratingTrigger)
        .task { await model.load(api: app.api, queue: app.reviewQueue) }
        .sheet(item: $lesson) { ref in NavigationStack { LessonView(ref: ref, asSheet: true) } }
        .onDisappear { Task { await app.syncOffline() } }
    }

    private func cardView(_ card: DueCard) -> some View {
        VStack(spacing: Space.l) {
            Spacer()
            Text(card.en).font(.system(.largeTitle, weight: .bold)).multilineTextAlignment(.center)
            if let ctx = card.context {
                Text(blanked(ctx, card.target)).font(.lcSource).foregroundStyle(LC.Color.textSecondary).multilineTextAlignment(.center)
            }
            if model.revealed {
                VStack(spacing: Space.s) {
                    Button { app.speaker.say(card.target, voice: app.tts) } label: {
                        Text(card.target).font(.system(.largeTitle, design: .serif)).foregroundStyle(LC.Color.textPrimary)
                    }
                    .accessibilityHint("Plays the \(app.lang.name)")
                    if let reason = card.reason { TintChip(tint: Tint.reason(card.reasonKind), text: reason) }
                    if let id = card.lessonId {
                        Button("Why it's built this way") { lesson = LessonRef(id: id) }.font(.lcCaption.weight(.semibold))
                    }
                    if let p = model.pronunciation {
                        Label(p.ok ? "Sounded right" : "Close — listen and try again", systemImage: p.ok ? "checkmark" : "ear")
                            .font(.lcCaption).foregroundStyle(p.ok ? LC.Color.success : LC.Color.warning)
                    }
                }
                .transition(.opacity)
            } else {
                Text("Tap to show, or hold the mic and say it").font(.lcCaption).foregroundStyle(LC.Color.accent)
            }
            Spacer()
            if !model.revealed {
                HoldToTalkButton(isRecording: app.transcriber.isRunning, level: app.transcriber.level,
                                 onBegin: { Task { await beginSpeaking() } },
                                 onEnd: { Task { await endSpeaking(card) } })
            }
        }
        .frame(maxWidth: .infinity)
        .padding(Space.xl)
        .background(LC.Color.surface, in: RoundedRectangle(cornerRadius: Radius.sheet, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: Radius.sheet, style: .continuous).strokeBorder(LC.Color.hairline))
        .contentShape(Rectangle())
        .onTapGesture { model.revealed = true }
        .accessibilityAction(named: "Show answer") { model.revealed = true }
    }

    private var ratings: some View {
        HStack(spacing: Space.s) {
            ForEach(Rating.allCases, id: \.self) { r in
                RatingButton(rating: r) {
                    if r == .gotIt || r == .easy { ratingTrigger += 1 }
                    Task { await model.rate(r, api: app.api, queue: app.reviewQueue) }
                }
            }
        }
        .opacity(model.revealed ? 1 : 0)
        .disabled(!model.revealed)
        .accessibilityHidden(!model.revealed)
    }

    private var summary: some View {
        VStack(alignment: .leading, spacing: Space.m) {
            Spacer()
            Text(model.reviewed == 0 ? "Nothing to review right now" : "\(model.reviewed) words done").font(.lcDisplay)
            if let next = model.nextDue {
                Text("Next review \(next.formatted(.relative(presentation: .named)))").font(.lcBody).foregroundStyle(LC.Color.textSecondary)
            }
            if model.savedOffline {
                Text("You're offline. These are saved on your iPhone and sync when you're back.")
                    .font(.lcBody).foregroundStyle(LC.Color.textSecondary)
            }
            Spacer()
            Button("Done") { dismiss() }.buttonStyle(.lcPrimary)
        }
    }

    private func blanked(_ context: String, _ word: String) -> String {
        context.replacingOccurrences(of: word, with: "____", options: [.caseInsensitive, .diacriticInsensitive])
    }

    private func beginSpeaking() async {
        await app.holdToTalkBegan()
        try? await app.transcriber.start(locale: app.sttLocale(target: true))
    }

    private func endSpeaking(_ card: DueCard) async {
        let heard = await app.transcriber.stop()
        await app.holdToTalkEnded()
        model.revealed = true
        if !heard.isEmpty { model.pronunciation = try? await app.api.pronunciation(card.lexemeId, expected: card.target, heard: heard) }
    }
}
