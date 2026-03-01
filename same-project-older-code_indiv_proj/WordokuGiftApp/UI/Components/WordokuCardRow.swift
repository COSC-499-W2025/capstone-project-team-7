import SwiftUI

struct WordokuCardRow: View {
    let levelNumber: Int
    let label: String
    let isLocked: Bool
    let isCompleted: Bool

    var body: some View {
        HStack(spacing: WordokuTheme.spacingM) {
            VStack(alignment: .leading, spacing: WordokuTheme.spacingXS) {
                Text("Level \(levelNumber)")
                    .font(.headline)
                    .foregroundColor(WordokuTheme.primaryText)
                Text(label)
                    .wordokuSubtleText()
            }
            Spacer()
            if isLocked {
                statusBadge(text: "Locked", color: WordokuTheme.accentYellow)
            } else if isCompleted {
                statusBadge(text: "Solved", color: WordokuTheme.accentBlue)
            }
        }
        .padding(WordokuTheme.spacingM)
        .wordokuCard()
        .opacity(isLocked ? 0.5 : 1)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityLabelText)
        .accessibilityHint(isLocked ? "Complete previous levels to unlock" : "Double tap to play")
        .accessibilityAddTraits(isLocked ? .isStaticText : .isButton)
        .accessibilityIdentifier("level_\(levelNumber)")
    }

    private var accessibilityLabelText: String {
        var text = "Level \(levelNumber)"
        if isLocked {
            text += ", locked"
        } else {
            text += ", \(label)"
            if isCompleted {
                text += ", completed"
            }
        }
        return text
    }

    private func statusBadge(text: String, color: Color) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(color)
                .frame(width: 6, height: 6)
            Text(text.uppercased())
                .font(.caption2.weight(.semibold))
        }
        .foregroundColor(color)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            Capsule()
                .fill(color.opacity(0.12))
        )
        .accessibilityHidden(true)
    }
}
