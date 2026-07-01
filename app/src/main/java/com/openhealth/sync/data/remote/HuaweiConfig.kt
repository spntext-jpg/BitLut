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

    // Legacy monolithic circuit breaker keys. Kept for backward compatibility
    // with already-installed app instances; no longer written to, but reading
    // them is harmless (SharedPreferences simply ignores unused keys).
    const val KEY_SYNC_FAILURE_COUNT: String = "sync_failure_count"
    const val KEY_SYNC_CIRCUIT_OPEN_UNTIL_MS: String = "sync_circuit_open_until_ms"

    // Per-dependency circuit breaker keys (v1.9.11+). Huawei Health Kit and
    // Health Connect fail independently of each other -- e.g. Huawei Health
    // Kit being stuck on the 50005 pending-approval state should not cause a
    // healthy Health Connect dependency to also look "failing", and vice
    // versa. Tracking failures separately lets each dependency open/close its
    // own breaker based on its own actual health.
    const val KEY_SYNC_FAILURE_COUNT_HUAWEI: String = "sync_failure_count_huawei"
    const val KEY_SYNC_CIRCUIT_OPEN_UNTIL_MS_HUAWEI: String = "sync_circuit_open_until_ms_huawei"
    const val KEY_SYNC_FAILURE_COUNT_GOOGLE: String = "sync_failure_count_google"
    const val KEY_SYNC_CIRCUIT_OPEN_UNTIL_MS_GOOGLE: String = "sync_circuit_open_until_ms_google"

    const val KEY_SYNC_LEASE_UNTIL_MS: String = "sync_lease_until_ms"
    const val KEY_SYNC_LEASE_OWNER: String = "sync_lease_owner"
    const val SYNC_WORKER_TAG: String = "BitLutSyncWorker"

    // Bounded, persisted diagnostic event log (v1.9.11+). Survives process
    // death/restart, unlike the in-memory-only AppLogger ring buffer, so a
    // person (or a future debugging session) can see *why* the circuit
    // breaker opened even after the app process was killed and relaunched.
    const val KEY_DIAGNOSTIC_LOG_JSON: String = "sync_diagnostic_log_json"

    fun hasDeveloperAppId(): Boolean = APP_ID.isNotBlank() && APP_ID != "0"
}
