import Foundation

/// Парсер ссылок `vless://` — порт `VlessLinkParser.java` из Android-версии.
enum VlessLinkParser {

    struct ParseError: LocalizedError {
        let message: String
        var errorDescription: String? { message }
    }

    static func parse(_ raw: String) throws -> Profile {
        let link = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard link.hasPrefix("vless://") else {
            throw ParseError(message: "Поддерживаются только ссылки vless://")
        }
        return try parseVless(link)
    }

    private static func parseVless(_ link: String) throws -> Profile {
        var body = String(link.dropFirst("vless://".count))

        var name = ""
        if let hash = body.firstIndex(of: "#") {
            name = urlDecode(String(body[body.index(after: hash)...]))
            body = String(body[..<hash])
        }

        var params = ""
        if let q = body.firstIndex(of: "?") {
            params = String(body[body.index(after: q)...])
            body = String(body[..<q])
        }

        guard let at = body.firstIndex(of: "@") else {
            throw ParseError(message: "Некорректная ссылка vless (нет @)")
        }
        let uuid = String(body[..<at])
        var addr = String(body[body.index(after: at)...])

        var port = 443
        var host: String
        if let colon = addr.lastIndex(of: ":") {
            host = String(addr[..<colon])
            if let p = Int(addr[addr.index(after: colon)...]) {
                port = p
            }
        } else {
            host = addr
        }

        guard isValidUUID(uuid) else {
            throw ParseError(message: "Некорректный UUID")
        }
        guard !host.isEmpty else {
            throw ParseError(message: "Пустой адрес сервера")
        }

        var profile = Profile()
        profile.uuid = uuid
        profile.host = host
        profile.port = port
        profile.name = name
        profile.transport = "tcp"
        profile.security = "none"
        profile.fingerprint = ""

        for pair in params.split(separator: "&") where !pair.isEmpty {
            guard let eq = pair.firstIndex(of: "=") else { continue }
            let key = urlDecode(String(pair[..<eq])).lowercased()
            let value = urlDecode(String(pair[pair.index(after: eq)...]))
            applyParam(key, value, to: &profile)
        }

        if profile.transport == "ws" && profile.wsHost.isEmpty {
            profile.wsHost = profile.sni.isEmpty ? host : profile.sni
        }

        return profile
    }

    private static func applyParam(_ key: String, _ value: String, to profile: inout Profile) {
        switch key {
        case "type":
            profile.transport = value.isEmpty ? "tcp" : value
        case "security":
            profile.security = value.isEmpty ? "none" : value
        case "sni":
            profile.sni = value
        case "fp":
            profile.fingerprint = value
        case "flow":
            profile.flow = value
        case "host":
            profile.wsHost = value
        case "path":
            profile.wsPath = value
        case "servicename":
            profile.grpcServiceName = value
        case "pbk":
            profile.publicKey = value
        case "sid":
            profile.shortId = value
        case "sname":
            profile.serverName = value
        default:
            break
        }
    }

    private static func isValidUUID(_ s: String) -> Bool {
        UUID(uuidString: s) != nil
    }

    private static func urlDecode(_ s: String) -> String {
        guard let decoded = s.removingPercentEncoding else { return s }
        return decoded
    }
}