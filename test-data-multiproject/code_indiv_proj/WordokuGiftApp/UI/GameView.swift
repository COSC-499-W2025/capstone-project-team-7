import SwiftUI

struct GameView: View {
    @StateObject private var viewModel: GameViewModel
    let levelNumber: Int
    let onComplete: () -> Void
    @State private var didNotify = false

    init(level: WordokuLevel, levelNumber: Int, onComplete: @escaping () -> Void = {}) {
        _viewModel = StateObject(wrappedValue: GameViewModel(level: level))
        self.levelNumber = levelNumber
        self.onComplete = onComplete
    }

    var body: some View {
        ZStack(alignment: .top) {
            ScrollView {
                VStack(spacing: WordokuTheme.spacingL) {
                    GridView(
                        grid: viewModel.grid,
                        letters: viewModel.letters,
                        selectedIndex: viewModel.selectedIndex,
                        givenIndices: viewModel.givenIndices,
                        conflictIndices: viewModel.conflictIndices,
                        forcedIndices: viewModel.forcedIndices,
                        isComplete: viewModel.isComplete,
                        onSelect: { viewModel.select(index: $0) }
                    )
                    .aspectRatio(1, contentMode: .fit)
                    .padding(WordokuTheme.spacingM)
                    .wordokuCard()
                    .padding(.horizontal, WordokuTheme.spacingL)
                    .padding(.top, WordokuTheme.spacingM)

                    VStack(spacing: WordokuTheme.spacingM) {
                        Toggle(isOn: $viewModel.showConflicts) {
                            Text("Highlight Conflicts")
                                .font(.body)
                        }
                        .toggleStyle(.switch)
                        .tint(WordokuTheme.accentBlue)
                        .padding(WordokuTheme.spacingM)
                        .wordokuCard()
                        .padding(.horizontal, WordokuTheme.spacingL)
                        .accessibilityLabel("Show conflicts")
                        .accessibilityHint("When enabled, cells with invalid values are highlighted")

                        LetterPaletteView(
                            letters: viewModel.letters,
                            onSelect: { viewModel.setValue($0) },
                            onDelete: { viewModel.setValue(nil) }
                        )
                        .padding(.horizontal, WordokuTheme.spacingL)
                    }

                    Spacer(minLength: WordokuTheme.spacingL)
                }
            }
            .background(WordokuPaperBackground())

            if viewModel.isComplete {
                WinOverlayView(forcedWord: viewModel.level.word.raw)
                    .padding(.top, WordokuTheme.spacingM)
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.18), value: viewModel.isComplete)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) {
                Text("Wordoku")
                    .font(.system(size: 20, weight: .semibold, design: .serif))
                    .foregroundColor(WordokuTheme.primaryText)
            }
            ToolbarItem(placement: .navigationBarTrailing) {
                Text("Level \(levelNumber)")
                    .wordokuSubtleText()
            }
        }
        .onChange(of: viewModel.isComplete) { newValue in
            if newValue && !didNotify {
                didNotify = true
                onComplete()
            }
        }
    }
}
