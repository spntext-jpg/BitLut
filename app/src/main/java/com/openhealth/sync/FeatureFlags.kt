package com.openhealth.sync

/**
 * Runtime feature gates.
 *
 * Huawei import stays in the codebase for the Health Kit approval phase, but it must
 * remain disabled in the AppGallery dashboard-first build. Flip this only after Huawei
 * Health Kit access is approved and import QA is complete.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = false
}
