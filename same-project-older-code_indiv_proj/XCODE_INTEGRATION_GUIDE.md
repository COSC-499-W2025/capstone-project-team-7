# Integrating WordokuGiftApp into Xcode Project

## Current Situation
- ✅ New Xcode project created at: `wordsudoku/wordsudoku.xcodeproj`
- ✅ Existing game code in: `WordokuGiftApp/` directory
- ❌ Need to integrate existing code into the Xcode project

---

## Steps to Integrate (Do this in Xcode)

### 1. Clean Up Template Files
In Xcode, **delete** these template files (Move to Trash):
- `wordsudoku/ContentView.swift`
- `wordsudoku/Item.swift`

### 2. Add Existing Source Files
**In Xcode**, right-click on the `wordsudoku` folder in the project navigator:
1. Select **"Add Files to 'wordsudoku'..."**
2. Navigate to the parent directory and select these folders:
   - `WordokuGiftApp/App/`
   - `WordokuGiftApp/Data/`
   - `WordokuGiftApp/Engine/`
   - `WordokuGiftApp/UI/`
   - `WordokuGiftApp/ViewModels/`
3. **Important**: Check **"Create groups"** (not "Create folder references")
4. **Important**: Check **"Copy items if needed"**
5. Click **Add**

### 3. Add Data File (wordlist.txt)
1. In Xcode, right-click on `wordsudoku` folder
2. Select **"Add Files to 'wordsudoku'..."**
3. Navigate to and select `wordlist.txt` from the parent directory
4. Check **"Copy items if needed"**
5. Click **Add**

### 4. Add Test Files
**In Xcode**, right-click on the `wordsudokuTests` folder:
1. Select **"Add Files to 'wordsudoku'..."**
2. Navigate to `WordokuGiftAppTests/`
3. Select all test folders:
   - `EngineTests/`
   - `ViewModelTests/`
   - `DataTests/`
4. Check **"Create groups"**
5. Check **"Copy items if needed"**
6. Make sure **Target Membership** is set to `wordsudokuTests` (not the main app)
7. Click **Add**

### 5. Add Privacy Manifest
1. In Xcode, right-click on `wordsudoku` folder
2. Select **"Add Files to 'wordsudoku'..."**
3. Navigate to and select `WordokuGiftApp/PrivacyInfo.xcprivacy`
4. Check **"Copy items if needed"**
5. Click **Add**

### 6. Update App Entry Point
Replace the content of `wordsudoku/wordsudokuApp.swift` with:

```swift
import SwiftUI

@main
struct WordokuApp: App {
    var body: some Scene {
        WindowGroup {
            LevelSelectView()
        }
    }
}
```

**Note**: Remove all SwiftData imports and references since your app uses UserDefaults.

### 7. Configure Project Settings

In Xcode, select the project in the navigator, then:

#### General Tab
- **Display Name**: Wordoku (or "Word Sudoku")
- **Bundle Identifier**: `com.yourname.wordoku` (change "yourname" to your actual name/company)
- **Version**: 1.0.0
- **Build**: 1
- **Deployment Target**: iOS 16.0 (minimum)
- **Supported Destinations**: iPhone, iPad
- **Orientation**: Portrait, Landscape

#### Signing & Capabilities
- Select your **Team** (Apple Developer account)
- Ensure **Automatically manage signing** is checked

#### Build Settings
- Search for "Swift Language Version"
  - Set to **Swift 5** (should be default)

### 8. Add App Icon (Later)
You'll need to design app icons and add them to:
- `wordsudoku/Assets.xcassets/AppIcon.appiconset/`

### 9. Test Build
1. Select a simulator (e.g., iPhone 15)
2. Press **⌘R** to build and run
3. Fix any compilation errors that appear

---

## Alternative: Use Command Line

If you prefer, you can copy files via terminal first, then let Xcode detect them:

```bash
# Navigate to project directory
cd /Users/joaquinalmora/Desktop/word-sudoku/wordsudoku/wordsudoku

# Copy source directories (preserving structure)
cp -r ../../WordokuGiftApp/App ./
cp -r ../../WordokuGiftApp/Data ./
cp -r ../../WordokuGiftApp/Engine ./
cp -r ../../WordokuGiftApp/UI ./
cp -r ../../WordokuGiftApp/ViewModels ./

# Copy data file
cp ../../wordlist.txt ./

# Copy privacy manifest
cp ../../WordokuGiftApp/PrivacyInfo.xcprivacy ./

# Copy tests
cd ../wordsudokuTests
cp -r ../../WordokuGiftAppTests/EngineTests ./
cp -r ../../WordokuGiftAppTests/ViewModelTests ./
cp -r ../../WordokuGiftAppTests/DataTests ./
```

Then in Xcode:
1. Right-click on the `wordsudoku` folder
2. Select **"Add Files to 'wordsudoku'..."**
3. Select all the copied folders
4. Check **"Create groups"**
5. Make sure **Target Membership** is correct
6. Click **Add**

---

## Expected Errors After Integration

You may see these errors initially:
1. **"Cannot find type 'LevelSelectView' in scope"** - This will resolve once all files are added
2. Missing `@testable import WordokuGiftApp` - Change to `@testable import wordsudoku` in test files

---

## After Integration Checklist

- [ ] Project builds without errors (⌘B)
- [ ] Tests run successfully (⌘U)
- [ ] App launches and shows level select screen
- [ ] Can play a level
- [ ] SwiftLint runs (if installed): `swiftlint` in terminal

---

## Next Steps After Integration

1. Update test imports from `@testable import WordokuGiftApp` to `@testable import wordsudoku`
2. Test the app thoroughly on simulator
3. Test on physical device
4. Create App Icon assets
5. Add Launch Screen
6. Configure for App Store submission

---

**Questions?** Let me know if you hit any issues during the integration!
