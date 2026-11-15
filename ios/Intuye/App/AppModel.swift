import Foundation
import IntuyeKit
import SwiftUI

/// One shared model: session state, the API client and platform services. Injected via the environment.
@MainActor
@Observable
final class AppModel {
    enum Phase { case launching, onboarding, signedIn }

    var phase: Phase = .launching
    var me: MeDTO?
    var selectedTab: AppTab = .today
    /// Bumped when data other tabs show has changed (new batch, scene created...).
    var refreshToken = 0
    /// Bumped by Siri, the Action Button or a control: Say starts listening hands-free.
    var talkRequest = 0
    /// Bumped by Siri or a control: the review session opens.
    var reviewRequest = 0

    let api: APIClient
    let attest: AttestService
    let transcriber = LiveTranscriber()
    let capture: AmbientCapture
    let speaker = Speaker()
    let calendar = CalendarService()
    var notifications = NotificationScheduler()
    let reviewQueue: ReviewQueue

    /// The server's languages (cached for offline). Screens read the learner's language and variety from here.
    var languages: LanguageCatalog? = LanguageCatalog.cached()
    var dialect: String { me?.settings.dialect ?? lang.defaultVariety }
    var lang: LanguageInfo { (languages ?? LanguageCatalog(default: "", languages: [])).language(forVariety: me?.settings.dialect) }
    var variety: VarietyInfo { (languages ?? LanguageCatalog(default: "", languages: [])).variety(dialect) }
    /// Voice for target-language speech, e.g. "es-MX".
    var tts: String { variety.tts }
    /// Speech recognition: the target language, or the learner's own (English) when `target` is false.
    func sttLocale(target: Bool) -> Locale { Locale(identifier: target ? variety.stt : "en-US") }

    func loadLanguages() async {
        if let c = try? await api.languages() { languages = c; c.cache() }
    }
    var firstName: String? { me?.user.displayName?.split(separator: " ").first.map(String.init) }

    init() {
        let raw = Bundle.main.object(forInfoDictionaryKey: "LCAPIBaseURL") as? String ?? "http://localhost:8000"
        let baseURL = URL(string: raw) ?? URL(string: "http://localhost:8000")!
        attest = AttestService(baseURL: baseURL)
        api = APIClient(baseURL: baseURL, tokens: KeychainStore(), signer: attest)
        capture = AmbientCapture(transcriber: transcriber, api: api)
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
        reviewQueue = ReviewQueue(fileURL: support.appendingPathComponent("review-queue.json"))
    }

    /// On launch and whenever the app comes back: replay offline reviews, then refresh the notification plan.
    func syncOffline() async {
        guard phase == .signedIn else { return }
        let sent = await reviewQueue.flush { r in _ = try await self.api.replay(r) }
        if sent > 0 { refreshToken += 1 }
        await syncNotifications()
    }

    /// Replaces every planned local notification with the server's plan (budget, quiet hours and spacing applied there).
    func syncNotifications() async {
        guard let plan = try? await api.notificationPlan() else { return }
        await notifications.apply(plan)
    }

    func boot() async {
        await api.onSignedOut { Task { @MainActor in self.signedOut() } }
        await loadLanguages()
        guard await api.isSignedIn else { phase = .onboarding; return }
        phase = .signedIn
        await loadMe()
        capture.startTicker()
        await syncOffline()
    }

    func loadMe() async {
        if let me = try? await api.me() {
            self.me = me
        }
    }

    func didSignIn() async {
        phase = .signedIn
        await loadMe()
        capture.startTicker()
        await syncOffline()
    }

    func signedOut() {
        me = nil
        capture.mode = .off
        phase = .onboarding
    }

    func signOut() async {
        await api.signOut()
        signedOut()
    }

    /// Hold-to-talk borrows the mic from ambient capture and gives it back afterwards.
    func holdToTalkBegan() async {
        capture.isPausedForHoldToTalk = true
        await capture.reconcile()
    }

    func holdToTalkEnded() async {
        capture.isPausedForHoldToTalk = false
        await capture.reconcile()
    }
}

enum AppTab: Hashable { case today, say, scenes, progress }
