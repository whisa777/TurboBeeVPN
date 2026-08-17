import Foundation
import NetworkExtension

/// Управление VPN через `NETunnelProviderManager`.
/// Расширение получает профиль через `providerConfiguration` (прокидывается
/// системой в `startTunnel(options:)`), поэтому App Group не нужна.
final class VPNManager: ObservableObject {

    static let shared = VPNManager()

    private let tunnelBundleId = "com.turbobee.vpn.ios.PacketTunnel"

    @Published private(set) var status: NEVPNStatus = .invalid
    @Published private(set) var lastError: String?

    private var manager: NETunnelProviderManager?
    private var statusObserver: NSObjectProtocol?

    private init() {
        observeStatus()
        refreshStatus()
    }

    deinit {
        if let statusObserver {
            NotificationCenter.default.removeObserver(statusObserver)
        }
    }

    var isConnected: Bool {
        status == .connected
    }

    var isConnecting: Bool {
        status == .connecting || status == .reasserting
    }

    var statusText: String {
        switch status {
        case .invalid: return "Не настроено"
        case .disconnected: return "Отключено"
        case .connecting: return "Подключение…"
        case .connected: return "Подключено"
        case .reasserting: return "Переподключение…"
        case .disconnecting: return "Отключение…"
        @unknown default: return "Неизвестно"
        }
    }

    /// Загрузка сохранённого VPN-конфига (создаётся при первом подключении).
    func load(completion: ((Error?) -> Void)? = nil) {
        NETunnelProviderManager.loadAllFromPreferences { managers, error in
            if let error {
                self.lastError = error.localizedDescription
                completion?(error)
                return
            }
            // Важно: на устройстве могут быть VPN-конфиги ДРУГИХ приложений
            // (например, собственный VPN SideStore, который ставит приложения).
            // Берём ТОЛЬКО свой конфиг по bundle id расширения, иначе
            // saveToPreferences() по чужому конфигу вернёт "permission denied".
            self.manager = managers?.first(where: { manager in
                (manager.protocolConfiguration as? NETunnelProviderProtocol)?
                    .providerBundleIdentifier == self.tunnelBundleId
            })
            if self.manager == nil {
                let m = NETunnelProviderManager()
                let p = NETunnelProviderProtocol()
                p.providerBundleIdentifier = self.tunnelBundleId
                p.serverAddress = ""
                m.protocolConfiguration = p
                self.manager = m
            }
            self.refreshStatus()
            completion?(nil)
        }
    }

    /// Сохранение профиля и настройка VPN-конфига.
    func saveProfile(_ profile: Profile, completion: ((Error?) -> Void)? = nil) {
        ProfileStore.shared.profile = profile
        load { [weak self] error in
            guard let self, error == nil else {
                completion?(error ?? NSError(domain: "VPNManager", code: -1))
                return
            }
            guard let m = self.manager,
                  let p = m.protocolConfiguration as? NETunnelProviderProtocol
            else {
                completion?(NSError(domain: "VPNManager", code: -2, userInfo: [NSLocalizedDescriptionKey: "Нет VPN-конфигурации"]))
                return
            }
            p.serverAddress = profile.host.isEmpty ? "turbobee" : profile.host
            p.providerConfiguration = profile.providerConfiguration()
            m.protocolConfiguration = p
            m.isEnabled = true
            m.saveToPreferences { error in
                if let error {
                    self.lastError = error.localizedDescription
                }
                completion?(error)
            }
        }
    }

    /// Запуск туннеля.
    func connect(completion: ((Error?) -> Void)? = nil) {
        guard let manager else {
            lastError = "Сначала сохраните профиль"
            completion?(NSError(domain: "VPNManager", code: -3))
            return
        }
        do {
            try manager.connection.startVPNTunnel(options: [:])
            completion?(nil)
        } catch {
            lastError = error.localizedDescription
            completion?(error)
        }
    }

    func disconnect() {
        manager?.connection.stopVPNTunnel()
    }

    private func observeStatus() {
        statusObserver = NotificationCenter.default.addObserver(
            forName: .NEVPNStatusDidChange,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.refreshStatus()
        }
    }

    private func refreshStatus() {
        if let connection = manager?.connection {
            status = connection.status
        } else {
            status = .invalid
        }
    }
}