import Foundation
import os.log

/// Errors that can occur when loading word lists
public enum WordListLoaderError: Error, LocalizedError {
    case fileNotFound(String)
    case readError(String, Error)
    case noValidWords
    
    public var errorDescription: String? {
        switch self {
        case .fileNotFound(let filename):
            return "Word list file '\(filename)' not found in bundle"
        case .readError(let filename, let underlying):
            return "Failed to read '\(filename)': \(underlying.localizedDescription)"
        case .noValidWords:
            return "No valid 9-letter words found in word list"
        }
    }
}

/// Result of loading words, including any rejected entries
public struct WordListLoadResult {
    public let words: [WordokuWord]
    public let rejectedCount: Int
    public let totalLines: Int
}

public struct WordListLoader {
    public init() {}

    /// Loads words from the bundled word list file.
    /// - Parameter bundle: The bundle containing the word list (defaults to main bundle)
    /// - Returns: Array of valid WordokuWord objects
    /// - Note: This method logs errors but returns an empty array on failure for graceful degradation
    public func loadWords(from bundle: Bundle = .main) -> [WordokuWord] {
        do {
            let result = try loadWordsWithDetails(from: bundle)
            return result.words
        } catch {
            WordokuLogger.data.error("Failed to load words: \(error.localizedDescription)")
            return []
        }
    }
    
    /// Loads words with detailed information about the loading process.
    /// - Parameter bundle: The bundle containing the word list
    /// - Returns: WordListLoadResult with words and statistics
    /// - Throws: WordListLoaderError if loading fails
    public func loadWordsWithDetails(from bundle: Bundle = .main) throws -> WordListLoadResult {
        let filename = "wordlist"
        let ext = "txt"
        
        guard let url = bundle.url(forResource: filename, withExtension: ext) else {
            WordokuLogger.data.error("Word list file not found: \(filename).\(ext)")
            throw WordListLoaderError.fileNotFound("\(filename).\(ext)")
        }
        
        let contents: String
        do {
            contents = try String(contentsOf: url, encoding: .utf8)
            WordokuLogger.data.debug("Successfully read word list file")
        } catch {
            WordokuLogger.data.error("Failed to read word list: \(error.localizedDescription)")
            throw WordListLoaderError.readError("\(filename).\(ext)", error)
        }
        
        let lines = contents.split(whereSeparator: \.isNewline)
        let totalLines = lines.count
        WordokuLogger.data.info("Processing \(totalLines) lines from word list")
        
        var validWords: [WordokuWord] = []
        var rejectedCount = 0
        
        for line in lines {
            let trimmed = String(line).trimmingCharacters(in: .whitespaces)
            if let word = WordokuWord(raw: trimmed) {
                validWords.append(word)
            } else if !trimmed.isEmpty {
                rejectedCount += 1
                WordokuLogger.data.debug("Rejected word: '\(trimmed)' (invalid format or length)")
            }
        }
        
        WordokuLogger.data.info("Loaded \(validWords.count) valid words, rejected \(rejectedCount)")
        
        if validWords.isEmpty {
            WordokuLogger.data.warning("No valid words found in word list")
            throw WordListLoaderError.noValidWords
        }
        
        return WordListLoadResult(
            words: validWords,
            rejectedCount: rejectedCount,
            totalLines: totalLines
        )
    }
}
