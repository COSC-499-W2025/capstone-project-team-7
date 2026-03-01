import SwiftUI

struct MainMenuView: View {
    @State private var summary = ProgressSummary(levelCount: 0, easyCompleted: 0, mediumCompleted: 0, hardCompleted: 0)
    @State private var preferredDifficulty: Difficulty = .easy
    private let levelCount: Int = {
        let loader = WordListLoader()
        return min(loader.loadWords().count, 30)
    }()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: WordokuTheme.spacingXL) {
                    VStack(alignment: .leading, spacing: WordokuTheme.spacingS) {
                        Text("Wordoku")
                            .font(.system(size: 40, weight: .semibold, design: .serif))
                            .foregroundColor(WordokuTheme.primaryText)
                        Text("A letter puzzle with newspaper calm.")
                            .font(.subheadline)
                            .foregroundColor(WordokuTheme.secondaryText)
                    }

                    MainMenuProgressCard(
                        summary: summary,
                        preferredDifficulty: preferredDifficulty,
                        levelCount: max(levelCount, 1)
                    )

                    VStack(spacing: WordokuTheme.spacingM) {
                        NavigationLink {
                            LevelSelectView()
                        } label: {
                            MenuActionCard(
                                title: "Play",
                                subtitle: "Open your next level",
                                symbol: "newspaper.fill",
                                badge: preferredDifficulty.rawValue.capitalized,
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

                    Spacer(minLength: WordokuTheme.spacingL)
                }
                .padding(.horizontal, WordokuTheme.spacingL)
                .padding(.top, WordokuTheme.spacingXL)
                .padding(.bottom, WordokuTheme.spacingL)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(WordokuPaperBackground())
            .navigationBarTitleDisplayMode(.inline)
            .onAppear {
                summary = ProgressStore.loadSummary(levelCount: max(levelCount, 1))
                preferredDifficulty = ProgressStore.loadSelectedDifficulty()
            }
        }
    }
}

private struct MainMenuProgressCard: View {
    let summary: ProgressSummary
    let preferredDifficulty: Difficulty
    let levelCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: WordokuTheme.spacingM) {
            Text("Completed Levels")
                .font(.headline)
                .foregroundColor(WordokuTheme.primaryText)

            HStack(alignment: .firstTextBaseline, spacing: WordokuTheme.spacingS) {
                Text("\(summary.totalCompleted)")
                    .font(.system(size: 34, weight: .semibold, design: .default))
                    .foregroundColor(WordokuTheme.primaryText)
                Text("of \(summary.totalAvailable)")
                    .font(.subheadline)
                    .foregroundColor(WordokuTheme.secondaryText)
            }

            HStack(spacing: WordokuTheme.spacingS) {
                DifficultyProgressPill(title: "Easy", completed: summary.easyCompleted, total: levelCount)
                DifficultyProgressPill(title: "Medium", completed: summary.mediumCompleted, total: levelCount)
                DifficultyProgressPill(title: "Hard", completed: summary.hardCompleted, total: levelCount)
            }

            Text("Last selected: \(preferredDifficulty.rawValue.capitalized)")
                .font(.footnote)
                .foregroundColor(WordokuTheme.secondaryText)
        }
        .padding(WordokuTheme.spacingM)
        .background(
            RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                .fill(WordokuTheme.cardBackground)
                .overlay(
                    RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                        .stroke(WordokuTheme.divider, lineWidth: WordokuTheme.borderWidth)
                )
        )
        .shadow(color: WordokuTheme.cardShadow, radius: 10, x: 0, y: 6)
    }
}

private struct DifficultyProgressPill: View {
    let title: String
    let completed: Int
    let total: Int

    var body: some View {
        VStack(spacing: 2) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundColor(WordokuTheme.secondaryText)
            Text("\(completed)/\(total)")
                .font(.footnote.weight(.medium))
                .foregroundColor(WordokuTheme.primaryText)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(WordokuTheme.subtleFill)
        .clipShape(RoundedRectangle(cornerRadius: 10))
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
