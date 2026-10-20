import java.util.Properties

plugins {
    id("com.android.application")
}

val local = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

android {
    namespace = "com.alolalab.shelflens"
    compileSdk = 36
    ndkVersion = "28.2.13676358"

    defaultConfig {
        applicationId = "com.alolalab.shelflens"
        minSdk = 29
        targetSdk = 36
        versionCode = 2
        versionName = "1.0"
        // 64- and 32-bit ARM phones; a store build goes as an App Bundle, split by ABI there.
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a") }
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
            signingConfig = signingConfigs.getByName("debug")   // no release keystore: signed with the debug key
        }
    }
    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }
    androidResources {
        noCompress += listOf("onnx")   // the detector, copied out of the APK as it is
    }
    packaging {
        jniLibs { pickFirsts += "**/libonnxruntime.so" }   // the Maven package and the linked copy are one version
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

// The recognition API's password: the environment variable CHTOZAVINO_API_PASSWORD goes into
// the APK's assets; a build of the APK without it fails. The password is not an input of the
// task, so Gradle keeps no copy of it in its build history, and the task runs at every build.
abstract class PasswordAsset : DefaultTask() {
    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    init {
        outputs.upToDateWhen { false }
    }

    @TaskAction
    fun write() {
        val password = System.getenv("CHTOZAVINO_API_PASSWORD")?.trim()
        if (password.isNullOrEmpty())
            throw GradleException("CHTOZAVINO_API_PASSWORD is not set: the APK needs the password of the " +
                    "recognition API (shelf-lens/README.md, «Сборка и запуск»)")
        val out = outputDir.get().asFile
        out.deleteRecursively()
        out.mkdirs()
        File(out, "api_password.txt").writeText(password)
    }
}

androidComponents {
    onVariants { variant ->
        val task = tasks.register<PasswordAsset>("${variant.name}PasswordAsset")
        variant.sources.assets?.addGeneratedSourceDirectory(task, PasswordAsset::outputDir)
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
