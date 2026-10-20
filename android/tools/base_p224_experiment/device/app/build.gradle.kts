plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
val fullImagePooling = providers.gradleProperty("fullImagePooling").orNull == "true"
val disPooling = providers.gradleProperty("disPooling").orNull == "true"
val disResolution = providers.gradleProperty("disResolution").orNull == "true"
require(!(fullImagePooling && disPooling))
require(!disResolution || disPooling)

// Reuse frozen lifecycle and geometry code without editing the running experiment.
val shared = file("../../../offline_benchmark/device/app/src")
val sharedSources = tasks.register<Sync>("prepareSharedBenchmarkSources") {
    from(shared.resolve("main/java"))
    listOf("BenchmarkServer", "BenchmarkRuntime", "BenchmarkForegroundService",
        "BottleLabelSegmenter", "MaskGeometry", "MattingFrame", "MaskCoverage",
        "EncoderOptions", "NativeDot").forEach { include("**/$it.kt") }
    into(layout.buildDirectory.dir("generated/benchmark-shared"))
}
val sharedTests = tasks.register<Sync>("prepareSharedBenchmarkTests") {
    from(shared.resolve("test/java"))
    listOf("MaskCoverageTest", "EncoderOptionsTest", "ForegroundManifestTest")
        .forEach { include("**/$it.kt") }
    into(layout.buildDirectory.dir("generated/benchmark-tests"))
}
android {
    namespace = "com.alolalab.chtozavino.offlinebench"
    compileSdk = 36
    defaultConfig {
        applicationId = when { disResolution -> "com.alolalab.chtozavino.disresbench"
            disPooling -> "com.alolalab.chtozavino.dispoolbench"
            fullImagePooling -> "com.alolalab.chtozavino.fullpoolbench"
            else -> "com.alolalab.chtozavino.basepoolbench" }
        minSdk = 28
        targetSdk = 36
        versionCode = when { disResolution -> 8;disPooling -> 7;fullImagePooling -> 4;else -> 2 }
        versionName = when { disResolution -> "0.1.7-dis-resolution"
            disPooling -> "0.1.6-dis-p512-pooling"
            fullImagePooling -> "0.1.3-full-image-p512-pooling"
            else -> "0.1.1-base-p224-p512-pooling" }
        ndk { abiFilters += "arm64-v8a" }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    sourceSets {
        getByName("main").java.srcDir(layout.buildDirectory.dir("generated/benchmark-shared"))
        getByName("main").res.srcDir(shared.resolve("main/res"))
        getByName("test").java.srcDir(layout.buildDirectory.dir("generated/benchmark-tests"))
    }
    packaging {
        jniLibs.pickFirsts += setOf("**/libc++_shared.so", "**/libtensorflowlite_jni.so", "**/libtensorflowlite_gpu_jni.so")
    }
}
tasks.matching { it.name == "preBuild" }.configureEach { dependsOn(sharedSources,sharedTests) }
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
dependencies {
    implementation(files("../../../../app/libs/naflex-0.2.0.aar"))
    implementation("com.google.ai.edge.litert:litert:2.2.0")
    implementation("org.nanohttpd:nanohttpd:2.3.1")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20260814")
}
