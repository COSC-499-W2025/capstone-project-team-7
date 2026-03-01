import Foundation

enum WordMeaningProvider {
    private static let meanings: [String: String] = [
        "ALMSGIVER": "Someone who gives to the poor",
        "AUTHORING": "The act of writing or creating",
        "ANGELFISH": "A tropical reef fish",
        "ANXIOUSLY": "With worry or nervousness",
        "ANCHOVIES": "Small saltwater fish used as food",
        "ABOLISHED": "Officially ended or put an end to",
        "AWESTRUCK": "Filled with awe",
        "ABLUTIONS": "Washing or cleansing, often as a ritual",
        "ALCHEMIST": "A person who practices alchemy",
        "ABSOLVING": "Freeing from blame or responsibility",
        "ALGORITHM": "A step-by-step procedure for solving a problem",
        "AMPLITUDE": "The maximum extent of a vibration",
        "BLOCKHEAD": "A stupid or slow-witted person",
        "BETRAYING": "Acting disloyally or revealing secrets",
        "BLEACHING": "Whitening or lightening by chemical or sunlight",
        "BENCHMARK": "A standard or point of reference",
        "BOHEMIANS": "People with an artistic, unconventional lifestyle",
        "BREATHING": "The act of inhaling and exhaling air",
        "BURNISHED": "Polished to a smooth, shiny finish",
        "BINOCULAR": "Relating to both eyes",
        "BIRDCAGES": "Cages for keeping birds",
        "BREACHING": "Breaking through a barrier or agreement",
        "BIFURCATE": "To divide into two branches",
        "BRIMSTONE": "Sulfur",
        "BLACKOUTS": "Losses of consciousness or power failures",
        "BROACHING": "Raising a subject for discussion",
        "BRIGHTENS": "Makes lighter or more cheerful",
        "BREAKDOWN": "A failure or collapse",
        "CAMPFIRES": "Outdoor fires used for warmth or cooking",
        "CAPTURING": "Taking control of or recording"
    ]

    static func meaning(for word: String) -> String {
        meanings[word.uppercased()] ?? "A nine-letter word"
    }
}
