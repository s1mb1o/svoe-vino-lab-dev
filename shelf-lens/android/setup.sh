#!/usr/bin/env bash
# The native dependencies of the Android app, fetched once into third_party/ (not in git),
# and android/local.properties written for them. After a clone:
#
#     android/setup.sh
#     cd android && ./gradlew assembleDebug
#
# The Android SDK comes from ANDROID_HOME (or ANDROID_SDK_ROOT, or the usual place of
# Android Studio); Gradle fetches the NDK and CMake the build names into it. The detector
# model is in git (app/src/main/assets); the recognition API's password is pushed to the
# phone apart (README).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TP="$ROOT/third_party"
OPENCV=5.0.0
ORT=1.22.0
EIGEN=5.0.1
JSON=3.12.0
mkdir -p "$TP"

fetch() {   # url file: once, a broken download is not kept
    if [ ! -s "$2" ]; then
        echo "fetching $1"
        curl -fL --retry 3 -o "$2.part" "$1"
        mv "$2.part" "$2"
    fi
}

if [ ! -d "$TP/opencv-android/OpenCV-android-sdk/sdk/native/jni" ]; then
    fetch "https://github.com/opencv/opencv/releases/download/$OPENCV/opencv-$OPENCV-android-sdk-16kb-page-fix.zip" "$TP/opencv-android.zip"
    rm -rf "$TP/opencv-android" && mkdir -p "$TP/opencv-android"
    unzip -q "$TP/opencv-android.zip" -d "$TP/opencv-android"
    rm "$TP/opencv-android.zip"
fi

if [ ! -f "$TP/ort-android/jni/arm64-v8a/libonnxruntime.so" ]; then
    fetch "https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-android/$ORT/onnxruntime-android-$ORT.aar" "$TP/ort-android.aar"
    rm -rf "$TP/ort-android" && mkdir -p "$TP/ort-android"
    unzip -q "$TP/ort-android.aar" -d "$TP/ort-android"
    rm "$TP/ort-android.aar"
fi

if [ ! -f "$TP/eigen/Eigen/Core" ]; then
    fetch "https://gitlab.com/libeigen/eigen/-/archive/$EIGEN/eigen-$EIGEN.tar.gz" "$TP/eigen.tar.gz"
    rm -rf "$TP/eigen" && mkdir -p "$TP/eigen"
    tar -xzf "$TP/eigen.tar.gz" -C "$TP/eigen" --strip-components=1
    rm "$TP/eigen.tar.gz"
fi

if [ ! -f "$TP/json/nlohmann/json.hpp" ]; then
    mkdir -p "$TP/json/nlohmann"
    fetch "https://github.com/nlohmann/json/releases/download/v$JSON/json.hpp" "$TP/json/nlohmann/json.hpp"
fi

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [ -z "$SDK" ]; then
    if [ -d "$HOME/Library/Android/sdk" ]; then SDK="$HOME/Library/Android/sdk"; else SDK="$HOME/Android/Sdk"; fi
fi
cat > "$ROOT/android/local.properties" <<PROPS
sdk.dir=$SDK
opencv.dir=$TP/opencv-android/OpenCV-android-sdk/sdk/native/jni
eigen.dir=$TP/eigen
json.dir=$TP/json
ort.dir=$TP/ort-android
PROPS
echo "android/local.properties written (Android SDK: $SDK)"
