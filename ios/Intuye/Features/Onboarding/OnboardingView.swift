import AuthenticationServices
import IntuyeKit
import SwiftUI

/// Welcome → which variety → rough level → Sign in with Apple. Permissions are asked later, in context.
/// The language, its varieties and the sample sentence come from the server's language pack.
struct OnboardingView: View {
    @Environment(AppModel.self) private var model
    @State private var step = 0
    @State private var dialect = ""
    @State private var level = 0
    @State private var nonce = Nonce.random()
    @State private var error: String?
    @State private var busy = false


    var body: some View {
        VStack(alignment: .leading, spacing: Space.xl) {
            Spacer(minLength: Space.xl)
            switch step {
            case 0: welcome
            case 1: dialectStep
            default: levelAndSignIn
            }
            Spacer()
            if let error { ErrorBanner(message: error) }
        }
        .padding(.horizontal, Space.margin)
        .padding(.bottom, Space.xl)
        .background(AmbientBackground(.sea, .plum))
        .animation(Motion.spring, value: step)
    }

    private var welcome: some View {
        VStack(alignment: .leading, spacing: Space.l) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Intuye").font(.headline).foregroundStyle(LC.Color.accent)
                Text("in-TOO-yeh: “sense it”. \(model.lang.name) in your own words.").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
            .accessibilityElement(children: .combine)
            Text("Say it your way.").font(.lcDisplay)
            Text("Speak English, \(model.lang.name) or a mix. Get \(model.lang.name) back that stays close to what you said.")
                .font(.lcBody).foregroundStyle(LC.Color.textSecondary)
            if let pairs = model.lang.ui?.examplePairs, !pairs.isEmpty {
                InterlinearLine(pairs: pairs).lcCard()
                Text("Tap a word to see its partner.").font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
            VStack(alignment: .leading, spacing: Space.m) {
                promise(.sea, "text.bubble", "Say anything, in any mix", "English, \(model.lang.name) or both at once")
                promise(.sage, "calendar", "Get ready for what's coming up", "The dentist, a meeting, dinner with friends")
                promise(.sand, "rectangle.stack", "Keep 5 to 10 words a day", "Picked from what you actually say")
            }
            .padding(.top, Space.s)
            Button("Continue") { step = 1 }.buttonStyle(.lcPrimary).padding(.top, Space.l)
        }
    }

    private var dialectStep: some View {
        VStack(alignment: .leading, spacing: Space.l) {
            Text("Which \(model.lang.name)?").font(.lcDisplay)
            if let note = model.lang.ui?.varietyNote {
                Text(note).font(.lcBody).foregroundStyle(LC.Color.textSecondary)
            }
            ForEach(model.lang.varieties) { v in
                choice(v.label, selected: (dialect.isEmpty ? model.lang.defaultVariety : dialect) == v.code) { dialect = v.code }
            }
            Button("Continue") { step = 2 }.buttonStyle(.lcPrimary).padding(.top, Space.l)
        }
    }

    private var levelAndSignIn: some View {
        VStack(alignment: .leading, spacing: Space.l) {
            Text("Where are you now?").font(.lcDisplay)
            ForEach([(0, "Just starting"), (2, "I get by"), (4, "I can hold a conversation")], id: \.0) { value, name in
                choice(name, selected: level == value) { level = value }
            }
            SignInWithAppleButton(.continue) { request in
                nonce = Nonce.random()
                request.requestedScopes = [.fullName]
                request.nonce = Nonce.sha256(nonce)
            } onCompletion: { result in
                Task { await handle(result) }
            }
            .signInWithAppleButtonStyle(.black)
            .frame(height: 52)
            .clipShape(RoundedRectangle(cornerRadius: Radius.control, style: .continuous))
            .disabled(busy)
            .padding(.top, Space.l)
            Text("We never see your Apple ID password. Audio stays on your iPhone.")
                .font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
        }
    }

    private func choice(_ title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Text(title).font(.lcBody).foregroundStyle(LC.Color.textPrimary)
                Spacer()
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selected ? LC.Color.accent : LC.Color.borderStrong)
            }
            .lcCard()
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }

    private func handle(_ result: Result<ASAuthorization, Error>) async {
        busy = true; defer { busy = false }
        switch result {
        case .failure(let e):
            if (e as? ASAuthorizationError)?.code != .canceled { error = "Apple sign-in didn't finish. Try again." }
        case .success(let auth):
            guard let cred = auth.credential as? ASAuthorizationAppleIDCredential,
                  let tokenData = cred.identityToken, let token = String(data: tokenData, encoding: .utf8) else {
                error = "Apple sign-in didn't return a token. Try again."; return
            }
            let name = [cred.fullName?.givenName, cred.fullName?.familyName].compactMap { $0 }.joined(separator: " ")
            do {
                try await model.api.signInWithApple(identityToken: token, rawNonce: nonce, displayName: name.isEmpty ? nil : name)
                _ = try? await model.api.updateSettings(["dialect": dialect.isEmpty ? model.lang.defaultVariety : dialect])
                _ = try? await model.api.updateLevel(level)
                await model.didSignIn()
                model.selectedTab = .say
            } catch {
                self.error = error.localizedDescription
            }
        }
    }

    private func promise(_ tint: Tint, _ symbol: String, _ title: String, _ sub: String) -> some View {
        HStack(spacing: Space.m) {
            TintTile(tint: tint, symbol: symbol, size: 36)
            VStack(alignment: .leading, spacing: 1) {
                Text(title).font(.lcBody.weight(.semibold))
                Text(sub).font(.lcCaption).foregroundStyle(LC.Color.textSecondary)
            }
        }
        .accessibilityElement(children: .combine)
    }
}
