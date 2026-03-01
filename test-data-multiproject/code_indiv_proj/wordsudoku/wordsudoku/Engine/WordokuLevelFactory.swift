import Foundation

public struct WordokuLevelFactory {
    public init() {}

    public func makeLevel(word: WordokuWord, difficulty: Difficulty, forcedAxis: ForcedAxis = .row, forcedIndex: Int = 0, rng: inout RandomNumberGenerator) -> WordokuLevel? {
        let solutionGen = WordokuSolutionGenerator()
        guard let solution = solutionGen.generateSolution(word: word, forcedAxis: forcedAxis, forcedIndex: forcedIndex, rng: &rng) else { return nil }
        let puzzle = WordokuPuzzleGenerator().generatePuzzle(from: solution, difficulty: difficulty, rng: &rng)
        return WordokuLevel(word: word, difficulty: difficulty, puzzle: puzzle, solution: solution, forcedAxis: forcedAxis, forcedIndex: forcedIndex)
    }
}
