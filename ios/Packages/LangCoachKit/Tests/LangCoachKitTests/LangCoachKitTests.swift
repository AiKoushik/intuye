import XCTest
@testable import LangCoachKit

final class LangCoachKitTests: XCTestCase {
    func testDecodesCoachResultFromSnakeCase() throws {
        let json = """
        {"intent":"to_es","source":"me gusta escuchar este en mi mind","close":"Me gusta escuchar esto en mi mente.",
         "natural":null,"alignment":[{"src":"mind","tgt":"mente","new":true}],"answer":null,"utterance_id":"u1"}
        """.data(using: .utf8)!
        let d = JSONDecoder(); d.keyDecodingStrategy = .convertFromSnakeCase
        let r = try d.decode(CoachResult.self, from: json)
        XCTAssertEqual(r.intent, .toEs)
        XCTAssertEqual(r.alignment.first?.tgt, "mente")
        XCTAssertEqual(r.utteranceId, "u1")
    }

    func testParsesPythonIsoformatDates() {
        XCTAssertNotNil(LCDate.parse("2026-11-10T10:00:00.123456+00:00"))
        XCTAssertNotNil(LCDate.parse("2026-11-10T10:00:00Z"))
    }

    func testOfflineQueueForgetsRecentItems() async throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let q = OfflineQueue(fileURL: url)
        await q.append(UtteranceUpload(text: "old", spokenAt: Date().addingTimeInterval(-3600)))
        await q.append(UtteranceUpload(text: "new", spokenAt: Date()))
        await q.forget(minutes: 10)
        let remaining = await q.count
        XCTAssertEqual(remaining, 1)
    }
}
