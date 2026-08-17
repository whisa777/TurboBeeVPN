import Foundation
import Libbox
import NetworkExtension
import os

/// NEPacketTunnelProvider: получает профиль через `startTunnel(options:)`
/// (значения `providerConfiguration` из приложения), строит конфиг sing-box
/// и запускает ядро через `LibboxCommandServer`.
final class PacketTunnelProvider: NEPacketTunnelProvider {
    private let logger = Logger(subsystem: "com.turbobee.vpn.ios.packettunnel", category: "PacketTunnelProvider")

    private lazy var platformInterface = PlatformInterface(provider: self)
    private var commandServer: LibboxCommandServer?

    override func startTunnel(options: [String: NSObject]?) async throws {
        guard let profile = Profile(providerConfiguration: options) else {
            throw NSError(domain: "PacketTunnelProvider", code: -1, userInfo: [
                NSLocalizedDescriptionKey: "Отсутствует профиль в параметрах туннеля",
            ])
        }
        logger.info("startTunnel: \(profile.host, privacy: .public):\(profile.port)")

        let configContent = try ConfigBuilder.build(profile: profile)

        let basePath = NSSearchPathForDirectoriesInDomains(.documentDirectory, .userDomainMask, true).first ?? NSTemporaryDirectory()
        let workingPath = (basePath as NSString).appendingPathComponent("Working")
        let tempPath = NSTemporaryDirectory()

        let setup = LibboxSetupOptions()
        setup.basePath = basePath
        setup.workingPath = workingPath
        setup.tempPath = tempPath
        setup.logMaxLines = 3000
        setup.debug = false
        setup.oomKillerEnabled = true

        var setupError: NSError?
        LibboxSetup(setup, &setupError)
        if let setupError {
            throw setupError
        }

        var error: NSError?
        commandServer = LibboxNewCommandServer(platformInterface, platformInterface, &error)
        if let error {
            throw error
        }
        do {
            try commandServer!.start()
        } catch {
            throw error
        }
        do {
            try commandServer!.startOrReloadService(configContent, options: LibboxOverrideOptions())
        } catch {
            throw error
        }
        logger.info("sing-box service started")
    }

    override func stopTunnel(with reason: NEProviderStopReason) async {
        logger.info("stopTunnel, reason: \(reason.rawValue)")
        if let commandServer {
            try? commandServer.closeService()
            commandServer.close()
            self.commandServer = nil
        }
    }
}