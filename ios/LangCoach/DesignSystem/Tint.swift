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

    var bg: Color {
        switch self {
        case .sage: LC.Color.sageSubtle
        case .sea: LC.Color.seaSubtle
        case .sand: LC.Color.sandSubtle
        case .rose: LC.Color.roseSubtle
        case .plum: LC.Color.plumSubtle
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
        (.sea, ["work", "job", "office", "meeting", "study", "science", "neuro", "tech", "career", "universit", "interview", "class"]),
        (.sand, ["home", "family", "kid", "son", "daughter", "child", "school", "parent", "landlord", "house", "neighbo"]),
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
