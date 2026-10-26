import SwiftUI

/// Soft header-style ×, always to the right of the finish count.
/// Faint until the card is hovered; circle only when the × itself is hovered.
struct HeaderCloseButton: View {
    var visible: Bool
    @State private var hovering = false

    var body: some View {
        Button {
            Log.action("ui: close")
            NSApp.terminate(nil)
        } label: {
            Image(systemName: "xmark")
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(Color.white.opacity(hovering ? 1 : (visible ? 0.55 : 0.28)))
                .frame(width: 22, height: 22)
                .background(Circle().fill(Color.white.opacity(hovering ? 0.10 : 0)))
        }
        .buttonStyle(.plain)
        .help("Close (⌘Q)")
        .onHover { hovering = $0 }
        .animation(.easeInOut(duration: 0.12), value: hovering)
        .animation(.easeInOut(duration: 0.16), value: visible)
    }
}
