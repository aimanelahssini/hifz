import SwiftUI

enum Theme {
    static let cardBg = Color(red: 16 / 255, green: 16 / 255, blue: 20 / 255).opacity(0.76)
    static let border = Color.white.opacity(0.09)
    static let headMuted = Color.white.opacity(0.52)
    static let surah = Color.white.opacity(0.72)
    static let current = Color.white
    static let dim = Color.white.opacity(0.56)
    static let gold = Color(red: 233 / 255, green: 196 / 255, blue: 106 / 255)
    static let recited = Color(red: 126 / 255, green: 226 / 255, blue: 168 / 255)
    static let countBg = Color.white.opacity(0.08)
    static let radius: CGFloat = 18

    static func lineOpacity(distance: Int) -> Double {
        switch distance {
        case ..<0: return 0
        case 0: return 1
        case 1: return 1
        case 2: return 0.78
        case 3: return 0.58
        default: return 0.42
        }
    }

    static var arabicFont: Font {
        if NSFont(name: "Amiri Quran", size: 18) != nil {
            return .custom("Amiri Quran", size: 18)
        }
        if NSFont(name: "Amiri", size: 18) != nil {
            return .custom("Amiri", size: 18)
        }
        return .system(size: 18)
    }
}
