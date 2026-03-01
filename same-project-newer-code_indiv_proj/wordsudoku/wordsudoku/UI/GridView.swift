import SwiftUI

struct GridView: View {
    let grid: WordokuGrid
    let letters: [Character]
    let selectedIndex: Int?
    let givenIndices: Set<Int>
    let conflictIndices: Set<Int>
    let forcedIndices: Set<Int>
    let orderedForcedIndices: [Int]  // Ordered list for animation sequence
    let isComplete: Bool
    let isWordComplete: Bool
    let onSelect: (Int) -> Void
    
    @State private var revealedCellCount: Int = 0
    @State private var animationTimer: Timer?
    
    private func wordCellAnimationIndex(for index: Int) -> Int? {
        guard let position = orderedForcedIndices.firstIndex(of: index) else { return nil }
        return position
    }
    
    private func isCellRevealed(index: Int) -> Bool {
        guard let animationIndex = wordCellAnimationIndex(for: index) else { return false }
        return animationIndex < revealedCellCount
    }

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
                        let isInWordSequence = forcedIndices.contains(index)
                        let isWordCellRevealed = isWordComplete && !isComplete && isInWordSequence && isCellRevealed(index: index)
                        let animationIndex = wordCellAnimationIndex(for: index)
                        let row = index / 9
                        let column = index % 9
                        let isRelated = isRelatedCell(index: index, selectedIndex: selectedIndex, row: row, column: column)
                        let isSameLetter = isSameLetterCell(index: index, selectedIndex: selectedIndex)
                        WordokuGridCellView(
                            text: letter(for: value),
                            isGiven: isGiven,
                            isSelected: isSelected,
                            isConflict: isConflict,
                            isForced: isForced,
                            isWordCell: isWordCellRevealed,
                            isRelated: isRelated,
                            isSameLetter: isSameLetter,
                            size: cellSize,
                            row: row,
                            column: column,
                            animationIndex: animationIndex,
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
                .allowsHitTesting(false)
                Path { path in
                    for i in stride(from: 0, through: 9, by: 3) {
                        let pos = CGFloat(i) * cellSize
                        path.move(to: CGPoint(x: pos, y: 0))
                        path.addLine(to: CGPoint(x: pos, y: size))
                        path.move(to: CGPoint(x: 0, y: pos))
                        path.addLine(to: CGPoint(x: size, y: pos))
                    }
                }
                .stroke(WordokuTheme.primaryText.opacity(0.25), lineWidth: 1.5)
                .allowsHitTesting(false)
            }
            .frame(width: size, height: size)
            .accessibilityElement(children: .contain)
            .accessibilityLabel("Sudoku grid, 9 by 9")
        }
        .aspectRatio(1, contentMode: .fit)
        .onChange(of: isWordComplete) { newValue in
            if newValue && !isComplete {
                startDominoAnimation()
            }
        }
        .onDisappear {
            animationTimer?.invalidate()
            animationTimer = nil
        }
    }
    
    private func startDominoAnimation() {
        revealedCellCount = 0
        animationTimer?.invalidate()
        
        animationTimer = Timer.scheduledTimer(withTimeInterval: 0.08, repeats: true) { timer in
            if revealedCellCount < orderedForcedIndices.count {
                withAnimation(.spring(response: 0.4, dampingFraction: 0.5)) {
                    revealedCellCount += 1
                }
            } else {
                timer.invalidate()
                animationTimer = nil
            }
        }
    }

    private func letter(for value: Int?) -> String {
        guard let value = value, value >= 0, value < letters.count else { return "" }
        return String(letters[value])
    }
    
    private func isRelatedCell(index: Int, selectedIndex: Int?, row: Int, column: Int) -> Bool {
        guard let selectedIndex = selectedIndex, index != selectedIndex else { return false }
        let selectedRow = selectedIndex / 9
        let selectedCol = selectedIndex % 9
        
        if row == selectedRow { return true }
        if column == selectedCol { return true }
        
        let boxStartRow = (row / 3) * 3
        let boxStartCol = (column / 3) * 3
        let selectedBoxStartRow = (selectedRow / 3) * 3
        let selectedBoxStartCol = (selectedCol / 3) * 3
        
        return boxStartRow == selectedBoxStartRow && boxStartCol == selectedBoxStartCol
    }
    
    private func isSameLetterCell(index: Int, selectedIndex: Int?) -> Bool {
        guard let selectedIndex = selectedIndex,
              index != selectedIndex,
              let selectedValue = grid.cells[selectedIndex],
              let cellValue = grid.cells[index] else { return false }
        return selectedValue == cellValue
    }
}
