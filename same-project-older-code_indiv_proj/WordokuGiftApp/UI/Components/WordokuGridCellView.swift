import SwiftUI

struct WordokuGridCellView: View {
    let text: String
    let isGiven: Bool
    let isSelected: Bool
    let isConflict: Bool
    let isForced: Bool
    let size: CGFloat
    let row: Int
    let column: Int
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(text)
                .font(isGiven ? .headline.weight(.semibold) : .headline.weight(.regular))
                .foregroundColor(WordokuTheme.primaryText)
                .frame(width: size, height: size)
                .background(backgroundColor)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(accessibilityLabelText)
        .accessibilityHint(accessibilityHintText)
        .accessibilityAddTraits(isGiven ? .isStaticText : [])
        .accessibilityIdentifier("cell_\(row)_\(column)")
    }

    private var backgroundColor: Color {
        if isConflict { return WordokuTheme.conflictFill }
        if isSelected { return WordokuTheme.selectedFill }
        if isForced { return WordokuTheme.subtleFill }
        return Color.clear
    }

    private var accessibilityLabelText: String {
        let position = "Row \(row + 1), Column \(column + 1)"
        let content = text.isEmpty ? "Empty" : "Letter \(text)"
        let status = isGiven ? ", given" : ""
        let conflict = isConflict ? ", has conflict" : ""
        return "\(position), \(content)\(status)\(conflict)"
    }

    private var accessibilityHintText: String {
        if isGiven {
            return "This cell cannot be changed"
        }
        return isSelected ? "Cell is selected. Choose a letter from the palette" : "Double tap to select this cell"
    }
}
