import SwiftUI

/// Two voices: SF Pro for the UI and your words, New York (serif) for Spanish. All map to Dynamic Type styles.
extension Font {
    static let lcDisplay = Font.largeTitle.weight(.bold)
    static let lcSpanishXL = Font.system(.title, design: .serif)
    static let lcSpanish = Font.system(.title3, design: .serif)
    static let lcSpanishBody = Font.system(.body, design: .serif)
    static let lcHeadline = Font.headline
    static let lcBody = Font.body
    static let lcSource = Font.callout
    static let lcCaption = Font.footnote
}

enum Space {
    static let xs: CGFloat = 4
    static let s: CGFloat = 8
    static let m: CGFloat = 12
    static let l: CGFloat = 16
    static let xl: CGFloat = 24
    static let xxl: CGFloat = 32
    static let xxxl: CGFloat = 48
    static let margin: CGFloat = 20
}

enum Radius {
    static let sheet: CGFloat = 28
    static let card: CGFloat = 20
    static let control: CGFloat = 12
}

enum Motion {
    static let spring = Animation.spring(response: 0.35, dampingFraction: 0.85)
    static let pair = Animation.easeOut(duration: 0.18)

    /// Use instead of withAnimation when Reduce Motion should become a cross-fade.
    static func animate(_ reduceMotion: Bool, _ body: () -> Void) {
        withAnimation(reduceMotion ? .easeInOut(duration: 0.15) : spring, body)
    }
}
