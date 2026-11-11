import Foundation

/// Persists captured sentences until they upload, so nothing is lost offline or when the app is killed.
public actor OfflineQueue {
    private let fileURL: URL
    private var items: [UtteranceUpload]

    public init(fileURL: URL) {
        self.fileURL = fileURL
        self.items = (try? JSONDecoder().decode([UtteranceUpload].self, from: Data(contentsOf: fileURL))) ?? []
    }

    public var count: Int { items.count }

    public func append(_ item: UtteranceUpload) {
        items.append(item)
        persist()
    }

    /// Removes items whose spoken time is within the last `minutes` (local half of "forget last N minutes").
    public func forget(minutes: Int, now: Date = Date()) {
        let cutoff = now.addingTimeInterval(-Double(minutes) * 60)
        items.removeAll { (LCDate.parse($0.spokenAt) ?? .distantPast) >= cutoff }
        persist()
    }

    /// Uploads in batches of up to 200; keeps whatever fails.
    @discardableResult
    public func flush(using upload: (_ batch: [UtteranceUpload]) async throws -> Void) async -> Int {
        var sent = 0
        while !items.isEmpty {
            let batch = Array(items.prefix(200))
            do { try await upload(batch) } catch { break }
            items.removeFirst(batch.count)
            sent += batch.count
            persist()
        }
        return sent
    }

    private func persist() {
        let data = (try? JSONEncoder().encode(items)) ?? Data()
        try? data.write(to: fileURL, options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
    }
}
