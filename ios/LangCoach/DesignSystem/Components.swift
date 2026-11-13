import LangCoachKit
import SwiftUI

// MARK: Card

struct LCCard: ViewModifier {
    var padding: CGFloat = Space.l
    func body(content: Content) -> some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(LC.Color.surface, in: RoundedRectangle(cornerRadius: Radius.card, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: Radius.card, style: .continuous).strokeBorder(LC.Color.hairline, lineWidth: 1))
    }
}

extension View {
    func lcCard(padding: CGFloat = Space.l) -> some View { modifier(LCCard(padding: padding)) }
}

// MARK: Buttons

struct PrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .frame(maxWidth: .infinity, minHeight: 50)
            .foregroundStyle(LC.Color.onAccent)
            .background(LC.Color.accentFill.opacity(isEnabled ? 1 : 0.4),
                        in: RoundedRectangle(cornerRadius: Radius.control, style: .continuous))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct SubtleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .frame(maxWidth: .infinity, minHeight: 50)
            .foregroundStyle(LC.Color.accent)
            .background(LC.Color.accentSubtle, in: RoundedRectangle(cornerRadius: Radius.control, style: .continuous))
            .opacity(configuration.isPressed ? 0.8 : 1)
    }
}

extension ButtonStyle where Self == PrimaryButtonStyle { static var lcPrimary: PrimaryButtonStyle { .init() } }
extension ButtonStyle where Self == SubtleButtonStyle { static var lcSubtle: SubtleButtonStyle { .init() } }

// MARK: Flow layout (wraps interlinear groups and chips)

struct FlowLayout: Layout {
    var spacing: CGFloat = 10
    var lineSpacing: CGFloat = 10

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let rows = arrange(width: proposal.width ?? .infinity, subviews: subviews)
        let height = rows.map(\.height).reduce(0, +) + lineSpacing * CGFloat(max(rows.count - 1, 0))
        let width = rows.map(\.width).max() ?? 0
        return CGSize(width: proposal.width ?? width, height: height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var y = bounds.minY
        for row in arrange(width: bounds.width, subviews: subviews) {
            var x = bounds.minX
            for index in row.indices {
                let size = subviews[index].sizeThatFits(.unspecified)
                subviews[index].place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
                x += size.width + spacing
            }
            y += row.height + lineSpacing
        }
    }

    private struct Row { var indices: [Int] = []; var width: CGFloat = 0; var height: CGFloat = 0 }

    private func arrange(width: CGFloat, subviews: Subviews) -> [Row] {
        var rows = [Row()]
        for (i, sub) in subviews.enumerated() {
            let size = sub.sizeThatFits(.unspecified)
            let needed = rows[rows.count - 1].indices.isEmpty ? size.width : rows[rows.count - 1].width + spacing + size.width
            if needed > width && !rows[rows.count - 1].indices.isEmpty {
                rows.append(Row())
            }
            var row = rows[rows.count - 1]
            row.width = row.indices.isEmpty ? size.width : row.width + spacing + size.width
            row.height = max(row.height, size.height)
            row.indices.append(i)
            rows[rows.count - 1] = row
        }
        return rows
    }
}

// MARK: Interlinear line — the signature component

/// Your words on top (SF Pro, secondary), the other language beneath (New York serif). Tap a group to pair it;
/// new-to-you Spanish carries a saffron highlighter mark.
struct InterlinearLine: View {
    let pairs: [AlignedPair]
    /// True when the bottom line is English (Spanish → English results), so "new" marks the top line.
    var bottomIsEnglish = false
    @State private var selected: Int?
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        FlowLayout(spacing: 10, lineSpacing: 12) {
            // Index identity: the same pair can appear twice in one sentence ("en ... en").
            ForEach(Array(pairs.enumerated()), id: \.offset) { index, pair in
                group(pair, index: index)
            }
        }
        .accessibilityElement(children: .contain)
    }

    private func group(_ pair: AlignedPair, index: Int) -> some View {
        let isOn = selected == index
        return VStack(alignment: .leading, spacing: 1) {
            Text(pair.src)
                .font(bottomIsEnglish ? .lcSpanishBody : .lcSource)
                .foregroundStyle(isOn ? LC.Color.onHighlight : LC.Color.textSecondary)
            Text(pair.tgt)
                .font(bottomIsEnglish ? .lcSource : .lcSpanish)
                .foregroundStyle(isOn ? LC.Color.onHighlight : LC.Color.textPrimary)
                .background(alignment: .bottom) {
                    if pair.new && !isOn {
                        LC.Color.highlight.frame(height: 7).offset(y: -2)
                    }
                }
        }
        .padding(.horizontal, 3)
        .padding(.vertical, 1)
        .background(isOn ? LC.Color.highlight : .clear, in: RoundedRectangle(cornerRadius: 6, style: .continuous))
        .contentShape(Rectangle())
        .onTapGesture {
            withAnimation(reduceMotion ? nil : Motion.pair) { selected = isOn ? nil : index }
        }
        .sensoryFeedback(.selection, trigger: selected)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(pair.src), \(bottomIsEnglish ? "English" : "Spanish"): \(pair.tgt)\(pair.new ? ", new word" : "")")
        .accessibilityAddTraits(.isButton)
    }
}

// MARK: Small pieces

struct WordChip: View {
    let text: String
    var isNew = false
    var tint: Tint? = nil
    var body: some View {
        Text(text)
            .font(.lcSpanishBody)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(tint?.bg ?? LC.Color.sunken, in: Capsule())
            .overlay(alignment: .bottom) {
                if isNew { Capsule().fill(LC.Color.highlight).frame(height: 3).padding(.horizontal, 8) }
            }
            .accessibilityLabel(isNew ? "\(text), new word" : text)
    }
}

struct DirectionChip: View {
    let intent: CoachIntent
    var body: some View {
        let tint: Tint = intent == .toEn ? .plum : intent == .toEs ? .sea : .sand
        TintChip(tint: tint, text: intent == .toEn ? "Spanish → English" : intent == .toEs ? "English → Spanish" : "You asked")
    }
}

struct ReadinessDots: View {
    let value: Int?
    var tint: Tint? = nil
    var body: some View {
        let c = tint?.fg ?? LC.Color.accent
        HStack(spacing: 4) {
            ForEach(1...5, id: \.self) { i in
                Circle()
                    .strokeBorder(c, lineWidth: 1.5)
                    .background(Circle().fill(i <= (value ?? 0) ? c : .clear))
                    .frame(width: 8, height: 8)
            }
        }
        .accessibilityElement()
        .accessibilityLabel(value.map { "Readiness \($0) of 5" } ?? "Not rated yet")
    }
}

struct RatingButton: View {
    let rating: Rating
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: symbol).font(.body.weight(.semibold))
                Text(label).font(.footnote.weight(.semibold))
            }
            .frame(maxWidth: .infinity, minHeight: 56)
            .foregroundStyle(color)
            .background(LC.Color.surface, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(color, lineWidth: 1.5))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }

    private var label: String { ["Forgot", "Hard", "Got it", "Easy"][rating.rawValue - 1] }
    private var symbol: String { ["xmark", "tilde", "checkmark", "bolt"][rating.rawValue - 1] }
    private var color: Color { [LC.Color.danger, LC.Color.warning, LC.Color.success, LC.Color.accent][rating.rawValue - 1] }
}

struct EmptyState: View {
    let message: String
    let actionTitle: String?
    var action: (() -> Void)?
    var body: some View {
        VStack(alignment: .leading, spacing: Space.m) {
            Text(message).font(.lcBody).foregroundStyle(LC.Color.textSecondary)
            if let actionTitle, let action {
                Button(actionTitle, action: action).buttonStyle(.lcSubtle)
            }
        }
        .lcCard()
    }
}

struct ErrorBanner: View {
    let message: String
    var retry: (() -> Void)?
    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: Space.s) {
            Image(systemName: "exclamationmark.circle").foregroundStyle(LC.Color.danger)
            Text(message).font(.lcCaption).foregroundStyle(LC.Color.textPrimary)
            Spacer(minLength: 0)
            if let retry { Button("Retry", action: retry).font(.lcCaption.weight(.semibold)) }
        }
        .padding(Space.m)
        .background(LC.Color.sunken, in: RoundedRectangle(cornerRadius: Radius.control, style: .continuous))
    }
}
