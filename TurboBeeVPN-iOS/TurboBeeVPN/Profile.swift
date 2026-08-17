import Foundation

/// Профиль сервера — порт модели `Profile` из Android-версии.
struct Profile: Codable, Equatable {
    var uuid: String = ""
    var host: String = ""
    var port: Int = 443
    var name: String = ""
    var transport: String = "tcp"       // tcp | ws | grpc
    var security: String = "none"       // none | tls | reality
    var sni: String = ""
    var fingerprint: String = ""
    var flow: String = ""
    var wsPath: String = ""
    var wsHost: String = ""
    var grpcServiceName: String = ""
    var publicKey: String = ""
    var shortId: String = ""
    var serverName: String = ""
    var bypassRu: Bool = true
}

// MARK: - Конвертация в словарь для providerConfiguration

extension Profile {
    /// Значения, передаваемые в `NETunnelProviderProtocol.providerConfiguration`.
    /// Система прокидывает их в `startTunnel(options:)` расширения.
    func providerConfiguration() -> [String: NSObject] {
        var dict: [String: NSObject] = [:]
        dict["uuid"] = uuid as NSString
        dict["host"] = host as NSString
        dict["port"] = NSNumber(value: port)
        dict["name"] = name as NSString
        dict["transport"] = transport as NSString
        dict["security"] = security as NSString
        dict["sni"] = sni as NSString
        dict["fingerprint"] = fingerprint as NSString
        dict["flow"] = flow as NSString
        dict["wsPath"] = wsPath as NSString
        dict["wsHost"] = wsHost as NSString
        dict["grpcServiceName"] = grpcServiceName as NSString
        dict["publicKey"] = publicKey as NSString
        dict["shortId"] = shortId as NSString
        dict["serverName"] = serverName as NSString
        dict["bypassRu"] = NSNumber(value: bypassRu)
        return dict
    }

    init?(providerConfiguration options: [String: NSObject]?) {
        guard let options,
              let uuid = options["uuid"] as? String,
              let host = options["host"] as? String
        else {
            return nil
        }
        self.uuid = uuid
        self.host = host
        port = (options["port"] as? NSNumber)?.intValue ?? 443
        name = options["name"] as? String ?? ""
        transport = options["transport"] as? String ?? "tcp"
        security = options["security"] as? String ?? "none"
        sni = options["sni"] as? String ?? ""
        fingerprint = options["fingerprint"] as? String ?? ""
        flow = options["flow"] as? String ?? ""
        wsPath = options["wsPath"] as? String ?? ""
        wsHost = options["wsHost"] as? String ?? ""
        grpcServiceName = options["grpcServiceName"] as? String ?? ""
        publicKey = options["publicKey"] as? String ?? ""
        shortId = options["shortId"] as? String ?? ""
        serverName = options["serverName"] as? String ?? ""
        bypassRu = (options["bypassRu"] as? NSNumber)?.boolValue ?? true
    }
}