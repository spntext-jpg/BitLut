package com.openhealth.sync.data.remote

import com.openhealth.sync.BuildConfig

object HuaweiConfig {
    val APP_ID: String get() = BuildConfig.HUAWEI_APP_ID
    val CLIENT_ID: String get() = BuildConfig.HUAWEI_CLIENT_ID
    val CLIENT_SECRET: String get() = BuildConfig.HUAWEI_CLIENT_SECRET
    val REDIRECT_URI: String get() = BuildConfig.HUAWEI_REDIRECT_URI
    val SCOPES: String get() = BuildConfig.HUAWEI_SCOPES

    const val PREFS_NAME: String = "bitlut_prefs"
    const val KEY_HUAWEI_AUTHORIZED: String = "huawei_authorized"
    const val KEY_LAST_SYNC_MS: String = "last_sync_ms"
    const val KEY_LAST_SYNC_ATTEMPT_MS: String = "last_sync_attempt_ms"
    const val KEY_SYNC_FAILURE_COUNT: String = "sync_failure_count"
    const val KEY_SYNC_CIRCUIT_OPEN_UNTIL_MS: String = "sync_circuit_open_until_ms"
    const val KEY_SYNC_LEASE_UNTIL_MS: String = "sync_lease_until_ms"
    const val KEY_SYNC_LEASE_OWNER: String = "sync_lease_owner"
    const val SYNC_WORKER_TAG: String = "BitLutSyncWorker"

    fun hasDeveloperAppId(): Boolean = APP_ID.isNotBlank() && APP_ID != "0"
}


/*
 * Basic Sport Health Data coverage requested for Health Kit approval:
 * - Step
 * - Distance, ascent & altitude
 * - Active Hours / moderate-to-high intensity
 * - Daily Activity Summary
 * - Activity record
 * - Activity
 *
 * Keep actual Huawei scope constants in this file aligned with the scopes approved in AppGallery
 * Connect. SyncWorker and HuaweiHealthManager must treat 50005 as a server-side approval/cache state,
 * not as a recoverable user-action error.
 */
