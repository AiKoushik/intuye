import IntuyeKit
import SwiftUI

/// Moments (H8): one day of what you said and what capture heard, grouped by hour.
/// Swipe to delete a line; "Forget last 10 minutes" removes recent ones here and on the server.
struct MomentsView: View {
    @Environment(AppModel.self) private var app
    @State private var day = Date()
    @State private var items: [Moment] = []
    @State private var loading = true
    @State private var note: String?
    @State private var error: String?

    private var isToday: Bool { Calendar.current.isDateInToday(day) }

    var body: some View {
        List {
            Section { dayNavigation }
            if let error { Section { ErrorBanner(message: error) { Task { await load() } } } }
            if loading && items.isEmpty {
                Section { ProgressView().frame(maxWidth: .infinity) }
            } else if items.isEmpty {
                Section {
                    Text(isToday ? "Nothing yet today. Say something on the Say tab, or turn on capture." : "Nothing was captured on this day.")
                        .font(.lcBody).foregroundStyle(LC.Color.textSecondary)
                }
            }
            ForEach(groups, id: \.hour) { group in
                Section(group.hour) {
                    ForEach(group.items) { m in row(m) }
                        .onDelete { offsets in Task { await delete(offsets.map { group.items[$0] }) } }
                }
            }
            if !items.isEmpty {
                Section {
                    if isToday {
                        Button("Forget last 10 minutes", role: .destructive) { Task { await forget() } }
                    }
                } footer: {
                    Text("\(items.count) \(items.count == 1 ? "sentence" : "sentences"). Sentences are deleted after your retention period in Settings."
                         + (note.map { " \($0)" } ?? ""))
                }
            }
        }
        .lcGroupedBackground()
        .navigationTitle("Moments")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await load() }
        .task(id: day) { await load() }
        .sensoryFeedback(.success, trigger: note)
    }

    private var dayNavigation: some View {
        HStack {
            Button { shift(-1) } label: { Image(systemName: "chevron.left") }.accessibilityLabel("Previous day")
            Spacer()
            VStack(spacing: 1) {
                Text(isToday ? "Today" : day.formatted(.relative(presentation: .named)).capitalized).font(.lcHeadline)
                Text(day.formatted(.dateTime.weekday(.wide).day().month(.wide))).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
            Spacer()
            Button { shift(1) } label: { Image(systemName: "chevron.right") }.disabled(isToday).accessibilityLabel("Next day")
        }
        .buttonStyle(.borderless)
    }

    private struct HourGroup { let hour: String; let items: [Moment] }

    private var groups: [HourGroup] {
        var order: [String] = []
        var byHour: [String: [Moment]] = [:]
        for m in items {
            let d = LCDate.parse(m.spokenAt)
            let key = d.map { String(format: "%02d:00", Calendar.current.component(.hour, from: $0)) } ?? "—"
            if byHour[key] == nil { order.append(key) }
            byHour[key, default: []].append(m)
        }
        return order.map { HourGroup(hour: $0, items: byHour[$0] ?? []) }
    }

    private func row(_ m: Moment) -> some View {
        let (tint, label): (Tint, String) = switch m.source {
        case "ambient": (.sand, "Heard")
        case "say": (.sea, "You said")
        case "rehearsal": (.sage, "Rehearsal")
        default: (.plum, m.source)
        }
        return VStack(alignment: .leading, spacing: Space.xs) {
            HStack(spacing: Space.s) {
                TintChip(tint: tint, text: label)
                if let d = LCDate.parse(m.spokenAt) {
                    Text(d.formatted(date: .omitted, time: .shortened)).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                }
            }
            Text(m.text).font(.lcSource).foregroundStyle(LC.Color.textSecondary)
            if let t = m.closeTarget {
                Button { app.speaker.say(t, voice: app.tts) } label: {
                    Text(t).font(.lcTarget).foregroundStyle(LC.Color.textPrimary).multilineTextAlignment(.leading)
                }
                .buttonStyle(.plain)
                .accessibilityHint("Plays the \(app.lang.name)")
            }
        }
        .padding(.vertical, 2)
    }

    private func shift(_ days: Int) {
        guard let d = Calendar.current.date(byAdding: .day, value: days, to: day), d <= .now else { return }
        day = d; items = []; note = nil
    }

    private func load() async {
        loading = true; defer { loading = false }
        var utc = Calendar(identifier: .gregorian); utc.timeZone = TimeZone(identifier: "UTC")!
        let c = utc.dateComponents([.year, .month, .day], from: day)
        let iso = String(format: "%04d-%02d-%02d", c.year ?? 0, c.month ?? 0, c.day ?? 0)
        do { items = try await app.api.moments(day: iso).items; error = nil } catch { self.error = error.localizedDescription }
    }

    private func delete(_ moments: [Moment]) async {
        do {
            for m in moments { try await app.api.deleteMoment(m.id) }
            items.removeAll { m in moments.contains { $0.id == m.id } }
            note = "Deleted."
        } catch { self.error = error.localizedDescription }
    }

    private func forget() async {
        do {
            let n = try await app.capture.forget(minutes: 10)  // the local queue and the server
            note = n == 1 ? "Forgot 1 sentence." : "Forgot \(n) sentences."
            await load()
        } catch { self.error = error.localizedDescription }
    }
}
