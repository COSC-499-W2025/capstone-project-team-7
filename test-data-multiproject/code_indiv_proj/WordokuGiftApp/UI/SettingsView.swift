import SwiftUI

struct SettingsView: View {
    @AppStorage("settings.sound") private var soundEnabled = true
    @AppStorage("settings.haptics") private var hapticsEnabled = true
    @AppStorage("settings.showMistakes") private var showMistakes = true

    var body: some View {
        VStack(spacing: 0) {
            List {
                Section {
                    Toggle("Sound", isOn: $soundEnabled)
                    Toggle("Haptics", isOn: $hapticsEnabled)
                    Toggle("Show Mistakes", isOn: $showMistakes)
                } footer: {
                    Text("These preferences apply to all puzzles.")
                }
                .listRowBackground(WordokuTheme.cardBackground)
            }
            .listStyle(.insetGrouped)
            .scrollContentBackground(.hidden)
        }
        .background(WordokuPaperBackground())
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
        .tint(WordokuTheme.accentBlue)
    }
}

#Preview {
    NavigationStack {
        SettingsView()
    }
}
