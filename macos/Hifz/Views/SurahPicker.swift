import SwiftUI

struct SurahPicker: View {
    @ObservedObject var model: PrompterModel
    @State private var query = ""
    @FocusState private var focused: Bool

    var body: some View {
        VStack(spacing: 0) {
            TextField("Number or name", text: $query)
                .textFieldStyle(.roundedBorder)
                .focused($focused)
                .onSubmit { pickFirst() }
                .padding(.bottom, 6)

            ScrollViewReader { proxy in
                List {
                    if query.isEmpty && !model.store.saved.isEmpty {
                        Section("Saved") {
                            ForEach(model.store.saved, id: \.self) { n in
                                surahRow(n)
                            }
                        }
                    }
                    Section(query.isEmpty && !model.store.saved.isEmpty ? "All surahs" : "") {
                        ForEach(filtered, id: \.self) { n in
                            surahRow(n)
                        }
                    }
                }
                .listStyle(.plain)
                .frame(width: 280, height: 300)
                .onAppear {
                    focused = true
                    DispatchQueue.main.async {
                        proxy.scrollTo(model.surah, anchor: .center)
                    }
                }
            }
        }
        .padding(6)
    }

    private var filtered: [Int] {
        let q = query.trimmingCharacters(in: .whitespaces)
        if q.isEmpty { return Array(1...114) }
        if let n = Int(q) {
            return (1...114).filter { String($0).hasPrefix(String(n)) }
        }
        let needle = plain(q)
        return (1...114).filter { plain(Quran.name($0)).contains(needle) }
    }

    @ViewBuilder
    private func surahRow(_ n: Int) -> some View {
        let done = model.store.finished(n)
        let saved = model.store.saved.contains(n)
        HStack(spacing: 10) {
            Text("\(n)")
                .frame(width: 28, alignment: .trailing)
                .foregroundStyle(.secondary)
                .font(.body.monospacedDigit())
            Text(Quran.name(n))
                .foregroundStyle(done > 0 ? Theme.recited : .primary)
                .fontWeight(n == model.surah ? .bold : .regular)
            Spacer()
            if done > 0 {
                Text("✓\(done)")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
            }
            Button {
                model.toggleSaved(n)
            } label: {
                Image(systemName: saved ? "star.fill" : "star")
                    .foregroundStyle(saved ? Theme.gold : .secondary)
            }
            .buttonStyle(.plain)
        }
        .contentShape(Rectangle())
        .listRowBackground(n == model.surah ? Theme.gold.opacity(0.16) : Color.clear)
        .id(n)
        .onTapGesture {
            Log.action("ui: pick surah \(n)")
            model.showSurahPicker = false
            if n != model.surah {
                model.loadSurah(n)
            }
        }
    }

    private func pickFirst() {
        if let n = filtered.first {
            model.showSurahPicker = false
            if n != model.surah { model.loadSurah(n) }
        }
    }

    private func plain(_ s: String) -> String {
        let folded = s.lowercased().folding(options: .diacriticInsensitive, locale: .current)
        var out = folded.filter { $0.isLetter }
        out = out.replacingOccurrences(of: "ou", with: "u")
        out = out.replacingOccurrences(of: "ch", with: "sh")
        if out.hasSuffix("h") { out = String(out.dropLast()) }
        return out
    }
}
