import AppIntents
import SwiftUI

@main
struct IntuyeApp: App {
    @State private var model: AppModel
    @Environment(\.scenePhase) private var scenePhase

    init() {
        let model = AppModel()
        _model = State(initialValue: model)
        AppDependencyManager.shared.add(dependency: model)  // App Intents (Siri, controls) use the same model
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
                .tint(LC.Color.accent)
                .task { await model.boot() }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .background { Task { await model.capture.flush() } }
                    if phase == .active { Task { await model.syncOffline() } }
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
    @State private var showReview = false

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
        .fullScreenCover(isPresented: $showReview) { ReviewSessionView() }
        .onChange(of: model.reviewRequest) { showReview = true }
    }
}
