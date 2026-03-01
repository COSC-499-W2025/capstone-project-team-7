import Foundation
import SwiftUI
import Combine

@MainActor
final class LevelSelectViewModel: ObservableObject {
    @Published var words: [WordokuWord] = []
    @Published var unlockedCount: Int = 1 {
        didSet { saveProgressIfNeeded() }
    }
    @Published var completedLevels: Set<Int> = [] {
        didSet { saveProgressIfNeeded() }
    }
    @Published var difficulty: Difficulty = .easy {
        didSet {
            guard oldValue != difficulty else { return }
            guard hasLoadedProgress else { return }
            ProgressStore.saveSelectedDifficulty(difficulty)
            loadProgressForCurrentDifficulty()
        }
    }
    @Published var errorMessage: String?

    private let loader = WordListLoader()
    private let factory = WordokuLevelFactory()
    private let maxLevels = 30
    private var hasLoadedProgress = false
    private var isApplyingProgress = false

    init() {
        loadWords()
        difficulty = ProgressStore.loadSelectedDifficulty()
        loadProgressForCurrentDifficulty()
        hasLoadedProgress = true
        saveProgressIfNeeded()
    }

    var levelCount: Int {
        words.count
    }

    func loadWords() {
        let loaded = loader.loadWords()
        if loaded.isEmpty {
            if let fallback = WordokuWord(raw: "ABCDEFGHI") {
                words = [fallback]
                errorMessage = "wordlist.txt missing or invalid."
            } else {
                words = []
                errorMessage = "No valid words available."
            }
        } else {
            words = Array(loaded.prefix(maxLevels))
            errorMessage = nil
        }
        if words.isEmpty {
            unlockedCount = 0
        } else if unlockedCount < 1 {
            unlockedCount = 1
        } else if unlockedCount > words.count {
            unlockedCount = words.count
        }
        completedLevels = Set(completedLevels.filter { $0 < words.count })

        if hasLoadedProgress {
            loadProgressForCurrentDifficulty()
        }
    }

    func isLocked(index: Int) -> Bool {
        index >= unlockedCount
    }

    func makeLevel(index: Int) -> WordokuLevel? {
        guard index >= 0, index < words.count else { return nil }
        var rng: RandomNumberGenerator = SeededGenerator(seed: seed(for: index))
        let axes: [ForcedAxis] = [.row, .col, .diagonal, .antiDiagonal]
        let axis = axes[Int(rng.next() % UInt64(axes.count))]
        let forcedIndex = Int(rng.next() % 9)
        return factory.makeLevel(
            word: words[index],
            difficulty: difficulty,
            forcedAxis: axis,
            forcedIndex: forcedIndex,
            rng: &rng
        )
    }

    func markCompleted(index: Int) {
        completedLevels.insert(index)
        let nextUnlocked = min(index + 2, words.count)
        if nextUnlocked > unlockedCount {
            unlockedCount = nextUnlocked
        }
    }

    private func seed(for index: Int) -> UInt64 {
        let diffSeed: UInt64
        switch difficulty {
        case .easy: diffSeed = 1
        case .medium: diffSeed = 2
        case .hard: diffSeed = 3
        }
        return UInt64(index + 1) &* 0x9E3779B97F4A7C15 ^ diffSeed
    }

    private func loadProgressForCurrentDifficulty() {
        let progress = ProgressStore.loadProgress(for: difficulty, levelCount: words.count)
        isApplyingProgress = true
        unlockedCount = progress.unlockedCount
        completedLevels = progress.completedLevels
        isApplyingProgress = false
    }

    private func saveProgressIfNeeded() {
        guard hasLoadedProgress, !isApplyingProgress else { return }
        ProgressStore.saveSelectedDifficulty(difficulty)
        ProgressStore.saveProgress(for: difficulty, unlockedCount: unlockedCount, completedLevels: completedLevels)
    }
}
