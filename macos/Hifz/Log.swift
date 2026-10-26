import Foundation
import os

/// Console + unified-logging helper. Called on every user-visible action.
enum Log {
    private static let logger = Logger(subsystem: "io.github.aimanelahssini.Hifz", category: "app")

    static func action(_ message: String) {
        fputs("[hifz] \(message)\n", stderr)
        fflush(stderr)
        logger.info("\(message, privacy: .public)")
    }
}
