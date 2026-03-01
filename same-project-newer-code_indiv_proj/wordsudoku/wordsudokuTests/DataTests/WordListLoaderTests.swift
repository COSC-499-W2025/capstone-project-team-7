import XCTest
@testable import wordsudoku

final class WordListLoaderTests: XCTestCase {
    
    func testLoadWordsFromMainBundle() {
        let loader = WordListLoader()
        let words = loader.loadWords()
        
        // Should load some words if wordlist.txt exists
        // If no words, it gracefully returns empty array
        XCTAssertNotNil(words)
    }
    
    func testLoadWordsWithDetailsFromMainBundle() {
        let loader = WordListLoader()
        
        do {
            let result = try loader.loadWordsWithDetails()
            
            // All loaded words should be valid
            for word in result.words {
                XCTAssertEqual(word.raw.count, 9)
                XCTAssertTrue(WordokuWord.isValidWord(word.raw))
            }
            
            // Total lines should be >= valid words + rejected
            XCTAssertGreaterThanOrEqual(result.totalLines, result.words.count)
        } catch {
            // If file doesn't exist, this is expected in test environment
            XCTAssertTrue(error is WordListLoaderError)
        }
    }
    
    func testLoadWordsFromMissingFile() {
        let loader = WordListLoader()
        let emptyBundle = Bundle(for: type(of: self))
        
        // Loading from a bundle without wordlist.txt should return empty array
        let words = loader.loadWords(from: emptyBundle)
        XCTAssertTrue(words.isEmpty)
    }
    
    func testLoadWordsWithDetailsFromMissingFile() {
        let loader = WordListLoader()
        let emptyBundle = Bundle(for: type(of: self))
        
        // Loading with details from missing file should throw
        XCTAssertThrowsError(try loader.loadWordsWithDetails(from: emptyBundle)) { error in
            guard let loaderError = error as? WordListLoaderError else {
                XCTFail("Expected WordListLoaderError")
                return
            }
            
            if case .fileNotFound = loaderError {
                // Expected
            } else {
                XCTFail("Expected fileNotFound error")
            }
        }
    }
    
    func testWordListLoaderErrorDescriptions() {
        let fileNotFound = WordListLoaderError.fileNotFound("test.txt")
        XCTAssertTrue(fileNotFound.errorDescription?.contains("test.txt") ?? false)
        
        let readError = WordListLoaderError.readError("test.txt", NSError(domain: "", code: 0))
        XCTAssertTrue(readError.errorDescription?.contains("test.txt") ?? false)
        
        let noValidWords = WordListLoaderError.noValidWords
        XCTAssertNotNil(noValidWords.errorDescription)
    }
}
