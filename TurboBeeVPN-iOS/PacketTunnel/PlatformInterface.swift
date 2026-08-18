import Foundation
import Libbox
import Network
import NetworkExtension
import os

/// Минимальная реализация `LibboxPlatformInterfaceProtocol` и
/// `LibboxCommandServerHandlerProtocol`. Ключевой метод — `openTun`:
/// он настраивает `NEPacketTunnelNetworkSettings` и возвращает sing-box
/// file descriptor туннеля (аналог `ExtensionPlatformInterface.swift`
/// из sing-box-for-apple, урезанный до iOS без App Group).
final class PlatformInterface: NSObject {
    private static let logger = Logger(subsystem: "com.turbobee.vpn.ios.packettunnel", category: "PlatformInterface")

    private weak var provider: NEPacketTunnelProvider?
    private var nwMonitor: NWPathMonitor?

    init(provider: NEPacketTunnelProvider) {
        self.provider = provider
    }
}

// MARK: - LibboxPlatformInterfaceProtocol

extension PlatformInterface: LibboxPlatformInterfaceProtocol {
    func openTun(_ options: LibboxTunOptionsProtocol?, ret0_: UnsafeMutablePointer<Int32>?) throws {
        guard let provider else {
            throw NSError(domain: "PlatformInterface", code: -1, userInfo: [NSLocalizedDescriptionKey: "Нет tunnel provider"])
        }

        let settings = NEPacketTunnelNetworkSettings(tunnelRemoteAddress: "127.0.0.1")
        settings.mtu = NSNumber(value: options?.getMTU() ?? 1500)

        // IPv4: адреса из конфига (10.10.0.1/30), полный туннель через default route.
        var v4Addresses: [String] = []
        var v4Masks: [String] = []
        if let iterator = options?.getInet4Address() {
            while iterator.hasNext() {
                if let prefix = iterator.next() {
                    v4Addresses.append(prefix.address())
                    v4Masks.append(prefix.mask())
                }
            }
        }
        if v4Addresses.isEmpty {
            v4Addresses = ["10.10.0.1"]
            v4Masks = ["255.255.255.252"]
        }
        let ipv4Settings = NEIPv4Settings(addresses: v4Addresses, subnetMasks: v4Masks)
        ipv4Settings.includedRoutes = [NEIPv4Route.default()]
        settings.ipv4Settings = ipv4Settings

        // IPv6: забираем в туннель, иначе трафик по IPv6 обходит VPN и на
        // провайдерах с «битым» IPv6 RU-сайты не открываются.
        var v6Addresses: [String] = []
        var v6Prefixes: [NSNumber] = []
        if let iterator = options?.getInet6Address() {
            while iterator.hasNext() {
                if let prefix = iterator.next() {
                    v6Addresses.append(prefix.address())
                    v6Prefixes.append(NSNumber(value: prefix.prefix()))
                }
            }
        }
        if v6Addresses.isEmpty {
            v6Addresses = ["fd00::1"]
            v6Prefixes = [64]
        }
        let ipv6Settings = NEIPv6Settings(addresses: v6Addresses, networkPrefixLengths: v6Prefixes)
        ipv6Settings.includedRoutes = [NEIPv6Route.default()]
        settings.ipv6Settings = ipv6Settings

        // DNS: принудительно в туннель, чтобы правило hijack-dns ловило запросы.
        // Первым Яндекс-DNS (77.88.8.8): 8.8.8.8/1.1.1.1 отравляются RKN в РФ.
        let dnsSettings = NEDNSSettings(servers: ["77.88.8.8", "1.1.1.1", "8.8.8.8"])
        dnsSettings.matchDomains = [""]
        dnsSettings.matchDomainsNoSearch = true
        settings.dnsSettings = dnsSettings

        // setTunnelNetworkSettings обязан выполняться на main-потоке.
        let semaphore = DispatchSemaphore(value: 0)
        DispatchQueue.main.async { [provider] in
            provider.setTunnelNetworkSettings(settings) { _ in
                semaphore.signal()
            }
        }
        semaphore.wait()

        if let fd = provider.packetFlow.value(forKeyPath: "socket.fileDescriptor") as? Int32 {
            ret0_?.pointee = fd
            return
        }
        throw NSError(domain: "PlatformInterface", code: -2, userInfo: [NSLocalizedDescriptionKey: "Missing tun file descriptor"])
    }

    func usePlatformAutoDetectControl() -> Bool {
        false
    }

    func autoDetectControl(_: Int32) throws {}

    func findConnectionOwner(_: Int32, sourceAddress _: String?, sourcePort _: Int32, destinationAddress _: String?, destinationPort _: Int32) throws -> LibboxConnectionOwner {
        throw NSError(domain: "PlatformInterface", code: -3, userInfo: [NSLocalizedDescriptionKey: "findConnectionOwner not supported"])
    }

    func useProcFS() -> Bool {
        false
    }

    func writeLog(_ message: String?) {
        guard let message else { return }
        Self.logger.info("\(message, privacy: .public)")
    }

    func startDefaultInterfaceMonitor(_ listener: LibboxInterfaceUpdateListenerProtocol?) throws {
        guard let listener else { return }
        let monitor = NWPathMonitor()
        nwMonitor = monitor
        let semaphore = DispatchSemaphore(value: 0)
        monitor.pathUpdateHandler = { path in
            self.updateInterface(listener, path)
            semaphore.signal()
            monitor.pathUpdateHandler = { path in
                self.updateInterface(listener, path)
            }
        }
        monitor.start(queue: DispatchQueue.global())
        semaphore.wait()
    }

    private func updateInterface(_ listener: LibboxInterfaceUpdateListenerProtocol, _ path: Network.NWPath) {
        guard path.status != .unsatisfied,
              let defaultInterface = path.availableInterfaces.first
        else {
            listener.updateDefaultInterface("", interfaceIndex: -1, isExpensive: false, isConstrained: false)
            return
        }
        listener.updateDefaultInterface(
            defaultInterface.name,
            interfaceIndex: Int32(defaultInterface.index),
            isExpensive: path.isExpensive,
            isConstrained: path.isConstrained
        )
    }

    func closeDefaultInterfaceMonitor(_: LibboxInterfaceUpdateListenerProtocol?) throws {
        nwMonitor?.cancel()
        nwMonitor = nil
    }

    func getInterfaces() throws -> LibboxNetworkInterfaceIteratorProtocol {
        guard let nwMonitor else {
            return NetworkInterfaceArray([])
        }
        let path = nwMonitor.currentPath
        if path.status == .unsatisfied {
            return NetworkInterfaceArray([])
        }
        var interfaces: [LibboxNetworkInterface] = []
        for interface in path.availableInterfaces {
            let item = LibboxNetworkInterface()
            item.name = interface.name
            item.index = Int32(interface.index)
            switch interface.type {
            case .wifi:
                item.type = LibboxInterfaceTypeWIFI
            case .cellular:
                item.type = LibboxInterfaceTypeCellular
            case .wiredEthernet:
                item.type = LibboxInterfaceTypeEthernet
            default:
                item.type = LibboxInterfaceTypeOther
            }
            interfaces.append(item)
        }
        return NetworkInterfaceArray(interfaces)
    }

    func underNetworkExtension() -> Bool {
        true
    }

    func includeAllNetworks() -> Bool {
        false
    }

    func clearDNSCache() {}

    func readWIFIState() -> LibboxWIFIState? {
        nil
    }

    func readWIFISSID() -> String? {
        nil
    }

    func connectSSHAgent(_ ret0_: UnsafeMutablePointer<Int32>?) throws {
        ret0_?.pointee = -1
        throw NSError(domain: "PlatformInterface", code: -4, userInfo: [NSLocalizedDescriptionKey: "SSH agent is not supported"])
    }

    func serviceStop() throws {}

    func serviceReload() throws {}

    func getSystemProxyStatus() throws -> LibboxSystemProxyStatus {
        LibboxSystemProxyStatus()
    }

    func setSystemProxyEnabled(_: Bool) throws {}

    func triggerNativeCrash() throws {}

    func writeDebugMessage(_ message: String?) {
        writeLog(message)
    }

    func send(_: LibboxNotification?) throws {}

    func cancelNotification(_: String?, typeID _: Int32) throws {}

    func startNeighborMonitor(_: LibboxNeighborUpdateListenerProtocol?) throws {}

    func registerMyInterface(_: String?) {}

    func closeNeighborMonitor(_: LibboxNeighborUpdateListenerProtocol?) throws {}

    func localDNSTransport() -> (any LibboxLocalDNSTransportProtocol)? {
        nil
    }

    func systemCertificates() -> (any LibboxStringIteratorProtocol)? {
        nil
    }

    func usePlatformShell() -> Bool {
        false
    }

    func checkPlatformShell() throws {
        throw NSError(domain: "PlatformInterface", code: -5, userInfo: [NSLocalizedDescriptionKey: "Shell is not supported"])
    }

    func openShellSession(_: LibboxPlatformUser?, command _: String?, environ _: (any LibboxStringIteratorProtocol)?, term _: String?, rows _: Int32, cols _: Int32) throws -> any LibboxShellSessionProtocol {
        throw NSError(domain: "PlatformInterface", code: -6, userInfo: [NSLocalizedDescriptionKey: "Shell is not supported"])
    }

    func readSystemSSHHostKey(_ error: NSErrorPointer) -> String {
        error?.pointee = NSError(domain: "PlatformInterface", code: -7, userInfo: [NSLocalizedDescriptionKey: "not supported"])
        return ""
    }

    func lookupSFTPServer(_ error: NSErrorPointer) -> String {
        error?.pointee = NSError(domain: "PlatformInterface", code: -8, userInfo: [NSLocalizedDescriptionKey: "not supported"])
        return ""
    }

    func tailscaleHostname() -> String {
        ""
    }

    func usePlatformBridge() -> Bool {
        false
    }

    func createBridge(_: LibboxBridgeOptions?) throws -> any LibboxBridgeSessionProtocol {
        throw NSError(domain: "PlatformInterface", code: -9, userInfo: [NSLocalizedDescriptionKey: "Bridge is not supported"])
    }

    func lookupUser(_: String?) throws -> LibboxPlatformUser {
        throw NSError(domain: "PlatformInterface", code: -10, userInfo: [NSLocalizedDescriptionKey: "not supported"])
    }

    private final class NetworkInterfaceArray: NSObject, LibboxNetworkInterfaceIteratorProtocol {
        private var iterator: IndexingIterator<[LibboxNetworkInterface]>
        private var nextValue: LibboxNetworkInterface?

        init(_ array: [LibboxNetworkInterface]) {
            iterator = array.makeIterator()
        }

        func hasNext() -> Bool {
            nextValue = iterator.next()
            return nextValue != nil
        }

        func next() -> LibboxNetworkInterface? {
            nextValue
        }
    }
}

// MARK: - LibboxCommandServerHandlerProtocol

extension PlatformInterface: LibboxCommandServerHandlerProtocol {}