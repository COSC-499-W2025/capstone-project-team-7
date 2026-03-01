import Foundation

public struct WordokuSolver {
    public init() {}

    public func solve(_ grid: WordokuGrid) -> WordokuGrid? {
        var working = grid
        if solveRecursive(&working) {
            return working
        }
        return nil
    }

    public func countSolutions(_ grid: WordokuGrid, limit: Int) -> Int {
        var working = grid
        var count = 0
        countRecursive(&working, count: &count, limit: limit)
        return count
    }

    private func solveRecursive(_ grid: inout WordokuGrid) -> Bool {
        guard let next = nextCell(in: grid) else { return true }
        if next.candidates.isEmpty { return false }
        for value in next.candidates {
            grid.cells[next.index] = value
            if solveRecursive(&grid) { return true }
        }
        grid.cells[next.index] = nil
        return false
    }

    private func countRecursive(_ grid: inout WordokuGrid, count: inout Int, limit: Int) {
        if count >= limit { return }
        guard let next = nextCell(in: grid) else {
            count += 1
            return
        }
        if next.candidates.isEmpty { return }
        for value in next.candidates {
            grid.cells[next.index] = value
            countRecursive(&grid, count: &count, limit: limit)
            if count >= limit { break }
        }
        grid.cells[next.index] = nil
    }

    private func nextCell(in grid: WordokuGrid) -> (index: Int, candidates: [Int])? {
        var bestIndex: Int?
        var bestCandidates: [Int] = []
        var bestCount = Int.max
        for idx in 0..<81 where grid.cells[idx] == nil {
            let candidates = candidates(for: idx, grid: grid)
            if candidates.isEmpty { return (idx, []) }
            if candidates.count < bestCount {
                bestCount = candidates.count
                bestIndex = idx
                bestCandidates = candidates
                if bestCount == 1 { break }
            }
        }
        guard let index = bestIndex else { return nil }
        return (index, bestCandidates)
    }

    private func candidates(for index: Int, grid: WordokuGrid) -> [Int] {
        var available = Array(repeating: true, count: 9)
        for peer in WordokuGrid.peers(of: index) {
            if let value = grid.cells[peer] {
                available[value] = false
            }
        }
        var result: [Int] = []
        for value in 0..<9 where available[value] {
            result.append(value)
        }
        return result
    }
}
