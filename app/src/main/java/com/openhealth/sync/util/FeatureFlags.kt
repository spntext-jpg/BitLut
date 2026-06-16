package com.openhealth.sync.util

/**
 * Runtime switches for staged AppGallery rollout.
 *
 * Huawei import is preserved in the codebase, but hidden from UI/runtime until Huawei Health Kit
 * approval is granted. Enable this only after approval and real-device import validation.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = false
}
