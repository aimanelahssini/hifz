#!/usr/bin/env swift
/// Renders a simple Hifz app icon (matching the SVG) into AppIcon.appiconset PNGs.
import AppKit
import Foundation

let outDir = CommandLine.arguments.count > 1
    ? CommandLine.arguments[1]
    : FileManager.default.currentDirectoryPath + "/Hifz/Assets.xcassets/AppIcon.appiconset"

func drawIcon(size: CGFloat) -> NSImage {
    let image = NSImage(size: NSSize(width: size, height: size))
    image.lockFocus()
    let s = size / 128.0
    NSGraphicsContext.current?.imageInterpolation = .high

    let bg = NSGradient(colors: [
        NSColor(red: 0.145, green: 0.169, blue: 0.251, alpha: 1),
        NSColor(red: 0.067, green: 0.075, blue: 0.110, alpha: 1),
    ])!
    let rect = NSRect(x: 8 * s, y: 8 * s, width: 112 * s, height: 112 * s)
    let path = NSBezierPath(roundedRect: rect, xRadius: 28 * s, yRadius: 28 * s)
    bg.draw(in: path, angle: -90)

    NSColor.white.setFill()
    NSBezierPath(roundedRect: NSRect(x: 28 * s, y: 67 * s, width: 58 * s, height: 11 * s),
                 xRadius: 5.5 * s, yRadius: 5.5 * s).fill()
    NSColor.white.withAlphaComponent(0.42).setFill()
    NSBezierPath(roundedRect: NSRect(x: 28 * s, y: 49 * s, width: 72 * s, height: 9 * s),
                 xRadius: 4.5 * s, yRadius: 4.5 * s).fill()
    NSColor.white.withAlphaComponent(0.22).setFill()
    NSBezierPath(roundedRect: NSRect(x: 28 * s, y: 32 * s, width: 48 * s, height: 9 * s),
                 xRadius: 4.5 * s, yRadius: 4.5 * s).fill()

    let gold = NSGradient(colors: [
        NSColor(red: 0.965, green: 0.851, blue: 0.545, alpha: 1),
        NSColor(red: 0.851, green: 0.643, blue: 0.255, alpha: 1),
    ])!
    let circle = NSBezierPath(ovalIn: NSRect(x: 83 * s, y: 85 * s, width: 22 * s, height: 22 * s))
    gold.draw(in: circle, angle: -45)

    let check = NSBezierPath()
    check.move(to: NSPoint(x: 89 * s, y: 95.6 * s))
    check.line(to: NSPoint(x: 92.4 * s, y: 92.2 * s))
    check.line(to: NSPoint(x: 99 * s, y: 99.2 * s))
    check.lineWidth = 2.8 * s
    check.lineCapStyle = .round
    check.lineJoinStyle = .round
    NSColor(red: 0.102, green: 0.114, blue: 0.169, alpha: 1).setStroke()
    check.stroke()

    image.unlockFocus()
    return image
}

func writePNG(_ image: NSImage, size: Int, to url: URL) {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size,
                               bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                               colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    image.draw(in: NSRect(x: 0, y: 0, width: size, height: size),
               from: .zero, operation: .copy, fraction: 1)
    NSGraphicsContext.restoreGraphicsState()
    try! rep.representation(using: .png, properties: [:])!.write(to: url)
}

try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)
let sizes = [16, 32, 128, 256, 512]
var images: [[String: Any]] = []
for size in sizes {
    let img = drawIcon(size: CGFloat(size))
    let name = "icon_\(size).png"
    writePNG(img, size: size, to: URL(fileURLWithPath: outDir).appendingPathComponent(name))
    images.append(["size": "\(size)x\(size)", "idiom": "mac", "filename": name, "scale": "1x"])
    let img2 = drawIcon(size: CGFloat(size * 2))
    let name2 = "icon_\(size)@2x.png"
    writePNG(img2, size: size * 2, to: URL(fileURLWithPath: outDir).appendingPathComponent(name2))
    images.append(["size": "\(size)x\(size)", "idiom": "mac", "filename": name2, "scale": "2x"])
}
let contents: [String: Any] = [
    "images": images,
    "info": ["version": 1, "author": "xcode"],
]
let data = try! JSONSerialization.data(withJSONObject: contents, options: [.prettyPrinted, .sortedKeys])
try! data.write(to: URL(fileURLWithPath: outDir).appendingPathComponent("Contents.json"))
print("Wrote AppIcon to \(outDir)")
