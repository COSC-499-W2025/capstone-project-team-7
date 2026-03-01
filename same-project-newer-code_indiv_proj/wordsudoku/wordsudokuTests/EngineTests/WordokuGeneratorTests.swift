import XCTest
@testable import wordsudoku

final class WordokuGeneratorTests: XCTestCase {
    func testGeneratedPuzzleHasUniqueSolution() {
        guard let word = WordokuWord(raw: "ABCDEFGHI") else {
            XCTFail("Invalid test word")
            return
        }
        var rng: RandomNumberGenerator = SeededGenerator(seed: 42)
        let factory = WordokuLevelFactory()
        guard let level = factory.makeLevel(word: word, difficulty: .easy, forcedAxis: .row, forcedIndex: 0, rng: &rng) else {
            XCTFail("Failed to generate level")
            return
        }
        let solver = WordokuSolver()
        XCTAssertEqual(solver.countSolutions(level.puzzle, limit: 2), 1)
    }

    func testForcedRowPresentInSolution() {
        guard let word = WordokuWord(raw: "ABCDEFGHI") else {
            XCTFail("Invalid test word")
            return
        }
        var rng: RandomNumberGenerator = SeededGenerator(seed: 99)
        let factory = WordokuLevelFactory()
        guard let level = factory.makeLevel(word: word, difficulty: .easy, forcedAxis: .row, forcedIndex: 0, rng: &rng) else {
            XCTFail("Failed to generate level")
            return
        }
        let rowIndices = WordokuGrid.rowIndices(0)
        let rowValues = rowIndices.compactMap { level.solution.cells[$0] }
        XCTAssertEqual(rowValues, Array(0..<9))
    }

    func testPuzzleSymmetryAndBoxMinimums() {
        guard let word = WordokuWord(raw: "ABCDEFGHI") else {
            XCTFail("Invalid test word")
            return
        }
        var rng: RandomNumberGenerator = SeededGenerator(seed: 123)
        let factory = WordokuLevelFactory()
        guard let level = factory.makeLevel(word: word, difficulty: .medium, forcedAxis: .row, forcedIndex: 0, rng: &rng) else {
            XCTFail("Failed to generate level")
            return
        }
        let puzzle = level.puzzle
        for index in 0..<81 {
            let pair = 80 - index
            XCTAssertEqual(puzzle.cells[index] == nil, puzzle.cells[pair] == nil)
        }
        let minPerBox = Difficulty.medium.minGivensPerBox
        for box in 0..<9 {
            let count = WordokuGrid.boxIndices(box).reduce(0) { total, idx in
                total + (puzzle.cells[idx] == nil ? 0 : 1)
            }
            XCTAssertGreaterThanOrEqual(count, minPerBox)
        }
    }
}
