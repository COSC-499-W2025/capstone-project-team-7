import Foundation

public struct WordokuWord: Equatable {
    public let raw: String
    public let letters: [Character]

    public init?(raw: String) {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        let upper = trimmed.uppercased()
        guard WordokuWord.isValidWord(upper) else { return nil }
        self.raw = upper
        self.letters = Array(upper)
    }

    public static func isValidWord(_ word: String) -> Bool {
        let upper = word.uppercased()
        guard upper.count == 9 else { return false }
        let chars = Array(upper)
        var seen = Set<Character>()
        for ch in chars {
            for scalar in ch.unicodeScalars {
                if scalar.value > 127 { return false }
                if !CharacterSet.letters.contains(scalar) { return false }
            }
            if seen.contains(ch) { return false }
            seen.insert(ch)
        }
        return true
    }
}
