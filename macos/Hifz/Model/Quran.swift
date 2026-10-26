import Foundation

struct QuranLine: Codable, Identifiable, Equatable {
    let ayah: Int
    let arabic: String
    let phonetic: String

    var id: Int { ayah }
}

struct Surah: Codable, Identifiable, Equatable {
    let number: Int
    let name: String
    let ayahs: Int
    let lines: [QuranLine]

    var id: Int { number }
}

struct QuranData: Codable {
    let version: Int
    let surahs: [Surah]
}

enum Quran {
    private static let data: QuranData = {
        let bundles = [Bundle.main, Bundle(for: BundleToken.self)]
        for bundle in bundles {
            if let url = bundle.url(forResource: "quran", withExtension: "json"),
               let raw = try? Data(contentsOf: url),
               let decoded = try? JSONDecoder().decode(QuranData.self, from: raw) {
                Log.action("loaded quran.json: \(decoded.surahs.count) surahs")
                return decoded
            }
        }
        fatalError("quran.json missing from app bundle")
    }()

    private final class BundleToken {}

    static var all: [Surah] { data.surahs }

    static func surah(_ n: Int) -> Surah {
        precondition((1...114).contains(n))
        return data.surahs[n - 1]
    }

    static func name(_ n: Int) -> String { surah(n).name }

    static func lines(_ n: Int) -> [QuranLine] { surah(n).lines }
}
