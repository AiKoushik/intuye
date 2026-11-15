import IntuyeKit
import SwiftUI

/// Saved sentences, kept on device (H9). Server sync can come later.
@MainActor
@Observable
final class Phrasebook {
    static let shared = Phrasebook()
    struct Entry: Codable, Identifiable, Hashable {
        let id: String; let source: String; let target: String; let english: String; let saved: Date
        init(id: String, source: String, target: String, english: String, saved: Date) {
            self.id = id; self.source = source; self.target = target; self.english = english; self.saved = saved
        }
        private enum CodingKeys: String, CodingKey { case id, source, target, spanish, english, saved }
        // Entries saved before language packs stored the target text under "spanish".
        init(from d: Decoder) throws {
            let c = try d.container(keyedBy: CodingKeys.self)
            id = try c.decode(String.self, forKey: .id); source = try c.decode(String.self, forKey: .source)
            target = try c.decodeIfPresent(String.self, forKey: .target) ?? c.decode(String.self, forKey: .spanish)
            english = try c.decode(String.self, forKey: .english); saved = try c.decode(Date.self, forKey: .saved)
        }
        func encode(to e: Encoder) throws {
            var c = e.container(keyedBy: CodingKeys.self)
            try c.encode(id, forKey: .id); try c.encode(source, forKey: .source); try c.encode(target, forKey: .target)
            try c.encode(english, forKey: .english); try c.encode(saved, forKey: .saved)
        }
    }

    private(set) var entries: [Entry] = []
    private let url = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("phrasebook.json")

    private init() { entries = (try? JSONDecoder().decode([Entry].self, from: Data(contentsOf: url))) ?? [] }

    func contains(_ r: CoachResult) -> Bool { entries.contains { $0.id == r.id } }

    func toggle(_ r: CoachResult) {
        if let i = entries.firstIndex(where: { $0.id == r.id }) {
            entries.remove(at: i)
        } else {
            let target = r.intent == .toTarget ? r.close : r.source
            let english = r.intent == .toTarget ? r.source : r.close
            entries.insert(Entry(id: r.id, source: r.source, target: target, english: english, saved: Date()), at: 0)
        }
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? JSONEncoder().encode(entries).write(to: url, options: .atomic)
    }
}

struct PhrasebookView: View {
    @Environment(AppModel.self) private var app
    @State private var query = ""
    private var book: Phrasebook { .shared }

    var body: some View {
        List {
            if book.entries.isEmpty {
                Text("Tap the star on any result to keep it here.").foregroundStyle(LC.Color.textSecondary)
            }
            ForEach(book.entries.filter { query.isEmpty || $0.target.localizedCaseInsensitiveContains(query) || $0.english.localizedCaseInsensitiveContains(query) }) { e in
                Button { app.speaker.say(e.target, voice: app.tts) } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(e.target).font(.lcTargetBody).foregroundStyle(LC.Color.textPrimary)
                        Text(e.english).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                    }
                }
            }
        }
        .searchable(text: $query)
        .navigationTitle("Phrasebook")
    }
}
