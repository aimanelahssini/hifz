import Foundation

/// Literal Quran translations bundled from Tanzil plain-text files (6236 ayahs each).
enum Translations {
    static let basmalaAyah = 1  // 1:1 doubles as the basmala for other surahs

    private static let stems: [Store.Language: String] = [
        .en: "en.sahih",
        .fr: "fr.hamidullah",
        .tr: "tr.diyanet",
        .id: "id.indonesian",
        .es: "es.cortes",
    ]

    private static var cache: [Store.Language: [[String]]] = [:]

    static func text(_ lang: Store.Language, surah: Int, ayah: Int) -> String {
        guard lang != .ar, let stem = stems[lang] else { return "" }
        let bySurah = load(lang, stem: stem)
        if ayah == 0 {
            return bySurah[0].first ?? ""
        }
        guard (1...114).contains(surah), ayah >= 1 else { return "" }
        let rows = bySurah[surah - 1]
        guard ayah <= rows.count else { return "" }
        return rows[ayah - 1]
    }

    private static func load(_ lang: Store.Language, stem: String) -> [[String]] {
        if let hit = cache[lang] { return hit }
        let bundles = [Bundle.main, Bundle(for: BundleToken.self)]
        var raw: String?
        for bundle in bundles {
            if let url = bundle.url(forResource: stem, withExtension: "txt", subdirectory: "trans"),
               let s = try? String(contentsOf: url, encoding: .utf8) {
                raw = s
                break
            }
            // Flattened copy next to quran.json
            if let url = bundle.url(forResource: stem, withExtension: "txt"),
               let s = try? String(contentsOf: url, encoding: .utf8) {
                raw = s
                break
            }
        }
        guard let raw else {
            Log.action("translations: missing \(stem).txt")
            cache[lang] = Array(repeating: [], count: 114)
            return cache[lang]!
        }
        let flat = raw.split(whereSeparator: \.isNewline)
            .map(String.init)
            .filter { !$0.isEmpty && !$0.hasPrefix("#") }
        var i = 0
        var by: [[String]] = []
        for surah in Quran.all {
            let n = surah.ayahs
            let slice = Array(flat[i..<min(i + n, flat.count)])
            by.append(slice)
            i += n
        }
        Log.action("translations: loaded \(stem) (\(flat.count) ayahs)")
        cache[lang] = by
        return by
    }

    private final class BundleToken {}
}
