import SwiftUI

struct LevelSelectView: View {
    @StateObject private var viewModel = LevelSelectViewModel()
    @State private var savedState: SavedGameState?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: WordokuTheme.spacingXL) {
                LevelSelectHeader(
                    completedCount: viewModel.completedLevels.count,
                    totalCount: viewModel.levelCount,
                    difficulty: viewModel.difficulty.rawValue.capitalized
                )

                VStack(alignment: .leading, spacing: WordokuTheme.spacingS) {
                    Text("DIFFICULTY")
                        .font(.caption.weight(.semibold))
                        .foregroundColor(WordokuTheme.secondaryText)
                        .tracking(1.2)
                    
                    Picker("Difficulty", selection: $viewModel.difficulty) {
                        ForEach(Difficulty.allCases, id: \.self) { difficulty in
                            Text(difficulty.rawValue.capitalized).tag(difficulty)
                        }
                    }
                    .pickerStyle(.segmented)
                    .tint(WordokuTheme.accentBlue)
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
                
                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(.footnote)
                        .foregroundColor(.red)
                        .padding(.horizontal, WordokuTheme.spacingS)
                }

                if viewModel.unlockedCount > 0 {
                    LevelSection(title: "Available") {
                        ForEach(0..<viewModel.unlockedCount, id: \.self) { index in
                            let word = viewModel.words[index]
                            let isCompleted = viewModel.completedLevels.contains(index)
                            let inProgressState = savedStateForLevel(index: index)
                            
                            NavigationLink {
                                if let level = viewModel.makeLevel(index: index) {
                                    GameView(
                                        level: level,
                                        levelNumber: index + 1,
                                        difficulty: viewModel.difficulty,
                                        savedState: inProgressState,
                                        onComplete: {
                                            viewModel.markCompleted(index: index)
                                            if inProgressState != nil {
                                                savedState = nil
                                            }
                                        }
                                    )
                                    .id("\(index)-\(viewModel.difficulty.rawValue)")
                                } else {
                                    Text("Failed to generate level.")
                                }
                            } label: {
                                LevelCard(
                                    levelNumber: index + 1,
                                    label: word.raw.uppercased(),
                                    isLocked: false,
                                    isCompleted: isCompleted,
                                    isInProgress: inProgressState != nil
                                )
                            }
                        }
                    }
                }

                if viewModel.unlockedCount < viewModel.levelCount {
                    LevelSection(title: "Locked") {
                        ForEach(viewModel.unlockedCount..<viewModel.levelCount, id: \.self) { index in
                            LevelCard(
                                levelNumber: index + 1,
                                label: "???",
                                isLocked: true,
                                isCompleted: false,
                                isInProgress: false
                            )
                        }
                    }
                }

                HomeFooterRule()
            }
            .padding(.horizontal, WordokuTheme.spacingL)
            .padding(.top, WordokuTheme.spacingM)
            .padding(.bottom, WordokuTheme.spacingL)
        }
        .background(WordokuPaperBackground())
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            savedState = GameViewModel.loadSavedState()
        }
        .onChange(of: viewModel.difficulty) { _ in
            savedState = GameViewModel.loadSavedState()
        }
    }

    private func savedStateForLevel(index: Int) -> SavedGameState? {
        guard let savedState,
              savedState.difficulty == viewModel.difficulty.rawValue,
              savedState.levelIndex == index else {
            return nil
        }
        return savedState
    }
}

// MARK: - Header

private struct LevelSelectHeader: View {
    let completedCount: Int
    let totalCount: Int
    let difficulty: String

    var body: some View {
        VStack(alignment: .leading, spacing: WordokuTheme.spacingS) {
            Text("\(difficulty) Levels")
                .font(.title2.weight(.semibold))
                .foregroundColor(WordokuTheme.primaryText)
            
            HStack(spacing: WordokuTheme.spacingS) {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(WordokuTheme.accentBlue)
                    .font(.footnote)
                Text("\(completedCount) of \(totalCount) completed")
                    .font(.footnote)
                    .foregroundColor(WordokuTheme.secondaryText)
            }
        }
    }
}

// MARK: - Level Section

private struct LevelSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: WordokuTheme.spacingM) {
            Text(title.uppercased())
                .font(.caption.weight(.semibold))
                .foregroundColor(WordokuTheme.secondaryText)
                .tracking(1.2)
            
            VStack(spacing: WordokuTheme.spacingS) {
                content
            }
        }
    }
}

// MARK: - Level Card

private struct LevelCard: View {
    let levelNumber: Int
    let label: String
    let isLocked: Bool
    let isCompleted: Bool
    let isInProgress: Bool

    var body: some View {
        HStack(spacing: WordokuTheme.spacingM) {
            ZStack {
                Circle()
                    .fill(isLocked ? WordokuTheme.subtleFill : (isCompleted ? WordokuTheme.accentBlue : (isInProgress ? WordokuTheme.accentInk : WordokuTheme.accentYellow)))
                    .frame(width: 36, height: 36)
                
                if isLocked {
                    Image(systemName: "lock.fill")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(WordokuTheme.secondaryText)
                } else {
                    Text("\(levelNumber)")
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundColor(isCompleted || isInProgress ? .white : WordokuTheme.primaryText)
                }
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(isLocked ? "Level \(levelNumber)" : label)
                    .font(.headline)
                    .foregroundColor(isLocked ? WordokuTheme.secondaryText : WordokuTheme.primaryText)
                
                if isCompleted {
                    Text("Completed")
                        .font(.caption)
                        .foregroundColor(WordokuTheme.accentBlue)
                } else if isInProgress {
                    Text("In progress")
                        .font(.caption)
                        .foregroundColor(WordokuTheme.accentInk)
                } else if !isLocked {
                    Text("9 letters")
                        .font(.caption)
                        .foregroundColor(WordokuTheme.secondaryText)
                }
            }

            Spacer()

            if !isLocked {
                Image(systemName: "chevron.right")
                    .font(.footnote.weight(.semibold))
                    .foregroundColor(WordokuTheme.secondaryText)
            }
        }
        .padding(WordokuTheme.spacingM)
        .background(
            RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                .fill(isLocked ? WordokuTheme.subtleFill.opacity(0.5) : WordokuTheme.cardBackground)
                .overlay(
                    RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                        .stroke(WordokuTheme.divider, lineWidth: WordokuTheme.borderWidth)
                )
        )
        .shadow(color: isLocked ? .clear : WordokuTheme.cardShadow, radius: 8, x: 0, y: 4)
        .opacity(isLocked ? 0.7 : 1.0)
    }
}

private struct HomeFooterRule: View {
    var body: some View {
        HStack(spacing: WordokuTheme.spacingS) {
            Rectangle()
                .fill(WordokuTheme.divider)
                .frame(height: 1)
            Circle()
                .fill(WordokuTheme.accentYellow)
                .frame(width: 6, height: 6)
            Rectangle()
                .fill(WordokuTheme.divider)
                .frame(height: 1)
        }
    }
}
