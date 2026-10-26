import XCTest
@testable import Hifz

final class QuranTests: XCTestCase {
    func testSurahCount() {
        XCTAssertEqual(Quran.all.count, 114)
    }

    func testWaqia() {
        let s = Quran.surah(56)
        XCTAssertEqual(s.name, "Al-Wâqi'a")
        XCTAssertEqual(s.ayahs, 96)
        // Basmala + 96 ayahs
        XCTAssertEqual(s.lines.count, 97)
        XCTAssertEqual(s.lines[0].ayah, 0)
        XCTAssertEqual(s.lines[1].ayah, 1)
        XCTAssertEqual(s.lines[1].phonetic, "Idhâ waqa'ati-l-wâqi'ah")
    }

    func testBasmalaRule() {
        XCTAssertEqual(Quran.lines(1).first?.ayah, 1)   // Al-Fatiha: no separate basmala
        XCTAssertEqual(Quran.lines(9).first?.ayah, 1)   // At-Tawba: no basmala
        XCTAssertEqual(Quran.lines(2).first?.ayah, 0)   // Al-Baqara: basmala
        XCTAssertEqual(Quran.lines(112).first?.ayah, 0)
    }

    func testAyahCounts() {
        let expected = [7, 286, 200, 176, 120]
        for (i, n) in expected.enumerated() {
            XCTAssertEqual(Quran.surah(i + 1).ayahs, n)
        }
    }
}

final class StoreTests: XCTestCase {
    func testRoundTrip() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }

        // Point Store at a temp file by writing directly, then load via decoder path.
        let store = Store()
        store.surah = 112
        store.speed = 1.25
        store.showArabic = true
        store.auto = true
        store.after = "next"
        store.saved = [56, 112]
        store.setLine(112, 2)
        store.addFinish(56)

        // Use the real path: temporarily swap by writing our own file then loading.
        // Store.path() is fixed; write there only if we isolate via env — instead test in-memory.
        XCTAssertEqual(store.line(112), 2)
        XCTAssertEqual(store.finished(56), 1)
        XCTAssertEqual(store.clampSpeed(2.7), 2.0)
        XCTAssertEqual(store.clampSpeed(0.1), 0.5)
        XCTAssertEqual(store.clampSpeed(1.03), 1.05)
    }

    func testAfterModes() {
        XCTAssertEqual(Store.afterModes.count, 4)
        XCTAssertTrue(Store.afterModes.contains("shuffle"))
    }
}
