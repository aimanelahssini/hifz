import SwiftUI

struct SpeedPicker: View {
    @ObservedObject var model: PrompterModel

    private var steps: [Double] {
        stride(from: Store.speedMin, through: Store.speedMax, by: 0.05).map {
            ($0 * 20).rounded() / 20
        }
    }

    var body: some View {
        ScrollViewReader { proxy in
            List(steps, id: \.self) { v in
                Button {
                    Log.action("ui: pick speed \(v)")
                    model.setSpeed(v)
                    model.showSpeedPicker = false
                } label: {
                    Text("\(fmtSpeed(v))×")
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .fontWeight(abs(v - model.store.speed) < 0.001 ? .bold : .regular)
                }
                .buttonStyle(.plain)
                .listRowBackground(abs(v - model.store.speed) < 0.001 ? Theme.gold.opacity(0.16) : Color.clear)
                .id(v)
            }
            .listStyle(.plain)
            .frame(width: 100, height: 280)
            .onAppear {
                DispatchQueue.main.async {
                    proxy.scrollTo(model.store.speed, anchor: .center)
                }
            }
        }
        .padding(6)
    }
}
