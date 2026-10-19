plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.alolalab.chtozavino.offlinebench"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.alolalab.chtozavino.offlinebench"
        minSdk = 28
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-offlinebench"
        ndk { abiFilters += "arm64-v8a" }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    packaging {
        jniLibs.pickFirsts += setOf("**/libc++_shared.so", "**/libtensorflowlite_jni.so", "**/libtensorflowlite_gpu_jni.so")
    }
}
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
dependencies {
    implementation(files("../../../../app/libs/naflex-0.2.0.aar"))
    implementation("com.google.ai.edge.litert:litert:2.2.0")
    implementation("org.nanohttpd:nanohttpd:2.3.1")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20260814")
}
