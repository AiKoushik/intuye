import AVFoundation
import Foundation
import Speech

enum CaptureError: LocalizedError {
    case micDenied, noAudioFormat, unsupportedLocale
    var errorDescription: String? {
        switch self {
        case .micDenied: "Microphone access is off. Turn it on in Settings to talk to your coach."
        case .noAudioFormat: "This iPhone can't transcribe right now. Try typing instead."
        case .unsupportedLocale: "On-device speech isn't available for this language yet."
        }
    }
}

/// On-device transcription with SpeechAnalyzer + SpeechTranscriber (iOS 26). Audio never leaves the phone.
/// Used for hold-to-talk (Say, Review, Rehearse) and, continuously, by AmbientCapture.
@MainActor
@Observable
final class LiveTranscriber {
    private(set) var text = ""
    private(set) var isRunning = false
    private(set) var level: Float = 0

    /// Called for each finalised segment (ambient capture turns these into moments).
    var onFinal: ((String) -> Void)?

    private let engine = AVAudioEngine()
    private var analyzer: SpeechAnalyzer?
    private var input: AsyncStream<AnalyzerInput>.Continuation?
    private var resultsTask: Task<Void, Never>?
    private var finalized = ""

    func start(locale: Locale, continuous: Bool = false) async throws {
        guard !isRunning else { return }
        guard await AVAudioApplication.requestRecordPermission() else { throw CaptureError.micDenied }
        guard let supported = await SpeechTranscriber.supportedLocale(equivalentTo: locale) else { throw CaptureError.unsupportedLocale }

        let transcriber = SpeechTranscriber(locale: supported, transcriptionOptions: [],
                                            reportingOptions: [.volatileResults], attributeOptions: [])
        if let request = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
            try await request.downloadAndInstall()
        }
        guard let format = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [transcriber]) else {
            throw CaptureError.noAudioFormat
        }
        let analyzer = SpeechAnalyzer(modules: [transcriber])
        let (stream, continuation) = AsyncStream<AnalyzerInput>.makeStream()

        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: continuous ? .default : .spokenAudio, options: [.duckOthers, .defaultToSpeaker])
        try session.setActive(true)

        let node = engine.inputNode
        let inputFormat = node.outputFormat(forBus: 0)
        guard let converter = AVAudioConverter(from: inputFormat, to: format) else { throw CaptureError.noAudioFormat }
        node.installTap(onBus: 0, bufferSize: 4096, format: inputFormat,
                        block: Self.makeTap(converter: converter, outFormat: format, continuation: continuation) { [weak self] level in
                            Task { @MainActor in self?.level = level }
                        })
        engine.prepare()
        try engine.start()
        try await analyzer.start(inputSequence: stream)

        self.analyzer = analyzer
        self.input = continuation
        text = ""; finalized = ""; isRunning = true

        resultsTask = Task { [weak self] in
            do {
                for try await result in transcriber.results {
                    guard let self else { return }
                    let chunk = String(result.text.characters)
                    if result.isFinal {
                        self.finalized += chunk
                        self.text = self.finalized
                        let trimmed = chunk.trimmingCharacters(in: .whitespacesAndNewlines)
                        if !trimmed.isEmpty { self.onFinal?(trimmed) }
                    } else {
                        self.text = self.finalized + chunk
                    }
                }
            } catch {
                // Analyzer finished or failed; whatever was transcribed so far is kept.
            }
        }
    }

    /// Stops listening and returns everything transcribed in this session.
    @discardableResult
    func stop() async -> String {
        guard isRunning else { return text }
        engine.stop()
        engine.inputNode.removeTap(onBus: 0)
        input?.finish()
        try? await analyzer?.finalizeAndFinishThroughEndOfInput()
        await resultsTask?.value
        analyzer = nil; input = nil; resultsTask = nil
        isRunning = false; level = 0
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        return text.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Built outside the main actor: the tap runs on the audio thread.
    nonisolated private static func makeTap(converter: AVAudioConverter, outFormat: AVAudioFormat,
                                            continuation: AsyncStream<AnalyzerInput>.Continuation,
                                            level: @escaping @Sendable (Float) -> Void) -> AVAudioNodeTapBlock {
        { buffer, _ in
            if let data = buffer.floatChannelData?[0] {
                let n = Int(buffer.frameLength)
                var sum: Float = 0
                for i in 0..<n { sum += data[i] * data[i] }
                level(min(1, sqrt(sum / Float(max(n, 1))) * 8))
            }
            let ratio = outFormat.sampleRate / buffer.format.sampleRate
            let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 1
            guard let out = AVAudioPCMBuffer(pcmFormat: outFormat, frameCapacity: capacity) else { return }
            var consumed = false
            var error: NSError?
            converter.convert(to: out, error: &error) { _, status in
                if consumed { status.pointee = .noDataNow; return nil }
                consumed = true
                status.pointee = .haveData
                return buffer
            }
            if error == nil, out.frameLength > 0 { continuation.yield(AnalyzerInput(buffer: out)) }
        }
    }
}
