import IntuyeKit
import SwiftUI

/// Settings and privacy centre: your language, notifications, capture, and your data.
struct SettingsView: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    @State private var settings: SettingsDTO?
    @State private var exportURL: URL?
    @State private var confirmDelete = false
    @State private var error: String?
    @State private var plan: NotificationPlan?

    var body: some View {
        NavigationStack {
            Form {
                if let s = settings {
                    Section("Your \(app.lang.name)") {
                        Picker("Variety", selection: binding(s.dialect) { v in ["dialect": v] }) {
                            ForEach(app.languages?.languages ?? [app.lang]) { lang in
                                ForEach(lang.varieties) { v in
                                    Text((app.languages?.languages.count ?? 1) > 1 ? "\(lang.name) (\(v.label))" : v.label).tag(v.code)
                                }
                            }
                        }
                        Picker("Level", selection: levelBinding(s.level)) {
                            ForEach(Levels.names.indices, id: \.self) { Text(Levels.names[$0]).tag($0) }
                        }
                    }
                    Section {
                        Stepper("At most \(s.dailyNotificationBudget) a day", value: budgetBinding(s.dailyNotificationBudget), in: 0...6)
                        DatePicker("Quiet from", selection: timeBinding(s.quietStart, key: "quiet_start"), displayedComponents: .hourAndMinute)
                        DatePicker("Quiet until", selection: timeBinding(s.quietEnd, key: "quiet_end"), displayedComponents: .hourAndMinute)
                    } header: { Text("Notifications") } footer: { Text("Never more than one an hour. Each one says why it's there.") }
                    if let plan, !plan.notifications.isEmpty {
                        Section {
                            ForEach(plan.notifications.prefix(6)) { n in
                                HStack(alignment: .firstTextBaseline, spacing: Space.m) {
                                    Text(n.local).font(.footnote.weight(.semibold)).monospacedDigit().foregroundStyle(Tint.rose.fg)
                                        .frame(width: 76, alignment: .leading)
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(n.title)
                                        Text(n.why).font(.footnote).foregroundStyle(LC.Color.textSecondary)
                                    }
                                }
                                .accessibilityElement(children: .combine)
                            }
                        } header: { Text("Coming up") } footer: {
                            if !plan.suppressed.isEmpty {
                                Text("\(plan.suppressed.count) more were left out to stay inside your limit and quiet hours.")
                            }
                        }
                    }
                }
                Section("Capture") {
                    NavigationLink("Capture and privacy") { CaptureSheet() }
                }
                Section {
                    LabeledContent("Audio", value: "Stays on this iPhone")
                    LabeledContent("Sentences", value: "Kept \(settings?.momentRetentionDays ?? 90) days")
                    Button("Export my data") { Task { await export() } }
                    if let exportURL { ShareLink("Share export", item: exportURL) }
                    Button("Delete account", role: .destructive) { confirmDelete = true }
                } header: { Text("Your data") } footer: {
                    Text("Deleting removes your sentences, words, scenes and progress from our servers. It can't be undone.")
                }
                if let error { Section { Text(error).foregroundStyle(LC.Color.danger) } }
                Section {
                    LabeledContent("Intuye", value: "Sense it. Say it.")
                    Link("Source code", destination: URL(string: "https://github.com/AiKoushik/intuye")!)
                    LabeledContent("Licence", value: "GNU AGPL v3 or later")
                } header: { Text("About") } footer: { Text("Intuye is free software. You can read, change and share its code.") }
                Section { Button("Sign out") { Task { await app.signOut(); dismiss() } } }
            }
            .lcGroupedBackground()
            .navigationTitle("Settings")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
            .confirmationDialog("Delete your account and all your data?", isPresented: $confirmDelete, titleVisibility: .visible) {
                Button("Delete account", role: .destructive) { Task { await deleteAccount() } }
            }
            .task {
                settings = app.me?.settings; await app.loadMe(); settings = app.me?.settings
                plan = try? await app.api.notificationPlan()
            }
        }
    }

    private func binding(_ value: String, patch: @escaping (String) -> [String: String]) -> Binding<String> {
        Binding(get: { value }, set: { v in Task { await save { try await app.api.updateSettings(patch(v)) } } })
    }

    private func levelBinding(_ value: Int) -> Binding<Int> {
        Binding(get: { value }, set: { v in Task { await save { try await app.api.updateLevel(v) } } })
    }

    private func budgetBinding(_ value: Int) -> Binding<Int> {
        Binding(get: { value }, set: { v in Task { await save { try await app.api.send("PATCH", "/v1/me/settings", body: ["daily_notification_budget": v]) } } })
    }

    /// "HH:mm" strings from the server shown as times; changes are saved as "HH:mm" again.
    private func timeBinding(_ value: String, key: String) -> Binding<Date> {
        let parts = value.split(separator: ":").compactMap { Int($0) }
        let date = Calendar.current.date(bySettingHour: parts.first ?? 22, minute: parts.count > 1 ? parts[1] : 0, second: 0, of: .now) ?? .now
        return Binding(get: { date }, set: { d in
            let c = Calendar.current.dateComponents([.hour, .minute], from: d)
            let hm = String(format: "%02d:%02d", c.hour ?? 0, c.minute ?? 0)
            Task { await save { try await app.api.updateSettings([key: hm]) } }
        })
    }

    private func save(_ op: () async throws -> SettingsDTO) async {
        do {
            settings = try await op(); await app.loadMe(); error = nil
            await app.syncNotifications()
            plan = try? await app.api.notificationPlan()
        } catch { self.error = error.localizedDescription }
    }

    private func export() async {
        do {
            let data = try await app.api.exportAccount()
            let url = FileManager.default.temporaryDirectory.appendingPathComponent("intuye-export.json")
            try data.write(to: url, options: [.atomic, .completeFileProtection])
            exportURL = url
        } catch { self.error = error.localizedDescription }
    }

    private func deleteAccount() async {
        do {
            try await app.api.deleteAccount()
            KeychainStore.setString(nil, for: "attestKeyId")
            app.signedOut()
            dismiss()
        } catch { self.error = error.localizedDescription }
    }
}
