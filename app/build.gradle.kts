import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

apply(plugin = "com.huawei.agconnect")

val localProps = Properties().apply {
    val f = rootProject.file("local.properties")
    if (f.exists()) load(f.inputStream())
}

val huaweiEnvProps = Properties().apply {
    val f = rootProject.file(".huawei.env")
    if (f.exists()) {
        f.readLines()
            .map { it.trim() }
            .filter { it.isNotEmpty() && !it.startsWith("#") && it.contains("=") }
            .forEach { line ->
                val idx = line.indexOf('=')
                put(line.substring(0, idx).trim(), line.substring(idx + 1).trim())
            }
    }
}

fun secretProp(key: String, fallback: String = ""): String =
    System.getenv(key)
        ?: localProps[key]?.toString()
        ?: huaweiEnvProps[key]?.toString()
        ?: fallback

fun escapedBuildConfig(key: String, fallback: String = ""): String =
    secretProp(key, fallback).replace("\\", "\\\\").replace("\"", "\\\"")

val releaseKeystorePath = secretProp("BITLUT_KEYSTORE_PATH")
val releaseKeystorePassword = secretProp("BITLUT_KEYSTORE_PASSWORD")
val releaseKeyAlias = secretProp("BITLUT_KEY_ALIAS")
val releaseKeyPassword = secretProp("BITLUT_KEY_PASSWORD")
val hasReleaseSigning = releaseKeystorePath.isNotBlank() &&
    releaseKeystorePassword.isNotBlank() &&
    releaseKeyAlias.isNotBlank() &&
    releaseKeyPassword.isNotBlank()


android {
    namespace = "com.openhealth.sync"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.openhealth.sync"
        minSdk = 26
        targetSdk = 35
        versionCode = 18
        versionName = "1.1.7"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables { useSupportLibrary = true }

        val huaweiAppId = secretProp("HUAWEI_APP_ID", "117824685")
        manifestPlaceholders["huaweiAppId"] = huaweiAppId

        buildConfigField("String", "HUAWEI_APP_ID", "\"${escapedBuildConfig("HUAWEI_APP_ID", "117824685")}\"")
        buildConfigField("String", "HUAWEI_CLIENT_ID", "\"${escapedBuildConfig("HUAWEI_CLIENT_ID")}\"")
        buildConfigField("String", "HUAWEI_CLIENT_SECRET", "\"${escapedBuildConfig("HUAWEI_CLIENT_SECRET")}\"")
        buildConfigField("String", "HUAWEI_REDIRECT_URI", "\"${escapedBuildConfig("HUAWEI_REDIRECT_URI", "https://com.openhealth.sync/oauth_callback")}\"")
        buildConfigField("String", "HUAWEI_SCOPES", "\"${escapedBuildConfig("HUAWEI_SCOPES", "https://www.huawei.com/auth/healthkit.step.read+https://www.huawei.com/auth/healthkit.heartrate.read")}\"")
    }

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                storeFile = rootProject.file(releaseKeystorePath)
                storePassword = releaseKeystorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    buildTypes {
        release {
            if (hasReleaseSigning) signingConfig = signingConfigs.getByName("release")
            isDebuggable = false
            isMinifyEnabled = false
            isShrinkResources = false
        }
        debug {
            isDebuggable = true
            // No applicationIdSuffix: Huawei AppGallery/Health Kit package must stay com.openhealth.sync.
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions { jvmTarget = "17" }

    buildFeatures {
        compose = true
        buildConfig = true
    }

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
    val composeBom = platform("androidx.compose:compose-bom:2025.04.01")
    implementation(composeBom)

    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material3:material3-adaptive-navigation-suite")
    implementation("androidx.compose.material:material-icons-extended")

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.appcompat:appcompat:1.7.0")

    implementation("androidx.health.connect:connect-client:1.1.0-alpha11")
    implementation("androidx.work:work-runtime-ktx:2.10.0")

    implementation("com.huawei.hms:health:6.11.0.303")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}
