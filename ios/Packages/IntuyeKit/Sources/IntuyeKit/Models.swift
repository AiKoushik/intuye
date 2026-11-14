import Foundation

// DTOs mirroring backend/app/routers/*. Keys are snake_case on the wire (see APIClient coders).
// Dates stay as ISO-8601 strings on the wire and are parsed lazily with `LCDate.parse`.

public struct UserDTO: Codable, Hashable, Sendable {
    public let id: String
    public let displayName: String?
}

public struct SessionDTO: Codable, Sendable {
    public let accessToken: String
    public let refreshToken: String
    public let expiresIn: Int
    public let user: UserDTO?
}

public struct SettingsDTO: Codable, Hashable, Sendable {
    public var dialect: String
    public var level: Int
    public var dailyNotificationBudget: Int
    public var quietStart: String
    public var quietEnd: String
    public var momentRetentionDays: Int
    public var timezone: String
}

public struct MeDTO: Codable, Sendable {
    public let user: UserDTO
    public let settings: SettingsDTO
}

// MARK: Say it my way

public enum CoachDirection: String, Codable, Sendable { case auto, toEs = "to_es", toEn = "to_en" }
public enum CoachIntent: String, Codable, Sendable { case toEs = "to_es", toEn = "to_en", ask }

public struct AlignedPair: Codable, Hashable, Sendable, Identifiable {
    public let src: String
    public let tgt: String
    public let new: Bool
    public var id: String { src + "→" + tgt }
    public init(src: String, tgt: String, new: Bool) { self.src = src; self.tgt = tgt; self.new = new }
}

public struct CoachRequest: Codable, Sendable {
    public let text: String
    public let direction: CoachDirection
    public init(text: String, direction: CoachDirection = .auto) { self.text = text; self.direction = direction }
}

public struct CoachResult: Codable, Hashable, Sendable, Identifiable {
    public let intent: CoachIntent
    public let source: String
    public let close: String
    public let natural: String?
    public let alignment: [AlignedPair]
    public let answer: String?
    public let utteranceId: String?
    public var id: String { utteranceId ?? (source + close + (answer ?? "")) }
}

// MARK: Capture

public struct UtteranceUpload: Codable, Sendable, Hashable {
    public let text: String
    public let spokenAt: String
    public let source: String
    public init(text: String, spokenAt: Date, source: String = "ambient") {
        self.text = text; self.spokenAt = LCDate.string(spokenAt); self.source = source
    }
}

public struct UtteranceBatch: Codable, Sendable { public let items: [UtteranceUpload] }

public struct IngestResult: Codable, Sendable {
    public let accepted: Int
    public let lexemesTouched: Int
    public let suggestedScenarios: [SuggestedScenario]
}

public struct SuggestedScenario: Codable, Sendable, Hashable { public let id: String; public let title: String; public let topic: String }

public struct Moment: Codable, Sendable, Hashable, Identifiable {
    public let id: String
    public let text: String
    public let closeEs: String?
    public let topic: String?
    public let source: String
    public let spokenAt: String
}

public struct MomentsDTO: Codable, Sendable { public let day: String; public let items: [Moment] }

// MARK: Words

public struct BatchItemDTO: Codable, Sendable, Hashable, Identifiable {
    public let lexemeId: String
    public let es: String
    public let en: String
    public let reason: String
    public let reasonKind: String
    public let context: String?
    public var id: String { lexemeId }
}

public struct BatchDTO: Codable, Sendable { public let batchId: String; public let items: [BatchItemDTO] }

public struct DueCard: Codable, Sendable, Hashable, Identifiable {
    public let lexemeId: String
    public let es: String
    public let en: String
    public let context: String?
    public let state: String
    public let reason: String?
    public let reasonKind: String?
    public var id: String { lexemeId }
}

public struct DueDTO: Codable, Sendable { public let items: [DueCard] }

public enum Rating: Int, Codable, Sendable, CaseIterable { case forgot = 1, hard, gotIt, easy }

public struct ReviewRequest: Codable, Sendable { public let lexemeId: String; public let rating: Int }
public struct ReviewResult: Codable, Sendable { public let dueAt: String?; public let scheduledDays: Double; public let state: String }

public struct PronunciationRequest: Codable, Sendable { public let lexemeId: String; public let expected: String; public let heard: String }
public struct PronunciationResult: Codable, Sendable { public let score: Double; public let ok: Bool }

// MARK: Scenarios & rehearsal

public struct PhraseDTO: Codable, Sendable, Hashable, Identifiable {
    public let id: String
    public let en: String
    public let es: String
    public let alignment: [PhrasePair]
}

public struct PhrasePair: Codable, Sendable, Hashable { public let src: String; public let tgt: String }

public struct Readiness: Codable, Sendable, Hashable { public let before: Int?; public let after: Int?; public let current: Int? }

public struct PhraseGroups: Codable, Sendable, Hashable { public let key: [PhraseDTO]; public let rescue: [PhraseDTO]; public let hear: [PhraseDTO] }

public struct ScenarioDTO: Codable, Sendable, Hashable, Identifiable {
    public let id: String
    public let title: String
    public let details: String?
    public let kind: String
    public let topic: String?
    public let status: String
    public let startsAt: String?
    public let readiness: Readiness
    public let phrases: PhraseGroups?
    public let templateId: String?
    /// Only on create: what happened to the scene in the shared library.
    public let library: LibraryShareResult?
}

public struct ScenarioList: Codable, Sendable { public let upcoming: [ScenarioDTO]; public let recurring: [ScenarioDTO]; public let mine: [ScenarioDTO] }

public struct NewScenario: Codable, Sendable {
    public let title: String
    public let details: String?
    public let startsAt: String?
    public let kind: String
    public let share: Bool
    public let credit: String  // anonymous | name
    public init(title: String, details: String? = nil, startsAt: Date?, kind: String = "manual", share: Bool = true, showName: Bool = false) {
        self.title = title; self.details = details; self.startsAt = startsAt.map(LCDate.string); self.kind = kind
        self.share = share; self.credit = share && showName ? "name" : "anonymous"
    }
}

// MARK: Scene library

public struct LibraryCard: Codable, Sendable, Hashable, Identifiable {
    public let id: String
    public let title: String
    public let situation: String
    public let topic: String?
    public let uses: Int
    public let credit: String?
    public let similarity: Double?
}

public struct LibrarySearchResult: Codable, Sendable { public let results: [LibraryCard] }

public struct LibraryPhrase: Codable, Sendable, Hashable {
    public let en: String
    public let es: String
    public let alignment: [PhrasePair]?
}

public struct LibraryPhrases: Codable, Sendable, Hashable {
    public let key: [LibraryPhrase]; public let rescue: [LibraryPhrase]; public let hear: [LibraryPhrase]
}

public struct LibraryScene: Codable, Sendable, Hashable, Identifiable {
    public let id: String
    public let title: String
    public let situation: String
    public let topic: String?
    public let uses: Int
    public let credit: String?
    public let level: Int
    public let phrases: LibraryPhrases
}

public struct LibraryShareResult: Codable, Sendable, Hashable {
    public let status: String  // shared | already_in_library | private
    public let template: LibraryCard?
    public let credit: String?
    public let reason: String?

    /// One line for the learner after building a scene.
    public var message: String {
        switch status {
        case "shared": return credit == "name" ? "Added to the library with your name" : "Added to the library, anonymously"
        case "already_in_library": return "Already in the library as “\(template?.title ?? "a similar scene")”"
        default: return reason == "personal" ? "Kept private: it's personal to you" : "Scene ready"
        }
    }
}

public struct UseLibrarySceneRequest: Codable, Sendable { public let startsAt: String?; public let kind: String }
public enum LibraryReportReason: String, Codable, Sendable, CaseIterable {
    case personal, offensive, wrong, other
    public var label: String {
        switch self {
        case .personal: "It has someone's personal details"
        case .offensive: "It's offensive or unsafe"
        case .wrong: "The Spanish is wrong"
        case .other: "Something else"
        }
    }
}

public struct CalendarEventUpload: Codable, Sendable { public let title: String; public let startsAt: String
    public init(title: String, startsAt: Date) { self.title = title; self.startsAt = LCDate.string(startsAt) } }
public struct CalendarUpload: Codable, Sendable { public let events: [CalendarEventUpload] }
public struct CalendarResult: Codable, Sendable { public let created: [ScenarioDTO] }

public struct ReadinessRequest: Codable, Sendable { public let value: Int; public let phase: String }

public struct CoachLine: Codable, Sendable, Hashable { public let es: String; public let en: String }
public struct RehearsalStart: Codable, Sendable { public let rehearsalId: String; public let coach: CoachLine }
public struct RehearsalTurnResult: Codable, Sendable { public let native: String?; public let coach: CoachLine; public let done: Bool }
public struct KeepPhrase: Codable, Sendable, Hashable { public let en: String; public let es: String }
public struct RehearsalEnd: Codable, Sendable { public let summary: String; public let keepPhrases: [KeepPhrase] }

// MARK: Progress & today

public struct WeekRatio: Codable, Sendable, Hashable { public let week: String; public let ratio: Double; public let sentences: Int }
public struct ConfidenceRow: Codable, Sendable, Hashable { public let scenarioId: String; public let title: String; public let before: Int?; public let after: Int? }
public struct WordStats: Codable, Sendable, Hashable { public let met: Int; public let kept: Int; public let due: Int }
public struct ProgressDTO: Codable, Sendable { public let spanglishRatio: [WeekRatio]; public let confidence: [ConfidenceRow]; public let words: WordStats }

public struct PreviewWord: Codable, Sendable, Hashable { public let es: String; public let origin: String? }
public struct WordsReady: Codable, Sendable, Hashable { public let count: Int; public let preview: [String]; public let previewItems: [PreviewWord]? }
public struct RecentSentence: Codable, Sendable, Hashable, Identifiable { public let id: String; public let text: String; public let closeEs: String?; public let spokenAt: String }
public struct TodayDTO: Codable, Sendable {
    public let nextScenario: ScenarioDTO?
    public let suggestedScenarios: Int
    public let wordsReady: WordsReady
    public let recent: [RecentSentence]
}

// MARK: Dates

public enum LCDate {
    private static let withFraction: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]; return f
    }()
    private static let plain: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime]; return f
    }()

    public static func string(_ date: Date) -> String { plain.string(from: date) }

    /// Accepts Python's isoformat (microseconds, +00:00) as well as plain RFC 3339.
    public static func parse(_ s: String?) -> Date? {
        guard var s else { return nil }
        if let d = plain.date(from: s) ?? withFraction.date(from: s) { return d }
        if let dot = s.firstIndex(of: "."),
           let tz = s[dot...].firstIndex(where: { $0 == "+" || $0 == "-" || $0 == "Z" }) {
            let digits = s[s.index(after: dot)..<tz]
            s.replaceSubrange(s.index(after: dot)..<tz, with: String(digits.prefix(3)).padding(toLength: 3, withPad: "0", startingAt: 0))
            return withFraction.date(from: s)
        }
        return nil
    }
}

// MARK: Practice (rescue drill, shadowing, pronunciation)

public struct PracticePhoneme: Codable, Sendable, Hashable { public let p: String; public let ok: Bool; public let heard: String? }
public struct PracticeWord: Codable, Sendable, Hashable {
    public let word: String
    public let heard: String?
    public let ok: Bool
    public let phonemes: [PracticePhoneme]
}
public struct PracticeResult: Codable, Sendable, Hashable {
    public let score: Double
    public let ok: Bool
    public let words: [PracticeWord]
    public let tips: [String]
}
