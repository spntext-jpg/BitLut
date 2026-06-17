package com.openhealth.sync.config

/**
 * Runtime switches for staged releases.
 *
 * v1.5 is a Google Health Connect dashboard-first AppGallery review build.
 * Huawei import is preserved in code and visible as a locked sync method,
 * but no Huawei runtime import flow is enabled before Health Kit approval.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = false
    const val GOOGLE_HEALTH_DASHBOARD_ENABLED: Boolean = true
    const val RELEASE_TRACK: String = "v1.5-dashboard-first"
}
