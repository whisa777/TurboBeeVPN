import Foundation

/// Хранение профиля в UserDefaults приложения.
final class ProfileStore {
    static let shared = ProfileStore()

    private let key = "saved_profile"
    private let defaults = UserDefaults.standard

    var profile: Profile? {
        get {
            guard let data = defaults.data(forKey: key) else { return nil }
            return try? JSONDecoder().decode(Profile.self, from: data)
        }
        set {
            if let newValue {
                if let data = try? JSONEncoder().encode(newValue) {
                    defaults.set(data, forKey: key)
                }
            } else {
                defaults.removeObject(forKey: key)
            }
        }
    }
}