import SwiftUI

struct LevelSelectView: View {
    @StateObject private var viewModel = LevelSelectViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: WordokuTheme.spacingM) {
                VStack(alignment: .leading, spacing: WordokuTheme.spacingS) {
                    Text("Wordoku")
                        .font(.system(size: 34, weight: .semibold, design: .serif))
                        .foregroundColor(WordokuTheme.primaryText)
                    Text("Select a puzzle to begin.")
                        .font(.callout)
                        .foregroundColor(WordokuTheme.secondaryText)
                    HStack {
                        Text("Progress")
                            .wordokuSubtleText()
                        Spacer()
                        Text("\(viewModel.completedLevels.count) of \(viewModel.levelCount)")
                            .wordokuSubtleText()
                    }
                    .wordokuDivider()
                    Picker("Difficulty", selection: $viewModel.difficulty) {
                        ForEach(Difficulty.allCases, id: \.self) { difficulty in
                            Text(difficulty.rawValue.capitalized).tag(difficulty)
                        }
                    }
                    .pickerStyle(.segmented)
                    .tint(WordokuTheme.accentBlue)
                }
                .padding(.horizontal, WordokuTheme.spacingL)
                if let error = viewModel.errorMessage {
                    Text(error)
                        .wordokuSubtleText()
                        .padding(.horizontal, WordokuTheme.spacingL)
                }
                List {
                    if viewModel.unlockedCount > 0 {
                        Section(header: Text("Available").sectionHeader()) {
                            ForEach(0..<viewModel.unlockedCount, id: \.self) { index in
                                let word = viewModel.words[index]
                                NavigationLink {
                                    if let level = viewModel.makeLevel(index: index) {
                                        GameView(level: level, levelNumber: index + 1, onComplete: {
                                            viewModel.markCompleted(index: index)
                                        })
                                        .id("\(index)-\(viewModel.difficulty.rawValue)")
                                    } else {
                                        Text("Failed to generate level.")
                                    }
                                } label: {
                                    WordokuCardRow(
                                        levelNumber: index + 1,
                                        label: word.raw,
                                        isLocked: false,
                                        isCompleted: viewModel.completedLevels.contains(index)
                                    )
                                }
                                .listRowBackground(Color.clear)
                                .listRowSeparator(.hidden)
                                .listRowInsets(EdgeInsets(top: WordokuTheme.spacingS, leading: WordokuTheme.spacingL, bottom: WordokuTheme.spacingS, trailing: WordokuTheme.spacingL))
                            }
                        }
                    }
                    if viewModel.unlockedCount < viewModel.levelCount {
                        Section(header: Text("Locked").sectionHeader()) {
                            ForEach(viewModel.unlockedCount..<viewModel.levelCount, id: \.self) { index in
                                WordokuCardRow(
                                    levelNumber: index + 1,
                                    label: "Locked",
                                    isLocked: true,
                                    isCompleted: false
                                )
                                .listRowBackground(Color.clear)
                                .listRowSeparator(.hidden)
                                .listRowInsets(EdgeInsets(top: WordokuTheme.spacingS, leading: WordokuTheme.spacingL, bottom: WordokuTheme.spacingS, trailing: WordokuTheme.spacingL))
                            }
                        }
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            }
            .padding(.top, WordokuTheme.spacingM)
            .background(WordokuPaperBackground())
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

private extension Text {
    func sectionHeader() -> some View {
        font(.caption.weight(.semibold))
            .foregroundColor(WordokuTheme.secondaryText)
            .textCase(.uppercase)
            .tracking(1.2)
    }
}
