import XCTest
@testable import wordsudoku

final class WordokuValidatorTests: XCTestCase {
    func testValidatorDetectsRowDuplicates() {
        var grid = WordokuGrid()
        grid.cells[0] = 0
        grid.cells[1] = 0
        XCTAssertFalse(WordokuValidator.isValid(grid: grid))
    }

    func testValidatorDetectsColumnDuplicates() {
        var grid = WordokuGrid()
        grid.cells[0] = 1
        grid.cells[9] = 1
        XCTAssertFalse(WordokuValidator.isValid(grid: grid))
    }

    func testValidatorDetectsBoxDuplicates() {
        var grid = WordokuGrid()
        grid.cells[0] = 2
        grid.cells[10] = 2
        XCTAssertFalse(WordokuValidator.isValid(grid: grid))
    }

    func testValidatorAcceptsValidRow() {
        var grid = WordokuGrid()
        for i in 0..<9 {
            grid.cells[i] = i
        }
        XCTAssertTrue(WordokuValidator.isValid(grid: grid))
    }
}
