import SwiftUI

/// Bottom accessory: always honest about whether the mic is on. Shape-coded dot (filled = listening).
struct CapturePill: View {
    @Environment(AppModel.self) private var model
    let open: () -> Void

    var body: some View {
        Button(action: open) {
            HStack(spacing: Space.s) {
                ZStack {
                    Circle().fill(model.capture.isListening ? LC.Color.success : .clear)
                    Circle().strokeBorder(model.capture.isListening ? LC.Color.success : LC.Color.borderStrong, lineWidth: 1.5)
                }
                .frame(width: 10, height: 10)
                Text(model.capture.isListening ? "Listening" : "Capture off").font(.subheadline)
                Spacer()
                Text("\(model.capture.sentencesToday) sentences today")
                    .font(.subheadline).foregroundStyle(LC.Color.textSecondary).monospacedDigit()
            }
            .padding(.horizontal, Space.l)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(model.capture.isListening ? "Capture on, \(model.capture.sentencesToday) sentences today" : "Capture off")
        .accessibilityHint("Opens capture controls")
    }
}

struct CaptureSheet: View {
    @Environment(AppModel.self) private var model
    @State private var toast: String?
    @State private var forgetTrigger = 0

    var body: some View {
        @Bindable var capture = model.capture
        NavigationStack {
            Form {
                Section {
                    Picker("Listen", selection: $capture.mode) {
                        ForEach(AmbientCapture.Mode.allCases) { Text($0.label).tag($0) }
                    }
                    .pickerStyle(.inline)
                    .labelsHidden()
                } header: { Text("Capture") } footer: {
                    Text("Your sentences are transcribed on this iPhone. Only text is sent. Windows: 9–12 and 18–21.")
                }
                if let err = model.capture.lastError {
                    Section { Text(err).foregroundStyle(LC.Color.danger) }
                }
                Section {
                    Button("Forget last 10 minutes", role: .destructive) {
                        Task {
                            let n = (try? await model.capture.forget(minutes: 10)) ?? 0
                            forgetTrigger += 1
                            toast = n == 1 ? "Forgot 1 sentence" : "Forgot \(n) sentences"
                        }
                    }
                } footer: {
                    if let toast { Text(toast) }
                }
            }
            .navigationTitle("Capture")
            .navigationBarTitleDisplayMode(.inline)
            .sensoryFeedback(.warning, trigger: forgetTrigger)
        }
    }
}
