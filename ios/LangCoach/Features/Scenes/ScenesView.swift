import LangCoachKit
import SwiftUI

struct ScenesView: View {
    @Environment(AppModel.self) private var app
    @State private var list: ScenarioList?
    @State private var showNew = false
    @State private var error: String?
    @State private var importing = false

    var body: some View {
        List {
            if let error { ErrorBanner(message: error) { Task { await load() } }.listRowBackground(Color.clear) }
            if let list {
                if list.upcoming.isEmpty && list.recurring.isEmpty && list.mine.isEmpty {
                    Text("Add something coming up — a dentist visit, a meeting, dinner with friends — and get the Spanish for it.")
                        .foregroundStyle(LC.Color.textSecondary)
                }
                section("Coming up", list.upcoming)
                section("From your conversations", list.recurring)
                section("Yours", list.mine)
            }
            Section {
                Button { Task { await importCalendar() } } label: {
                    Label(importing ? "Reading your calendar…" : "Use my calendar", systemImage: "calendar")
                }
                .disabled(importing)
            } footer: { Text("Only event titles and times for the next two weeks are sent.") }
        }
        .navigationTitle("Scenes")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { showNew = true } label: { Image(systemName: "plus") }.accessibilityLabel("Something coming up")
            }
        }
        .refreshable { await load() }
        .task(id: app.refreshToken) { await load() }
        .sheet(isPresented: $showNew) { NewSceneSheet { await load() } }
    }

    @ViewBuilder
    private func section(_ title: String, _ items: [ScenarioDTO]) -> some View {
        if !items.isEmpty {
            Section(title) {
                ForEach(items) { s in
                    if s.status == "suggested" {
                        HStack {
                            VStack(alignment: .leading) {
                                Text(s.title).font(.lcBody)
                                Text("Suggested from what you talk about").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
                            }
                            Spacer()
                            Button("Add") { Task { _ = try? await app.api.setScenarioStatus(s.id, "active"); await load() } }
                                .buttonStyle(.borderedProminent)
                        }
                    } else {
                        NavigationLink { SceneDetailView(scenarioId: s.id) } label: { SceneRow(scene: s) }
                    }
                }
            }
        }
    }

    private func load() async {
        do { list = try await app.api.scenarios(); error = nil } catch { self.error = error.localizedDescription }
    }

    private func importCalendar() async {
        importing = true; defer { importing = false }
        do {
            let events = try await app.calendar.upcomingEvents()
            let created = try await app.api.importCalendar(events)
            _ = await app.notifications.requestPermission()
            for s in created {
                if let d = LCDate.parse(s.startsAt) {
                    await app.notifications.scheduleSceneReminder(id: s.id, title: s.title, phrases: 8, startsAt: d)
                }
            }
            await load()
        } catch { self.error = error.localizedDescription }
    }
}

struct SceneRow: View {
    let scene: ScenarioDTO
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(scene.title).font(.lcBody)
                Text(whenLabel(scene)).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
            Spacer()
            ReadinessDots(value: scene.readiness.current)
        }
        .padding(.vertical, 2)
    }
}

struct NewSceneSheet: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    let onCreated: () async -> Void
    @State private var title = ""
    @State private var hasDate = false
    @State private var date = Date().addingTimeInterval(86400)
    @State private var busy = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("e.g. Dentist, parent-teacher meeting", text: $title)
                } header: { Text("What's coming up?") }
                Section {
                    Toggle("It has a date", isOn: $hasDate)
                    if hasDate { DatePicker("When", selection: $date, in: Date()...) }
                }
                if let error { Text(error).foregroundStyle(LC.Color.danger) }
            }
            .navigationTitle("New scene")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(busy ? "Preparing…" : "Prepare") { Task { await create() } }
                        .disabled(title.trimmingCharacters(in: .whitespaces).count < 2 || busy)
                }
            }
        }
    }

    private func create() async {
        busy = true; defer { busy = false }
        do {
            let s = try await app.api.createScenario(NewScenario(title: title, startsAt: hasDate ? date : nil,
                                                                 kind: hasDate ? "upcoming" : "manual"))
            if hasDate {
                _ = await app.notifications.requestPermission()
                await app.notifications.scheduleSceneReminder(id: s.id, title: s.title, phrases: s.phrases?.key.count ?? 8, startsAt: date)
            }
            app.refreshToken += 1
            await onCreated()
            dismiss()
        } catch { self.error = error.localizedDescription }
    }
}
