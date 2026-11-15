import Foundation

/// Where session tokens live. The app implements this with the Keychain (ThisDeviceOnly).
public protocol TokenStore: Sendable {
    func load() -> StoredSession?
    func save(_ session: StoredSession)
    func clear()
}

public struct StoredSession: Codable, Sendable, Equatable {
    public var accessToken: String
    public var refreshToken: String
    public var accessExpiry: Date
    public init(accessToken: String, refreshToken: String, accessExpiry: Date) {
        self.accessToken = accessToken; self.refreshToken = refreshToken; self.accessExpiry = accessExpiry
    }
}

/// Adds App Attest assertion headers. Client data must match backend/app/security/app_attest.py:
/// "METHOD\nPATH?QUERY\nSHA256_HEX(body)\nUNIX_TIMESTAMP".
public protocol RequestSigner: Sendable {
    func headers(method: String, pathAndQuery: String, body: Data) async -> [String: String]
}

public struct APIError: Error, Sendable, Equatable, LocalizedError {
    public let status: Int
    public let code: String
    public let message: String
    public var errorDescription: String? { message }
    public static let offline = APIError(status: 0, code: "offline", message: "You're offline. We'll sync when you're back.")
}

private struct ErrorEnvelope: Decodable { struct Body: Decodable { let code: String; let message: String }; let error: Body }
public struct Empty: Codable, Sendable { public init() {} }

public actor APIClient {
    public let baseURL: URL
    private let urlSession: URLSession
    private let tokens: TokenStore
    private let signer: RequestSigner?
    private var refreshTask: Task<StoredSession, Error>?
    private var signedOutHandler: (@Sendable () -> Void)?

    private let encoder: JSONEncoder = { let e = JSONEncoder(); e.keyEncodingStrategy = .convertToSnakeCase; return e }()
    private let decoder: JSONDecoder = { let d = JSONDecoder(); d.keyDecodingStrategy = .convertFromSnakeCase; return d }()

    public init(baseURL: URL, tokens: TokenStore, signer: RequestSigner?, urlSession: URLSession = .shared) {
        self.baseURL = baseURL; self.tokens = tokens; self.signer = signer; self.urlSession = urlSession
    }

    public func onSignedOut(_ handler: @escaping @Sendable () -> Void) { signedOutHandler = handler }
    public var isSignedIn: Bool { tokens.load() != nil }

    // MARK: Core

    public func send<T: Decodable>(_ method: String, _ path: String, body: (any Encodable)? = nil,
                                   authorized: Bool = true, as: T.Type = T.self) async throws -> T {
        let payload = try body.map { try encoder.encode($0) } ?? Data()
        do {
            return try await perform(method, path, payload: payload, authorized: authorized)
        } catch let e as APIError where authorized && e.status == 401 && e.code == "token_expired" {
            _ = try await refreshedSession(force: true)
            return try await perform(method, path, payload: payload, authorized: authorized)
        }
    }

    private func perform<T: Decodable>(_ method: String, _ path: String, payload: Data, authorized: Bool) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else { throw APIError(status: 0, code: "bad_url", message: path) }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.timeoutInterval = 30
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if !payload.isEmpty {
            req.httpBody = payload
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if authorized {
            let session = try await refreshedSession(force: false)
            req.setValue("Bearer \(session.accessToken)", forHTTPHeaderField: "Authorization")
        }
        if let signer {
            let pathAndQuery = url.path + (url.query.map { "?\($0)" } ?? "")
            for (k, v) in await signer.headers(method: method, pathAndQuery: pathAndQuery, body: payload) {
                req.setValue(v, forHTTPHeaderField: k)
            }
        }
        let data: Data, response: URLResponse
        do { (data, response) = try await urlSession.data(for: req) } catch { throw APIError.offline }
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(status) else {
            let env = try? decoder.decode(ErrorEnvelope.self, from: data)
            let err = APIError(status: status, code: env?.error.code ?? "http_\(status)",
                               message: env?.error.message ?? "Something went wrong (\(status)).")
            if status == 401, ["invalid_refresh", "session_revoked", "refresh_reuse", "refresh_expired", "invalid_token"].contains(err.code) {
                tokens.clear(); signedOutHandler?()
            }
            throw err
        }
        if T.self == Empty.self || data.isEmpty { return Empty() as! T }  // swiftlint:disable:this force_cast
        return try decoder.decode(T.self, from: data)
    }

    /// Single-flight refresh: concurrent callers share one refresh request (rotation makes duplicates fatal).
    private func refreshedSession(force: Bool) async throws -> StoredSession {
        guard let current = tokens.load() else { throw APIError(status: 401, code: "missing_token", message: "Sign in to continue.") }
        if !force && current.accessExpiry > Date().addingTimeInterval(30) { return current }
        if let task = refreshTask { return try await task.value }
        let task = Task { () throws -> StoredSession in
            let s: SessionDTO = try await perform("POST", "/v1/auth/refresh",
                                                  payload: try encoder.encode(["refresh_token": current.refreshToken]),
                                                  authorized: false)
            let stored = StoredSession(accessToken: s.accessToken, refreshToken: s.refreshToken,
                                       accessExpiry: Date().addingTimeInterval(TimeInterval(s.expiresIn)))
            tokens.save(stored)
            return stored
        }
        refreshTask = task
        defer { refreshTask = nil }
        return try await task.value
    }

    // MARK: Auth & device

    public func attestChallenge() async throws -> String {
        struct R: Decodable { let challenge: String }
        return try await send("GET", "/v1/attest/challenge", authorized: false, as: R.self).challenge
    }

    public func attestRegister(keyId: String, attestation: String, challenge: String) async throws {
        _ = try await send("POST", "/v1/attest/register",
                           body: ["key_id": keyId, "attestation": attestation, "challenge": challenge], authorized: false, as: Empty.self)
    }

    @discardableResult
    public func signInWithApple(identityToken: String, rawNonce: String, displayName: String?) async throws -> UserDTO? {
        struct Body: Encodable { let identityToken: String; let rawNonce: String; let displayName: String? }
        let s = try await send("POST", "/v1/auth/apple", body: Body(identityToken: identityToken, rawNonce: rawNonce,
                                                                    displayName: displayName), authorized: false, as: SessionDTO.self)
        tokens.save(StoredSession(accessToken: s.accessToken, refreshToken: s.refreshToken,
                                  accessExpiry: Date().addingTimeInterval(TimeInterval(s.expiresIn))))
        return s.user
    }

    public func signOut() async {
        if let s = tokens.load() {
            _ = try? await send("POST", "/v1/auth/logout", body: ["refresh_token": s.refreshToken], authorized: false, as: Empty.self)
        }
        tokens.clear()
    }

    public func me() async throws -> MeDTO { try await send("GET", "/v1/me") }
    public func updateSettings(_ patch: [String: String]) async throws -> SettingsDTO { try await send("PATCH", "/v1/me/settings", body: patch) }
    public func updateLevel(_ level: Int) async throws -> SettingsDTO { try await send("PATCH", "/v1/me/settings", body: ["level": level]) }
    /// Raw JSON of everything stored about the user, for the share sheet.
    public func exportAccount() async throws -> Data {
        guard let url = URL(string: "/v1/account/export", relativeTo: baseURL) else { throw APIError.offline }
        var req = URLRequest(url: url)
        let session = try await refreshedSession(force: false)
        req.setValue("Bearer \(session.accessToken)", forHTTPHeaderField: "Authorization")
        if let signer {
            for (k, v) in await signer.headers(method: "GET", pathAndQuery: url.path, body: Data()) { req.setValue(v, forHTTPHeaderField: k) }
        }
        return try await urlSession.data(for: req).0
    }
    public func deleteAccount() async throws {
        _ = try await send("DELETE", "/v1/account", as: Empty.self)
        tokens.clear()
    }

    // MARK: Features

    public func coach(_ text: String, direction: CoachDirection = .auto) async throws -> CoachResult {
        try await send("POST", "/v1/coach", body: CoachRequest(text: text, direction: direction))
    }
    public func upload(_ items: [UtteranceUpload]) async throws -> IngestResult {
        try await send("POST", "/v1/utterances", body: UtteranceBatch(items: items))
    }
    public func moments(day: String? = nil) async throws -> MomentsDTO {
        try await send("GET", "/v1/utterances" + (day.map { "?day=\($0)" } ?? ""))
    }
    public func forget(minutes: Int) async throws -> Int {
        struct R: Decodable { let deleted: Int }
        return try await send("POST", "/v1/utterances/forget", body: ["minutes": minutes], as: R.self).deleted
    }
    public func nextBatch(size: Int = 7) async throws -> BatchDTO { try await send("POST", "/v1/batches/next", body: ["size": size]) }
    public func dueCards() async throws -> [DueCard] { try await send("GET", "/v1/reviews/due", as: DueDTO.self).items }
    public func review(_ lexemeId: String, _ rating: Rating) async throws -> ReviewResult {
        try await send("POST", "/v1/reviews", body: ReviewRequest(lexemeId: lexemeId, rating: rating.rawValue))
    }
    public func replay(_ r: PendingReview) async throws -> ReviewResult {
        try await send("POST", "/v1/reviews", body: ReviewRequest(lexemeId: r.lexemeId, rating: r.rating, reviewedAt: r.reviewedAt))
    }
    /// What to notify about in the next week, already inside the learner's budget and quiet hours.
    public func notificationPlan(timeZone: String = TimeZone.current.identifier, days: Int = 7) async throws -> NotificationPlan {
        let tz = timeZone.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "UTC"
        return try await send("GET", "/v1/notifications/plan?days=\(days)&tz=\(tz)")
    }
    public func pronunciation(_ lexemeId: String, expected: String, heard: String) async throws -> PronunciationResult {
        try await send("POST", "/v1/pronunciation", body: PronunciationRequest(lexemeId: lexemeId, expected: expected, heard: heard))
    }
    public func scenarios() async throws -> ScenarioList { try await send("GET", "/v1/scenarios") }
    public func scenario(_ id: String) async throws -> ScenarioDTO { try await send("GET", "/v1/scenarios/\(id)") }
    public func createScenario(_ s: NewScenario) async throws -> ScenarioDTO { try await send("POST", "/v1/scenarios", body: s) }
    public func importCalendar(_ events: [CalendarEventUpload]) async throws -> [ScenarioDTO] {
        try await send("POST", "/v1/scenarios/calendar", body: CalendarUpload(events: events), as: CalendarResult.self).created
    }
    /// Library search by meaning, in the learner's language variety. An empty query lists the most-used scenes.
    public func library(_ query: String = "", limit: Int = 8) async throws -> [LibraryCard] {
        var allowed = CharacterSet.alphanumerics; allowed.insert(charactersIn: "-._~")
        let q = query.addingPercentEncoding(withAllowedCharacters: allowed) ?? ""
        return try await send("GET", "/v1/library?q=\(q)&limit=\(limit)", as: LibrarySearchResult.self).results
    }
    public func libraryScene(_ id: String) async throws -> LibraryScene { try await send("GET", "/v1/library/\(id)") }
    public func useLibraryScene(_ id: String, startsAt: Date? = nil, kind: String = "manual") async throws -> ScenarioDTO {
        try await send("POST", "/v1/library/\(id)/use", body: UseLibrarySceneRequest(startsAt: startsAt.map(LCDate.string), kind: kind))
    }
    public func reportLibraryScene(_ id: String, reason: LibraryReportReason) async throws {
        struct R: Decodable { let ok: Bool }
        _ = try await send("POST", "/v1/library/\(id)/report", body: ["reason": reason.rawValue], as: R.self)
    }
    /// Phoneme-level comparison of what you were asked to say with what recognition heard.
    public func practiceCompare(expected: String, heard: String) async throws -> PracticeResult {
        try await send("POST", "/v1/practice/compare", body: ["expected": expected, "heard": heard])
    }
    public func setScenarioStatus(_ id: String, _ status: String) async throws -> ScenarioDTO {
        try await send("PATCH", "/v1/scenarios/\(id)", body: ["status": status])
    }
    public func rate(_ id: String, value: Int, phase: String) async throws -> Readiness {
        try await send("POST", "/v1/scenarios/\(id)/readiness", body: ReadinessRequest(value: value, phase: phase))
    }
    public func startRehearsal(scenarioId: String, difficulty: String) async throws -> RehearsalStart {
        try await send("POST", "/v1/rehearsals", body: ["scenario_id": scenarioId, "difficulty": difficulty])
    }
    public func rehearsalTurn(_ id: String, text: String) async throws -> RehearsalTurnResult {
        try await send("POST", "/v1/rehearsals/\(id)/turns", body: ["text": text])
    }
    public func endRehearsal(_ id: String) async throws -> RehearsalEnd { try await send("POST", "/v1/rehearsals/\(id)/end") }
    public func progress() async throws -> ProgressDTO { try await send("GET", "/v1/progress") }
    public func languages() async throws -> LanguageCatalog { try await send("GET", "/v1/languages", authorized: false) }
    public func lessons() async throws -> [LessonSummary] { (try await send("GET", "/v1/lessons") as LessonsDTO).lessons }
    public func lesson(_ id: String) async throws -> Lesson { try await send("GET", "/v1/lessons/\(id)") }
    public func today() async throws -> TodayDTO { try await send("GET", "/v1/today") }
}
