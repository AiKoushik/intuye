import SwiftUI

/// 64-pt hold-to-talk control. Press and hold to speak, release to send. VoiceOver: double-tap to start,
/// double-tap again to stop. The ring follows input level (static when Reduce Motion is on).
struct HoldToTalkButton: View {
    let isRecording: Bool
    let level: Float
    let onBegin: () -> Void
    let onEnd: () -> Void
    @State private var pressing = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        ZStack {
            Circle()
                .fill(LC.Color.accentSubtle)
                .scaleEffect(isRecording && !reduceMotion ? 1.15 + CGFloat(level) * 0.35 : 1.12)
                .animation(.easeOut(duration: 0.12), value: level)
            Circle().fill(LC.Color.accentFill)
            Image(systemName: isRecording ? "waveform" : "mic.fill")
                .font(.title2.weight(.semibold))
                .foregroundStyle(LC.Color.onAccent)
                .symbolEffect(.variableColor.iterative, isActive: isRecording && !reduceMotion)
        }
        .frame(width: 64, height: 64)
        .scaleEffect(pressing ? 0.96 : 1)
        .contentShape(Circle())
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in
                    if !pressing { pressing = true; onBegin() }
                }
                .onEnded { _ in
                    pressing = false; onEnd()
                }
        )
        .sensoryFeedback(.impact(flexibility: .soft), trigger: pressing)
        .accessibilityElement()
        .accessibilityLabel(isRecording ? "Stop and send" : "Hold to talk")
        .accessibilityAddTraits(.isButton)
        .accessibilityAction { isRecording ? onEnd() : onBegin() }
    }
}
