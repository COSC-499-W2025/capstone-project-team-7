import SwiftUI

struct GridView: View {
    let grid: WordokuGrid
    let letters: [Character]
    let selectedIndex: Int?
    let givenIndices: Set<Int>
    let conflictIndices: Set<Int>
    let forcedIndices: Set<Int>
    let isComplete: Bool
    let onSelect: (Int) -> Void

    var body: some View {
        GeometryReader { geometry in
            let size = min(geometry.size.width, geometry.size.height)
            let cellSize = size / 9
            ZStack {
                LazyVGrid(columns: Array(repeating: GridItem(.fixed(cellSize), spacing: 0), count: 9), spacing: 0) {
                    ForEach(0..<81, id: \.self) { index in
                        let value = grid.cells[index]
                        let isGiven = givenIndices.contains(index)
                        let isSelected = selectedIndex == index
                        let isConflict = conflictIndices.contains(index)
                        let isForced = isComplete && forcedIndices.contains(index)
                        let row = index / 9
                        let column = index % 9
                        WordokuGridCellView(
                            text: letter(for: value),
                            isGiven: isGiven,
                            isSelected: isSelected,
                            isConflict: isConflict,
                            isForced: isForced,
                            size: cellSize,
                            row: row,
                            column: column,
                            action: { onSelect(index) }
                        )
                    }
                }
                Path { path in
                    for i in 0...9 {
                        let pos = CGFloat(i) * cellSize
                        path.move(to: CGPoint(x: pos, y: 0))
                        path.addLine(to: CGPoint(x: pos, y: size))
                        path.move(to: CGPoint(x: 0, y: pos))
                        path.addLine(to: CGPoint(x: size, y: pos))
                    }
                }
                .stroke(WordokuTheme.divider, lineWidth: 0.5)
                Path { path in
                    for i in stride(from: 0, through: 9, by: 3) {
                        let pos = CGFloat(i) * cellSize
                        path.move(to: CGPoint(x: pos, y: 0))
                        path.addLine(to: CGPoint(x: pos, y: size))
                        path.move(to: CGPoint(x: 0, y: pos))
                        path.addLine(to: CGPoint(x: size, y: pos))
                    }
                }
                .stroke(WordokuTheme.accentBlue.opacity(0.35), lineWidth: 1.5)
            }
            .frame(width: size, height: size)
            .accessibilityElement(children: .contain)
            .accessibilityLabel("Sudoku grid, 9 by 9")
        }
        .aspectRatio(1, contentMode: .fit)
    }

    private func letter(for value: Int?) -> String {
        guard let value = value, value >= 0, value < letters.count else { return "" }
        return String(letters[value])
    }
}
