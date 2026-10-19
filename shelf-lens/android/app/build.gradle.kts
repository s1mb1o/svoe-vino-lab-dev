import java.util.Properties

plugins {
    id("com.android.application")
}

val local = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

android {
    namespace = "ru.svoevino.shelfreid"
    compileSdk = 36
    ndkVersion = "28.2.13676358"

    defaultConfig {
        applicationId = "ru.svoevino.shelfreid"
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"
        ndk { abiFilters += "arm64-v8a" }
        externalNativeBuild {
            cmake {
                arguments += listOf(
                    "-DANDROID_STL=c++_shared",
                    "-DOpenCV_DIR=${local.getProperty("opencv.dir")}",
                    "-DEIGEN3_INCLUDE_DIR=${local.getProperty("eigen.dir")}",
                    "-DJSON_INCLUDE_DIR=${local.getProperty("json.dir")}",
                    "-DSHELFREID_TOOLS=OFF",
                    "-DORT_ANDROID_DIR=${local.getProperty("ort.dir")}",
                )
            }
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")   // a test build on our own phone
        }
    }
    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }
    packaging {
        jniLibs { pickFirsts += "**/libonnxruntime.so" }   // the Maven package and the linked copy are one version
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.22.0")   // the native library of the detector
    implementation("androidx.activity:activity:1.10.1")
    implementation("androidx.camera:camera-core:1.5.1")
    implementation("androidx.camera:camera-camera2:1.5.1")
    implementation("androidx.camera:camera-lifecycle:1.5.1")
    implementation("androidx.camera:camera-view:1.5.1")
}
