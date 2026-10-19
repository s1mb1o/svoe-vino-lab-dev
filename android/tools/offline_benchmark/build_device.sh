#!/usr/bin/env bash
set -euo pipefail
benchmark_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${ANDROID_HOME:?Set ANDROID_HOME to the Android SDK.}"
: "${JAVA_HOME:?Set JAVA_HOME to JDK 17.}"
ndk_compiler="$ANDROID_HOME/ndk/27.0.12077973/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang++"
native_output="$benchmark_root/device/app/src/main/jniLibs/arm64-v8a"
mkdir -p "$native_output"
"$ndk_compiler" -O3 -shared -fPIC -std=c++17 -static-libstdc++ \
  -Wl,-z,max-page-size=16384 \
  "$benchmark_root/device/app/src/main/cpp/offline_dot.cpp" \
  -o "$native_output/liboffline_dot.so"
"$benchmark_root/../../gradlew" -p "$benchmark_root/device" --offline --no-daemon \
  testDebugUnitTest lintDebug assembleDebug
