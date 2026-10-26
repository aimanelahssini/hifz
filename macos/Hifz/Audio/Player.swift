import AVFoundation
import Foundation

/// Plays one ayah at a time with pitch-preserving speed. Stop tears the engine down entirely.
final class Player {
    var onEnd: (() -> Void)?
    var onNext: (() -> Void)?
    var queued: URL?
    var speed: Double = 1.0 {
        didSet { applyRate() }
    }

    private(set) var playing: URL?
    private(set) var isPaused = false

    private var engine: AVAudioEngine?
    private var playerNode: AVAudioPlayerNode?
    private var timePitch: AVAudioUnitTimePitch?
    /// Next file already scheduled behind the current one (gapless).
    private var pendingGapless: URL?
    /// A new one at every play, halt and stop. Stopping the node calls the completion of every
    /// file it had scheduled; those belong to an older generation and are ignored, otherwise
    /// each one would move the text on by an ayah (going back 4 lines skipped 3).
    private var generation = 0

    var active: Bool { engine != nil }

    func start() {
        guard engine == nil else { return }
        Log.action("audio: engine start")
        let eng = AVAudioEngine()
        let node = AVAudioPlayerNode()
        let pitch = AVAudioUnitTimePitch()
        pitch.rate = Float(speed)
        pitch.pitch = 0
        eng.attach(node)
        eng.attach(pitch)
        eng.connect(node, to: pitch, format: nil)
        eng.connect(pitch, to: eng.mainMixerNode, format: nil)
        do {
            try eng.start()
        } catch {
            Log.action("audio: engine start failed: \(error)")
            return
        }
        engine = eng
        playerNode = node
        timePitch = pitch
    }

    func stop() {
        Log.action("audio: engine stop")
        generation += 1
        queued = nil
        pendingGapless = nil
        playerNode?.stop()
        engine?.stop()
        if let node = playerNode { engine?.detach(node) }
        if let pitch = timePitch { engine?.detach(pitch) }
        engine = nil
        playerNode = nil
        timePitch = nil
        playing = nil
        isPaused = false
    }

    func halt() {
        Log.action("audio: halt")
        generation += 1
        queued = nil
        pendingGapless = nil
        playerNode?.stop()
        playing = nil
        isPaused = false
    }

    func play(_ url: URL) {
        guard let node = playerNode, let eng = engine else { return }
        do {
            if !eng.isRunning { try eng.start() }
            let file = try AVAudioFile(forReading: url)
            generation += 1
            node.stop()
            playing = url
            isPaused = false
            pendingGapless = nil
            Log.action("audio: play \(url.lastPathComponent) @\(speed)x")
            schedule(file, url: url, on: node)
            applyRate()
            node.play()
            scheduleQueued(on: node)
        } catch {
            Log.action("audio: play failed: \(error)")
            playing = nil
        }
    }

    func pause() {
        guard let node = playerNode, playing != nil else { return }
        Log.action("audio: pause")
        node.pause()
        isPaused = true
    }

    func resume() {
        guard let node = playerNode, playing != nil else { return }
        Log.action("audio: resume \(playing?.lastPathComponent ?? "")")
        node.play()
        isPaused = false
    }

    private func applyRate() {
        timePitch?.rate = Float(speed)
        Log.action("audio: speed \(speed)x")
    }

    private func schedule(_ file: AVAudioFile, url: URL, on node: AVAudioPlayerNode) {
        let gen = generation
        // .dataPlayedBack: when the ayah has been heard, not when the file has been read.
        node.scheduleFile(file, at: nil, completionCallbackType: .dataPlayedBack) { [weak self] _ in
            DispatchQueue.main.async { self?.fileDidFinish(gen: gen, url: url) }
        }
    }

    private func scheduleQueued(on node: AVAudioPlayerNode) {
        guard let next = queued, FileManager.default.fileExists(atPath: next.path) else { return }
        do {
            let file = try AVAudioFile(forReading: next)
            queued = nil
            pendingGapless = next
            Log.action("audio: queue \(next.lastPathComponent)")
            schedule(file, url: next, on: node)
        } catch {
            Log.action("audio: queue failed: \(error)")
            pendingGapless = nil
        }
    }

    private func fileDidFinish(gen: Int, url: URL) {
        // Only the file playing now, scheduled since the last move, can end it.
        guard gen == generation, url == playing else { return }
        if let next = pendingGapless {
            playing = next
            pendingGapless = nil
            isPaused = false
            Log.action("audio: gapless next \(next.lastPathComponent)")
            onNext?()
            if let node = playerNode {
                scheduleQueued(on: node)
            }
            return
        }
        let was = playing
        playing = nil
        isPaused = false
        if was != nil {
            Log.action("audio: ended")
            onEnd?()
        }
    }
}
