import SwiftUI

struct LinesView: View {
    @ObservedObject var model: PrompterModel

    var body: some View {
        GeometryReader { geo in
            VStack(alignment: .leading, spacing: PrompterModel.lineSpacing) {
                ForEach(Array(model.lines.enumerated()), id: \.offset) { i, line in
                    LineRow(
                        line: line,
                        surah: model.surah,
                        distance: i - model.index,
                        language: model.store.language,
                        phonetics: model.store.phonetics
                    )
                        .background(
                            GeometryReader { g in
                                Color.clear.preference(
                                    key: LineHeightKey.self,
                                    value: [i: g.size.height]
                                )
                            }
                        )
                }
                Text("Finished? Press Space or scroll")
                    .font(.system(size: 14, weight: .semibold).italic())
                    .foregroundStyle(Theme.gold.opacity(model.index >= model.lines.count - 4 ? 0.90 : 0.35))
                Color.clear.frame(height: PrompterModel.viewHeight)
            }
            .padding(.horizontal, 18)
            .padding(.trailing, 2)
            .offset(y: -model.contentOffset)
            .frame(maxWidth: .infinity, alignment: .topLeading)
            .onPreferenceChange(LineHeightKey.self) { heights in
                for (i, h) in heights {
                    model.setLineHeight(i, h)
                }
            }
        }
        .frame(height: PrompterModel.viewHeight)
        .clipped()
        .padding(.top, 6)
    }
}

struct LineRow: View {
    let line: QuranLine
    let surah: Int
    let distance: Int
    let language: Store.Language
    let phonetics: Store.Phonetics

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            if language == .ph {
                // The phonetics alone, the original look.
                Text(phonetics.restyle(line.phonetic))
                    .font(.system(size: 17, weight: distance == 0 ? .bold : .medium))
                    .foregroundStyle(distance == 0 ? Theme.current : Theme.dim)
                    .shadow(color: distance == 0 ? Color.black.opacity(0.35) : .clear, radius: 1, y: 1)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else if language == .ar {
                Text(line.arabic)
                    .font(Theme.arabicFont)
                    .fontWeight(distance == 0 ? .medium : .regular)
                    .foregroundStyle(distance == 0 ? Theme.current : Theme.dim)
                    .shadow(color: distance == 0 ? Color.black.opacity(0.35) : .clear, radius: 1, y: 1)
                    .multilineTextAlignment(.trailing)
                    .environment(\.layoutDirection, .rightToLeft)
                    .frame(maxWidth: .infinity, alignment: .trailing)
                    .fixedSize(horizontal: false, vertical: true)
                Text(phonetics.restyle(line.phonetic))
                    .font(.system(size: 14, weight: distance == 0 ? .semibold : .medium))
                    .foregroundStyle(distance == 0 ? Theme.current.opacity(0.85) : Theme.dim)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                Text(Translations.text(language, surah: surah, ayah: line.ayah))
                    .font(.system(size: 17, weight: distance == 0 ? .bold : .medium))
                    .foregroundStyle(distance == 0 ? Theme.current : Theme.dim)
                    .shadow(color: distance == 0 ? Color.black.opacity(0.35) : .clear, radius: 1, y: 1)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .opacity(Theme.lineOpacity(distance: distance))
        .animation(.easeInOut(duration: 0.36), value: distance)
    }
}

private struct LineHeightKey: PreferenceKey {
    static var defaultValue: [Int: CGFloat] = [:]
    static func reduce(value: inout [Int: CGFloat], nextValue: () -> [Int: CGFloat]) {
        value.merge(nextValue(), uniquingKeysWith: { $1 })
    }
}
