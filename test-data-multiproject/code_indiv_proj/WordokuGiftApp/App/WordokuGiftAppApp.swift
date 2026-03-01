import SwiftUI

@main
struct WordokuGiftAppApp: App {
    var body: some Scene {
        WindowGroup {
            MainMenuView()
                .tint(WordokuTheme.accentBlue)
        }
    }
}
