import SwiftUI

/// Switches between the full card and the small book icon when hidden.
struct RootView: View {
    @ObservedObject var model: PrompterModel

    var body: some View {
        Group {
            if model.minimized {
                MiniBookView(model: model)
                    .frame(width: FloatingPanel.miniSize, height: FloatingPanel.miniSize)
            } else {
                CardView(model: model)
                    .frame(width: CardLayout.cardWidth, height: CardLayout.cardHeight)
            }
        }
    }
}

/// Compact stand-in when the card is hidden: click to reopen.
struct MiniBookView: View {
    @ObservedObject var model: PrompterModel
    @State private var hover = false

    var body: some View {
        ZStack(alignment: .topTrailing) {
            Button {
                model.showFromMini()
            } label: {
                ZStack {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [
                                    Color(red: 0.145, green: 0.169, blue: 0.251),
                                    Color(red: 0.067, green: 0.075, blue: 0.110),
                                ],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .strokeBorder(Color.white.opacity(0.12), lineWidth: 1)
                    Image(systemName: "book.closed.fill")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [
                                    Color(red: 0.965, green: 0.851, blue: 0.545),
                                    Color(red: 0.851, green: 0.643, blue: 0.255),
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .scaleEffect(hover ? 1.08 : 1.0)
                }
                .frame(width: FloatingPanel.miniSize, height: FloatingPanel.miniSize)
                .shadow(color: .black.opacity(hover ? 0.35 : 0.20), radius: hover ? 8 : 4, y: 2)
            }
            .buttonStyle(.plain)
            .help("Show Hifz")
        }
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) { hover = hovering }
        }
        .contextMenu {
            Button("Show") { model.showFromMini() }
            Menu("Position") {
                ForEach(Store.Placement.allCases) { place in
                    Button(place.title + (model.store.placement == place ? " ✓" : "")) {
                        model.setPlacement(place)
                    }
                }
            }
            Divider()
            Button("Quit") {
                Log.action("ui: quit from mini menu")
                NSApp.terminate(nil)
            }
        }
        .onAppear { Log.action("ui: mini book visible") }
    }
}
