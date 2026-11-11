import Foundation
import LangCoachKit
import Security

/// Session tokens in the Keychain, readable after first unlock, never synced or restored to another device.
final class KeychainStore: TokenStore, @unchecked Sendable {
    private let service: String
    private let account: String

    init(service: String = "com.example.langcoach.session", account: String = "session") {
        self.service = service; self.account = account
    }

    private var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: account]
    }

    func load() -> StoredSession? {
        var q = query
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let data = out as? Data else { return nil }
        return try? JSONDecoder().decode(StoredSession.self, from: data)
    }

    func save(_ session: StoredSession) {
        guard let data = try? JSONEncoder().encode(session) else { return }
        let attrs: [String: Any] = [kSecValueData as String: data,
                                    kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]
        if SecItemUpdate(query as CFDictionary, attrs as CFDictionary) == errSecItemNotFound {
            SecItemAdd(query.merging(attrs) { $1 } as CFDictionary, nil)
        }
    }

    func clear() { SecItemDelete(query as CFDictionary) }

    // Small helper for non-session secrets (e.g. the App Attest key id).
    static func string(_ key: String) -> String? {
        let store = KeychainStore(service: "com.example.langcoach.\(key)", account: key)
        var q = store.query
        q[kSecReturnData as String] = true
        var out: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let d = out as? Data else { return nil }
        return String(data: d, encoding: .utf8)
    }

    static func setString(_ value: String?, for key: String) {
        let store = KeychainStore(service: "com.example.langcoach.\(key)", account: key)
        SecItemDelete(store.query as CFDictionary)
        guard let value, let d = value.data(using: .utf8) else { return }
        SecItemAdd(store.query.merging([kSecValueData as String: d,
                                        kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]) { $1 } as CFDictionary, nil)
    }
}
