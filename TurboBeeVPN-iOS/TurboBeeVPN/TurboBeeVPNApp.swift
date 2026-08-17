import SwiftUI

@main
struct TurboBeeVPNApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(VPNManager.shared)
        }
    }
}