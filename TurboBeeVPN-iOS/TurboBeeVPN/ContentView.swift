import SwiftUI

struct ContentView: View {
    @EnvironmentObject var vpn: VPNManager
    @State private var linkText: String = ""
    @State private var bypassRu: Bool = true
    @State private var showError = false
    @State private var errorText = ""
    @State private var busy = false

    private let defaultLink = "vless://728d5344-1b29-4222-b281-d7f054542b86@185.133.173.72:8443?encryption=none&host=&path=%2Fws&security=none&type=ws#Server-ALINA"

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Сервер")) {
                    TextEditor(text: $linkText)
                        .frame(minHeight: 120)
                        .font(.system(.footnote, design: .monospaced))
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                    Button("Вставить ключ по умолчанию") {
                        linkText = defaultLink
                    }
                }

                Section(header: Text("Обход российских сайтов")) {
                    Toggle("RU-сайты напрямую", isOn: $bypassRu)
                        .disabled(vpn.isConnecting)
                }

                Section {
                    Button {
                        action()
                    } label: {
                        HStack {
                            Spacer()
                            if busy {
                                ProgressView()
                            } else {
                                Text(vpn.isConnected ? "Отключить" : "Подключить")
                                    .fontWeight(.semibold)
                                    .foregroundColor(.white)
                            }
                            Spacer()
                        }
                    }
                    .disabled(busy || vpn.isConnecting)
                }

                Section(header: Text("Статус")) {
                    Label(vpn.statusText, systemImage: statusIcon())
                        .foregroundColor(statusColor())
                    if let err = vpn.lastError {
                        Text(err)
                            .font(.footnote)
                            .foregroundColor(.red)
                    }
                }
            }
            .navigationTitle("TurboBee VPN")
            .onAppear {
                if linkText.isEmpty {
                    if let saved = ProfileStore.shared.profile {
                        linkText = savedLink(for: saved)
                        bypassRu = saved.bypassRu
                    } else {
                        linkText = defaultLink
                    }
                }
                vpn.load()
            }
            .alert(isPresented: $showError) {
                Alert(title: Text("Ошибка"), message: Text(errorText), dismissButton: .default(Text("OK")))
            }
        }
    }

    private func action() {
        if vpn.isConnected {
            vpn.disconnect()
            return
        }
        guard !linkText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            showError("Вставьте ссылку vless://")
            return
        }
        do {
            var profile = try VlessLinkParser.parse(linkText)
            profile.bypassRu = bypassRu
            busy = true
            vpn.saveProfile(profile) { error in
                if let error {
                    busy = false
                    showError(error.localizedDescription)
                    return
                }
                vpn.connect { error in
                    busy = false
                    if let error {
                        showError(error.localizedDescription)
                    }
                }
            }
        } catch {
            showError(error.localizedDescription)
        }
    }

    private func showError(_ message: String) {
        errorText = message
        showError = true
    }

    private func statusIcon() -> String {
        switch vpn.status {
        case .connected: return "checkmark.shield.fill"
        case .connecting, .reasserting, .disconnecting: return "hourglass"
        default: return "shield.slash"
        }
    }

    private func statusColor() -> Color {
        switch vpn.status {
        case .connected: return .green
        case .connecting, .reasserting: return .orange
        default: return .secondary
        }
    }

    private func savedLink(for profile: Profile) -> String {
        var query: [String] = []
        query.append("type=\(profile.transport)")
        query.append("security=\(profile.security)")
        if !profile.sni.isEmpty { query.append("sni=\(profile.sni)") }
        if !profile.wsPath.isEmpty { query.append("path=\(profile.wsPath)") }
        if !profile.wsHost.isEmpty { query.append("host=\(profile.wsHost)") }
        var link = "vless://\(profile.uuid)@\(profile.host):\(profile.port)"
        if !query.isEmpty { link += "?" + query.joined(separator: "&") }
        if !profile.name.isEmpty { link += "#" + profile.name }
        return link
    }
}