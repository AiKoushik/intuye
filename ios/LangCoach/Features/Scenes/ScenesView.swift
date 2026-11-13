import LangCoachKit
import SwiftUI

struct ScenesView: View {
    @Environment(AppModel.self) private var app
    @State private var list: ScenarioList?
    @State private var popular: [LibraryCard] = []
    @State private var query = ""
    @State private var results: [LibraryCard]?
    @State private var newTitle: NewSceneRequest?
    @State private var opened: ScenarioDTO?
    @State private var notice: String?
    @State private var error: String?
    @State private var importing = false

    var body: some View {
        List {
            Section {
                SceneSearchField(query: $query) { Task { await search() } }
                    .listRowInsets(EdgeInsets()).listRowBackground(Color.clear)
            }
            if let notice {
                HStack {
                    Label(notice, systemImage: "person.2").font(.lcCaption)
                    Spacer()
                    Button { self.notice = nil } label: { Image(systemName: "xmark") }.accessibilityLabel("Dismiss")
                }
                .foregroundStyle(LC.Color.textSecondary)
            }
            if let error { ErrorBanner(message: error) { Task { await load() } }.listRowBackground(Color.clear) }
            if let results {
                let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
                Section {
                    ForEach(results) { card in libraryLink(card) }
                    Button { newTitle = NewSceneRequest(title: q) } label: { Label("Build “\(q)”", systemImage: "plus") }
                } header: {
                    Text(results.isEmpty ? "Nothing like this in the library yet" : "In the library")
                } footer: {
                    Text("Matched by meaning, so “going to the dentist's” finds “At the dentist”.")
                }
            } else if let list {
                if list.upcoming.isEmpty && list.recurring.isEmpty && list.mine.isEmpty {
                    Text("Search for something coming up — a dentist visit, a meeting, dinner with friends — or build your own and get the Spanish for it.")
                        .foregroundStyle(LC.Color.textSecondary)
                }
                section("Coming up", list.upcoming)
                section("From your conversations", list.recurring)
                section("Yours", list.mine)
                if !popular.isEmpty {
                    Section("Popular in the library") { ForEach(popular) { card in libraryLink(card) } }
                }
                Section {
                    Button { Task { await importCalendar() } } label: {
                        Label(importing ? "Reading your calendar…" : "Use my calendar", systemImage: "calendar")
                    }
                    .disabled(importing)
                } footer: { Text("Only event titles and times for the next two weeks are sent, and calendar scenes are never shared.") }
            }
        }
        .navigationTitle("Scenes")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { newTitle = NewSceneRequest(title: "") } label: { Image(systemName: "plus") }.accessibilityLabel("Something coming up")
            }
        }
        .refreshable { await load() }
        .task(id: app.refreshToken) { await load() }
        .task(id: query) {
            try? await Task.sleep(for: .milliseconds(300))  // debounce typing
            guard !Task.isCancelled else { return }
            await search()
        }
        .sheet(item: $newTitle) { req in
            NewSceneSheet(initialTitle: req.title) { scene in
                if let lib = scene.library { notice = lib.message }
                clearSearch()
                await load()
                opened = scene
            }
        }
        .navigationDestination(item: $opened) { s in SceneDetailView(scenarioId: s.id) }
    }

    private func libraryLink(_ card: LibraryCard) -> some View {
        NavigationLink {
            LibrarySceneView(templateId: card.id) { scene in
                clearSearch()
                notice = "Added “\(scene.title)” to your scenes"
                Task { await load(); opened = scene }
            }
        } label: { LibraryRow(card: card) }
    }

    private func clearSearch() { query = ""; results = nil }

    private func search() async {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { results = nil; return }
        do {
            let found = try await app.api.library(q)
            if q == query.trimmingCharacters(in: .whitespacesAndNewlines) { results = found }
        } catch { self.error = error.localizedDescription }
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
        do {
            async let scenes = app.api.scenarios()
            async let top = app.api.library("", limit: 5)
            list = try await scenes
            popular = (try? await top) ?? []
            error = nil
        } catch { self.error = error.localizedDescription }
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
        let tint = Tint.topic(scene.topic, title: scene.title)
        HStack(spacing: Space.m) {
            TintTile(tint: tint)
            VStack(alignment: .leading, spacing: 2) {
                Text(scene.title).font(.lcBody)
                Text(whenLabel(scene)).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
            Spacer()
            ReadinessDots(value: scene.readiness.current, tint: tint)
        }
        .padding(.vertical, 2)
    }
}

struct NewSceneRequest: Identifiable { let id = UUID(); let title: String }

struct NewSceneSheet: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    let onCreated: (ScenarioDTO) async -> Void
    @State private var title: String
    @State private var details = ""
    @State private var share = true
    @State private var showName = false
    @State private var hasDate = false
    @State private var date = Date().addingTimeInterval(86400)
    @State private var busy = false
    @State private var error: String?

    init(initialTitle: String = "", onCreated: @escaping (ScenarioDTO) async -> Void) {
        _title = State(initialValue: initialTitle)
        self.onCreated = onCreated
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("e.g. Dentist, parent-teacher meeting", text: $title)
                } header: { Text("What's coming up?") }
                Section {
                    TextField("Anything that changes what you'll say, e.g. the teacher only speaks Spanish", text: $details, axis: .vertical)
                        .lineLimit(2...5)
                } header: { Text("Details (optional, never shared)") }
                Section {
                    Toggle("It has a date", isOn: $hasDate)
                    if hasDate { DatePicker("When", selection: $date, in: Date()...) }
                }
                Section {
                    Toggle("Share with other learners", isOn: $share)
                    Toggle("Show my name", isOn: $showName).disabled(!share)
                } header: { Text("Library") } footer: {
                    Text("We share a general version with names, places and your details removed, and only if it isn't in the library already.")
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
            // "upcoming" is reserved for calendar imports ("from your calendar"); hand-made scenes are "manual".
            let trimmed = details.trimmingCharacters(in: .whitespacesAndNewlines)
            let s = try await app.api.createScenario(NewScenario(title: title, details: trimmed.isEmpty ? nil : trimmed,
                                                                 startsAt: hasDate ? date : nil, kind: "manual",
                                                                 share: share, showName: showName))
            if hasDate {
                _ = await app.notifications.requestPermission()
                await app.notifications.scheduleSceneReminder(id: s.id, title: s.title, phrases: s.phrases?.key.count ?? 8, startsAt: date)
            }
            app.refreshToken += 1
            dismiss()
            await onCreated(s)
        } catch { self.error = error.localizedDescription }
    }
}
