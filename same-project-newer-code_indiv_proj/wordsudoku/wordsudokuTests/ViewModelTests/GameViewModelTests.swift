import XCTest
@testable import wordsudoku

@MainActor
final class GameViewModelTests: XCTestCase {
    
    private func createTestLevel() -> WordokuLevel {
        let word = WordokuWord(raw: "ABCDEFGHI")!
        
        // Create a simple solved grid
        let solutionCells: [Int?] = [
            0, 1, 2, 3, 4, 5, 6, 7, 8,
            3, 4, 5, 6, 7, 8, 0, 1, 2,
            6, 7, 8, 0, 1, 2, 3, 4, 5,
            1, 2, 3, 4, 5, 6, 7, 8, 0,
            4, 5, 6, 7, 8, 0, 1, 2, 3,
            7, 8, 0, 1, 2, 3, 4, 5, 6,
            2, 3, 4, 5, 6, 7, 8, 0, 1,
            5, 6, 7, 8, 0, 1, 2, 3, 4,
            8, 0, 1, 2, 3, 4, 5, 6, 7
        ]
        let solution = WordokuGrid(cells: solutionCells)
        
        // Create puzzle with some cells removed
        var puzzleCells = solutionCells
        puzzleCells[0] = nil  // Remove first cell
        puzzleCells[10] = nil // Remove another cell
        puzzleCells[20] = nil // Remove another cell
        let puzzle = WordokuGrid(cells: puzzleCells)
        
        return WordokuLevel(
            word: word,
            difficulty: .easy,
            puzzle: puzzle,
            solution: solution,
            forcedAxis: .row,
            forcedIndex: 0
        )
    }
    
    func testInitialization() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        XCTAssertEqual(viewModel.letters, Array("ABCDEFGHI"))
        XCTAssertNil(viewModel.selectedIndex)
        XCTAssertFalse(viewModel.isComplete)
        XCTAssertTrue(viewModel.showConflicts)
    }
    
    func testGivenIndices() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        // Cells 0, 10, 20 should not be in givenIndices (they were removed)
        let givenIndices = viewModel.givenIndices
        XCTAssertFalse(givenIndices.contains(0))
        XCTAssertFalse(givenIndices.contains(10))
        XCTAssertFalse(givenIndices.contains(20))
        
        // Cell 1 should be a given
        XCTAssertTrue(givenIndices.contains(1))
    }
    
    func testSelectIndex() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        viewModel.select(index: 5)
        XCTAssertEqual(viewModel.selectedIndex, 5)
        
        viewModel.select(index: 10)
        XCTAssertEqual(viewModel.selectedIndex, 10)
    }
    
    func testClearSelection() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        viewModel.select(index: 5)
        XCTAssertNotNil(viewModel.selectedIndex)
        
        viewModel.clearSelection()
        XCTAssertNil(viewModel.selectedIndex)
    }
    
    func testSetValueOnEmptyCell() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        // Select an empty cell (index 0 was removed in puzzle)
        viewModel.select(index: 0)
        
        // Set a value
        viewModel.setValue(5)
        XCTAssertEqual(viewModel.grid.cells[0], 5)
    }
    
    func testSetValueOnGivenCellDoesNothing() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        // Select a given cell (index 1 has a value)
        viewModel.select(index: 1)
        let originalValue = viewModel.grid.cells[1]
        
        // Try to set a different value
        viewModel.setValue(5)
        
        // Value should not change
        XCTAssertEqual(viewModel.grid.cells[1], originalValue)
    }
    
    func testSetValueWithoutSelectionDoesNothing() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        // Don't select anything
        XCTAssertNil(viewModel.selectedIndex)
        
        // Try to set a value - should not crash or modify anything
        viewModel.setValue(5)
        
        // Grid should remain unchanged from puzzle
        XCTAssertNil(viewModel.grid.cells[0])
    }
    
    func testDeleteValue() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        // Select and set a value
        viewModel.select(index: 0)
        viewModel.setValue(5)
        XCTAssertEqual(viewModel.grid.cells[0], 5)
        
        // Delete the value
        viewModel.setValue(nil)
        XCTAssertNil(viewModel.grid.cells[0])
    }
    
    func testForcedIndicesForRow() {
        let level = createTestLevel()  // forcedAxis: .row, forcedIndex: 0
        let viewModel = GameViewModel(level: level)
        
        let forcedIndices = viewModel.forcedIndices
        
        // Row 0 indices are 0-8
        for i in 0..<9 {
            XCTAssertTrue(forcedIndices.contains(i), "Row 0 should contain index \(i)")
        }
        XCTAssertEqual(forcedIndices.count, 9)
    }
    
    func testForcedIndicesForColumn() {
        let word = WordokuWord(raw: "ABCDEFGHI")!
        let solutionCells: [Int?] = Array(repeating: 0, count: 81)
        let solution = WordokuGrid(cells: solutionCells)
        let puzzle = WordokuGrid(cells: solutionCells)
        
        let level = WordokuLevel(
            word: word,
            difficulty: .easy,
            puzzle: puzzle,
            solution: solution,
            forcedAxis: .col,
            forcedIndex: 2
        )
        
        let viewModel = GameViewModel(level: level)
        let forcedIndices = viewModel.forcedIndices
        
        // Column 2 indices are 2, 11, 20, 29, 38, 47, 56, 65, 74
        let expectedIndices = [2, 11, 20, 29, 38, 47, 56, 65, 74]
        for idx in expectedIndices {
            XCTAssertTrue(forcedIndices.contains(idx), "Column 2 should contain index \(idx)")
        }
        XCTAssertEqual(forcedIndices.count, 9)
    }
    
    func testWinStateDetection() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        XCTAssertFalse(viewModel.isComplete)
        
        // Fill in the missing cells with correct values
        // Cell 0 should be 0, Cell 10 should be 4, Cell 20 should be 8
        viewModel.select(index: 0)
        viewModel.setValue(0)
        
        viewModel.select(index: 10)
        viewModel.setValue(4)
        
        viewModel.select(index: 20)
        viewModel.setValue(8)
        
        // Now the grid should match the solution
        XCTAssertTrue(viewModel.isComplete)
    }
    
    func testLetterConversion() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        XCTAssertEqual(viewModel.letter(for: 0), "A")
        XCTAssertEqual(viewModel.letter(for: 1), "B")
        XCTAssertEqual(viewModel.letter(for: 8), "I")
        XCTAssertEqual(viewModel.letter(for: nil), "")
        XCTAssertEqual(viewModel.letter(for: -1), "")
        XCTAssertEqual(viewModel.letter(for: 100), "")
    }
    
    func testConflictsToggle() {
        let level = createTestLevel()
        let viewModel = GameViewModel(level: level)
        
        XCTAssertTrue(viewModel.showConflicts)
        
        viewModel.showConflicts = false
        XCTAssertTrue(viewModel.conflictIndices.isEmpty)
    }
}
