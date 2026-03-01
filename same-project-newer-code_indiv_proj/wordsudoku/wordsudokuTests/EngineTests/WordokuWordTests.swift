import XCTest
@testable import wordsudoku

final class WordokuWordTests: XCTestCase {
    func testIsogramValidation() {
        XCTAssertTrue(WordokuWord.isValidWord("ABCDEFGHI"))
        XCTAssertFalse(WordokuWord.isValidWord("AABCDEFGHI"))
        XCTAssertFalse(WordokuWord.isValidWord("ABCDEFGH"))
        XCTAssertFalse(WordokuWord.isValidWord("ABCDEF1HI"))
    }
}
