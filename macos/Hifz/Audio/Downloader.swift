import Foundation

/// Fetches ayah MP3s from everyayah.com, one by one. Urgent requests jump the queue.
final class Downloader {
    static let reciters: [(id: String, name: String)] = [
        ("Alafasy_128kbps", "Mishary Alafasy"),
        ("Husary_128kbps", "Mahmoud Khalil Al-Husary"),
        ("Minshawy_Murattal_128kbps", "Mohamed Siddiq Al-Minshawi"),
        ("Abdul_Basit_Murattal_192kbps", "Abdul Basit Abdul Samad"),
        ("Abdurrahmaan_As-Sudais_192kbps", "Abdul Rahman Al-Sudais"),
        ("MaherAlMuaiqly128kbps", "Maher Al-Muaiqly"),
        ("Saood_ash-Shuraym_128kbps", "Saud Al-Shuraim"),
        ("Yasser_Ad-Dussary_128kbps", "Yasser Al-Dosari"),
    ]

    private struct Job {
        let path: URL
        let url: URL
        let done: ((URL?) -> Void)?
    }

    private let queue = DispatchQueue(label: "hifz.downloader")
    private var pending: [Job] = []
    private var running = false
    private let lock = NSLock()

    static func cacheDir(reciter: String) -> URL {
        let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first!
        return base.appendingPathComponent("Hifz/audio/\(reciter)", isDirectory: true)
    }

    /// The basmala (ayah 0) is played from Al-Fatiha 1:1.
    static func file(reciter: String, surah: Int, ayah: Int) -> (path: URL, url: URL) {
        var s = surah, a = ayah
        if a == 0 { s = 1; a = 1 }
        let name = String(format: "%03d%03d.mp3", s, a)
        let path = cacheDir(reciter: reciter).appendingPathComponent(name)
        let url = URL(string: "https://everyayah.com/data/\(reciter)/\(name)")!
        return (path, url)
    }

    func fetch(reciter: String, surah: Int, ayah: Int, urgent: Bool = false,
               done: ((URL?) -> Void)? = nil) {
        let (path, url) = Downloader.file(reciter: reciter, surah: surah, ayah: ayah)
        if FileManager.default.fileExists(atPath: path.path) {
            Log.action("audio: cache hit \(path.lastPathComponent)")
            DispatchQueue.main.async { done?(path) }
            return
        }
        lock.lock()
        let job = Job(path: path, url: url, done: done)
        if urgent {
            pending.insert(job, at: 0)
        } else {
            pending.append(job)
        }
        let start = !running
        if start { running = true }
        lock.unlock()
        if start {
            queue.async { [weak self] in self?.run() }
        }
    }

    private func run() {
        while true {
            lock.lock()
            guard !pending.isEmpty else {
                running = false
                lock.unlock()
                return
            }
            let job = pending.removeFirst()
            lock.unlock()

            var ok = FileManager.default.fileExists(atPath: job.path.path)
            if !ok {
                do {
                    try FileManager.default.createDirectory(
                        at: job.path.deletingLastPathComponent(),
                        withIntermediateDirectories: true)
                    var req = URLRequest(url: job.url, timeoutInterval: 30)
                    req.setValue("Hifz/1.0", forHTTPHeaderField: "User-Agent")
                    Log.action("audio: download \(job.url.lastPathComponent)")
                    let (data, response) = try URLSession.shared.syncData(for: req)
                    if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                        throw URLError(.badServerResponse)
                    }
                    let tmp = job.path.appendingPathExtension("part")
                    try data.write(to: tmp, options: .atomic)
                    if FileManager.default.fileExists(atPath: job.path.path) {
                        try FileManager.default.removeItem(at: job.path)
                    }
                    try FileManager.default.moveItem(at: tmp, to: job.path)
                    ok = true
                    Log.action("audio: saved \(job.path.lastPathComponent)")
                } catch {
                    Log.action("audio: download failed \(job.url.lastPathComponent): \(error)")
                    ok = false
                }
            }
            let result: URL? = ok ? job.path : nil
            DispatchQueue.main.async { job.done?(result) }
        }
    }
}

private extension URLSession {
    func syncData(for request: URLRequest) throws -> (Data, URLResponse) {
        var result: Result<(Data, URLResponse), Error>!
        let sem = DispatchSemaphore(value: 0)
        let task = dataTask(with: request) { data, response, error in
            if let error {
                result = .failure(error)
            } else if let data, let response {
                result = .success((data, response))
            } else {
                result = .failure(URLError(.unknown))
            }
            sem.signal()
        }
        task.resume()
        sem.wait()
        return try result.get()
    }
}
