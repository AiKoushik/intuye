import Foundation

/// The target languages this server offers (GET /v1/languages). Screens never name a language or a variety
/// themselves: they read the learner's pack from here, so a new language needs no app change.
public struct VarietyInfo: Codable, Sendable, Hashable, Identifiable {
    public let code: String    // stored as the learner's `dialect`, e.g. "es-419"
    public let label: String   // "Latin America"
    public let tts: String     // AVSpeechSynthesisVoice language
    public let stt: String     // SFSpeechRecognizer locale
    public var id: String { code }
}

public struct ExamplePair: Codable, Sendable, Hashable { public let src: String; public let tgt: String; public let new: Bool? }

public struct LanguageUI: Codable, Sendable, Hashable {
    public let varietyNote: String?
    public let example: [ExamplePair]?
    public let trySaying: [String]?
    public var examplePairs: [AlignedPair] { (example ?? []).map { AlignedPair(src: $0.src, tgt: $0.tgt, new: $0.new ?? false) } }
}

public struct LanguageInfo: Codable, Sendable, Hashable, Identifiable {
    public let code: String
    public let name: String         // English name, used in copy ("English in your Spanish")
    public let nativeName: String
    public let defaultVariety: String
    public let varieties: [VarietyInfo]
    public let ui: LanguageUI?
    public var id: String { code }

    /// Before the server has ever answered. Nothing language-specific.
    public static let unknown = LanguageInfo(code: "", name: "your new language", nativeName: "", defaultVariety: "",
                                             varieties: [VarietyInfo(code: "", label: "", tts: "", stt: "")], ui: nil)
}

public struct LanguageCatalog: Codable, Sendable, Hashable {
    public let `default`: String
    public let languages: [LanguageInfo]

    public init(default: String, languages: [LanguageInfo]) { self.default = `default`; self.languages = languages }

    /// The pack for a variety code ("es-419" -> Spanish), or the server's default language.
    public func language(forVariety code: String?) -> LanguageInfo {
        let prefix = (code ?? "").split(separator: "-").first.map(String.init) ?? ""
        return languages.first { $0.code == prefix } ?? languages.first { $0.code == self.default } ?? languages.first ?? .unknown
    }

    public func variety(_ code: String?) -> VarietyInfo {
        let lang = language(forVariety: code)
        return lang.varieties.first { $0.code == code } ?? lang.varieties.first { $0.code == lang.defaultVariety }
            ?? LanguageInfo.unknown.varieties[0]
    }

    // Cached so the app knows its language offline.
    private static let key = "intuye.languages"
    public static func cached() -> LanguageCatalog? {
        UserDefaults.standard.data(forKey: key).flatMap { try? JSONDecoder.snake.decode(LanguageCatalog.self, from: $0) }
    }
    public func cache() {
        if let data = try? JSONEncoder.snake.encode(self) { UserDefaults.standard.set(data, forKey: Self.key) }
    }
}

extension JSONDecoder {
    static var snake: JSONDecoder { let d = JSONDecoder(); d.keyDecodingStrategy = .convertFromSnakeCase; return d }
}

extension JSONEncoder {
    static var snake: JSONEncoder { let e = JSONEncoder(); e.keyEncodingStrategy = .convertToSnakeCase; return e }
}
