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

    func testDecodesSceneWithLibraryResult() throws {
        let json = """
        {"id":"s1","title":"At the dentist's","details":null,"kind":"manual","topic":"health","status":"active","starts_at":null,
         "template_id":"t1","readiness":{"before":null,"after":null,"current":null},"phrases":null,
         "library":{"status":"already_in_library","template":{"id":"t1","title":"At the dentist","situation":"A check-up.",
                    "topic":"health","uses":4,"credit":null}}}
        """.data(using: .utf8)!
        let d = JSONDecoder(); d.keyDecodingStrategy = .convertFromSnakeCase
        let s = try d.decode(ScenarioDTO.self, from: json)
        XCTAssertEqual(s.templateId, "t1")
        XCTAssertEqual(s.library?.message, "Already in the library as “At the dentist”")
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
