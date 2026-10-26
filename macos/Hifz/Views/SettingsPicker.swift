import SwiftUI

struct SettingsPicker: View {
    @ObservedObject var model: PrompterModel

    private let sample = "Idhâ waqa'ati-l-wâqi'ah · Qoul houwa-llâhou"
    private var arabic: Bool { model.store.language == .ar }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Language")
                .font(.system(size: 11, weight: .bold))
                .foregroundStyle(.secondary)
            Picker("Language", selection: Binding(
                get: { model.store.language },
                set: { model.setLanguage($0) }
            )) {
                ForEach(Store.Language.allCases) { lang in
                    Text(lang.title).tag(lang)
                }
            }
            .labelsHidden()

            Text("Transliteration")
                .font(.system(size: 11, weight: .bold))
                .foregroundStyle(.secondary)
                .opacity(arabic ? 1 : 0.4)
            Picker("Transliteration", selection: Binding(
                get: { model.store.phonetics },
                set: { model.setPhonetics($0) }
            )) {
                ForEach(Store.Phonetics.allCases) { style in
                    Text(style.title).tag(style)
                }
            }
            .pickerStyle(.segmented)
            .labelsHidden()
            .disabled(!arabic)
            .opacity(arabic ? 1 : 0.4)

            Text(model.store.phonetics.restyle(sample))
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .opacity(arabic ? 1 : 0.4)
        }
        .padding(14)
        .frame(width: 280)
        .onAppear { Log.action("ui: open settings") }
    }
}
