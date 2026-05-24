package com.openhealth.sync.data.remote

import com.openhealth.sync.BuildConfig

/**
 * Single source of truth for all Huawei OAuth2 constants.
 *
 * Credentials come from BuildConfig, which is populated at build time from:
 *   - LOCAL:  local.properties  (gitignored — safe for your machine)
 *   - CI:     GitHub Actions Secrets (HUAWEI_CLIENT_ID, HUAWEI_CLIENT_SECRET)
 *
 * Never paste real keys directly into this file.
 */
object HuaweiConfig {

    val CLIENT_ID: String get() = BuildConfig.HUAWEI_CLIENT_ID
    val CLIENT_SECRET: String get() = BuildConfig.HUAWEI_CLIENT_SECRET

    const val REDIRECT_URI: String = "https://com.openhealth.sync/oauth_callback"

    const val OAUTH_BASE_URL: String   = "https://oauth-login.cloud.huawei.com/"
    const val HEALTH_API_BASE_URL: String = "https://health-api.cloud.huawei.com/"

    const val SCOPES: String =
        "https://www.huawei.com/auth/healthkit.step.read" +
        "+https://www.huawei.com/auth/healthkit.heartrate.read" +
        "+https://www.huawei.com/auth/healthkit.sleep.read"

    const val PREFS_NAME: String          = "bitlut_prefs"
    const val KEY_ACCESS_TOKEN: String    = "access_token"
    const val KEY_REFRESH_TOKEN: String   = "refresh_token"
    const val KEY_EXPIRE_TIME: String     = "expire_time"
    const val KEY_LAST_SYNC_MS: String    = "last_sync_ms"
    const val TOKEN_REFRESH_THRESHOLD_MS: Long = 5 * 60 * 1000L
    const val SYNC_WORKER_TAG: String     = "BitLutSyncWorker"

    /** Returns true only when real credentials are present (not placeholders). */
    fun isConfigured(): Boolean =
        CLIENT_ID.isNotEmpty()
        && CLIENT_ID != "YOUR_HUAWEI_CLIENT_ID"
        && !CLIENT_ID.startsWith("YOUR_")
}
