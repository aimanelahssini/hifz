import SwiftUI

struct HeaderView: View {
    @ObservedObject var model: PrompterModel
    @State private var reminderOn = false

    var body: some View {
        HStack(spacing: 2) {
            surahButton
            whereLabel
                .layoutPriority(-1)
            Spacer(minLength: 2)
            // Keep the control cluster from being clipped by a long “where” label.
            HStack(spacing: 2) {
                settingsButton
                hideButton
                if model.loading {
                    ProgressView()
                        .controlSize(.mini)
                        .scaleEffect(0.7)
                }
                modeButton
                speedButton
                audioButton
                countPill
                HeaderCloseButton(visible: model.closeHover)
            }
            .layoutPriority(1)
            .fixedSize(horizontal: true, vertical: false)
        }
        .padding(.horizontal, 8)
        .frame(height: PrompterModel.headHeight)
        .onAppear {
            Reminder.isEnabled { reminderOn = $0 }
            Log.action("ui: header ready (gear, eye, close)")
        }
    }

    private var surahButton: some View {
        Button {
            Log.action("ui: open surah picker")
            model.showSurahPicker = true
        } label: {
            HStack(spacing: 5) {
                Text("\(model.surah)")
                    .foregroundStyle(Theme.headMuted)
                    .fontWeight(.semibold)
                Text(Quran.name(model.surah))
                    .foregroundStyle(Theme.surah)
                    .fontWeight(.semibold)
                Image(systemName: "chevron.down")
                    .font(.system(size: 8, weight: .semibold))
                    .foregroundStyle(Color.white.opacity(0.40))
            }
            .font(.system(size: 11))
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .popover(isPresented: $model.showSurahPicker, arrowEdge: .bottom) {
            SurahPicker(model: model)
        }
        .help("Choose a surah")
    }

    private var whereLabel: some View {
        let line = model.lines.indices.contains(model.index) ? model.lines[model.index] : nil
        let text: String = {
            guard let line else { return "" }
            let total = Quran.surah(model.surah).ayahs
            return line.ayah == 0 ? "  ·  Bismillah" : "  ·  \(line.ayah) / \(total)"
        }()
        return Text(text)
            .font(.system(size: 11))
            .foregroundStyle(Theme.headMuted)
            .lineLimit(1)
            .truncationMode(.tail)
            .frame(minWidth: 0, maxWidth: .infinity, alignment: .leading)
    }

    private var settingsButton: some View {
        Button {
            Log.action("ui: open settings")
            model.showSettingsPicker = true
        } label: {
            Image(systemName: "gearshape.fill")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(Color.white.opacity(0.70))
                .frame(width: 22, height: 22)
                .background(Circle().fill(Color.white.opacity(0.10)))
        }
        .buttonStyle(.plain)
        .popover(isPresented: $model.showSettingsPicker, arrowEdge: .bottom) {
            SettingsPicker(model: model)
        }
        .help("Settings")
        .accessibilityLabel("Settings")
    }

    private var hideButton: some View {
        Button {
            model.hideToMini()
        } label: {
            Image(systemName: "eye.slash.fill")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(Color.white.opacity(0.70))
                .frame(width: 22, height: 22)
                .background(Circle().fill(Color.white.opacity(0.10)))
        }
        .buttonStyle(.plain)
        .help("Hide (leaves a small book icon) · H")
        .accessibilityLabel("Hide")
    }

    private var modeButton: some View {
        let icons = [
            "repeat": "repeat",
            "next": "arrow.right",
            "previous": "arrow.left",
            "shuffle": "shuffle",
        ]
        let tips = [
            "repeat": "At the end: start again",
            "next": "At the end: the next surah",
            "previous": "At the end: the previous surah",
            "shuffle": "At the end: a random surah",
        ]
        return Button {
            model.cycleAfter()
        } label: {
            Image(systemName: icons[model.store.after] ?? "repeat")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(Color.white.opacity(0.45))
                .frame(width: 22, height: 22)
        }
        .buttonStyle(.plain)
        .help(tips[model.store.after] ?? "")
    }

    private var speedButton: some View {
        Button {
            Log.action("ui: open speed picker")
            model.showSpeedPicker = true
        } label: {
            Text(fmtSpeed(model.store.speed) + "×")
                .font(.system(size: 11, weight: .bold).monospacedDigit())
                .foregroundStyle(Theme.surah)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
        }
        .buttonStyle(.plain)
        .popover(isPresented: $model.showSpeedPicker, arrowEdge: .bottom) {
            SpeedPicker(model: model)
        }
        .help("Speed (← and →)")
    }

    private var audioButton: some View {
        Button {
            model.toggleAudio()
        } label: {
            Image(systemName: model.audioOn ? "speaker.wave.2.fill" : "speaker.slash.fill")
                .font(.system(size: 11))
                .foregroundStyle(model.audioOn ? Color.white : Color.white.opacity(0.45))
                .frame(width: 22, height: 22)
        }
        .buttonStyle(.plain)
        .help(model.audioOn ? "Recitation on (M)" : "Recitation off (M)")
    }

    private var countPill: some View {
        let n = model.store.finished(model.surah)
        return HStack(spacing: 3) {
            Image(systemName: "checkmark")
                .font(.system(size: 8, weight: .bold))
            Text("\(n)")
                .font(.system(size: 11, weight: .bold))
        }
        .foregroundStyle(n == 0 ? Color.white.opacity(0.32) : Color.white.opacity(0.60))
        .padding(.horizontal, 8)
        .padding(.vertical, 1)
        .background(Capsule().fill(Theme.countBg))
        .help("Times you finished this surah")
    }
}

func fmtSpeed(_ s: Double) -> String {
    if s == s.rounded() { return String(Int(s)) }
    return String(format: "%g", s)
}
