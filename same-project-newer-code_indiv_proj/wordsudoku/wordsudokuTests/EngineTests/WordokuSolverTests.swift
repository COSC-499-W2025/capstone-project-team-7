import XCTest
@testable import wordsudoku

final class WordokuSolverTests: XCTestCase {
    func testSolverFindsSolution() {
        let puzzle: [Int?] = [
            4, 2, nil, nil, 6, nil, nil, nil, nil,
            5, nil, nil, 0, 8, 4, nil, nil, nil,
            nil, 8, 7, nil, nil, nil, nil, 5, nil,
            7, nil, nil, nil, 5, nil, nil, nil, 2,
            3, nil, nil, 7, nil, 2, nil, nil, 0,
            6, nil, nil, nil, 1, nil, nil, nil, 5,
            nil, 5, nil, nil, nil, nil, 1, 7, nil,
            nil, nil, nil, 3, 0, 8, nil, nil, 4,
            nil, nil, nil, nil, 7, nil, nil, 6, 8
        ]
        let solution: [Int?] = [
            4, 2, 3, 5, 6, 7, 8, 0, 1,
            5, 6, 1, 0, 8, 4, 2, 3, 7,
            0, 8, 7, 2, 3, 1, 4, 5, 6,
            7, 4, 8, 6, 5, 0, 3, 1, 2,
            3, 1, 5, 7, 4, 2, 6, 8, 0,
            6, 0, 2, 8, 1, 3, 7, 4, 5,
            8, 5, 0, 4, 2, 6, 1, 7, 3,
            1, 7, 6, 3, 0, 8, 5, 2, 4,
            2, 3, 4, 1, 7, 5, 0, 6, 8
        ]
        let solver = WordokuSolver()
        let solved = solver.solve(WordokuGrid(cells: puzzle))
        XCTAssertEqual(solved?.cells, solution)
    }

    func testSolutionCounterStopsAtTwo() {
        let solver = WordokuSolver()
        let count = solver.countSolutions(WordokuGrid(), limit: 2)
        XCTAssertEqual(count, 2)
    }
}
