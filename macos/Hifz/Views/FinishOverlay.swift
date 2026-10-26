import SwiftUI

struct FinishOverlay: View {
    @ObservedObject var model: PrompterModel

    var body: some View {
        ZStack {
            Color(red: 10 / 255, green: 10 / 255, blue: 14 / 255).opacity(0.45)
            VStack(spacing: 6) {
                Text("Finished \(Quran.name(model.surah))?")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(.white)
                let n = model.store.finished(model.surah)
                Text(n == 0 ? "It will count as your first time"
                      : "Finished \(n) time\(n == 1 ? "" : "s") so far")
                    .font(.system(size: 12))
                    .foregroundStyle(Color.white.opacity(0.60))
                if let then = model.thenSurah {
                    Text(then == model.surah ? "Then from the start"
                          : "Then \(then) \(Quran.name(then))")
                        .font(.system(size: 11))
                        .foregroundStyle(Theme.gold.opacity(0.85))
                }
                HStack(spacing: 10) {
                    Button("Not yet") {
                        model.answer(false)
                    }
                    .buttonStyle(FinishButtonStyle(primary: false))
                    Button("Yes, I finished") {
                        model.answer(true)
                    }
                    .buttonStyle(FinishButtonStyle(primary: true))
                    .keyboardShortcut(.defaultAction)
                }
                .padding(.top, 10)
            }
            .padding(20)
        }
        .clipShape(RoundedRectangle(cornerRadius: Theme.radius, style: .continuous))
    }
}

struct FinishButtonStyle: ButtonStyle {
    let primary: Bool

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .semibold))
            .padding(.horizontal, 18)
            .padding(.vertical, 6)
            .background(
                Capsule().fill(primary
                    ? Color.white.opacity(configuration.isPressed ? 0.86 : 1)
                    : Color.white.opacity(configuration.isPressed ? 0.20 : 0.12))
            )
            .foregroundStyle(primary ? Color(red: 0.067, green: 0.067, blue: 0.078) : .white)
    }
}
