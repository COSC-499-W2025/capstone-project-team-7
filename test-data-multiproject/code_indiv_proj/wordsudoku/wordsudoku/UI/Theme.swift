import SwiftUI

enum WordokuTheme {
    #if os(iOS)
    static let background = Color(uiColor: .systemBackground)
    static let cardBackground = Color(uiColor: .secondarySystemBackground)
    static let primaryText = Color.primary
    static let secondaryText = Color.secondary
    static let divider = Color(uiColor: .separator).opacity(0.6)
    static let subtleFill = Color(uiColor: .systemGray6)
    static let selectedFill = Color(uiColor: .systemGray5)
    static let conflictFill = Color(uiColor: .systemGray4)
    static let forcedFill = Color(uiColor: .systemGray5)
    #elseif os(macOS)
    static let background = Color(nsColor: .windowBackgroundColor)
    static let cardBackground = Color(nsColor: .controlBackgroundColor)
    static let primaryText = Color.primary
    static let secondaryText = Color.secondary
    static let divider = Color(nsColor: .separatorColor).opacity(0.6)
    static let subtleFill = Color(nsColor: .systemGray)
    static let selectedFill = Color(nsColor: .lightGray)
    static let conflictFill = Color(nsColor: .darkGray)
    static let forcedFill = Color(nsColor: .lightGray)
    #endif

    static let cornerRadius: CGFloat = 14
    static let borderWidth: CGFloat = 1

    static let spacingXS: CGFloat = 4
    static let spacingS: CGFloat = 8
    static let spacingM: CGFloat = 16
    static let spacingL: CGFloat = 24
    static let spacingXL: CGFloat = 32
}

struct WordokuCardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(WordokuTheme.cardBackground)
            .overlay(
                RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                    .stroke(WordokuTheme.divider, lineWidth: WordokuTheme.borderWidth)
            )
            .clipShape(RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius))
    }
}

struct WordokuTitleModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.title2.weight(.semibold))
            .foregroundColor(WordokuTheme.primaryText)
    }
}

struct WordokuSubtleTextModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.footnote.weight(.medium))
            .foregroundColor(WordokuTheme.secondaryText)
    }
}

struct WordokuDividerModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .overlay(alignment: .bottom) {
                Rectangle()
                    .fill(WordokuTheme.divider)
                    .frame(height: 0.5)
            }
    }
}

extension View {
    func wordokuCard() -> some View {
        modifier(WordokuCardModifier())
    }

    func wordokuTitle() -> some View {
        modifier(WordokuTitleModifier())
    }

    func wordokuSubtleText() -> some View {
        modifier(WordokuSubtleTextModifier())
    }

    func wordokuDivider() -> some View {
        modifier(WordokuDividerModifier())
    }
}
