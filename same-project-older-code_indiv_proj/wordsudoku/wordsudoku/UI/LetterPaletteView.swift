import SwiftUI

struct LetterPaletteView: View {
    let letters: [Character]
    let onSelect: (Int) -> Void
    let onDelete: () -> Void

    private var columns: [GridItem] {
        Array(repeating: GridItem(.flexible(), spacing: WordokuTheme.spacingS), count: 5)
    }

    var body: some View {
        LazyVGrid(columns: columns, spacing: WordokuTheme.spacingS) {
            ForEach(0..<letters.count, id: \.self) { index in
                paletteButton(label: String(letters[index]), accessibilityLabel: "Letter \(letters[index])") {
                    onSelect(index)
                }
            }
            paletteButton(label: "Del", accessibilityLabel: "Delete") {
                onDelete()
            }
        }
        .padding(WordokuTheme.spacingM)
        .wordokuCard()
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Letter palette")
    }

    private func paletteButton(label: String, accessibilityLabel: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(label)
                .font(.headline)
                .foregroundColor(WordokuTheme.primaryText)
                .frame(maxWidth: .infinity, minHeight: 44)
                .background(WordokuTheme.background)
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(WordokuTheme.divider, lineWidth: 1)
                )
                .cornerRadius(10)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityHint("Double tap to enter this value")
        .accessibilityIdentifier("palette_\(label)")
    }
}
