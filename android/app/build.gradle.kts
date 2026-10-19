import java.security.MessageDigest
import java.util.zip.ZipFile
import groovy.json.JsonSlurper

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val applicationVersionName = "0.2.0"
val naFlexAar = layout.projectDirectory.file("libs/naflex-0.2.0.aar")
val verifyNaFlexLibrary by tasks.registering {
    inputs.file(naFlexAar)
    val libraryFile = naFlexAar.asFile
    doLast {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(libraryFile.readBytes()).joinToString("") { "%02x".format(it) }
        check(digest == "323f9392dfe32879951be58c3ae6e9b903d6e00f2a550104f201a198fcc7d6a4") {
            "The NaFlex library does not match the verified v0.2.0 release."
        }
    }
}
tasks.matching { it.name == "preBuild" }.configureEach { dependsOn(verifyNaFlexLibrary) }

val verifyBuiltInModelPack by tasks.registering {
    val packFile = layout.projectDirectory.file("src/main/assets/default_model_pack.zip").asFile
    inputs.file(packFile)
    doLast {
        ZipFile(packFile).use { archive ->
            val manifest = archive.getInputStream(archive.getEntry("manifest.json")).reader().use {
                JsonSlurper().parse(it) as Map<*, *>
            }
            check(manifest["format_version"] == 6 &&
                manifest["siglip2_runtime"] == "naflex-complete" &&
                manifest["pipeline"] == "raw-native-naflex-base-p512-v1" &&
                manifest["vector_dim"] == 768 && manifest["max_num_patches"] == 512 &&
                manifest["profile_sha256"] ==
                "1ac1a7a3a88074c04fc1559c9d0ae350820a8f681bc84f6176ef2aaed786683c") {
                "Build the verified format 6 Base NaFlex p512 pack before APK assembly."
            }
        }
    }
}
tasks.matching { it.name == "preBuild" }.configureEach { dependsOn(verifyBuiltInModelPack) }

android {
    namespace = "com.alolalab.chtozavino"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.alolalab.chtozavino"
        minSdk = 28
        targetSdk = 36
        versionCode = 6
        versionName = applicationVersionName

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

val copyFriendlyDebugApk by tasks.registering(Sync::class) {
    dependsOn("packageDebug")
    from(generatedDebugApk)
    into(layout.buildDirectory.dir("outputs/apk/friendly"))
    rename("app-debug.apk", "chtozavino-$applicationVersionName-debug.apk")
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
    implementation(files("libs/naflex-0.2.0.aar"))
    implementation("androidx.exifinterface:exifinterface:1.4.2")
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
    debugImplementation("org.nanohttpd:nanohttpd:2.3.1")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20260814")
}
