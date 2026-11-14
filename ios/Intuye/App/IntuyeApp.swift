import SwiftUI

@main
struct IntuyeApp: App {
    @State private var model = AppModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
                .tint(LC.Color.accent)
                .task { await model.boot() }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .background { Task { await model.capture.flush() } }
                }
        }
    }
}

struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        switch model.phase {
        case .launching:
            LC.Color.canvas.ignoresSafeArea()
        case .onboarding:
            OnboardingView()
        case .signedIn:
            MainTabView()
        }
    }
}

struct MainTabView: View {
    @Environment(AppModel.self) private var model
    @State private var showCapture = false

    var body: some View {
        @Bindable var model = model
        TabView(selection: $model.selectedTab) {
            Tab("Today", systemImage: "sun.max", value: AppTab.today) { NavigationStack { TodayView() } }
            Tab("Say", systemImage: "text.bubble", value: AppTab.say) { NavigationStack { SayView() } }
            Tab("Scenes", systemImage: "theatermasks", value: AppTab.scenes) { NavigationStack { ScenesView() } }
            Tab("Progress", systemImage: "chart.line.uptrend.xyaxis", value: AppTab.progress) { NavigationStack { ProgressScreen() } }
        }
        .tabViewBottomAccessory {
            CapturePill { showCapture = true }
        }
        .sheet(isPresented: $showCapture) { CaptureSheet().presentationDetents([.medium]) }
    }
}
