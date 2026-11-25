import SwiftUI

/// Bottom accessory: always honest about whether the mic is on. Shape-coded dot (filled = listening).
struct CapturePill: View {
    @Environment(AppModel.self) private var model
    let open: () -> Void

    /// Capture is on but paused because the phone is inside a never-record place.
    private var pausedAt: NeverRecordPlace? { model.capture.mode == .off ? nil : model.neverRecord.current }
    private var status: String {
        if model.capture.isListening { return "Listening" }
        if let place = pausedAt { return "Paused at \(place.name)" }
        return "Capture off"
    }

    var body: some View {
        Button(action: open) {
            HStack(spacing: Space.s) {
                ZStack {
                    Circle().fill(model.capture.isListening ? LC.Color.success : .clear)
                    Circle().strokeBorder(model.capture.isListening ? LC.Color.success : LC.Color.borderStrong, lineWidth: 1.5)
                    if pausedAt != nil {  // a bar through the dot: deliberately not listening here
                        Capsule().fill(LC.Color.borderStrong).frame(width: 12, height: 1.5).rotationEffect(.degrees(-45))
                    }
                }
                .frame(width: 10, height: 10)
                Text(status).font(.subheadline).lineLimit(1)
                Spacer()
                Text("\(model.capture.sentencesToday) sentences today")
                    .font(.subheadline).foregroundStyle(LC.Color.textSecondary).monospacedDigit()
            }
            .padding(.horizontal, Space.l)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(model.capture.isListening ? "Capture on, \(model.capture.sentencesToday) sentences today" : status)
        .accessibilityHint("Opens capture controls")
    }
}

struct CaptureSheet: View {
    @Environment(AppModel.self) private var model
    @State private var toast: String?
    @State private var forgetTrigger = 0
    @State private var addingPlace = false

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
                NeverRecordSection(adding: $addingPlace)
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
            .lcGroupedBackground()
            .navigationTitle("Capture")
            .navigationBarTitleDisplayMode(.inline)
            .sensoryFeedback(.warning, trigger: forgetTrigger)
            .sheet(isPresented: $addingPlace) { AddNeverRecordPlace().presentationDetents([.medium]) }
        }
    }
}

/// The places where capture never listens. Kept on this iPhone only.
struct NeverRecordSection: View {
    @Environment(AppModel.self) private var model
    @Binding var adding: Bool

    var body: some View {
        let places = model.neverRecord
        Section {
            ForEach(places.places) { place in
                HStack {
                    Image(systemName: "location.slash").foregroundStyle(Tint.rose.fg).accessibilityHidden(true)
                    Text(place.name)
                    Spacer()
                    if places.current?.id == place.id {
                        TintChip(tint: .rose, text: "You're here")
                    }
                    Text("\(Int(place.radius)) m").foregroundStyle(LC.Color.textSecondary).monospacedDigit()
                }
                .accessibilityElement(children: .combine)
            }
            .onDelete { offsets in
                let gone = offsets.map { places.places[$0] }
                Task { for p in gone { await places.remove(p) } }
            }
            Button { adding = true } label: { Label("Add where I am now", systemImage: "plus") }
        } header: { Text("Never record here") } footer: {
            if places.authorization == .denied || places.authorization == .restricted {
                Text("Location is off for Intuye, so these places can't pause capture. Turn it on in Settings, Privacy, Location Services.")
            } else {
                Text("Capture pauses whenever you're within these places. They stay on this iPhone and are never sent to the server.")
            }
        }
    }
}

/// Names the current location and picks how far around it counts.
struct AddNeverRecordPlace: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var radius: Double = 200
    @State private var busy = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Name, e.g. Clinic or Office", text: $name)
                        .textInputAutocapitalization(.words)
                        .submitLabel(.done)
                    Picker("Covers", selection: $radius) {
                        ForEach(NeverRecordPlaces.radii, id: \.self) { Text("\(Int($0)) m around here").tag($0) }
                    }
                } footer: {
                    Text("Uses where your iPhone is now. Intuye may ask to use your location, including in the background, so capture can pause even when the app isn't open.")
                }
                if let error { Section { Text(error).foregroundStyle(LC.Color.danger) } }
            }
            .lcGroupedBackground()
            .navigationTitle("Never record here")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    if busy { ProgressView() } else { Button("Add") { Task { await add() } } }
                }
            }
            .interactiveDismissDisabled(busy)
        }
    }

    private func add() async {
        busy = true; defer { busy = false }
        do {
            try await model.neverRecord.addCurrentLocation(name: name, radius: radius)
            dismiss()
        } catch { self.error = error.localizedDescription }
    }
}
