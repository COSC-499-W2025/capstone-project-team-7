import Foundation

public struct CellIndex: Hashable {
    public let row: Int
    public let col: Int

    public init(row: Int, col: Int) {
        self.row = row
        self.col = col
    }

    public var linearIndex: Int {
        row * 9 + col
    }
}

public struct WordokuGrid: Equatable {
    public var cells: [Int?]

    public init() {
        self.cells = Array(repeating: nil, count: 81)
    }

    public init(cells: [Int?]) {
        if cells.count == 81 {
            self.cells = cells
        } else if cells.count < 81 {
            self.cells = cells + Array(repeating: nil, count: 81 - cells.count)
        } else {
            self.cells = Array(cells.prefix(81))
        }
    }

    public subscript(row: Int, col: Int) -> Int? {
        get { cells[row * 9 + col] }
        set { cells[row * 9 + col] = newValue }
    }

    public func givenCount() -> Int {
        cells.compactMap { $0 }.count
    }

    public static func row(of index: Int) -> Int {
        index / 9
    }

    public static func col(of index: Int) -> Int {
        index % 9
    }

    public static func box(of index: Int) -> Int {
        (row(of: index) / 3) * 3 + (col(of: index) / 3)
    }

    public static func rowIndices(_ row: Int) -> [Int] {
        (0..<9).map { row * 9 + $0 }
    }

    public static func colIndices(_ col: Int) -> [Int] {
        (0..<9).map { $0 * 9 + col }
    }

    public static func boxIndices(_ box: Int) -> [Int] {
        let startRow = (box / 3) * 3
        let startCol = (box % 3) * 3
        var indices: [Int] = []
        indices.reserveCapacity(9)
        for r in 0..<3 {
            for c in 0..<3 {
                indices.append((startRow + r) * 9 + (startCol + c))
            }
        }
        return indices
    }

    public static func peers(of index: Int) -> Set<Int> {
        let rowIdx = row(of: index)
        let colIdx = col(of: index)
        let boxIdx = box(of: index)
        var peers = Set<Int>()
        peers.formUnion(rowIndices(rowIdx))
        peers.formUnion(colIndices(colIdx))
        peers.formUnion(boxIndices(boxIdx))
        peers.remove(index)
        return peers
    }
}

public enum Difficulty: String, CaseIterable, Codable {
    case easy
    case medium
    case hard

    public var targetGivens: Int {
        switch self {
        case .easy: return 40
        case .medium: return 32
        case .hard: return 26
        }
    }

    public var minGivensPerBox: Int {
        switch self {
        case .easy: return 4
        case .medium: return 3
        case .hard: return 2
        }
    }
}

public enum ForcedAxis: String, Codable {
    case row
    case col
}

public struct WordokuLevel: Equatable {
    public let word: WordokuWord
    public let difficulty: Difficulty
    public let puzzle: WordokuGrid
    public let solution: WordokuGrid
    public let forcedAxis: ForcedAxis
    public let forcedIndex: Int

    public init(word: WordokuWord, difficulty: Difficulty, puzzle: WordokuGrid, solution: WordokuGrid, forcedAxis: ForcedAxis, forcedIndex: Int) {
        self.word = word
        self.difficulty = difficulty
        self.puzzle = puzzle
        self.solution = solution
        self.forcedAxis = forcedAxis
        self.forcedIndex = forcedIndex
    }
}
