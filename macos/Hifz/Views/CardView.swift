import SwiftUI

struct CardView: View {
    @ObservedObject var model: PrompterModel
    @State private var reminderOn = false
    @State private var scrollAcc: Double = 0

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: Theme.radius, style: .continuous)
                .fill(Theme.cardBg)
                .overlay(
                    RoundedRectangle(cornerRadius: Theme.radius, style: .continuous)
                        .strokeBorder(Theme.border, lineWidth: 1)
                )

            VStack(spacing: 0) {
                HeaderView(model: model)
                LinesView(model: model)
                    .blur(radius: model.finishing ? 14 : 0)
                    .opacity(model.finishing ? 0.50 : 1)
            }

            if model.finishing {
                FinishOverlay(model: model)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: Theme.radius, style: .continuous))
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.16)) {
                model.closeHover = hovering
            }
        }
        .focusable()
        .onKeyPress { press in
            let key = press.key
            let mods = press.modifiers
            return model.handleKey(key, modifiers: mods) ? .handled : .ignored
        }
        .onAppear {
            Reminder.isEnabled { reminderOn = $0 }
        }
        .contextMenu { contextMenu }
        .background(ScrollWheelMonitor { dy in
            handleScroll(dy)
        })
        .background(KeyMonitor(model: model))
    }

    @ViewBuilder
    private var contextMenu: some View {
        Menu("Speed") {
            ForEach(Store.speeds, id: \.self) { s in
                Button("\(fmtSpeed(s))×") { model.setSpeed(s) }
            }
        }
        Button(model.audioOn ? "Recitation ✓" : "Recitation") {
            model.toggleAudio()
        }
        Menu("Reciter") {
            ForEach(Downloader.reciters, id: \.id) { r in
                Button(r.name + (model.store.reciter == r.id ? " ✓" : "")) {
                    model.setReciter(r.id)
                }
            }
        }
        Button(model.store.auto ? "Continue automatically ✓" : "Continue automatically") {
            model.toggleAuto()
        }
        Button(model.store.language == .ar ? "Arabic ✓" : "Arabic") {
            model.toggleArabic()
        }
        Button(reminderOn
               ? "Remind me at 22:00 (\(Quran.name(56))) ✓"
               : "Remind me at 22:00 (\(Quran.name(56)))") {
            reminderOn.toggle()
            Reminder.setEnabled(reminderOn)
            Log.action("ui: reminder \(reminderOn)")
        }
        Menu("Position") {
            ForEach(Store.Placement.allCases) { place in
                Button(place.title + (model.store.placement == place ? " ✓" : "")) {
                    model.setPlacement(place)
                }
            }
        }
        Divider()
        Button("Hide") { model.hideToMini() }
        Button("Back to the beginning") { model.restart() }
        Button("Close") {
            Log.action("ui: close from menu")
            NSApp.terminate(nil)
        }
    }

    private func handleScroll(_ dy: Double) {
        if model.finishing { return }
        scrollAcc += dy
        while scrollAcc >= 1 {
            scrollAcc -= 1
            model.move(model.next)
        }
        while scrollAcc <= -1 {
            scrollAcc += 1
            model.move(model.prev)
        }
    }
}

/// Captures scroll wheel events that SwiftUI may not deliver to a non-scroll view.
struct ScrollWheelMonitor: NSViewRepresentable {
    var onScroll: (Double) -> Void

    func makeNSView(context: Context) -> ScrollCatcher {
        let v = ScrollCatcher()
        v.onScroll = onScroll
        return v
    }

    func updateNSView(_ nsView: ScrollCatcher, context: Context) {
        nsView.onScroll = onScroll
    }

    final class ScrollCatcher: NSView {
        var onScroll: ((Double) -> Void)?
        override var acceptsFirstResponder: Bool { false }
        override func scrollWheel(with event: NSEvent) {
            // Positive dy = scroll up = previous; negative = next (match Linux).
            let dy = event.hasPreciseScrollingDeltas ? Double(event.scrollingDeltaY) / 40.0 : Double(event.scrollingDeltaY)
            // Invert so scroll-down (negative) advances, like Linux's EventControllerScroll.
            onScroll?(-dy)
        }
        override func hitTest(_ point: NSPoint) -> NSView? { nil }
    }
}

/// Ensures key events reach the model even when the panel is key but SwiftUI focus is soft.
struct KeyMonitor: NSViewRepresentable {
    @ObservedObject var model: PrompterModel

    func makeNSView(context: Context) -> KeyCatcher {
        let v = KeyCatcher()
        v.model = model
        DispatchQueue.main.async { v.window?.makeFirstResponder(v) }
        return v
    }

    func updateNSView(_ nsView: KeyCatcher, context: Context) {
        nsView.model = model
    }

    final class KeyCatcher: NSView {
        weak var model: PrompterModel?
        override var acceptsFirstResponder: Bool { true }

        override func keyDown(with event: NSEvent) {
            guard let model else {
                super.keyDown(with: event)
                return
            }
            if let key = Self.map(event) {
                let mods: EventModifiers = event.modifierFlags.contains(.command) ? .command : []
                if model.handleKey(key, modifiers: mods) {
                    Log.action("key: \(event.charactersIgnoringModifiers ?? "?")")
                    return
                }
            }
            super.keyDown(with: event)
        }

        override func mouseDown(with event: NSEvent) {
            window?.makeFirstResponder(self)
            super.mouseDown(with: event)
        }

        static func map(_ event: NSEvent) -> KeyEquivalent? {
            if event.modifierFlags.contains(.command) {
                if let c = event.charactersIgnoringModifiers?.lowercased(), c == "q" || c == "w" {
                    return KeyEquivalent(Character(c))
                }
            }
            switch event.keyCode {
            case 49: return " "
            case 125: return .downArrow
            case 126: return .upArrow
            case 123: return .leftArrow
            case 124: return .rightArrow
            case 36, 76: return .return
            case 53: return .escape
            case 51: return KeyEquivalent(Character(UnicodeScalar(0x7f)!))
            case 115: return .home
            default:
                if let c = event.charactersIgnoringModifiers?.first {
                    return KeyEquivalent(c)
                }
                return nil
            }
        }
    }
}
