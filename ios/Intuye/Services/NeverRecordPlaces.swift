import CoreLocation
import Foundation

/// A place where capture never listens, such as a clinic, an office or a friend's home.
/// Stored only on this iPhone. Never sent to the server and not part of the account export.
struct NeverRecordPlace: Codable, Identifiable, Hashable {
    var id = UUID()
    var name: String
    var latitude: Double
    var longitude: Double
    var radius: Double  // metres

    var center: CLLocationCoordinate2D { CLLocationCoordinate2D(latitude: latitude, longitude: longitude) }
}

/// Keeps the never-record places and knows whether the phone is inside one right now (H7).
/// Uses CLMonitor geofences, so the check happens on the device and costs little battery.
@MainActor
@Observable
final class NeverRecordPlaces {
    static let radii: [Double] = [100, 200, 400]

    private(set) var places: [NeverRecordPlace] = []
    /// The place the phone is in right now, if any. Capture stays off while this is set.
    private(set) var current: NeverRecordPlace?
    private(set) var authorization: CLAuthorizationStatus
    /// Called when `current` changes, so capture can start or stop.
    var onChange: (() -> Void)?

    private let fileURL: URL
    private let manager = CLLocationManager()
    private var monitor: CLMonitor?
    private var inside: Set<String> = []
    private var events: Task<Void, Never>?

    init() {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        fileURL = dir.appendingPathComponent("never-record-places.json")
        places = (try? JSONDecoder().decode([NeverRecordPlace].self, from: Data(contentsOf: fileURL))) ?? []
        authorization = manager.authorizationStatus
    }

    var locationAllowed: Bool { authorization == .authorizedWhenInUse || authorization == .authorizedAlways }

    /// Starts watching the saved places. Safe to call more than once.
    func start() async {
        authorization = manager.authorizationStatus
        guard !places.isEmpty, locationAllowed else { return }
        let monitor = await ensureMonitor()
        let wanted = Set(places.map(\.id.uuidString))
        for id in await monitor.identifiers where !wanted.contains(id) { await monitor.remove(id) }
        let have = Set(await monitor.identifiers)
        for p in places where !have.contains(p.id.uuidString) {
            await monitor.add(CLMonitor.CircularGeographicCondition(center: p.center, radius: p.radius),
                              identifier: p.id.uuidString, assuming: .unsatisfied)
        }
        // After a relaunch, pick up where each geofence already stands instead of waiting for the next change.
        for id in await monitor.identifiers {
            if let record = await monitor.record(for: id) {
                if record.lastEvent.state == .satisfied { inside.insert(id) } else { inside.remove(id) }
            }
        }
        updateCurrent()
    }

    /// Adds the phone's current location. Asks for location access the first time.
    func addCurrentLocation(name: String, radius: Double) async throws {
        authorization = manager.authorizationStatus
        if authorization == .denied || authorization == .restricted { throw PlaceError.noLocation }
        if authorization == .notDetermined { manager.requestWhenInUseAuthorization() }
        guard let location = try await currentLocation() else { throw PlaceError.noLocation }
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let place = NeverRecordPlace(name: trimmed.isEmpty ? "This place" : String(trimmed.prefix(40)),
                                     latitude: location.coordinate.latitude, longitude: location.coordinate.longitude,
                                     radius: radius)
        places.append(place)
        save()
        // Background geofence events need "Always". Ask once, after the learner has shown they want this.
        if manager.authorizationStatus == .authorizedWhenInUse { manager.requestAlwaysAuthorization() }
        // You're standing in it, so capture pauses at once rather than waiting for the first geofence event.
        inside.insert(place.id.uuidString)
        updateCurrent()
        await start()
    }

    func remove(_ place: NeverRecordPlace) async {
        places.removeAll { $0.id == place.id }
        save()
        inside.remove(place.id.uuidString)
        updateCurrent()
        await monitor?.remove(place.id.uuidString)
    }

    enum PlaceError: LocalizedError {
        case noLocation
        var errorDescription: String? { "Couldn't find where you are. Check that location is on for Intuye in Settings." }
    }

    // MARK: Private

    private func ensureMonitor() async -> CLMonitor {
        if let monitor { return monitor }
        let m = await CLMonitor("intuye.never-record")
        monitor = m
        events = Task { [weak self] in
            do {
                for try await event in await m.events {
                    guard let self else { return }
                    if event.state == .satisfied { self.inside.insert(event.identifier) } else { self.inside.remove(event.identifier) }
                    self.updateCurrent()
                }
            } catch {}
        }
        return m
    }

    private func updateCurrent() {
        let now = places.first { inside.contains($0.id.uuidString) }
        guard now != current else { return }
        current = now
        onChange?()
    }

    private func currentLocation() async throws -> CLLocation? {
        if let recent = manager.location, recent.timestamp.timeIntervalSinceNow > -60, recent.horizontalAccuracy <= 100 {
            return recent
        }
        // First reasonably accurate fix, or give up after 30 seconds (time to answer the permission prompt).
        return try await withThrowingTaskGroup(of: CLLocation?.self) { group in
            group.addTask {
                for try await update in CLLocationUpdate.liveUpdates() {
                    if let loc = update.location, loc.horizontalAccuracy <= 100 { return loc }
                }
                return nil
            }
            group.addTask { try await Task.sleep(for: .seconds(30)); return nil }
            let first = try await group.next() ?? nil
            group.cancelAll()
            return first
        }
    }

    private func save() {
        let data = (try? JSONEncoder().encode(places)) ?? Data()
        try? data.write(to: fileURL, options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
    }
}
