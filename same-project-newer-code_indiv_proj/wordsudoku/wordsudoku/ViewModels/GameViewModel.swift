import Foundation
import SwiftUI
import Combine

final class GameViewModel: ObservableObject {
    let level: WordokuLevel
    @Published var grid: WordokuGrid
    @Published var selectedIndex: Int?
    @Published var showConflicts: Bool = true
    @Published var isComplete: Bool = false
    @Published var isWordComplete: Bool = false
    @Published var canUndo: Bool = false
    @Published var canRedo: Bool = false

    private var undoStack: [(index: Int, oldValue: Int?, newValue: Int?)] = []
    private var redoStack: [(index: Int, oldValue: Int?, newValue: Int?)] = []

    init(level: WordokuLevel) {
        self.level = level
        self.grid = level.puzzle
        self.selectedIndex = nil
        self.isComplete = false
        self.isWordComplete = false
        self.canUndo = false
        self.canRedo = false
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
        case .diagonal:
            return Set(WordokuGrid.mainDiagonalIndices())
        case .antiDiagonal:
            return Set(WordokuGrid.antiDiagonalIndices())
        }
    }
    
    var orderedForcedIndices: [Int] {
        switch level.forcedAxis {
        case .row:
            return WordokuGrid.rowIndices(level.forcedIndex)
        case .col:
            return WordokuGrid.colIndices(level.forcedIndex)
        case .diagonal:
            return WordokuGrid.mainDiagonalIndices()
        case .antiDiagonal:
            return WordokuGrid.antiDiagonalIndices()
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
        
        let oldValue = grid.cells[index]
        undoStack.append((index: index, oldValue: oldValue, newValue: value))
        
        if undoStack.count > 100 {
            undoStack.removeFirst()
        }
        
        redoStack.removeAll()
        canUndo = !undoStack.isEmpty
        canRedo = false
        
        grid.cells[index] = value
        updateWinState()
    }

    func clearSelection() {
        selectedIndex = nil
    }

    func undo() {
        guard let move = undoStack.popLast() else { return }
        grid.cells[move.index] = move.oldValue
        redoStack.append(move)
        canUndo = !undoStack.isEmpty
        canRedo = !redoStack.isEmpty
        updateWinState()
    }

    func redo() {
        guard let move = redoStack.popLast() else { return }
        grid.cells[move.index] = move.newValue
        undoStack.append(move)
        canUndo = !undoStack.isEmpty
        canRedo = !redoStack.isEmpty
        updateWinState()
    }

    private func updateWinState() {
        let wordIndices = forcedIndices
        let wordComplete = wordIndices.allSatisfy { index in
            grid.cells[index] == level.solution.cells[index]
        }
        if wordComplete && !isWordComplete {
            isWordComplete = true
        }
        isComplete = grid.cells == level.solution.cells
    }
    
    // MARK: - State Persistence
    
    func saveState(levelIndex: Int, difficulty: Difficulty) {
        let state = SavedGameState(
            levelIndex: levelIndex,
            difficulty: difficulty.rawValue,
            cells: grid.cells
        )
        if let encoded = try? JSONEncoder().encode(state) {
            UserDefaults.standard.set(encoded, forKey: SavedGameState.storageKey)
        }
    }
    
    func restoreState(from saved: SavedGameState) {
        grid = WordokuGrid(cells: saved.cells)
        updateWinState()
    }
    
    static func loadSavedState() -> SavedGameState? {
        guard let data = UserDefaults.standard.data(forKey: SavedGameState.storageKey),
              let state = try? JSONDecoder().decode(SavedGameState.self, from: data) else {
            return nil
        }
        return state
    }
    
    static func clearSavedState() {
        UserDefaults.standard.removeObject(forKey: SavedGameState.storageKey)
    }
}

struct SavedGameState: Codable {
    static let storageKey = "wordoku.savedGameState"
    
    let levelIndex: Int
    let difficulty: String
    let cells: [Int?]
}
