import CryptoKit
import DeviceCheck
import Foundation
import LangCoachKit

/// App Attest: registers a Secure Enclave key once, then signs every API request.
/// Client-data conventions must match backend/app/security/app_attest.py.
actor AttestService: RequestSigner {
    private let baseURL: URL
    private var keyId: String? = KeychainStore.string("attestKeyId")
    private var registering: Task<String?, Never>?

    init(baseURL: URL) { self.baseURL = baseURL }

    var isSupported: Bool { DCAppAttestService.shared.isSupported }

    func headers(method: String, pathAndQuery: String, body: Data) async -> [String: String] {
        guard DCAppAttestService.shared.isSupported, let keyId = await registeredKey() else { return [:] }
        let ts = String(Int(Date().timeIntervalSince1970))
        let bodyHash = SHA256.hash(data: body).map { String(format: "%02x", $0) }.joined()
        let clientData = Data("\(method.uppercased())\n\(pathAndQuery)\n\(bodyHash)\n\(ts)".utf8)
        let hash = Data(SHA256.hash(data: clientData))
        do {
            let assertion = try await DCAppAttestService.shared.generateAssertion(keyId, clientDataHash: hash)
            return ["X-LC-Key-Id": keyId, "X-LC-Assertion": assertion.base64EncodedString(), "X-LC-Timestamp": ts]
        } catch let error as DCError where error.code == .invalidKey {
            self.keyId = nil
            KeychainStore.setString(nil, for: "attestKeyId")  // key lost (e.g. restored backup): re-attest next call
            return [:]
        } catch {
            return [:]
        }
    }

    /// Generates and attests a key on first use; concurrent callers share the same registration.
    private func registeredKey() async -> String? {
        if let keyId { return keyId }
        if let registering { return await registering.value }
        let task = Task { () -> String? in
            do {
                let id = try await DCAppAttestService.shared.generateKey()
                let challenge = try await fetchChallenge()
                let hash = Data(SHA256.hash(data: Data(challenge.utf8)))
                let attestation = try await DCAppAttestService.shared.attestKey(id, clientDataHash: hash)
                try await register(keyId: id, attestation: attestation.base64EncodedString(), challenge: challenge)
                KeychainStore.setString(id, for: "attestKeyId")
                return id
            } catch {
                return nil  // server in report/off mode still works; enforce mode will reject until this succeeds
            }
        }
        registering = task
        let id = await task.value
        registering = nil
        keyId = id
        return id
    }

    private func fetchChallenge() async throws -> String {
        struct R: Decodable { let challenge: String }
        let (data, _) = try await URLSession.shared.data(from: baseURL.appendingPathComponent("v1/attest/challenge"))
        return try JSONDecoder().decode(R.self, from: data).challenge
    }

    private func register(keyId: String, attestation: String, challenge: String) async throws {
        var req = URLRequest(url: baseURL.appendingPathComponent("v1/attest/register"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: ["key_id": keyId, "attestation": attestation, "challenge": challenge])
        let (_, resp) = try await URLSession.shared.data(for: req)
        guard (resp as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.userAuthenticationRequired) }
    }
}
