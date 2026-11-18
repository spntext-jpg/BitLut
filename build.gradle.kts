buildscript {
    repositories {
        google()
        mavenCentral()
        maven(url = "https://developer.huawei.com/repo/")
    }

    dependencies {
        classpath("com.android.tools.build:gradle:9.1.1")
        classpath("com.huawei.agconnect:agcp:1.9.6.300")
        classpath(kotlin("gradle-plugin", version = "2.3.21"))
    }
}

plugins {
    id("com.android.application") version "9.1.1" apply false
    id("org.jetbrains.kotlin.android") version "2.3.21" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.3.21" apply false
}
