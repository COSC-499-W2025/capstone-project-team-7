import SwiftUI

enum WordokuTheme {
    static let background = Color(red: 0.985, green: 0.98, blue: 0.972)
    static let cardBackground = Color(red: 0.998, green: 0.997, blue: 0.994)
    static let primaryText = Color(red: 0.08, green: 0.08, blue: 0.09)
    static let secondaryText = Color(red: 0.36, green: 0.36, blue: 0.38)
    static let divider = Color(red: 0.1, green: 0.1, blue: 0.12, opacity: 0.12)
    static let subtleFill = Color(red: 0.965, green: 0.962, blue: 0.952)
    static let selectedFill = Color(red: 0.9, green: 0.94, blue: 0.99)
    static let conflictFill = Color(red: 0.985, green: 0.9, blue: 0.82)
    static let forcedFill = Color(red: 0.94, green: 0.95, blue: 0.94)
    static let accentBlue = Color(red: 0.1, green: 0.28, blue: 0.65)
    static let accentYellow = Color(red: 0.88, green: 0.72, blue: 0.2)
    static let accentInk = Color(red: 0.14, green: 0.14, blue: 0.16)
    static let accentBlueWash = Color(red: 0.1, green: 0.28, blue: 0.65).opacity(0.08)
    static let accentYellowWash = Color(red: 0.88, green: 0.72, blue: 0.2).opacity(0.14)
    static let cardShadow = Color.black.opacity(0.06)
    static let paperDot = Color.black.opacity(0.028)
    
    static let selectedCellFill = Color(red: 1.0, green: 0.976, blue: 0.89)
    static let relatedCellFill = Color(red: 0.98, green: 0.98, blue: 0.98)
    static let sameLetterFill = Color(red: 0.93, green: 0.96, blue: 0.99)

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
            .shadow(color: WordokuTheme.cardShadow, radius: 10, x: 0, y: 6)
    }
}

struct WordokuPaperBackground: View {
    var body: some View {
        ZStack {
            WordokuTheme.background
            WordokuPaperTexture()
        }
        .ignoresSafeArea()
    }
}

struct WordokuPaperTexture: View {
    var body: some View {
        GeometryReader { proxy in
            Canvas { context, size in
                let dotSize: CGFloat = 1.4
                let spacing: CGFloat = 18
                var path = Path()
                for y in stride(from: 0, through: size.height, by: spacing) {
                    for x in stride(from: 0, through: size.width, by: spacing) {
                        path.addEllipse(in: CGRect(x: x, y: y, width: dotSize, height: dotSize))
                    }
                }
                context.fill(path, with: .color(WordokuTheme.paperDot))
            }
        }
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
