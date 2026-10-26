import AppKit
import Combine
import Foundation
import SwiftUI

/// Layout constants (nonisolated so views can read them freely).
enum CardLayout {
    static let cardWidth: CGFloat = 440
    static let cardHeight: CGFloat = 212
    static let headHeight: CGFloat = 30
    static let pad: CGFloat = 18
    static var viewHeight: CGFloat { cardHeight - headHeight - pad }
    static let slideMs: Double = 0.42
    static let lineSpacing: CGFloat = 12
}

/// Port of the Linux Prompter: lines, navigation, finish flow, audio wiring.
@MainActor
final class PrompterModel: ObservableObject {
    let store: Store
    let player = Player()
    let downloads = Downloader()

    @Published var surah: Int
    @Published var lines: [QuranLine] = []
    @Published var index: Int = 0
    @Published var audioOn = false
    @Published var paused = false
    @Published var finishing = false
    @Published var loading = false
    @Published var scrollOffset: CGFloat = 0
    @Published var contentOffset: CGFloat = 0
    @Published var showSurahPicker = false
    @Published var showSpeedPicker = false
    @Published var showSettingsPicker = false
    @Published var closeHover = false
    @Published var thenSurah: Int?
    @Published var minimized = false

    static let cardWidth = CardLayout.cardWidth
    static let cardHeight = CardLayout.cardHeight
    static let headHeight = CardLayout.headHeight
    static let pad = CardLayout.pad
    static var viewHeight: CGFloat { CardLayout.viewHeight }
    static let slideMs = CardLayout.slideMs
    static let lineSpacing = CardLayout.lineSpacing

    private var want: (String, Int, Int)?
    private var spinWork: DispatchWorkItem?
    private var lineHeights: [Int: CGFloat] = [:]
    private var cancellables = Set<AnyCancellable>()

    init(store: Store, surah: Int? = nil) {
        self.store = store
        self.surah = surah ?? store.surah
        store.objectWillChange
            .receive(on: RunLoop.main)
            .sink { [weak self] _ in self?.objectWillChange.send() }
            .store(in: &cancellables)
        player.onEnd = { [weak self] in
            Task { @MainActor in self?.audioEnded() }
        }
        player.onNext = { [weak self] in
            Task { @MainActor in self?.audioNext() }
        }
        loadSurah(self.surah)
    }

    // MARK: - Surah / lines

    func loadSurah(_ n: Int) {
        Log.action("surah: load \(n) \(Quran.name(n))")
        player.halt()
        surah = n
        store.surah = n
        lines = Quran.lines(n)
        lineHeights = [:]
        index = min(store.line(n), max(0, lines.count - 1))
        finishing = false
        thenSurah = nil
        contentOffset = 0
        store.save()
        snapToIndex()
        if audioOn && !paused {
            prefetchAll()
            playCurrent()
        }
    }

    func setLineHeight(_ i: Int, _ h: CGFloat) {
        if lineHeights[i] != h {
            lineHeights[i] = h
        }
    }

    func y(for i: Int) -> CGFloat {
        var y: CGFloat = 0
        for k in 0..<i {
            y += (lineHeights[k] ?? estimatedHeight(k)) + Self.lineSpacing
        }
        return y
    }

    private func estimatedHeight(_ i: Int) -> CGFloat {
        guard i < lines.count else { return 28 }
        if store.language == .ar {
            let arRows = max(1, ceil(CGFloat(lines[i].arabic.count) / 28))
            let phChars = CGFloat(store.phonetics.restyle(lines[i].phonetic).count)
            let phRows = max(1, ceil(phChars / 40))
            return arRows * 26 + phRows * 18 + 2
        }
        let t = Translations.text(store.language, surah: surah, ayah: lines[i].ayah)
        let rows = max(1, ceil(CGFloat(t.count) / 40))
        return rows * 24
    }

    func snapToIndex() {
        contentOffset = y(for: index)
    }

    func slideTo(_ y: CGFloat, duration: Double = CardLayout.slideMs) {
        withAnimation(.easeOut(duration: duration)) {
            contentOffset = y
        }
    }

    // MARK: - Navigation

    func go(_ i: Int, slow: Bool = false, play: Bool = true) {
        let i = max(0, min(i, lines.count - 1))
        index = i
        store.setLine(surah, i)
        store.save()
        Log.action("go: line \(i) ayah \(lines[i].ayah)")
        slideTo(y(for: i), duration: slow ? 0.7 : CardLayout.slideMs)
        if audioOn && play && !paused {
            playCurrent()
        } else if paused {
            player.halt()
        }
    }

    func next() {
        if finishing { return }
        let top = y(for: index)
        let height = lineHeights[index] ?? estimatedHeight(index)
        let bottom = top + height
        let shown = contentOffset
        if bottom > shown + Self.viewHeight - 8 {
            let target = min(shown + Self.viewHeight * 0.7, bottom - Self.viewHeight * 0.5)
            Log.action("next: scroll inside long ayah")
            slideTo(target)
            return
        }
        if index >= lines.count - 1 {
            askFinish()
            return
        }
        go(index + 1)
    }

    func prev() {
        if finishing {
            hideFinish()
            return
        }
        let top = y(for: index)
        if contentOffset > top + 4 {
            Log.action("prev: scroll inside ayah")
            slideTo(max(top, contentOffset - Self.viewHeight * 0.7))
            return
        }
        if index > 0 {
            go(index - 1)
        }
    }

    func move(_ step: () -> Void) {
        paused = false
        step()
    }

    func space() {
        Log.action("key: space")
        let last = index >= lines.count - 1
        if !audioOn || last {
            next()
        } else if paused {
            paused = false
            if player.playing != nil {
                player.resume()
            } else {
                playCurrent()
            }
        } else if player.playing != nil {
            paused = true
            player.pause()
        } else {
            next()
        }
    }

    // MARK: - Finish

    func askFinish() {
        Log.action("finish: ask")
        finishing = true
        player.halt()
        thenSurah = afterSurah()
    }

    func afterSurah() -> Int {
        let n = surah
        switch store.after {
        case "next": return n % 114 + 1
        case "previous": return (n - 2 + 114) % 114 + 1
        case "shuffle":
            var pool = store.saved.filter { $0 != n }
            if pool.count < 2 {
                pool = Array(1...114).filter { $0 != n }
            }
            return pool.randomElement() ?? n
        default: return n
        }
    }

    func hideFinish() {
        finishing = false
        thenSurah = nil
    }

    func answer(_ yes: Bool) {
        Log.action("finish: answer yes=\(yes)")
        hideFinish()
        guard yes else { return }
        store.addFinish(surah)
        store.save()
        player.halt()
        paused = true
        let nxt = thenSurah ?? surah
        if nxt != surah {
            store.setLine(nxt, 0)
            loadSurah(nxt)
        } else {
            go(0, slow: true)
        }
    }

    func cycleAfter() {
        let modes = Store.afterModes
        let i = modes.firstIndex(of: store.after) ?? 0
        store.after = modes[(i + 1) % modes.count]
        store.save()
        Log.action("after: \(store.after)")
    }

    // MARK: - Audio

    func toggleAudio() {
        audioOn.toggle()
        paused = false
        Log.action("audio: toggle on=\(audioOn)")
        if audioOn {
            player.start()
            player.speed = store.speed
            prefetchAll()
            playCurrent()
        } else {
            player.stop()
            setLoading(false)
        }
    }

    func playCurrent() {
        guard index < lines.count else { return }
        player.halt()
        let ayah = lines[index].ayah
        let want = (store.reciter, surah, ayah)
        self.want = want
        setLoading(true)
        downloads.fetch(reciter: store.reciter, surah: surah, ayah: ayah, urgent: true) { [weak self] path in
            Task { @MainActor in
                guard let self else { return }
                guard self.audioOn, self.want?.0 == want.0, self.want?.1 == want.1, self.want?.2 == want.2 else { return }
                self.setLoading(false)
                if let path {
                    self.player.play(path)
                    self.queueNext()
                } else {
                    Log.action("audio: download failed for current ayah")
                }
            }
        }
    }

    func prefetchAll() {
        let ordered = Array(lines[index...]) + Array(lines[..<index])
        for line in ordered {
            downloads.fetch(reciter: store.reciter, surah: surah, ayah: line.ayah)
        }
    }

    private func setLoading(_ on: Bool) {
        spinWork?.cancel()
        if on {
            let work = DispatchWorkItem { [weak self] in
                self?.loading = true
            }
            spinWork = work
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.25, execute: work)
        } else {
            loading = false
        }
    }

    func queueNext() {
        player.queued = nil
        if audioOn && store.auto && index + 1 < lines.count {
            let (path, _) = Downloader.file(reciter: store.reciter, surah: surah, ayah: lines[index + 1].ayah)
            if FileManager.default.fileExists(atPath: path.path) {
                player.queued = path
            }
        }
    }

    private func audioNext() {
        if finishing || index + 1 >= lines.count { return }
        go(index + 1, play: false)
        queueNext()
    }

    private func audioEnded() {
        guard audioOn && store.auto && !finishing else { return }
        if index >= lines.count - 1 {
            askFinish()
        } else {
            go(index + 1)
        }
    }

    // MARK: - Settings

    func setSpeed(_ value: Double) {
        let s = store.clampSpeed(value)
        store.speed = s
        store.save()
        player.speed = s
        Log.action("speed: \(s)x")
    }

    func setReciter(_ id: String) {
        store.reciter = id
        store.save()
        Log.action("reciter: \(id)")
        if audioOn {
            prefetchAll()
            playCurrent()
        }
    }

    func toggleArabic() {
        if store.language == .ar {
            setLanguage(store.previousLanguage)
        } else {
            store.previousLanguage = store.language
            setLanguage(.ar)
        }
    }

    func setLanguage(_ lang: Store.Language) {
        guard lang != store.language else { return }
        if store.language != .ar {
            store.previousLanguage = store.language
        }
        store.language = lang
        store.save()
        Log.action("language: \(lang.rawValue)")
        DispatchQueue.main.async { [weak self] in self?.snapToIndex() }
    }

    func setPhonetics(_ style: Store.Phonetics) {
        guard store.language == .ar else { return }
        guard style != store.phonetics else { return }
        store.phonetics = style
        store.save()
        Log.action("phonetics: \(style.rawValue)")
        DispatchQueue.main.async { [weak self] in self?.snapToIndex() }
    }

    func toggleAuto() {
        store.auto.toggle()
        store.save()
        Log.action("auto: \(store.auto)")
        if player.playing != nil {
            queueNext()
        }
    }

    func toggleSaved(_ n: Int) {
        store.toggleSaved(n)
        store.save()
    }

    func restart() {
        Log.action("restart")
        go(0, slow: true)
    }

    func hideToMini() {
        Log.action("ui: hide to mini")
        showSurahPicker = false
        showSpeedPicker = false
        showSettingsPicker = false
        minimized = true
    }

    func showFromMini() {
        Log.action("ui: show from mini")
        minimized = false
    }

    func setPlacement(_ placement: Store.Placement) {
        store.placement = placement
        store.save()
        Log.action("placement: \(placement.rawValue)")
    }

    func handleKey(_ key: KeyEquivalent, modifiers: EventModifiers = []) -> Bool {
        if showSurahPicker || showSpeedPicker || showSettingsPicker { return false }
        if modifiers.contains(.command) && (key == "q" || key == "w") {
            Log.action("key: quit")
            NSApp.terminate(nil)
            return true
        }
        if finishing {
            if key == .return || key == "y" {
                answer(true)
                return true
            }
            if key == .escape || key == "n" || key == KeyEquivalent("\u{7f}") {
                answer(false)
                return true
            }
            return true
        }
        switch key {
        case " ":
            space()
        case .downArrow, "j":
            move(next)
        case .upArrow, "k", KeyEquivalent("\u{7f}"):
            move(prev)
        case .rightArrow, "+", "=":
            setSpeed(store.speed + 0.05)
        case .leftArrow, "-":
            setSpeed(store.speed - 0.05)
        case "m", "M":
            toggleAudio()
        case "a", "A":
            toggleArabic()
        case "h", "H":
            hideToMini()
        case .home:
            go(0, slow: true)
        default:
            return false
        }
        return true
    }
}
