#!/usr/bin/env bash
# Build the Eva Android APK.
#
# Requires the Android SDK at ~/Android/Sdk and JDK 17 (brew openjdk@17), both
# already wired into Flutter via `flutter config --android-sdk / --jdk-dir`.
# Output: build/app/outputs/flutter-apk/app-release.apk (debug-signed release,
# fine for sideloading to your own device).
set -euo pipefail
FLUTTER_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # flutter/
export PATH="$HOME/flutter/bin:$PATH"
export JAVA_HOME="$(brew --prefix openjdk@17)"

cd "$FLUTTER_DIR"
flutter build apk
APK="$FLUTTER_DIR/build/app/outputs/flutter-apk/app-release.apk"
echo "APK: $APK"
echo "Install to a connected phone (USB debugging on):"
echo "  ~/Android/Sdk/platform-tools/adb install -r '$APK'"
