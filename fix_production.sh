#!/bin/bash
# fix_production.sh
# Production-ready overhaul:
# 1. Fix duplicate resource conflict in mipmap folders
# 2. Update full dependency stack to latest stable compatible versions
# 3. Correct adaptive icon structure per Android standards
# 4. Upgrade compileSdk/targetSdk to 35
set -e

echo "=================================================="
echo " BitLut — Production Fix"
echo "=================================================="

# ── 1. REMOVE conflicting XML files from mipmap density folders
# Rule: mipmap-hdpi/mdpi/xhdpi/xxhdpi/xxxhdpi contain ONLY PNG raster fallbacks.
# Adaptive icon XML belongs ONLY in mipmap-anydpi-v26/.
echo "[1/5] Removing XML conflicts from density mipmap folders..."
for DENSITY in hdpi mdpi xhdpi xxhdpi xxxhdpi; do
  DIR="app/src/main/res/mipmap-${DENSITY}"
  rm -f "${DIR}/ic_launcher.xml"
  rm -f "${DIR}/ic_launcher_round.xml"
  echo "  Cleaned: ${DIR}"
done

# ── 2. REMOVE adaptive PNG layers from density folders
# ic_launcher_adaptive_back.png and ic_launcher_adaptive_fore.png are not
# part of the standard adaptive icon spec. The adaptive icon is defined
# entirely in mipmap-anydpi-v26/ and drawable/. Remove these artifacts.
echo "[2/5] Removing non-standard adaptive PNG layers..."
for DENSITY in hdpi mdpi xhdpi xxhdpi xxxhdpi; do
  DIR="app/src/main/res/mipmap-${DENSITY}"
  rm -f "${DIR}/ic_launcher_adaptive_back.png"
  rm -f "${DIR}/ic_launcher_adaptive_fore.png"
  echo "  Cleaned: ${DIR}"
done

# ── 3. WRITE correct mipmap-anydpi-v26 adaptive icon definitions
# These reference drawable vectors — works on Android 8+ (API 26+)
echo "[3/5] Writing correct adaptive icon definitions..."

cat > app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
EOF

cat > app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
EOF

# ── 4. WRITE drawable vector layers
# Background: solid dark — BitLut brand color
# Foreground: the converted BitLut icon (replace ic_launcher_foreground.xml
# with your converted SVG content after this script runs)
echo "[4/5] Writing drawable vector layers..."
mkdir -p app/src/main/res/drawable

cat > app/src/main/res/drawable/ic_launcher_background.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#0D0D0D"
        android:pathData="M0,0H108V108H0Z"/>
</vector>
EOF

# ic_launcher_foreground.xml — this is the placeholder.
# Replace with your BitLut.svg converted content via GitHub Web:
# app/src/main/res/drawable/ic_launcher_foreground.xml
cat > app/src/main/res/drawable/ic_launcher_foreground.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <!-- Outer sync ring -->
    <path
        android:strokeColor="#A3E635"
        android:strokeWidth="5"
        android:fillColor="#00000000"
        android:pathData="M30,54 A24,24 0 1,1 54,78"/>
    <path
        android:strokeColor="#A3E635"
        android:strokeWidth="5"
        android:fillColor="#00000000"
        android:pathData="M78,54 A24,24 0 1,1 54,30"/>
    <!-- Arrow heads -->
    <path
        android:fillColor="#A3E635"
        android:pathData="M54,22 L60,32 L48,32 Z"/>
    <path
        android:fillColor="#A3E635"
        android:pathData="M54,86 L48,76 L60,76 Z"/>
    <!-- Center heart -->
    <path
        android:fillColor="#A3E635"
        android:pathData="M54,66 C54,66 40,56 40,48 C40,43 44,40 48,41 C51,41 53,44 54,46 C55,44 57,41 60,41 C64,40 68,43 68,48 C68,56 54,66 54,66 Z"/>
</vector>
EOF

# ── 5. UPDATE full dependency stack to latest production-ready versions
# compileSdk 35 (Android 15) — latest stable
# material3 1.3.1 — latest stable, Material You / Expressive
# health connect 1.1.0-alpha11 — latest compatible with SDK 35
# compose BOM 2024.12.01 — aligns all Compose versions
echo "[5/5] Updating build.gradle.kts to production stack..."

cat > app/build.gradle.kts << 'EOF'
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
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
        freeCompilerArgs += listOf(
            "-opt-in=androidx.compose.material3.ExperimentalMaterial3Api",
            "-opt-in=kotlin.RequiresOptIn"
        )
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    // Compose compiler tied to Kotlin 1.8.22 — use BOM for library versions
    composeOptions {
        kotlinCompilerExtensionVersion = "1.4.8"
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
    // ── Compose BOM — aligns all Compose library versions ──────────────────
    val composeBom = platform("androidx.compose:compose-bom:2024.06.00")
    implementation(composeBom)

    // ── Compose ─────────────────────────────────────────────────────────────
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    // Material 3 — latest stable, Material You / Expressive
    implementation("androidx.compose.material3:material3:1.3.1")
    implementation("androidx.compose.material3:material3-window-size-class:1.3.1")

    // ── AndroidX core ────────────────────────────────────────────────────────
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")

    // ── AppCompat — required for HuaweiCallbackActivity ──────────────────────
    implementation("androidx.appcompat:appcompat:1.7.0")

    // ── Health Connect — latest compatible with compileSdk 35 ────────────────
    implementation("androidx.health.connect:connect-client:1.1.0-alpha11")

    // ── WorkManager ──────────────────────────────────────────────────────────
    implementation("androidx.work:work-runtime-ktx:2.10.0")

    // ── Network ──────────────────────────────────────────────────────────────
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // ── Secure storage ───────────────────────────────────────────────────────
    implementation("androidx.security:security-crypto:1.0.0")

    // ── Coroutines ───────────────────────────────────────────────────────────
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}
EOF

# ── 6. VERIFY final res structure
echo ""
echo "=== Final res structure ==="
find app/src/main/res -type f | sort

echo ""
echo "=== mipmap-anydpi-v26 (should have only XML) ==="
ls app/src/main/res/mipmap-anydpi-v26/

echo ""
echo "=== mipmap-hdpi (should have only PNG) ==="
ls app/src/main/res/mipmap-hdpi/

echo ""
echo "=== drawable (should have background + foreground vectors) ==="
ls app/src/main/res/drawable/

echo ""
echo "=== compileSdk in build.gradle.kts ==="
grep "compileSdk\|targetSdk\|minSdk" app/build.gradle.kts

echo ""
echo "=== material3 version ==="
grep "material3" app/build.gradle.kts

echo ""
echo "=================================================="
echo " Fix complete. Run: git add -A && git commit && git push"
echo "=================================================="
