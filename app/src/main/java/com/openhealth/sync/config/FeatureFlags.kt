package com.openhealth.sync.config

/**
 * Central runtime switches for staged releases.
 *
 * v1.5 ships as a Google Health Connect dashboard-first app for AppGallery review.
 * Huawei import code remains compiled and reviewable, but is not reachable from UI,
 * background work, or permission prompts until Huawei Health Kit approval is granted.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = false
    const val GOOGLE_HEALTH_DASHBOARD_ENABLED: Boolean = true
    const val RELEASE_TRACK: String = "v1.5-dashboard-first"
}
