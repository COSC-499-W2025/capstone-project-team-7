# Wordoku

A SwiftUI-based word sudoku puzzle game for iOS and iPadOS. Solve sudoku puzzles using letters instead of numbers, where completing the puzzle reveals a hidden word.

## Features

- **Letter-based Sudoku**: Classic 9x9 sudoku puzzles using 9 unique letters
- **Hidden Words**: Each puzzle reveals a secret word when solved
- **Progressive Difficulty**: Easy, Medium, and Hard difficulty levels
- **Level Progression**: Unlock new levels as you complete puzzles
- **Progress Tracking**: Your progress is automatically saved
- **Conflict Highlighting**: Optional visual indicators for invalid placements
- **Clean UI**: Minimalist design that works in both light and dark mode

## Requirements

- iOS 16.0+ / iPadOS 16.0+
- Xcode 15.0+
- Swift 5.9+

## Getting Started

### Building the Project

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/word-sudoku.git
   cd word-sudoku
   ```

2. Open the active project in Xcode:
   ```bash
   open wordsudoku/wordsudoku.xcodeproj
   ```

   Do not work from `WordokuGiftApp/`; it is an archive snapshot.

3. Select your target device or simulator

4. Build and run (⌘R)

### Running Tests

```bash
xcodebuild test \
  -project wordsudoku/wordsudoku.xcodeproj \
  -scheme wordsudoku \
  -destination 'platform=iOS Simulator,name=iPhone 15'
```

Or run tests directly in Xcode with ⌘U.

## Architecture

The app follows the **MVVM (Model-View-ViewModel)** architecture pattern:

```
wordsudoku/wordsudoku/
├── App/                    # App entry point
├── Data/                   # Data loading utilities
├── Engine/                 # Core game logic
│   ├── WordokuGrid         # Grid data structure
│   ├── WordokuWord         # Word validation
│   ├── WordokuValidator    # Sudoku rule validation
│   ├── WordokuSolver       # Backtracking solver
│   ├── WordokuSolutionGenerator
│   ├── WordokuPuzzleGenerator
│   └── WordokuLevelFactory
├── UI/                     # SwiftUI views
│   ├── LevelSelectView     # Level selection screen
│   ├── GameView            # Main game screen
│   ├── GridView            # Sudoku grid display
│   ├── LetterPaletteView   # Letter input palette
│   ├── WinOverlayView      # Victory overlay
│   └── Components/         # Reusable UI components
└── ViewModels/             # View state management
    ├── LevelSelectViewModel
    └── GameViewModel
```

## How to Play

1. **Select a Level**: Choose from available levels on the main screen
2. **Place Letters**: Tap a cell, then tap a letter from the palette
3. **Follow Sudoku Rules**: Each row, column, and 3x3 box must contain all 9 letters exactly once
4. **Find the Word**: Complete the puzzle to reveal the hidden word highlighted in a row or column
5. **Progress**: Completing a level unlocks the next one

## Data Storage

The app uses `UserDefaults` to persist:
- Unlocked level count
- Completed levels
- Difficulty preference
- In-progress game state (resume directly from level cards)

No personal data is collected or transmitted.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with SwiftUI
- Inspired by classic Sudoku and word puzzle games
