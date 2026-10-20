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

// The recognition API's password: api_password.txt at the root of the repository (git ignores
// it) goes into the APK's assets when it is there; without it the build carries none.
abstract class PasswordAsset : DefaultTask() {
    @get:InputFiles
    @get:PathSensitive(PathSensitivity.NONE)
    abstract val password: ConfigurableFileCollection

    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    @TaskAction
    fun copy() {
        val out = outputDir.get().asFile
        out.deleteRecursively()   // a password taken out of the repository leaves the next build too
        out.mkdirs()
        password.files.filter { it.isFile }.forEach { it.copyTo(File(out, "api_password.txt"), overwrite = true) }
    }
}

androidComponents {
    onVariants { variant ->
        val task = tasks.register<PasswordAsset>("${variant.name}PasswordAsset") {
            password.from(rootProject.file("../api_password.txt"))
        }
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
