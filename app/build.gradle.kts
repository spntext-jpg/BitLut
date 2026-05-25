import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val localProps = Properties().apply {
    val f = rootProject.file("local.properties")
    if (f.exists()) load(f.inputStream())
}

fun huaweiProp(key: String): String =
    System.getenv(key)
        ?: localProps[key]?.toString()
        ?: "YOUR_${key}"

android {
    namespace = "com.openhealth.sync"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.openhealth.sync"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables { useSupportLibrary = true }

        buildConfigField("String", "HUAWEI_CLIENT_ID",
            "\"${huaweiProp("HUAWEI_CLIENT_ID")}\"")
        buildConfigField("String", "HUAWEI_CLIENT_SECRET",
            "\"${huaweiProp("HUAWEI_CLIENT_SECRET")}\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isDebuggable = true
            applicationIdSuffix = ".debug"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    // composeOptions block removed — Kotlin 2.0 + Compose Plugin handles this automatically

    packaging {
        resources {
            excludes += setOf(
                "/META-INF/{AL2.0,LGPL2.1}",
                "/META-INF/DEPENDENCIES"
            )
        }
    }
}

dependencies {
    // Compose BOM — aligns all Compose library versions
    val composeBom = platform("androidx.compose:compose-bom:2025.04.01")
    implementation(composeBom)

    // Compose
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    // Material 3 Expressive — latest stable
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material3:material3-adaptive-navigation-suite")

    // AndroidX core
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")

    // AppCompat — required for HuaweiCallbackActivity
    implementation("androidx.appcompat:appcompat:1.7.0")

    // Health Connect — latest compatible with compileSdk 35
    implementation("androidx.health.connect:connect-client:1.1.0-alpha11")

    // WorkManager
    implementation("androidx.work:work-runtime-ktx:2.10.0")

    // Network
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Secure storage
    implementation("androidx.security:security-crypto:1.0.0")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}
