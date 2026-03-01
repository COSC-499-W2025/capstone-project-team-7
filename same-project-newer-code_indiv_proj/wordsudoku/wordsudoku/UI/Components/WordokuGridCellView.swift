import SwiftUI

struct WordokuGridCellView: View {
    let text: String
    let isGiven: Bool
    let isSelected: Bool
    let isConflict: Bool
    let isForced: Bool
    let isWordCell: Bool
    let isRelated: Bool
    let isSameLetter: Bool
    let size: CGFloat
    let row: Int
    let column: Int
    let animationIndex: Int?
    let action: () -> Void

    var body: some View {
        Text(text)
            .font(isGiven ? .headline.weight(.semibold) : .headline.weight(.regular))
            .foregroundColor(isWordCell ? WordokuTheme.accentBlue : WordokuTheme.primaryText)
            .frame(width: size, height: size)
            .background(backgroundColor)
            .contentShape(Rectangle())
            .onTapGesture {
                action()
            }
            .scaleEffect(isWordCell ? 1.15 : 1.0)
            .offset(y: isWordCell ? -4 : 0)
            .zIndex(isWordCell ? 1 : 0)
            .animation(.spring(response: 0.4, dampingFraction: 0.5), value: isWordCell)
            .accessibilityLabel(accessibilityLabelText)
            .accessibilityHint(accessibilityHintText)
            .accessibilityAddTraits(isGiven ? .isStaticText : .isButton)
            .accessibilityIdentifier("cell_\(row)_\(column)")
    }

    private var backgroundColor: Color {
        if isConflict { return WordokuTheme.conflictFill }
        if isWordCell { return WordokuTheme.accentYellowWash }
        if isSelected { return WordokuTheme.selectedCellFill }
        if isSameLetter { return WordokuTheme.sameLetterFill }
        if isRelated { return WordokuTheme.relatedCellFill }
        if isForced { return WordokuTheme.subtleFill }
        return Color.clear
    }

    private var accessibilityLabelText: String {
        let position = "Row \(row + 1), Column \(column + 1)"
        let content = text.isEmpty ? "Empty" : "Letter \(text)"
        let status = isGiven ? ", given" : ""
        let conflict = isConflict ? ", has conflict" : ""
        let wordFound = isWordCell ? ", word found" : ""
        return "\(position), \(content)\(status)\(conflict)\(wordFound)"
    }

    private var accessibilityHintText: String {
        if isGiven {
            return "This cell cannot be changed"
        }
        return isSelected ? "Cell is selected. Choose a letter from the palette" : "Double tap to select this cell"
    }
}
