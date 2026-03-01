import SwiftUI

struct WinOverlayView: View {
    let forcedWord: String

    var body: some View {
        HStack(spacing: WordokuTheme.spacingS) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundColor(WordokuTheme.secondaryText)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 2) {
                Text("Level Complete")
                    .font(.headline)
                    .foregroundColor(WordokuTheme.primaryText)
                Text("Reveal: \(forcedWord)")
                    .wordokuSubtleText()
            }
        }
        .padding(.horizontal, WordokuTheme.spacingL)
        .padding(.vertical, WordokuTheme.spacingS)
        .background(WordokuTheme.cardBackground)
        .overlay(
            RoundedRectangle(cornerRadius: 999)
                .stroke(WordokuTheme.divider, lineWidth: 1)
        )
        .clipShape(Capsule())
        .shadow(color: Color.black.opacity(0.05), radius: 6, x: 0, y: 2)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Level complete! The hidden word is \(forcedWord)")
        .accessibilityAddTraits(.isStaticText)
    }
}
