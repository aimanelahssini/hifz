import AppKit
import QuartzCore
import SwiftUI

/// Borderless floating panel pinned to a chosen screen corner (or top center).
/// Stays fixed on screen across Space swipes so you can keep reading while switching desktops.
final class FloatingPanel: NSPanel {
    static let width: CGFloat = CardLayout.cardWidth
    static let height: CGFloat = CardLayout.cardHeight
    static let miniSize: CGFloat = 44
    static let margin: CGFloat = 16

    private var hostingView: NSHostingView<AnyView>?

    init(rootView: some View) {
        super.init(
            contentRect: NSRect(x: 0, y: 0, width: Self.width, height: Self.height),
            styleMask: [.borderless, .nonactivatingPanel, .utilityWindow],
            backing: .buffered,
            defer: false
        )
        isOpaque = false
        backgroundColor = .clear
        hasShadow = false
        // Above normal windows so Spaces compositing treats us like a HUD, not a desktop window.
        level = .statusBar
        pinAcrossSpaces()
        isMovableByWindowBackground = false
        becomesKeyOnlyIfNeeded = true
        hidesOnDeactivate = false
        // Don't participate in the Space-switch slide animation.
        animationBehavior = .none
        titleVisibility = .hidden
        titlebarAppearsTransparent = true
        isFloatingPanel = true
        // Needed so SwiftUI .onHover (eye/× visibility) fires on a non-activating panel.
        acceptsMouseMovedEvents = true
        ignoresMouseEvents = false

        let host = NSHostingView(rootView: AnyView(rootView))
        host.frame = NSRect(x: 0, y: 0, width: Self.width, height: Self.height)
        contentView = host
        hostingView = host

        NotificationCenter.default.addObserver(
            self, selector: #selector(screenChanged),
            name: NSApplication.didChangeScreenParametersNotification, object: nil)
        NSWorkspace.shared.notificationCenter.addObserver(
            self, selector: #selector(spaceChanged),
            name: NSWorkspace.activeSpaceDidChangeNotification, object: nil)

        Log.action("panel: created (pinned across Spaces)")
    }

    /// Appear on every Space and stay visually fixed during the swipe (like the menu bar).
    private func pinAcrossSpaces() {
        var behavior: NSWindow.CollectionBehavior = [
            .canJoinAllSpaces,
            .stationary,
            .fullScreenAuxiliary,
            .ignoresCycle,
        ]
        if #available(macOS 13.0, *) {
            behavior.insert(.canJoinAllApplications)
        }
        collectionBehavior = behavior
    }

    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }

    private var lastPlacement: Store.Placement = .topRight
    private var lastMinimized = false

    @objc private func screenChanged() {
        apply(placement: lastPlacement, minimized: lastMinimized, animate: false)
    }

    @objc private func spaceChanged() {
        // Re-assert pin + keep us ordered front; do not move the frame (that would look like a jump).
        pinAcrossSpaces()
        orderFrontRegardless()
        Log.action("panel: space changed — stayed put")
    }

    func apply(placement: Store.Placement, minimized: Bool, animate: Bool = true) {
        lastPlacement = placement
        lastMinimized = minimized
        let size = minimized
            ? NSSize(width: Self.miniSize, height: Self.miniSize)
            : NSSize(width: Self.width, height: Self.height)
        let origin = Self.origin(for: placement, size: size)
        let frame = NSRect(origin: origin, size: size)
        Log.action("panel: apply \(placement.rawValue) mini=\(minimized) at (\(Int(origin.x)), \(Int(origin.y)))")
        if animate {
            NSAnimationContext.runAnimationGroup { ctx in
                ctx.duration = 0.22
                ctx.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
                animator().setFrame(frame, display: true)
            }
        } else {
            setFrame(frame, display: true)
        }
        hostingView?.frame = NSRect(origin: .zero, size: size)
    }

    static func origin(for placement: Store.Placement, size: NSSize) -> NSPoint {
        guard let screen = NSScreen.main ?? NSScreen.screens.first else {
            return .zero
        }
        let f = screen.visibleFrame
        let m = margin
        switch placement {
        case .topLeft:
            return NSPoint(x: f.minX + m, y: f.maxY - size.height - m)
        case .topCenter:
            return NSPoint(x: f.midX - size.width / 2, y: f.maxY - size.height - m)
        case .topRight:
            return NSPoint(x: f.maxX - size.width - m, y: f.maxY - size.height - m)
        case .bottomLeft:
            return NSPoint(x: f.minX + m, y: f.minY + m)
        case .bottomRight:
            return NSPoint(x: f.maxX - size.width - m, y: f.minY + m)
        }
    }
}
