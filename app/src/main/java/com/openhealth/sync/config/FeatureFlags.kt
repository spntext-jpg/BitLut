package com.openhealth.sync.config

/**
 * Central runtime switches for production-safe rollout.
 *
 * Huawei import is enabled as a real code path after AppGallery approval.
 * Health Kit access is still guarded by HMS Core, Huawei Health, user auth
 * and server-side Health Kit approval checks inside HuaweiHealthManager/SyncWorker.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = true
    const val PERIODIC_HUAWEI_SYNC_ENABLED: Boolean = true
    const val HEALTH_COVERAGE_VERIFICATION_ENABLED: Boolean = true
}
