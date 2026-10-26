import AppKit
import Combine
import SwiftUI
import UserNotifications

final class AppDelegate: NSObject, NSApplicationDelegate, UNUserNotificationCenterDelegate {
    private var panel: FloatingPanel?
    private var model: PrompterModel?
    private var store: Store?
    private var pendingURL: URL?
    private var cancellables = Set<AnyCancellable>()

    func applicationDidFinishLaunching(_ notification: Notification) {
        Log.action("app: launch")
        UNUserNotificationCenter.current().delegate = self
        Reminder.registerCategory()

        DistributedNotificationCenter.default().addObserver(
            self,
            selector: #selector(onDistributedURL(_:)),
            name: NSNotification.Name("HifzOpenURL"),
            object: nil)

        NSApp.mainMenu = Self.buildMainMenu()

        let store = Store.load()
        self.store = store
        let model = PrompterModel(store: store)
        self.model = model

        let root = RootView(model: model)
        let panel = FloatingPanel(rootView: root)
        self.panel = panel
        panel.apply(placement: store.placement, minimized: false, animate: false)
        panel.orderFrontRegardless()
        panel.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        Log.action("app: panel ordered front")

        bindPanel(to: model, store: store)

        if let url = pendingURL {
            pendingURL = nil
            handle(url: url)
        }

        if !UserDefaults.standard.bool(forKey: "reminderAsked") {
            UserDefaults.standard.set(true, forKey: "reminderAsked")
            Reminder.schedule()
        }
    }

    @MainActor
    private func bindPanel(to model: PrompterModel, store: Store) {
        Publishers.CombineLatest(model.$minimized, store.$placement)
            .dropFirst()
            .receive(on: RunLoop.main)
            .sink { [weak self] minimized, placement in
                self?.panel?.apply(placement: placement, minimized: minimized, animate: true)
                if !minimized {
                    self?.panel?.makeKeyAndOrderFront(nil)
                }
            }
            .store(in: &cancellables)
    }

    @objc private func onDistributedURL(_ note: Notification) {
        guard let s = note.object as? String, let url = URL(string: s) else { return }
        Log.action("app: distributed url \(s)")
        handle(url: url)
    }

    private static func buildMainMenu() -> NSMenu {
        let main = NSMenu()
        let appItem = NSMenuItem()
        main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Hifz", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Quit Hifz", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu

        let editItem = NSMenuItem()
        main.addItem(editItem)
        let edit = NSMenu(title: "Edit")
        edit.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = edit
        return main
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        Log.action("app: reopen")
        Task { @MainActor in
            model?.showFromMini()
            panel?.makeKeyAndOrderFront(nil)
        }
        return true
    }

    func application(_ application: NSApplication, open urls: [URL]) {
        for url in urls {
            if model == nil {
                pendingURL = url
            } else {
                handle(url: url)
            }
        }
    }

    func handle(url: URL) {
        Log.action("app: url \(url.absoluteString)")
        let parts = url.pathComponents.filter { $0 != "/" }
        var n: Int?
        if url.host == "surah", let first = parts.first, let v = Int(first) {
            n = v
        } else if let host = url.host, let v = Int(host) {
            n = v
        } else if let first = parts.first, let v = Int(first) {
            n = v
        } else if parts.count >= 2, parts[0] == "surah", let v = Int(parts[1]) {
            n = v
        }
        if let n, (1...114).contains(n) {
            openSurah(n)
        } else {
            Task { @MainActor in
                model?.showFromMini()
                panel?.makeKeyAndOrderFront(nil)
            }
        }
    }

    func openSurah(_ n: Int) {
        Log.action("app: openSurah \(n)")
        Task { @MainActor in
            model?.showFromMini()
            model?.loadSurah(n)
            panel?.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        Log.action("app: terminate")
        model?.player.stop()
        store?.save()
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner, .sound])
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        Log.action("reminder: clicked action=\(response.actionIdentifier)")
        let info = response.notification.request.content.userInfo
        let n = (info["surah"] as? Int) ?? Reminder.surah
        openSurah(n)
        completionHandler()
    }
}
