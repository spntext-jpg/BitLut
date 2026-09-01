package com.openhealth.sync.data.remote

import com.openhealth.sync.BuildConfig

object HuaweiConfig {
    val APP_ID: String get() = BuildConfig.HUAWEI_APP_ID

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

    // 2026-08-31: SYNC_WORKER_TAG above is applied to every worker in this
    // app (SyncWorker's periodic + one-time requests, AND
    // EveningReminderWorker's periodic request) -- fine for WorkManager
    // maintenance/cancellation, but useless for driving a "Syncing..." UI
    // indicator, since it can't tell a real health-data sync apart from an
    // unrelated notification-scheduling worker. This tag is applied only to
    // SyncWorker's two enqueue sites (schedulePeriodic + enqueueImmediateSync
    // in BackgroundSyncScheduler), so observing WorkInfo for THIS tag
    // reflects "is any SyncWorker (periodic or manual, whichever one)
    // actually running right now" -- a real device log showed the previous
    // isSyncing signal (SyncViewModel.markSyncStarted/markSyncCompleted,
    // wired only to the two MainActivity-triggered call sites) never fired
    // at all when the periodic background worker happened to win the sync
    // lease race: the UI-triggered attempt got deferred and its own
    // started/completed pair collapsed to well under a second, too fast to
    // ever render, while the periodic worker that did the real 10-second
    // sync had no path to isSyncing whatsoever.
    // BITLUT_SYNC_ACTIVITY_TAG_2026_08_31
    const val SYNC_ACTIVITY_TAG: String = "BitLutSyncActivity"

    // Bounded, persisted diagnostic event log (v1.9.11+). Survives process
    // death/restart, unlike the in-memory-only AppLogger ring buffer, so a
    // person (or a future debugging session) can see *why* the circuit
    // breaker opened even after the app process was killed and relaunched.
    const val KEY_DIAGNOSTIC_LOG_JSON: String = "sync_diagnostic_log_json"

    fun hasDeveloperAppId(): Boolean = APP_ID.isNotBlank() && APP_ID != "0"
}
