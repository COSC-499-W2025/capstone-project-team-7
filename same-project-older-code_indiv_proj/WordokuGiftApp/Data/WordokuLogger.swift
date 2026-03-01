import Foundation
import os.log

/// Centralized logging for the Wordoku app using Apple's unified logging system.
/// Use these loggers for consistent, filterable logging throughout the app.
enum WordokuLogger {
    /// Logger for data loading operations (word lists, resources)
    static let data = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.wordoku", category: "data")
    
    /// Logger for game engine operations (puzzle generation, solving, validation)
    static let engine = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.wordoku", category: "engine")
    
    /// Logger for UI-related events
    static let ui = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.wordoku", category: "ui")
    
    /// Logger for user progress and persistence
    static let progress = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.wordoku", category: "progress")
}
