import IntuyeKit
import SwiftUI

/// Saved sentences, kept on device (H9). Server sync can come later.
@MainActor
@Observable
final class Phrasebook {
    static let shared = Phrasebook()
    struct Entry: Codable, Identifiable, Hashable { let id: String; let source: String; let spanish: String; let english: String; let saved: Date }

    private(set) var entries: [Entry] = []
    private let url = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("phrasebook.json")

    private init() { entries = (try? JSONDecoder().decode([Entry].self, from: Data(contentsOf: url))) ?? [] }

    func contains(_ r: CoachResult) -> Bool { entries.contains { $0.id == r.id } }

    func toggle(_ r: CoachResult) {
        if let i = entries.firstIndex(where: { $0.id == r.id }) {
            entries.remove(at: i)
        } else {
            let spanish = r.intent == .toEs ? r.close : r.source
            let english = r.intent == .toEs ? r.source : r.close
            entries.insert(Entry(id: r.id, source: r.source, spanish: spanish, english: english, saved: Date()), at: 0)
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
            ForEach(book.entries.filter { query.isEmpty || $0.spanish.localizedCaseInsensitiveContains(query) || $0.english.localizedCaseInsensitiveContains(query) }) { e in
                Button { app.speaker.say(e.spanish, dialect: app.dialect) } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(e.spanish).font(.lcSpanishBody).foregroundStyle(LC.Color.textPrimary)
                        Text(e.english).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                    }
                }
            }
        }
        .searchable(text: $query)
        .navigationTitle("Phrasebook")
    }
}
