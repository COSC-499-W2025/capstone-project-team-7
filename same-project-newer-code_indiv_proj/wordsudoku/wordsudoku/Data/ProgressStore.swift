import Foundation

struct DifficultyProgress {
    let unlockedCount: Int
    let completedLevels: Set<Int>
}

struct ProgressSummary {
    let levelCount: Int
    let easyCompleted: Int
    let mediumCompleted: Int
    let hardCompleted: Int

    var totalCompleted: Int {
        easyCompleted + mediumCompleted + hardCompleted
    }

    var totalAvailable: Int {
        levelCount * Difficulty.allCases.count
    }
}

enum ProgressStore {
    private static let defaults = UserDefaults.standard
    private static let selectedDifficultyKey = "wordoku.difficulty"

    static func loadSelectedDifficulty() -> Difficulty {
        guard let raw = defaults.string(forKey: selectedDifficultyKey),
              let difficulty = Difficulty(rawValue: raw) else {
            return .easy
        }
        return difficulty
    }

    static func saveSelectedDifficulty(_ difficulty: Difficulty) {
        defaults.set(difficulty.rawValue, forKey: selectedDifficultyKey)
    }

    static func loadProgress(for difficulty: Difficulty, levelCount: Int) -> DifficultyProgress {
        guard levelCount > 0 else {
            return DifficultyProgress(unlockedCount: 0, completedLevels: [])
        }

        let unlockedKey = unlockedCountKey(for: difficulty)
        let completedKey = completedLevelsKey(for: difficulty)
        let rawUnlocked = defaults.object(forKey: unlockedKey) as? Int ?? 1
        let rawCompleted = defaults.array(forKey: completedKey) as? [Int] ?? []

        let unlockedCount = min(max(rawUnlocked, 1), levelCount)
        let completedLevels = Set(rawCompleted.filter { $0 >= 0 && $0 < levelCount })
        return DifficultyProgress(unlockedCount: unlockedCount, completedLevels: completedLevels)
    }

    static func saveProgress(for difficulty: Difficulty, unlockedCount: Int, completedLevels: Set<Int>) {
        defaults.set(unlockedCount, forKey: unlockedCountKey(for: difficulty))
        defaults.set(Array(completedLevels).sorted(), forKey: completedLevelsKey(for: difficulty))
    }

    static func loadSummary(levelCount: Int) -> ProgressSummary {
        let easy = loadProgress(for: .easy, levelCount: levelCount)
        let medium = loadProgress(for: .medium, levelCount: levelCount)
        let hard = loadProgress(for: .hard, levelCount: levelCount)
        return ProgressSummary(
            levelCount: levelCount,
            easyCompleted: easy.completedLevels.count,
            mediumCompleted: medium.completedLevels.count,
            hardCompleted: hard.completedLevels.count
        )
    }

    private static func unlockedCountKey(for difficulty: Difficulty) -> String {
        "wordoku.unlockedCount.\(difficulty.rawValue)"
    }

    private static func completedLevelsKey(for difficulty: Difficulty) -> String {
        "wordoku.completedLevels.\(difficulty.rawValue)"
    }
}
