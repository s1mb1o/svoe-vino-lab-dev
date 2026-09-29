plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.alolalab.chtozavino"
    compileSdk = 36

    defaultConfig {
        applicationId = "chtozavino.alolalab.com"
        minSdk = 28
        targetSdk = 36
        versionCode = 5
        versionName = "0.1.4"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables.useSupportLibrary = true

        ndk {
            abiFilters += setOf("arm64-v8a")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    packaging {
        jniLibs.pickFirsts += setOf(
            "**/libc++_shared.so",
            "**/libtensorflowlite_jni.so",
            "**/libtensorflowlite_gpu_jni.so",
        )
        resources.excludes += setOf("/META-INF/{AL2.0,LGPL2.1}")
    }

    androidResources {
        noCompress += "zip"
    }

    testOptions {
        unitTests.isIncludeAndroidResources = true
    }
}

val generatedDebugApk = layout.buildDirectory.file("outputs/apk/debug/app-debug.apk")

val copyFriendlyDebugApk by tasks.registering(Copy::class) {
    dependsOn("packageDebug")
    from(generatedDebugApk)
    into(layout.buildDirectory.dir("outputs/apk/friendly"))
    rename { "chtozavino_debug.apk" }
}

tasks.matching { it.name == "assembleDebug" }.configureEach {
    finalizedBy(copyFriendlyDebugApk)
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

dependencies {
    implementation("androidx.activity:activity-compose:1.12.4")
    implementation("androidx.core:core-ktx:1.17.0")
    // Google Play services still requests Fragment 1.1.0 transitively. Activity Result
    // APIs require Fragment 1.3.0 or later even though this Compose app has no fragments.
    implementation("androidx.fragment:fragment:1.8.9")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.10.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.10.0")

    implementation("androidx.compose.ui:ui:1.10.5")
    implementation("androidx.compose.ui:ui-tooling-preview:1.10.5")
    implementation("androidx.compose.foundation:foundation:1.10.5")
    implementation("androidx.compose.material3:material3:1.3.2")
    debugImplementation("androidx.compose.ui:ui-tooling:1.10.5")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
    implementation("com.google.android.gms:play-services-code-scanner:16.1.0")
    implementation("com.google.ai.edge.litert:litert:2.2.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20260814")
}
