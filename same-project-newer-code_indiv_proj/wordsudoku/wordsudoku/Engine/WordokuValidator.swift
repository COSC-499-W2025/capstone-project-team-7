import Foundation

public struct WordokuValidator {
    public init() {}

    public static func isValid(grid: WordokuGrid) -> Bool {
        for row in 0..<9 {
            if hasDuplicates(indices: WordokuGrid.rowIndices(row), grid: grid) { return false }
        }
        for col in 0..<9 {
            if hasDuplicates(indices: WordokuGrid.colIndices(col), grid: grid) { return false }
        }
        for box in 0..<9 {
            if hasDuplicates(indices: WordokuGrid.boxIndices(box), grid: grid) { return false }
        }
        return true
    }

    public static func isComplete(grid: WordokuGrid) -> Bool {
        !grid.cells.contains(where: { $0 == nil }) && isValid(grid: grid)
    }

    public static func isValidPlacement(grid: WordokuGrid, index: Int, value: Int) -> Bool {
        let peers = WordokuGrid.peers(of: index)
        for peer in peers {
            if grid.cells[peer] == value { return false }
        }
        return true
    }

    public static func conflictingIndices(in grid: WordokuGrid) -> Set<Int> {
        var conflicts = Set<Int>()
        for row in 0..<9 {
            conflicts.formUnion(conflictsIn(indices: WordokuGrid.rowIndices(row), grid: grid))
        }
        for col in 0..<9 {
            conflicts.formUnion(conflictsIn(indices: WordokuGrid.colIndices(col), grid: grid))
        }
        for box in 0..<9 {
            conflicts.formUnion(conflictsIn(indices: WordokuGrid.boxIndices(box), grid: grid))
        }
        return conflicts
    }

    private static func hasDuplicates(indices: [Int], grid: WordokuGrid) -> Bool {
        var seen = Set<Int>()
        for idx in indices {
            if let value = grid.cells[idx] {
                if seen.contains(value) { return true }
                seen.insert(value)
            }
        }
        return false
    }

    private static func conflictsIn(indices: [Int], grid: WordokuGrid) -> Set<Int> {
        var positionsByValue: [Int: [Int]] = [:]
        for idx in indices {
            if let value = grid.cells[idx] {
                positionsByValue[value, default: []].append(idx)
            }
        }
        var conflicts = Set<Int>()
        for (_, positions) in positionsByValue where positions.count > 1 {
            conflicts.formUnion(positions)
        }
        return conflicts
    }
}
