import XCTest
@testable import wordsudoku

@MainActor
final class LevelSelectViewModelTests: XCTestCase {
    
    override func setUp() async throws {
        // Clear UserDefaults before each test
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: "wordoku.unlockedCount")
        defaults.removeObject(forKey: "wordoku.completedLevels")
        defaults.removeObject(forKey: "wordoku.difficulty")
    }
    
    override func tearDown() async throws {
        // Clean up after tests
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: "wordoku.unlockedCount")
        defaults.removeObject(forKey: "wordoku.completedLevels")
        defaults.removeObject(forKey: "wordoku.difficulty")
    }
    
    func testInitialState() {
        let viewModel = LevelSelectViewModel()
        
        // Initial unlocked count should be 1
        XCTAssertGreaterThanOrEqual(viewModel.unlockedCount, 1)
        // Completed levels should be empty initially
        XCTAssertTrue(viewModel.completedLevels.isEmpty)
        // Default difficulty should be easy
        XCTAssertEqual(viewModel.difficulty, .easy)
    }
    
    func testMarkCompleted() {
        let viewModel = LevelSelectViewModel()
        
        // Complete level 0
        viewModel.markCompleted(index: 0)
        
        XCTAssertTrue(viewModel.completedLevels.contains(0))
        // Unlocked count should increase to 2
        XCTAssertGreaterThanOrEqual(viewModel.unlockedCount, 2)
    }
    
    func testMarkCompletedUnlocksNextLevel() {
        let viewModel = LevelSelectViewModel()
        
        // Initial state
        let initialUnlocked = viewModel.unlockedCount
        
        // Complete level 0
        viewModel.markCompleted(index: 0)
        
        // Should unlock at least one more level
        XCTAssertGreaterThan(viewModel.unlockedCount, initialUnlocked)
    }
    
    func testIsLocked() {
        let viewModel = LevelSelectViewModel()
        
        // Level 0 should be unlocked
        XCTAssertFalse(viewModel.isLocked(index: 0))
        
        // Levels beyond unlockedCount should be locked
        if viewModel.levelCount > viewModel.unlockedCount {
            XCTAssertTrue(viewModel.isLocked(index: viewModel.unlockedCount))
        }
    }
    
    func testDifficultyPersistence() {
        // Create first view model and change difficulty
        let viewModel1 = LevelSelectViewModel()
        viewModel1.difficulty = .hard
        
        // Create new view model - should load saved difficulty
        let viewModel2 = LevelSelectViewModel()
        XCTAssertEqual(viewModel2.difficulty, .hard)
    }
    
    func testCompletedLevelsPersistence() {
        // Create first view model and mark a level complete
        let viewModel1 = LevelSelectViewModel()
        viewModel1.markCompleted(index: 0)
        
        // Create new view model - should load saved progress
        let viewModel2 = LevelSelectViewModel()
        XCTAssertTrue(viewModel2.completedLevels.contains(0))
    }
    
    func testMakeLevelReturnsLevel() {
        let viewModel = LevelSelectViewModel()
        
        // If words are loaded, makeLevel should return a level
        if viewModel.levelCount > 0 {
            let level = viewModel.makeLevel(index: 0)
            XCTAssertNotNil(level)
        }
    }
    
    func testMakeLevelOutOfBounds() {
        let viewModel = LevelSelectViewModel()
        
        // Should return nil for invalid indices
        XCTAssertNil(viewModel.makeLevel(index: -1))
        XCTAssertNil(viewModel.makeLevel(index: 1000))
    }
    
    func testLevelCountMatchesWords() {
        let viewModel = LevelSelectViewModel()
        
        XCTAssertEqual(viewModel.levelCount, viewModel.words.count)
    }
    
    func testDeterministicLevelGeneration() {
        let viewModel = LevelSelectViewModel()
        
        guard viewModel.levelCount > 0 else {
            XCTSkip("No words loaded")
            return
        }
        
        // Same index and difficulty should produce the same level
        let level1 = viewModel.makeLevel(index: 0)
        let level2 = viewModel.makeLevel(index: 0)
        
        XCTAssertEqual(level1?.puzzle.cells, level2?.puzzle.cells)
        XCTAssertEqual(level1?.solution.cells, level2?.solution.cells)
    }
    
    func testDifferentDifficultyProducesDifferentLevel() {
        let viewModel = LevelSelectViewModel()
        
        guard viewModel.levelCount > 0 else {
            XCTSkip("No words loaded")
            return
        }
        
        viewModel.difficulty = .easy
        let easyLevel = viewModel.makeLevel(index: 0)
        
        viewModel.difficulty = .hard
        let hardLevel = viewModel.makeLevel(index: 0)
        
        // Different difficulties should have different numbers of given cells
        let easyGivens = easyLevel?.puzzle.givenCount() ?? 0
        let hardGivens = hardLevel?.puzzle.givenCount() ?? 0
        
        // Easy should have more givens than hard
        XCTAssertGreaterThan(easyGivens, hardGivens)
    }
}
