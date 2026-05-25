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
    const val SYNC_WORKER_TAG: String = "BitLutSyncWorker"

    fun hasDeveloperAppId(): Boolean = APP_ID.isNotBlank() && APP_ID != "0"
}
