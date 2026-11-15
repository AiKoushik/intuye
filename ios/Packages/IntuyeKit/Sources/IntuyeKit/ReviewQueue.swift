import Foundation

/// A rating made offline, replayed later with the moment it actually happened (P6).
public struct PendingReview: Codable, Sendable, Hashable {
    public let lexemeId: String
    public let rating: Int
    public let reviewedAt: String
    public init(lexemeId: String, rating: Int, reviewedAt: String) { self.lexemeId = lexemeId; self.rating = rating; self.reviewedAt = reviewedAt }
}

/// Keeps the last due list on the device so a review session can run in airplane mode,
/// and queues the ratings until the server is reachable again.
public actor ReviewQueue {
    private struct Stored: Codable { var pending: [PendingReview] = []; var due: [DueCard] = [] }
    private let fileURL: URL
    private var stored: Stored

    public init(fileURL: URL) {
        self.fileURL = fileURL
        self.stored = (try? JSONDecoder().decode(Stored.self, from: Data(contentsOf: fileURL))) ?? Stored()
    }

    public var count: Int { stored.pending.count }

    public func cache(_ due: [DueCard]) { stored.due = due; persist() }

    /// Cached cards not yet rated offline.
    public func cachedDue() -> [DueCard] {
        let done = Set(stored.pending.map(\.lexemeId))
        return stored.due.filter { !done.contains($0.lexemeId) }
    }

    public func append(_ review: PendingReview) { stored.pending.append(review); persist() }

    /// Replays in order; stops at the first network failure, drops ones the server refuses.
    @discardableResult
    public func flush(using send: (PendingReview) async throws -> Void) async -> Int {
        var sent = 0
        while let first = stored.pending.first {
            do { try await send(first) } catch let e as APIError where e.status == 0 { break } catch {}
            stored.pending.removeFirst()
            sent += 1
            persist()
        }
        return sent
    }

    private func persist() {
        let data = (try? JSONEncoder().encode(stored)) ?? Data()
        try? data.write(to: fileURL, options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
    }
}
