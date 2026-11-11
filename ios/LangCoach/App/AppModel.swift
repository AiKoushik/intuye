import Foundation
import LangCoachKit
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

    let api: APIClient
    let attest: AttestService
    let transcriber = LiveTranscriber()
    let capture: AmbientCapture
    let speaker = Speaker()
    let calendar = CalendarService()
    var notifications = NotificationScheduler()

    var dialect: String { me?.settings.dialect ?? "es-419" }
    var firstName: String? { me?.user.displayName?.split(separator: " ").first.map(String.init) }

    init() {
        let raw = Bundle.main.object(forInfoDictionaryKey: "LCAPIBaseURL") as? String ?? "http://localhost:8000"
        let baseURL = URL(string: raw) ?? URL(string: "http://localhost:8000")!
        attest = AttestService(baseURL: baseURL)
        api = APIClient(baseURL: baseURL, tokens: KeychainStore(), signer: attest)
        capture = AmbientCapture(transcriber: transcriber, api: api)
    }

    func boot() async {
        await api.onSignedOut { Task { @MainActor in self.signedOut() } }
        guard await api.isSignedIn else { phase = .onboarding; return }
        phase = .signedIn
        await loadMe()
        capture.startTicker()
    }

    func loadMe() async {
        if let me = try? await api.me() {
            self.me = me
            notifications.budget = me.settings.dailyNotificationBudget
            notifications.quietStart = Int(me.settings.quietStart.prefix(2)) ?? 22
            notifications.quietEnd = Int(me.settings.quietEnd.prefix(2)) ?? 8
        }
    }

    func didSignIn() async {
        phase = .signedIn
        await loadMe()
        capture.startTicker()
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
