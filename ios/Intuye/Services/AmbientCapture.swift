import Foundation
import IntuyeKit

/// Ambient capture: transcribes your sentences on-device during the windows you choose and queues the text.
/// It never listens inside a never-record place (H7).
/// P2 hardening still to do: own-voice filtering (speaker enrolment) and long-run background survival checks.
@MainActor
@Observable
final class AmbientCapture {
    enum Mode: String, CaseIterable, Identifiable {
        case off, windows, always
        var id: String { rawValue }
        var label: String { ["off": "Off", "windows": "During my windows", "always": "Always"][rawValue]! }
    }

    var mode: Mode = Mode(rawValue: UserDefaults.standard.string(forKey: "captureMode") ?? "off") ?? .off {
        didSet { UserDefaults.standard.set(mode.rawValue, forKey: "captureMode"); Task { await reconcile() } }
    }
    /// Capture windows as hour ranges, e.g. [9..<12, 18..<21].
    var windows: [Range<Int>] = [9..<12, 18..<21]
    private(set) var sentencesToday = 0
    private(set) var isListening = false
    private(set) var lastError: String?
    var isPausedForHoldToTalk = false
    /// Set by the app: the never-record place the phone is in right now, if any.
    var placeCheck: (@MainActor () -> NeverRecordPlace?)?

    private let transcriber: LiveTranscriber
    private let queue: OfflineQueue
    private let api: APIClient
    private var ticker: Task<Void, Never>?

    init(transcriber: LiveTranscriber, api: APIClient) {
        self.transcriber = transcriber
        self.api = api
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        self.queue = OfflineQueue(fileURL: dir.appendingPathComponent("capture-queue.json"))
        self.sentencesToday = UserDefaults.standard.integer(forKey: Self.todayKey)
    }

    private static var todayKey: String { "sentences-" + ISO8601DateFormatter.string(from: Date(), timeZone: .current, formatOptions: [.withFullDate]) }

    func startTicker() {
        ticker?.cancel()
        ticker = Task { [weak self] in
            while !Task.isCancelled {
                await self?.reconcile()
                await self?.flush()
                try? await Task.sleep(for: .seconds(60))
            }
        }
    }

    var shouldListen: Bool {
        guard !isPausedForHoldToTalk, placeCheck?() == nil else { return false }
        switch mode {
        case .off: return false
        case .always: return true
        case .windows:
            let hour = Calendar.current.component(.hour, from: Date())
            return windows.contains { $0.contains(hour) }
        }
    }

    func reconcile() async {
        if shouldListen && !isListening {
            transcriber.onFinal = { [weak self] sentence in self?.capture(sentence) }
            do {
                try await transcriber.start(locale: Locale(identifier: "en-US"), continuous: true)  // ambient capture hears the learner's own language
                isListening = true; lastError = nil
            } catch {
                lastError = error.localizedDescription
            }
        } else if !shouldListen && isListening {
            await transcriber.stop()
            transcriber.onFinal = nil
            isListening = false
        }
    }

    private func capture(_ sentence: String) {
        guard sentence.split(separator: " ").count >= 2 else { return }  // skip "um", "okay"
        sentencesToday += 1
        UserDefaults.standard.set(sentencesToday, forKey: Self.todayKey)
        Task { await queue.append(UtteranceUpload(text: sentence, spokenAt: Date())) }
    }

    func flush() async {
        let api = self.api
        await queue.flush { batch in _ = try await api.upload(batch) }
    }

    /// "Forget last N minutes": removes queued text locally and stored moments on the server.
    func forget(minutes: Int) async throws -> Int {
        await queue.forget(minutes: minutes)
        return try await api.forget(minutes: minutes)
    }
}
