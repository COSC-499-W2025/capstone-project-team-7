import Foundation
import SwiftUI
import Combine

@MainActor
final class LevelSelectViewModel: ObservableObject {
    @Published var words: [WordokuWord] = []
    @Published var unlockedCount: Int = 1 {
        didSet { saveProgress() }
    }
    @Published var completedLevels: Set<Int> = [] {
        didSet { saveProgress() }
    }
    @Published var difficulty: Difficulty = .easy {
        didSet { saveProgress() }
    }
    @Published var errorMessage: String?

    private let loader = WordListLoader()
    private let factory = WordokuLevelFactory()
    private let maxLevels = 30
    private let progressStore = UserDefaults.standard
    private var hasLoadedProgress = false

    init() {
        loadProgress()
        loadWords()
        hasLoadedProgress = true
        saveProgress()
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
    }

    func isLocked(index: Int) -> Bool {
        index >= unlockedCount
    }

    func makeLevel(index: Int) -> WordokuLevel? {
        guard index >= 0, index < words.count else { return nil }
        var rng: RandomNumberGenerator = SeededGenerator(seed: seed(for: index))
        let axis: ForcedAxis = (rng.next() % 2 == 0) ? .row : .col
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

    private func loadProgress() {
        let savedUnlocked = progressStore.integer(forKey: ProgressKeys.unlockedCount)
        if savedUnlocked > 0 {
            unlockedCount = savedUnlocked
        }
        if let savedCompleted = progressStore.array(forKey: ProgressKeys.completedLevels) as? [Int] {
            completedLevels = Set(savedCompleted)
        }
        if let savedDifficulty = progressStore.string(forKey: ProgressKeys.difficulty),
           let parsed = Difficulty(rawValue: savedDifficulty) {
            difficulty = parsed
        }
    }

    private func saveProgress() {
        guard hasLoadedProgress else { return }
        progressStore.set(unlockedCount, forKey: ProgressKeys.unlockedCount)
        progressStore.set(Array(completedLevels), forKey: ProgressKeys.completedLevels)
        progressStore.set(difficulty.rawValue, forKey: ProgressKeys.difficulty)
    }
}

private enum ProgressKeys {
    static let unlockedCount = "wordoku.unlockedCount"
    static let completedLevels = "wordoku.completedLevels"
    static let difficulty = "wordoku.difficulty"
}
