import SwiftUI

struct MainMenuView: View {
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: WordokuTheme.spacingXL) {
                VStack(alignment: .leading, spacing: WordokuTheme.spacingS) {
                    Text("Wordoku")
                        .font(.system(size: 38, weight: .semibold, design: .serif))
                        .foregroundColor(WordokuTheme.primaryText)
                    Text("A calm word sudoku to start your day.")
                        .font(.callout)
                        .foregroundColor(WordokuTheme.secondaryText)
                }

                VStack(spacing: WordokuTheme.spacingM) {
                    NavigationLink {
                        LevelSelectView()
                    } label: {
                        MenuActionCard(
                            title: "Play",
                            subtitle: "Choose difficulty",
                            symbol: "grid",
                            badge: "Daily",
                            accent: WordokuTheme.accentBlue,
                            highlight: WordokuTheme.accentBlueWash
                        )
                    }

                    NavigationLink {
                        SettingsView()
                    } label: {
                        MenuActionCard(
                            title: "Settings",
                            subtitle: "Sound, haptics, mistakes",
                            symbol: "slider.horizontal.3",
                            badge: "Prefs",
                            accent: WordokuTheme.accentYellow,
                            highlight: WordokuTheme.accentYellowWash
                        )
                    }
                }

                Spacer()

                HStack(spacing: WordokuTheme.spacingS) {
                    Circle()
                        .fill(WordokuTheme.accentBlue)
                        .frame(width: 6, height: 6)
                    Rectangle()
                        .fill(WordokuTheme.divider)
                        .frame(height: 1)
                    Circle()
                        .fill(WordokuTheme.accentYellow)
                        .frame(width: 6, height: 6)
                }
            }
            .padding(.horizontal, WordokuTheme.spacingL)
            .padding(.top, WordokuTheme.spacingXL)
            .padding(.bottom, WordokuTheme.spacingL)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(WordokuPaperBackground())
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

private struct MenuActionCard: View {
    let title: String
    let subtitle: String
    let symbol: String
    let badge: String
    let accent: Color
    let highlight: Color

    var body: some View {
        VStack(alignment: .leading, spacing: WordokuTheme.spacingS) {
            HStack(alignment: .center, spacing: WordokuTheme.spacingS) {
                ZStack {
                    Circle()
                        .fill(accent.opacity(0.15))
                    Image(systemName: symbol)
                        .font(.footnote.weight(.semibold))
                        .foregroundColor(accent)
                }
                .frame(width: 34, height: 34)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.headline)
                        .foregroundColor(WordokuTheme.primaryText)
                    Text(subtitle)
                        .font(.footnote)
                        .foregroundColor(WordokuTheme.secondaryText)
                }

                Spacer()

                Text(badge.uppercased())
                    .font(.caption2.weight(.semibold))
                    .foregroundColor(accent)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(
                        Capsule()
                            .fill(accent.opacity(0.12))
                    )
            }
        }
        .padding(WordokuTheme.spacingM)
        .background(
            RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                .fill(WordokuTheme.cardBackground)
                .overlay(
                    RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                        .fill(highlight)
                )
        )
        .overlay(
            RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                .stroke(WordokuTheme.divider, lineWidth: WordokuTheme.borderWidth)
        )
        .shadow(color: WordokuTheme.cardShadow, radius: 10, x: 0, y: 6)
    }
}

#Preview {
    MainMenuView()
}
