import Combine
import Foundation

/// Progress and settings. Same JSON schema as the Linux app's state.py.
final class Store: ObservableObject {
    static let speeds: [Double] = [0.5, 0.75, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0]
    static let speedMin = 0.5
    static let speedMax = 2.0
    static let defaultSurah = 56
    static let afterModes = ["repeat", "next", "previous", "shuffle"]

    enum Placement: String, CaseIterable, Identifiable {
        case topLeft, topCenter, topRight, bottomLeft, bottomRight

        var id: String { rawValue }

        var title: String {
            switch self {
            case .topLeft: return "Top left"
            case .topCenter: return "Top center"
            case .topRight: return "Top right"
            case .bottomLeft: return "Bottom left"
            case .bottomRight: return "Bottom right"
            }
        }
    }

    enum Language: String, CaseIterable, Identifiable {
        case ar, en, fr, tr, id, es

        var id: String { rawValue }

        var title: String {
            switch self {
            case .ar: return "Arabic"
            case .en: return "English"
            case .fr: return "French"
            case .tr: return "Turkish"
            case .id: return "Indonesian"
            case .es: return "Spanish"
            }
        }
    }

    enum Phonetics: String, CaseIterable, Identifiable {
        case fr, en, tr

        var id: String { rawValue }

        var title: String {
            switch self {
            case .fr: return "French"
            case .en: return "English"
            case .tr: return "Turkish"
            }
        }

        /// Respells a French transcription. French only uses "o" in ou/oû and "c" in ch.
        func restyle(_ text: String) -> String {
            guard self != .fr else { return text }
            var s = text
            let pairs: [(String, String)] = {
                switch self {
                case .fr: return []
                case .en:
                    return [("Oû", "Oo"), ("oû", "oo"), ("Ou", "U"), ("ou", "u"),
                            ("Ch", "Sh"), ("ch", "sh"), ("Â", "Aa"), ("â", "aa"),
                            ("Î", "Ee"), ("î", "ee")]
                case .tr:
                    return [("Oû", "Ū"), ("oû", "ū"), ("Ou", "U"), ("ou", "u"),
                            ("Ch", "Sh"), ("ch", "sh"), ("Â", "Ā"), ("â", "ā"),
                            ("Î", "Ī"), ("î", "ī")]
                }
            }()
            for (a, b) in pairs { s = s.replacingOccurrences(of: a, with: b) }
            return s
        }
    }

    @Published var surah: Int
    @Published var speed: Double
    @Published var reciter: String
    @Published var language: Language
    @Published var phonetics: Phonetics
    @Published var auto: Bool
    @Published var after: String
    @Published var saved: [Int]
    @Published var placement: Placement
    private var surahs: [String: SurahEntry]

    /// Last non-Arabic language, for the A key toggle.
    var previousLanguage: Language = .en

    var showArabic: Bool { language == .ar }

    struct SurahEntry: Codable {
        var line: Int
        var finished: Int
        var finishes: [String]
    }

    private struct File: Codable {
        var version: Int
        var surah: Int
        var speed: Double
        var reciter: String
        var show_arabic: Bool?
        var language: String?
        var phonetics: String?
        var auto: Bool
        var after: String
        var saved: [Int]
        var surahs: [String: SurahEntry]
        var placement: String?
    }

    init() {
        self.surah = Store.defaultSurah
        self.speed = 1.0
        self.reciter = "Alafasy_128kbps"
        self.language = .ar
        self.phonetics = .fr
        self.auto = false
        self.after = "repeat"
        self.saved = []
        self.surahs = [:]
        self.placement = .topRight
    }

    private init(file: File) {
        var s = file.surah
        if !(1...114).contains(s) { s = Store.defaultSurah }
        self.surah = s
        var sp = file.speed
        sp = (min(Store.speedMax, max(Store.speedMin, sp)) * 20).rounded() / 20
        self.speed = sp
        self.reciter = file.reciter
        let loadedLang: Language
        if let lang = file.language, let parsed = Language(rawValue: lang) {
            loadedLang = parsed
        } else {
            loadedLang = .ar
        }
        self.language = loadedLang
        self.phonetics = Phonetics(rawValue: file.phonetics ?? "") ?? .fr
        self.auto = file.auto
        self.after = Store.afterModes.contains(file.after) ? file.after : "repeat"
        self.saved = file.saved.filter { (1...114).contains($0) }
        self.surahs = file.surahs
        self.placement = Placement(rawValue: file.placement ?? "") ?? .topRight
        if loadedLang != .ar {
            self.previousLanguage = loadedLang
        }
    }

    static func stateDir() -> URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return base.appendingPathComponent("Hifz", isDirectory: true)
    }

    static func path() -> URL {
        stateDir().appendingPathComponent("progress.json")
    }

    static func load() -> Store {
        let url = path()
        guard let data = try? Data(contentsOf: url),
              let file = try? JSONDecoder().decode(File.self, from: data) else {
            Log.action("state: no progress.json, using defaults")
            return Store()
        }
        Log.action("state: loaded surah=\(file.surah) speed=\(file.speed)")
        return Store(file: file)
    }

    func save() {
        do {
            try FileManager.default.createDirectory(at: Store.stateDir(), withIntermediateDirectories: true)
            let file = File(
                version: 1,
                surah: surah,
                speed: speed,
                reciter: reciter,
                show_arabic: language == .ar,
                language: language.rawValue,
                phonetics: phonetics.rawValue,
                auto: auto,
                after: after,
                saved: saved,
                surahs: surahs,
                placement: placement.rawValue
            )
            let enc = JSONEncoder()
            enc.outputFormatting = [.prettyPrinted, .sortedKeys]
            let data = try enc.encode(file)
            let tmp = Store.path().appendingPathExtension("tmp")
            try data.write(to: tmp, options: .atomic)
            if FileManager.default.fileExists(atPath: Store.path().path) {
                try FileManager.default.removeItem(at: Store.path())
            }
            try FileManager.default.moveItem(at: tmp, to: Store.path())
            Log.action("state: saved surah=\(surah) line=\(line(surah))")
        } catch {
            Log.action("state: save failed: \(error)")
        }
    }

    private func entry(_ n: Int) -> SurahEntry {
        if let e = surahs[String(n)] { return e }
        let e = SurahEntry(line: 0, finished: 0, finishes: [])
        surahs[String(n)] = e
        return e
    }

    private func setEntry(_ n: Int, _ e: SurahEntry) {
        surahs[String(n)] = e
        objectWillChange.send()
    }

    func line(_ n: Int) -> Int {
        surahs[String(n)]?.line ?? 0
    }

    func setLine(_ n: Int, _ line: Int) {
        var e = entry(n)
        e.line = line
        setEntry(n, e)
    }

    func finished(_ n: Int) -> Int {
        surahs[String(n)]?.finished ?? 0
    }

    func addFinish(_ n: Int) {
        var e = entry(n)
        e.finished += 1
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withDashSeparatorInDate, .withColonSeparatorInTime]
        e.finishes.append(fmt.string(from: Date()))
        e.line = 0
        setEntry(n, e)
        Log.action("finish: surah \(n) now \(e.finished) times")
    }

    func toggleSaved(_ n: Int) {
        if let i = saved.firstIndex(of: n) {
            saved.remove(at: i)
            Log.action("saved: removed \(n)")
        } else {
            saved.append(n)
            saved.sort()
            Log.action("saved: added \(n)")
        }
    }

    func clampSpeed(_ value: Double) -> Double {
        (min(Store.speedMax, max(Store.speedMin, value)) * 20).rounded() / 20
    }
}
