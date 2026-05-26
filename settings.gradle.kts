pluginManagement {
    repositories {
        maven { url = uri("https://developer.huawei.com/repo/") }
        google { content { includeGroupByRegex("com\\.android.*"); includeGroupByRegex("com\\.google.*"); includeGroupByRegex("androidx.*") } }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        maven { url = uri("https://developer.huawei.com/repo/") }
        google()
        mavenCentral()
    }
}
rootProject.name = "BitLut"
include(":app")
