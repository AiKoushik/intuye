import AVFoundation
import CryptoKit
import EventKit
import Foundation
import IntuyeKit
import UserNotifications

/// Reads upcoming event titles on device; only title + start time are sent to the server.
struct CalendarService {
    func upcomingEvents(days: Int = 14) async throws -> [CalendarEventUpload] {
        let store = EKEventStore()
        guard try await store.requestFullAccessToEvents() else { return [] }
        let start = Date(), end = start.addingTimeInterval(Double(days) * 86400)
        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: nil)
        return store.events(matching: predicate)
            .filter { !$0.isAllDay && !($0.title ?? "").isEmpty }
            .prefix(20)
            .map { CalendarEventUpload(title: $0.title ?? "", startsAt: $0.startDate) }
    }
}

/// Speaks Spanish lines in the learner's chosen variety.
@MainActor
final class Speaker {
    private let synth = AVSpeechSynthesizer()

    func say(_ text: String, dialect: String, slow: Bool = false) {
        synth.stopSpeaking(at: .immediate)
        let u = AVSpeechUtterance(string: text)
        u.voice = AVSpeechSynthesisVoice(language: dialect == "es-ES" ? "es-ES" : "es-MX")
        u.rate = slow ? 0.38 : 0.47
        synth.speak(u)
    }
}

/// Local notifications. The server plans them (budget, quiet hours, one an hour, a reason on each);
/// this only asks permission and mirrors the plan into the system's schedule.
struct NotificationScheduler {
    static let prefix = "plan-"

    func requestPermission() async -> Bool {
        (try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge])) ?? false
    }

    func apply(_ plan: NotificationPlan) async {
        let center = UNUserNotificationCenter.current()
        guard await center.notificationSettings().authorizationStatus == .authorized else { return }
        let old = await center.pendingNotificationRequests().map(\.identifier).filter { $0.hasPrefix(Self.prefix) || $0.hasPrefix("scene-") }
        center.removePendingNotificationRequests(withIdentifiers: old)
        for n in plan.notifications {
            guard let fire = LCDate.parse(n.fireAt), fire > .now else { continue }
            let content = UNMutableNotificationContent()
            content.title = n.title
            content.body = n.body
            content.subtitle = n.why
            content.sound = .default
            content.threadIdentifier = n.kind
            content.userInfo = ["kind": n.kind, "scenario_id": n.scenarioId ?? ""]
            let comps = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute], from: fire)
            try? await center.add(UNNotificationRequest(identifier: Self.prefix + n.id, content: content,
                                                        trigger: UNCalendarNotificationTrigger(dateMatching: comps, repeats: false)))
        }
    }
}

enum Nonce {
    static func random() -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return Data(bytes).base64EncodedString().replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "+", with: "-")
    }

    static func sha256(_ s: String) -> String { SHA256.hash(data: Data(s.utf8)).map { String(format: "%02x", $0) }.joined() }
}
