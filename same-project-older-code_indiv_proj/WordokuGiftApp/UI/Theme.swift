import SwiftUI

enum WordokuTheme {
    static let background = Color(red: 0.99, green: 0.985, blue: 0.97)
    static let cardBackground = Color(red: 0.995, green: 0.992, blue: 0.985)
    static let primaryText = Color.primary
    static let secondaryText = Color.secondary
    static let divider = Color(red: 0.1, green: 0.1, blue: 0.12, opacity: 0.18)
    static let subtleFill = Color(red: 0.97, green: 0.965, blue: 0.95)
    static let selectedFill = Color(red: 0.9, green: 0.93, blue: 0.98)
    static let conflictFill = Color(red: 0.98, green: 0.9, blue: 0.72)
    static let forcedFill = Color(red: 0.93, green: 0.94, blue: 0.92)
    static let accentBlue = Color(red: 0.12, green: 0.33, blue: 0.72)
    static let accentYellow = Color(red: 0.95, green: 0.78, blue: 0.2)
    static let accentBlueWash = Color(red: 0.12, green: 0.33, blue: 0.72).opacity(0.08)
    static let accentYellowWash = Color(red: 0.95, green: 0.78, blue: 0.2).opacity(0.12)
    static let cardShadow = Color.black.opacity(0.08)
    static let paperDot = Color.black.opacity(0.035)

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
            LinearGradient(
                colors: [WordokuTheme.background, WordokuTheme.accentYellowWash],
                startPoint: .top,
                endPoint: .bottom
            )
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
