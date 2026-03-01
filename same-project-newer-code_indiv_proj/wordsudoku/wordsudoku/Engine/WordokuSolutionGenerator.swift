import Foundation

public struct WordokuSolutionGenerator {
    public init() {}

    public func generateSolution(word: WordokuWord, forcedAxis: ForcedAxis, forcedIndex: Int, rng: inout RandomNumberGenerator) -> WordokuGrid? {
        var grid = WordokuGrid()
        for i in 0..<9 {
            let index: Int
            switch forcedAxis {
            case .row:
                index = forcedIndex * 9 + i
            case .col:
                index = i * 9 + forcedIndex
            case .diagonal:
                index = i * 10
            case .antiDiagonal:
                index = (i + 1) * 8
            }
            grid.cells[index] = i
        }
        guard WordokuValidator.isValid(grid: grid) else { return nil }
        if fillGrid(&grid, rng: &rng) { return grid }
        return nil
    }

    private func fillGrid(_ grid: inout WordokuGrid, rng: inout RandomNumberGenerator) -> Bool {
        guard let next = nextCell(in: grid) else { return true }
        if next.candidates.isEmpty { return false }
        var candidates = next.candidates
        candidates.shuffle(using: &rng)
        for value in candidates {
            grid.cells[next.index] = value
            if fillGrid(&grid, rng: &rng) { return true }
        }
        grid.cells[next.index] = nil
        return false
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

public struct SeededGenerator: RandomNumberGenerator {
    private var state: UInt64

    public init(seed: UInt64) {
        self.state = seed == 0 ? 0x12345678abcdef : seed
    }

    public mutating func next() -> UInt64 {
        state &+= 0x9E3779B97F4A7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        return z ^ (z >> 31)
    }
}
