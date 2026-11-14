import SwiftUI

/// Sober tints say what something is about or why it's here. Azulejo (the accent) stays for things you tap.
/// A tint always sits next to a label, never alone.
enum Tint: CaseIterable {
    case sage, sea, sand, rose, plum

    var fg: Color {
        switch self {
        case .sage: LC.Color.sage
        case .sea: LC.Color.sea
        case .sand: LC.Color.sand
        case .rose: LC.Color.rose
        case .plum: LC.Color.plum
        }
    }

    /// Chips and tiles.
    var bg: Color {
        switch self {
        case .sage: LC.Color.sageSubtle
        case .sea: LC.Color.seaSubtle
        case .sand: LC.Color.sandSubtle
        case .rose: LC.Color.roseSubtle
        case .plum: LC.Color.plumSubtle
        }
    }

    /// Whole cards: just off the page, so different kinds of card read as different at a glance.
    var wash: Color {
        switch self {
        case .sage: LC.Color.sageWash
        case .sea: LC.Color.seaWash
        case .sand: LC.Color.sandWash
        case .rose: LC.Color.roseWash
        case .plum: LC.Color.plumWash
        }
    }

    /// The soft glow at the top of a screen.
    var ambient: Color {
        switch self {
        case .sage: LC.Color.sageAmbient
        case .sea: LC.Color.seaAmbient
        case .sand: LC.Color.sandAmbient
        case .rose: LC.Color.roseAmbient
        case .plum: LC.Color.plumAmbient
        }
    }

    /// What scenes in this tint are about.
    var topicLabel: String {
        switch self {
        case .sage: "Health and body"
        case .sea: "Work and study"
        case .sand: "Home and family"
        case .rose: "Food and friends"
        case .plum: "Travel and errands"
        }
    }

    var symbol: String {
        switch self {
        case .sage: "heart"
        case .sea: "briefcase"
        case .sand: "house"
        case .rose: "fork.knife"
        case .plum: "mappin.and.ellipse"
        }
    }

    private static let keywords: [(Tint, [String])] = [
        (.sage, ["health", "dentist", "doctor", "medic", "pharmac", "hospital", "body", "tooth", "clinic", "sport", "fitness"]),
        (.sand, ["home", "family", "kid", "son", "daughter", "child", "school", "parent", "landlord", "house", "neighbo"]),
        (.sea, ["work", "job", "office", "meeting", "study", "science", "neuro", "tech", "career", "universit", "interview", "class"]),
        (.rose, ["food", "restaurant", "cook", "dinner", "lunch", "breakfast", "friend", "party", "social", "café", "cafe", "order"]),
        (.plum, ["travel", "errand", "bank", "shop", "ticket", "train", "bus", "airport", "hotel", "plumber", "repair", "admin", "taxi"]),
    ]

    /// Topic first, then the title; unknown topics get a stable tint from their text.
    static func topic(_ topic: String?, title: String = "") -> Tint {
        let t = (topic ?? "").lowercased()
        for (tint, words) in keywords where words.contains(where: t.contains) { return tint }
        let all = "\(t) \(title.lowercased())"
        for (tint, words) in keywords where words.contains(where: all.contains) { return tint }
        let h = all.unicodeScalars.reduce(UInt32(0)) { ($0 &* 31) &+ $1.value }
        return allCases[Int(h % UInt32(allCases.count))]
    }

    /// Why a word is in your batch (reason kind or lexeme origin).
    static func reason(_ kind: String?) -> Tint {
        switch kind {
        case "spoken": .sea
        case "scenario": .sage
        case "struggle": .rose
        case "topic", "grammar": .plum
        default: .sand
        }
    }
}

struct TintTile: View {
    let tint: Tint
    var symbol: String? = nil
    var size: CGFloat = 32
    var body: some View {
        Image(systemName: symbol ?? tint.symbol)
            .font(.system(size: size * 0.5, weight: .medium))
            .foregroundStyle(tint.fg)
            .frame(width: size, height: size)
            .background(tint.bg, in: RoundedRectangle(cornerRadius: size * 0.28, style: .continuous))
            .accessibilityHidden(true)
    }
}

struct TintChip: View {
    let tint: Tint
    let text: String
    var body: some View {
        Text(text)
            .font(.caption.weight(.medium))
            .foregroundStyle(tint.fg)
            .padding(.horizontal, 10).padding(.vertical, 3)
            .background(tint.bg, in: Capsule())
    }
}

/// The page: the canvas with a faint glow from two tints at the top corners.
struct AmbientBackground: View {
    let leading: Tint
    let trailing: Tint
    init(_ leading: Tint, _ trailing: Tint) { self.leading = leading; self.trailing = trailing }

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .top) {
                LC.Color.canvas
                EllipticalGradient(colors: [leading.ambient, leading.ambient.opacity(0)], center: .topLeading,
                                   startRadiusFraction: 0, endRadiusFraction: 0.72)
                    .frame(width: geo.size.width * 1.5, height: geo.size.height * 0.46)
                    .frame(maxWidth: .infinity, alignment: .leading)
                EllipticalGradient(colors: [trailing.ambient, trailing.ambient.opacity(0)], center: .topTrailing,
                                   startRadiusFraction: 0, endRadiusFraction: 0.66)
                    .frame(width: geo.size.width * 1.2, height: geo.size.height * 0.40)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
            .frame(width: geo.size.width, height: geo.size.height, alignment: .top)
            .clipped()
        }
        .ignoresSafeArea()
        .accessibilityHidden(true)
    }
}
