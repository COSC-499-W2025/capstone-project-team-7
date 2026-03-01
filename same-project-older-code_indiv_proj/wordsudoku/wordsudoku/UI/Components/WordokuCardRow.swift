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
                Image(systemName: "lock.fill")
                    .foregroundColor(WordokuTheme.secondaryText)
                    .accessibilityHidden(true)
            } else if isCompleted {
                Image(systemName: "checkmark.circle")
                    .foregroundColor(WordokuTheme.secondaryText)
                    .accessibilityHidden(true)
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
}
