import Foundation

public struct WordokuPuzzleGenerator {
    public init() {}

    public func generatePuzzle(from solution: WordokuGrid, difficulty: Difficulty, rng: inout RandomNumberGenerator) -> WordokuGrid {
        var puzzle = solution
        var indices = Array(0..<81)
        indices.shuffle(using: &rng)
        let target = difficulty.targetGivens
        let minPerBox = difficulty.minGivensPerBox
        let solver = WordokuSolver()

        for idx in indices {
            if puzzle.givenCount() <= target { break }
            let pair = 80 - idx
            let removal = Array(Set([idx, pair]))
            if removal.allSatisfy({ puzzle.cells[$0] == nil }) { continue }
            if puzzle.givenCount() - removal.count < target { continue }
            let saved = removal.map { puzzle.cells[$0] }
            for index in removal { puzzle.cells[index] = nil }
            if violatesBoxMinimum(puzzle, minPerBox: minPerBox) || solver.countSolutions(puzzle, limit: 2) != 1 {
                for (offset, index) in removal.enumerated() { puzzle.cells[index] = saved[offset] }
            }
        }
        return puzzle
    }

    private func violatesBoxMinimum(_ grid: WordokuGrid, minPerBox: Int) -> Bool {
        for box in 0..<9 {
            let count = WordokuGrid.boxIndices(box).reduce(0) { total, index in
                total + (grid.cells[index] == nil ? 0 : 1)
            }
            if count < minPerBox { return true }
        }
        return false
    }
}
