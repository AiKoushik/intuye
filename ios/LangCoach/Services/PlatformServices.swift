import AVFoundation
import CryptoKit
import EventKit
import Foundation
import LangCoachKit
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

/// Local notifications with a daily budget and quiet hours (defaults: 3/day, 22:00–08:00).
struct NotificationScheduler {
    var budget = 3
    var quietStart = 22
    var quietEnd = 8

    func requestPermission() async -> Bool {
        (try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge])) ?? false
    }

    /// Scene reminder the evening before (19:00), or 2 hours before if that's sooner and still ahead.
    func scheduleSceneReminder(id: String, title: String, phrases: Int, startsAt: Date) async {
        let cal = Calendar.current
        var fire = cal.date(bySettingHour: 19, minute: 0, second: 0, of: startsAt.addingTimeInterval(-86400)) ?? startsAt
        if fire < Date() { fire = startsAt.addingTimeInterval(-7200) }
        guard fire > Date(), await allowed(at: fire) else { return }
        let content = UNMutableNotificationContent()
        content.title = "\(title) \(cal.isDate(startsAt, inSameDayAs: fire) ? "today" : "tomorrow")"
        content.body = "\(phrases) phrases ready"
        content.sound = .default
        content.userInfo = ["scenario_id": id]
        let comps = cal.dateComponents([.year, .month, .day, .hour, .minute], from: fire)
        let req = UNNotificationRequest(identifier: "scene-\(id)", content: content,
                                        trigger: UNCalendarNotificationTrigger(dateMatching: comps, repeats: false))
        try? await UNUserNotificationCenter.current().add(req)
    }

    private func allowed(at date: Date) async -> Bool {
        let hour = Calendar.current.component(.hour, from: date)
        let quiet = quietStart > quietEnd ? (hour >= quietStart || hour < quietEnd) : (hour >= quietStart && hour < quietEnd)
        if quiet { return false }
        let pending = await UNUserNotificationCenter.current().pendingNotificationRequests()
        let sameDay = pending.filter {
            guard let t = $0.trigger as? UNCalendarNotificationTrigger, let d = t.nextTriggerDate() else { return false }
            return Calendar.current.isDate(d, inSameDayAs: date)
        }
        return sameDay.count < budget
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
