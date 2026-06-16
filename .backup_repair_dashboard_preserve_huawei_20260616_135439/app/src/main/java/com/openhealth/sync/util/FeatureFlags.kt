package com.openhealth.sync.util

/**
 * Central runtime switches for staged AppGallery rollout.
 *
 * Huawei import is intentionally preserved in the codebase, but hidden from UI/runtime until
 * Huawei Health Kit approval is granted. When approval is complete, enable the flag and route
 * the import entry point from navigation/settings without rebuilding the import pipeline.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = false
}
