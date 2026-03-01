import SwiftUI

struct GameView: View {
    @StateObject private var viewModel: GameViewModel
    let levelNumber: Int
    let difficulty: Difficulty
    let onComplete: () -> Void
    @State private var didNotify = false
    @State private var showWordIntro: Bool
    @State private var wordIntroVisible: Bool
    @State private var showCompletionPopup = false
    @Environment(\.dismiss) private var dismiss

    init(level: WordokuLevel, levelNumber: Int, difficulty: Difficulty, savedState: SavedGameState? = nil, onComplete: @escaping () -> Void = {}) {
        let vm = GameViewModel(level: level)
        let shouldShowWordIntro = !WordIntroTracker.hasSeen(levelNumber: levelNumber, difficulty: difficulty)
        if let saved = savedState {
            vm.restoreState(from: saved)
        }
        _viewModel = StateObject(wrappedValue: vm)
        _showWordIntro = State(initialValue: shouldShowWordIntro)
        _wordIntroVisible = State(initialValue: false)
        self.levelNumber = levelNumber
        self.difficulty = difficulty
        self.onComplete = onComplete
    }

    var body: some View {
        ZStack(alignment: .top) {
            ScrollView {
                VStack(spacing: WordokuTheme.spacingL) {
                    GameHeader(word: viewModel.level.word.raw, levelNumber: levelNumber)
                    
                    GridView(
                        grid: viewModel.grid,
                        letters: viewModel.letters,
                        selectedIndex: viewModel.selectedIndex,
                        givenIndices: viewModel.givenIndices,
                        conflictIndices: viewModel.conflictIndices,
                        forcedIndices: viewModel.forcedIndices,
                        orderedForcedIndices: viewModel.orderedForcedIndices,
                        isComplete: viewModel.isComplete,
                        isWordComplete: viewModel.isWordComplete,
                        onSelect: { viewModel.select(index: $0) }
                    )
                    .aspectRatio(1, contentMode: .fit)
                    .padding(.horizontal, WordokuTheme.spacingM)

                    GameControls(
                        showConflicts: $viewModel.showConflicts,
                        letters: viewModel.letters,
                        onSelectIndex: { viewModel.setValue($0) },
                        onDelete: { viewModel.setValue(nil) }
                    )

                    Spacer(minLength: WordokuTheme.spacingXL)
                }
                .padding(.top, WordokuTheme.spacingM)
            }
            .background(WordokuPaperBackground())

            if viewModel.isComplete {
                WinOverlayView(forcedWord: viewModel.level.word.raw)
                    .padding(.top, WordokuTheme.spacingM)
                    .transition(.opacity)
            }

            if showWordIntro {
                WordIntroOverlay(
                    word: viewModel.level.word.raw,
                    meaning: WordMeaningProvider.meaning(for: viewModel.level.word.raw),
                    isVisible: wordIntroVisible,
                    onDismiss: dismissWordIntro
                )
            }

            if showCompletionPopup {
                CompletionPopupOverlay(
                    word: viewModel.level.word.raw,
                    levelNumber: levelNumber,
                    onDismiss: { dismiss() },
                    onContinue: { dismiss() }
                )
            }
        }
        .animation(.easeInOut(duration: 0.18), value: viewModel.isComplete)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                HStack(spacing: 12) {
                    Button(action: { viewModel.undo() }) {
                        Image(systemName: "arrow.uturn.backward")
                            .foregroundColor(WordokuTheme.accentBlue)
                    }
                    .disabled(!viewModel.canUndo)
                    .opacity(viewModel.canUndo ? 1.0 : 0.3)
                    .accessibilityLabel("Undo")
                    
                    Button(action: { viewModel.redo() }) {
                        Image(systemName: "arrow.uturn.forward")
                            .foregroundColor(WordokuTheme.accentBlue)
                    }
                    .disabled(!viewModel.canRedo)
                    .opacity(viewModel.canRedo ? 1.0 : 0.3)
                    .accessibilityLabel("Redo")
                }
            }
        }
        .onChange(of: viewModel.isComplete) { newValue in
            if newValue && !didNotify {
                didNotify = true
                onComplete()
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                    withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
                        showCompletionPopup = true
                    }
                }
            }
        }
        .onAppear {
            guard showWordIntro else { return }
            withAnimation(.easeOut(duration: 0.4)) {
                wordIntroVisible = true
            }
        }
        .onDisappear {
            if viewModel.isComplete {
                GameViewModel.clearSavedState()
            } else {
                viewModel.saveState(levelIndex: levelNumber - 1, difficulty: difficulty)
            }
        }
    }

    private func dismissWordIntro() {
        WordIntroTracker.markSeen(levelNumber: levelNumber, difficulty: difficulty)
        withAnimation(.easeInOut(duration: 0.25)) {
            wordIntroVisible = false
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            showWordIntro = false
        }
    }
}

private enum WordIntroTracker {
    private static let defaults = UserDefaults.standard

    static func hasSeen(levelNumber: Int, difficulty: Difficulty) -> Bool {
        defaults.bool(forKey: key(levelNumber: levelNumber, difficulty: difficulty))
    }

    static func markSeen(levelNumber: Int, difficulty: Difficulty) {
        defaults.set(true, forKey: key(levelNumber: levelNumber, difficulty: difficulty))
    }

    private static func key(levelNumber: Int, difficulty: Difficulty) -> String {
        "wordoku.wordIntroSeen.\(difficulty.rawValue).\(levelNumber)"
    }
}

// MARK: - Game Header

private struct GameHeader: View {
    let word: String
    let levelNumber: Int
    
    var body: some View {
        VStack(spacing: WordokuTheme.spacingS) {
            Text("LEVEL \(levelNumber)")
                .font(.caption.weight(.semibold))
                .foregroundColor(WordokuTheme.secondaryText)
                .tracking(1.2)
            
            Text(word.uppercased())
                .font(.system(size: 32, weight: .bold, design: .serif))
                .tracking(6)
                .foregroundColor(WordokuTheme.primaryText)
        }
        .padding(.vertical, WordokuTheme.spacingS)
    }
}

// MARK: - Word Intro Overlay

private struct WordIntroOverlay: View {
    let word: String
    let meaning: String
    let isVisible: Bool
    let onDismiss: () -> Void

    @State private var showWord = false
    @State private var showMeaning = false
    @State private var showPrompt = false

    var body: some View {
        ZStack {
            WordokuPaperBackground()
                .overlay(Color.black.opacity(0.18).ignoresSafeArea())
                .onTapGesture { onDismiss() }

            VStack(spacing: 0) {
                Spacer(minLength: 0)

                VStack(spacing: WordokuTheme.spacingL) {
                    Text("Your Hidden Word")
                        .font(.caption.weight(.semibold))
                        .tracking(1.3)
                        .foregroundColor(WordokuTheme.secondaryText)
                        .opacity(showWord ? 1 : 0)

                    Text(word.uppercased())
                        .font(.system(size: 44, weight: .semibold, design: .serif))
                        .tracking(7)
                        .foregroundColor(WordokuTheme.primaryText)
                        .opacity(showWord ? 1 : 0)
                        .offset(y: showWord ? 0 : 10)

                    Text(meaning)
                        .font(.title3.weight(.regular))
                        .foregroundColor(WordokuTheme.secondaryText)
                        .multilineTextAlignment(.center)
                        .lineSpacing(6)
                        .padding(.horizontal, WordokuTheme.spacingXL)
                        .opacity(showMeaning ? 1 : 0)
                        .offset(y: showMeaning ? 0 : 12)

                    Text("Tap anywhere to begin")
                        .font(.footnote.weight(.medium))
                        .foregroundColor(WordokuTheme.secondaryText.opacity(0.9))
                        .padding(.top, WordokuTheme.spacingM)
                        .opacity(showPrompt ? 1 : 0)
                }

                Spacer(minLength: 0)
            }
            .padding(.vertical, WordokuTheme.spacingXL)
            .contentShape(Rectangle())
            .onTapGesture { onDismiss() }
        }
        .opacity(isVisible ? 1 : 0)
        .animation(.easeInOut(duration: 0.35), value: isVisible)
        .onChange(of: isVisible) { visible in
            if visible {
                runStagedReveal()
            }
        }
        .onAppear {
            if isVisible {
                runStagedReveal()
            }
        }
        .allowsHitTesting(isVisible)
    }

    private func runStagedReveal() {
        showWord = false
        showMeaning = false
        showPrompt = false

        withAnimation(.easeOut(duration: 0.45)) {
            showWord = true
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.28) {
            withAnimation(.easeOut(duration: 0.6)) {
                showMeaning = true
            }
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.75) {
            withAnimation(.easeOut(duration: 0.45)) {
                showPrompt = true
            }
        }
    }
}

// MARK: - Game Controls

private struct GameControls: View {
    @Binding var showConflicts: Bool
    let letters: [Character]
    let onSelectIndex: (Int) -> Void
    let onDelete: () -> Void
    
    var body: some View {
        VStack(spacing: WordokuTheme.spacingM) {
            HStack {
                Text("Show conflicts")
                    .font(.subheadline)
                    .foregroundColor(WordokuTheme.primaryText)
                Spacer()
                Toggle("", isOn: $showConflicts)
                    .labelsHidden()
                    .tint(WordokuTheme.accentBlue)
            }
            .padding(.horizontal, WordokuTheme.spacingM)
            .padding(.vertical, WordokuTheme.spacingS)
            .background(
                RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                    .fill(WordokuTheme.cardBackground)
                    .overlay(
                        RoundedRectangle(cornerRadius: WordokuTheme.cornerRadius)
                            .stroke(WordokuTheme.divider, lineWidth: WordokuTheme.borderWidth)
                    )
            )
            .padding(.horizontal, WordokuTheme.spacingL)
            
            LetterPaletteView(
                letters: letters,
                onSelect: onSelectIndex,
                onDelete: onDelete
            )
            .padding(.horizontal, WordokuTheme.spacingL)
        }
    }
}

// MARK: - Completion Popup Overlay

private struct CompletionPopupOverlay: View {
    let word: String
    let levelNumber: Int
    let onDismiss: () -> Void
    let onContinue: () -> Void
    @State private var isVisible = false

    var body: some View {
        ZStack {
            Color.black.opacity(0.4)
                .ignoresSafeArea()
                .onTapGesture {
                    onDismiss()
                }

            VStack(spacing: WordokuTheme.spacingL) {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 56))
                    .foregroundColor(WordokuTheme.accentBlue)

                VStack(spacing: WordokuTheme.spacingS) {
                    Text("Level \(levelNumber) Complete!")
                        .font(.system(size: 24, weight: .bold, design: .serif))
                        .foregroundColor(WordokuTheme.primaryText)

                    Text("You found the word")
                        .font(.subheadline)
                        .foregroundColor(WordokuTheme.secondaryText)

                    Text(word.uppercased())
                        .font(.system(size: 28, weight: .semibold, design: .serif))
                        .tracking(4)
                        .foregroundColor(WordokuTheme.accentBlue)
                        .padding(.top, WordokuTheme.spacingXS)
                }

                Button(action: onContinue) {
                    Text("Continue")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(WordokuTheme.accentBlue)
                        .cornerRadius(12)
                }
                .padding(.top, WordokuTheme.spacingS)
            }
            .padding(WordokuTheme.spacingXL)
            .background(
                RoundedRectangle(cornerRadius: 24)
                    .fill(WordokuTheme.cardBackground)
                    .overlay(
                        RoundedRectangle(cornerRadius: 24)
                            .stroke(WordokuTheme.divider, lineWidth: WordokuTheme.borderWidth)
                    )
            )
            .shadow(color: Color.black.opacity(0.2), radius: 24, y: 12)
            .padding(WordokuTheme.spacingL)
            .opacity(isVisible ? 1 : 0)
            .scaleEffect(isVisible ? 1 : 0.9)
        }
        .onAppear {
            withAnimation(.spring(response: 0.4, dampingFraction: 0.75)) {
                isVisible = true
            }
        }
    }
}
