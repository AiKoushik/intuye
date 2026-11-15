import AppIntents
import IntuyeKit
import SwiftUI

// H5: Siri, Shortcuts, Spotlight and the Action Button. The Control Center and Lock Screen controls that run
// these live in the widget extension (IntuyeWidgets). Language names come from the learner's pack, never hardcoded.

/// "How do I say …" — answers by voice without opening the app, and keeps the word for review.
struct HowDoISayIntent: AppIntent {
    static let title: LocalizedStringResource = "How do I say…"
    static let description = IntentDescription("Hear a phrase in the language you're learning, close to how you said it.")
    static let openAppWhenRun = false

    @Parameter(title: "Phrase", requestValueDialog: "What do you want to say?")
    var phrase: String

    @Dependency var app: AppModel

    @MainActor
    func perform() async throws -> some IntentResult & ReturnsValue<String> & ProvidesDialog {
        let r = try await app.api.coach(phrase, direction: .toTarget)
        app.speaker.say(r.close, voice: app.tts)
        return .result(value: r.close, dialog: IntentDialog(stringLiteral: r.close))
    }
}

/// "What does … mean" — the other direction, into English.
struct WhatDoesItMeanIntent: AppIntent {
    static let title: LocalizedStringResource = "What does it mean?"
    static let description = IntentDescription("Get a short English meaning of something you heard.")
    static let openAppWhenRun = false

    @Parameter(title: "Phrase", requestValueDialog: "What did you hear?")
    var phrase: String

    @Dependency var app: AppModel

    @MainActor
    func perform() async throws -> some IntentResult & ReturnsValue<String> & ProvidesDialog {
        let r = try await app.api.coach(phrase, direction: .toNative)
        return .result(value: r.close, dialog: IntentDialog(stringLiteral: r.close))
    }
}

/// Opens Say and starts listening right away (good on the Action Button: press, speak, tap Done).
struct TalkNowIntent: AppIntent {
    static let title: LocalizedStringResource = "Talk to your coach"
    static let description = IntentDescription("Open Say and start listening.")
    static let openAppWhenRun = true

    @Dependency var app: AppModel

    @MainActor
    func perform() async throws -> some IntentResult {
        app.selectedTab = .say
        app.talkRequest += 1
        return .result()
    }
}

/// Starts or stops ambient capture.
struct SetCaptureIntent: AppIntent {
    static let title: LocalizedStringResource = "Capture sentences"
    static let description = IntentDescription("Turn capture on during your windows, always, or off.")
    static let openAppWhenRun = true  // the microphone needs the app in the foreground to start

    @Parameter(title: "Capture", default: .windows)
    var mode: CaptureModeEntity

    @Dependency var app: AppModel

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        app.capture.mode = mode.mode
        return .result(dialog: IntentDialog(stringLiteral: mode == .off ? "Capture is off." : "Capture is on."))
    }
}

enum CaptureModeEntity: String, AppEnum {
    case off, windows, always
    static let typeDisplayRepresentation: TypeDisplayRepresentation = "Capture"
    static let caseDisplayRepresentations: [CaptureModeEntity: DisplayRepresentation] = [
        .off: "Off", .windows: "During my windows", .always: "Always",
    ]
    @MainActor var mode: AmbientCapture.Mode { AmbientCapture.Mode(rawValue: rawValue) ?? .off }
}

/// Opens today's review.
struct ReviewWordsIntent: AppIntent {
    static let title: LocalizedStringResource = "Review my words"
    static let description = IntentDescription("Start today's review of words picked from what you said.")
    static let openAppWhenRun = true

    @Dependency var app: AppModel

    @MainActor
    func perform() async throws -> some IntentResult {
        app.reviewRequest += 1
        return .result()
    }
}

struct IntuyeShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: HowDoISayIntent(), phrases: ["How do I say something in \(.applicationName)",
                                                          "Ask \(.applicationName) how to say something"],
                    shortTitle: "How do I say…", systemImageName: "text.bubble")
        AppShortcut(intent: WhatDoesItMeanIntent(), phrases: ["What does it mean in \(.applicationName)",
                                                              "Ask \(.applicationName) what something means"],
                    shortTitle: "What does it mean?", systemImageName: "questionmark.bubble")
        AppShortcut(intent: TalkNowIntent(), phrases: ["Talk to \(.applicationName)", "Open \(.applicationName) and listen"],
                    shortTitle: "Talk now", systemImageName: "mic")
        AppShortcut(intent: SetCaptureIntent(), phrases: ["Start capture in \(.applicationName)", "\(.applicationName) capture \(\.$mode)"],
                    shortTitle: "Capture", systemImageName: "waveform")
        AppShortcut(intent: ReviewWordsIntent(), phrases: ["Review my words in \(.applicationName)"],
                    shortTitle: "Review words", systemImageName: "rectangle.stack")
    }
}
