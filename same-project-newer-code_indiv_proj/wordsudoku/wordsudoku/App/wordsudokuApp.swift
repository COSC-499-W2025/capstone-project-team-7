import SwiftUI
@main
struct WordokuApp: App {
    var body: some Scene {
        WindowGroup {
            MainMenuView()
                .tint(WordokuTheme.accentBlue)
        }
    }
}
