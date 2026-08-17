import Foundation

/// Формирует JSON-конфиг sing-box для iOS.
/// Логика маршрутизации — порт `XrayConfigBuilder.java` (Android):
///   1. sniff + hijack-dns
///   2. всегда-через-VPN (YouTube/WhatsApp/Meta/OpenAI)  -> proxy
///   3. белый список RU                                -> direct
///   4. (если включено) geosite-ru + geoip-ru          -> direct
///   final                                             -> proxy
enum ConfigBuilder {

    struct RoutingData: Codable {
        var alwaysProxy: [String]
        var ruWhitelist: [String]
    }

    static func build(profile: Profile) throws -> String {
        let routing = try loadRoutingData()

        var rules: [[String: Any]] = [
            ["action": "sniff"],
            ["protocol": "dns", "action": "hijack-dns"],
            ["action": "route", "domain": routing.alwaysProxy, "outbound": "proxy"],
            ["action": "route", "domain": routing.ruWhitelist, "outbound": "direct"],
        ]

        var ruleSet: [[String: Any]] = []
        if profile.bypassRu {
            rules.append([
                "action": "route",
                "rule_set": ["geoip-ru", "geosite-ru"],
                "outbound": "direct",
            ])
            ruleSet = [
                ["type": "local", "tag": "geoip-ru", "format": "binary", "path": srsPath("geoip-ru")],
                ["type": "local", "tag": "geosite-ru", "format": "binary", "path": srsPath("geosite-ru")],
            ]
        }

        let config: [String: Any] = [
            "log": ["level": "info", "timestamp": true],
            "dns": [
                "servers": [["type": "local", "tag": "dns-local"]],
                "final": "dns-local",
                "strategy": "ipv4_only",
            ],
            "inbounds": [
                [
                    "type": "tun",
                    "tag": "tun-in",
                    "address": ["10.10.0.1/30"],
                    "mtu": 1500,
                    "auto_redirect": false,
                    "stack": "gvisor",
                ],
            ],
            "outbounds": [
                vlessOutbound(profile),
                ["type": "direct", "tag": "direct"],
                ["type": "block", "tag": "block"],
            ],
            "route": [
                "auto_detect_interface": true,
                "final": "proxy",
                "rules": rules,
                "rule_set": ruleSet,
            ],
        ]

        let data = try JSONSerialization.data(withJSONObject: config, options: [.prettyPrinted, .sortedKeys])
        guard let json = String(data: data, encoding: .utf8) else {
            throw NSError(domain: "ConfigBuilder", code: -1, userInfo: [NSLocalizedDescriptionKey: "Не удалось сериализовать конфиг"])
        }
        return json
    }

    // MARK: - Outbounds

    private static func vlessOutbound(_ p: Profile) -> [String: Any] {
        var out: [String: Any] = [
            "type": "vless",
            "tag": "proxy",
            "server": p.host,
            "server_port": p.port,
            "uuid": p.uuid,
        ]
        if !p.flow.isEmpty {
            out["flow"] = p.flow
        }
        if p.security == "tls" {
            out["tls"] = [
                "enabled": true,
                "server_name": p.sni.isEmpty ? p.host : p.sni,
                "utls": [
                    "enabled": true,
                    "fingerprint": p.fingerprint.isEmpty ? "chrome" : p.fingerprint,
                ],
                "alpn": ["http/1.1"],
            ]
        }
        switch p.transport {
        case "ws":
            out["transport"] = [
                "type": "ws",
                "path": p.wsPath.isEmpty ? "/" : p.wsPath,
                "headers": ["Host": p.wsHost.isEmpty ? (p.sni.isEmpty ? p.host : p.sni) : p.wsHost],
            ]
        case "grpc":
            out["transport"] = ["type": "grpc", "service_name": p.grpcServiceName]
        default:
            break
        }
        return out
    }

    // MARK: - Ресурсы

    private static func loadRoutingData() throws -> RoutingData {
        guard let url = Bundle.main.url(forResource: "RoutingData", withExtension: "json") else {
            throw NSError(domain: "ConfigBuilder", code: -2, userInfo: [NSLocalizedDescriptionKey: "Нет RoutingData.json"])
        }
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(RoutingData.self, from: data)
    }

    private static func srsPath(_ name: String) -> String {
        Bundle.main.path(forResource: name, ofType: "srs") ?? name + ".srs"
    }
}