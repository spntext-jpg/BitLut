package com.openhealth.sync.config

/**
 * Runtime feature switches.
 * Huawei import is enabled because AppGallery approval is complete and Health Kit review is in progress.
 * The actual sync flow remains guarded by runtime permission/auth checks in Settings and SyncWorker.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = true
}
