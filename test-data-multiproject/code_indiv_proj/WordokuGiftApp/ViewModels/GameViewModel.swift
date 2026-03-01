import Foundation
import SwiftUI

final class GameViewModel: ObservableObject {
    let level: WordokuLevel
    @Published var grid: WordokuGrid
    @Published var selectedIndex: Int?
    @Published var showConflicts: Bool = true
    @Published var isComplete: Bool = false

    init(level: WordokuLevel) {
        self.level = level
        self.grid = level.puzzle
        self.selectedIndex = nil
        self.isComplete = false
        updateWinState()
    }

    var letters: [Character] {
        level.word.letters
    }

    var givenIndices: Set<Int> {
        var indices = Set<Int>()
        for idx in 0..<81 where level.puzzle.cells[idx] != nil {
            indices.insert(idx)
        }
        return indices
    }

    var conflictIndices: Set<Int> {
        guard showConflicts else { return [] }
        return WordokuValidator.conflictingIndices(in: grid)
    }

    var forcedIndices: Set<Int> {
        switch level.forcedAxis {
        case .row:
            return Set(WordokuGrid.rowIndices(level.forcedIndex))
        case .col:
            return Set(WordokuGrid.colIndices(level.forcedIndex))
        }
    }

    func letter(for value: Int?) -> String {
        guard let value = value, value >= 0, value < letters.count else { return "" }
        return String(letters[value])
    }

    func select(index: Int) {
        selectedIndex = index
    }

    func setValue(_ value: Int?) {
        guard let index = selectedIndex else { return }
        if givenIndices.contains(index) { return }
        grid.cells[index] = value
        updateWinState()
    }

    func clearSelection() {
        selectedIndex = nil
    }

    private func updateWinState() {
        isComplete = grid.cells == level.solution.cells
    }
}
