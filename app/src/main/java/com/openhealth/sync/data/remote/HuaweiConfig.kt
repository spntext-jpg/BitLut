package com.openhealth.sync.data.remote

/**
 * Single source of truth for all Huawei OAuth2 and Health API constants.
 *
 * HOW TO CONFIGURE:
 * 1. Register your app at https://developer.huawei.com/
 * 2. Enable Health Kit API in your project
 * 3. Replace the placeholder strings below with real values from the console.
 *
 * NOTE: For production, move these to BuildConfig fields in build.gradle.kts
 * and store real values in a local.properties file (which is gitignored).
 */
object HuaweiConfig {

    // ── Developer Console credentials ────────────────────────────────────────
    // Replace with your actual Huawei AppGallery Connect client_id
    const val CLIENT_ID: String = "YOUR_HUAWEI_CLIENT_ID"

    // Replace with your actual client_secret (NEVER commit the real value to git)
    const val CLIENT_SECRET: String = "YOUR_HUAWEI_CLIENT_SECRET"

    // ── OAuth2 redirect URI ───────────────────────────────────────────────────
    // Must match EXACTLY what is registered in Huawei Developer Console
    // AND the <data android:host=...> filter in AndroidManifest.xml
    const val REDIRECT_URI: String = "https://com.openhealth.sync/oauth_callback"

    // ── API base URLs ─────────────────────────────────────────────────────────
    const val OAUTH_BASE_URL: String = "https://oauth-login.cloud.huawei.com/"
    const val HEALTH_API_BASE_URL: String = "https://health-api.cloud.huawei.com/"

    // ── OAuth2 scopes ─────────────────────────────────────────────────────────
    const val SCOPES: String =
        "https://www.huawei.com/auth/healthkit.step.read" +
        "+https://www.huawei.com/auth/healthkit.heartrate.read" +
        "+https://www.huawei.com/auth/healthkit.sleep.read"

    // ── SharedPreferences key names ───────────────────────────────────────────
    const val PREFS_NAME: String = "huawei_auth_prefs"
    const val KEY_ACCESS_TOKEN: String = "access_token"
    const val KEY_REFRESH_TOKEN: String = "refresh_token"
    const val KEY_EXPIRE_TIME: String = "expire_time"
    const val KEY_LAST_SYNC_MS: String = "last_sync_ms"

    // ── Sync settings ─────────────────────────────────────────────────────────
    // Token refresh window: refresh if less than 5 minutes remain
    const val TOKEN_REFRESH_THRESHOLD_MS: Long = 5 * 60 * 1000L

    // WorkManager unique task name
    const val SYNC_WORKER_TAG: String = "BitLutSyncWorker"
}
