import AppKit

/// Pure AppKit entry: SwiftUI App with only a Settings scene never ordered the panel front.
@main
enum HifzMain {
    static let bundleId = "io.github.aimanelahssini.Hifz"

    static func main() {
        // Hand off to an already-running copy (e.g. when launched by a URL while open).
        let others = NSRunningApplication.runningApplications(withBundleIdentifier: bundleId)
            .filter { $0.processIdentifier != ProcessInfo.processInfo.processIdentifier && !$0.isTerminated }
        if let other = others.first {
            Log.action("app: another instance running, activating pid=\(other.processIdentifier)")
            other.activate(options: [.activateAllWindows, .activateIgnoringOtherApps])
            // Forward any launch URLs via distributed notification.
            let urls = ProcessInfo.processInfo.arguments.dropFirst().compactMap { arg -> String? in
                arg.hasPrefix("hifz:") ? arg : nil
            }
            if let first = urls.first {
                DistributedNotificationCenter.default().postNotificationName(
                    NSNotification.Name("HifzOpenURL"),
                    object: first, userInfo: nil, deliverImmediately: true)
            }
            return
        }

        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        Log.action("app: main starting")
        app.run()
    }
}
