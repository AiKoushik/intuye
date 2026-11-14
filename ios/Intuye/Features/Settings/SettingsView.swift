import IntuyeKit
import SwiftUI

/// Settings and privacy centre: your Spanish, notifications, capture, and your data.
struct SettingsView: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    @State private var settings: SettingsDTO?
    @State private var exportURL: URL?
    @State private var confirmDelete = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                if let s = settings {
                    Section("Your Spanish") {
                        Picker("Variety", selection: binding(s.dialect) { v in ["dialect": v] }) {
                            Text("Latin America").tag("es-419"); Text("Mexico").tag("es-MX"); Text("Spain").tag("es-ES")
                        }
                        Picker("Level", selection: levelBinding(s.level)) {
                            Text("Just starting").tag(0); Text("Beginner").tag(1); Text("I get by").tag(2)
                            Text("Intermediate").tag(3); Text("Conversational").tag(4); Text("Fluent").tag(5)
                        }
                    }
                    Section {
                        Stepper("At most \(s.dailyNotificationBudget) a day", value: budgetBinding(s.dailyNotificationBudget), in: 0...6)
                        LabeledContent("Quiet hours", value: "\(s.quietStart)–\(s.quietEnd)")
                    } header: { Text("Notifications") } footer: { Text("Never more than one an hour. Each one says why it's there.") }
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
            .task { settings = app.me?.settings; await app.loadMe(); settings = app.me?.settings }
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

    private func save(_ op: () async throws -> SettingsDTO) async {
        do { settings = try await op(); await app.loadMe(); error = nil } catch { self.error = error.localizedDescription }
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
