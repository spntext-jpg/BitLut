package com.openhealth.sync.data.worker

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.min
import kotlin.random.Random

private const val TAG = "SyncReliability"

data class SyncWindow(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val savedLastSyncMs: Long
)

object SyncWindowPlanner {
    private const val DEFAULT_LOOKBACK_MS = 24L * 60L * 60L * 1000L
    private const val MAX_LOOKBACK_MS = 7L * 24L * 60L * 60L * 1000L
    private const val OVERLAP_MS = 5L * 60L * 1000L

    fun plan(prefs: SharedPreferences, nowMs: Long): SyncWindow {
        val saved = prefs.getLong(HuaweiConfig.KEY_LAST_SYNC_MS, 0L)
        val minStart = nowMs - MAX_LOOKBACK_MS
        val fallbackStart = nowMs - DEFAULT_LOOKBACK_MS

        val baseStart = when {
            saved <= 0L -> fallbackStart
            saved >= nowMs -> {
                AppLogger.w(TAG, "Corrupted future last_sync_ms=$saved; falling back to last 24h")
                fallbackStart
            }
            saved < minStart -> minStart
            else -> saved
        }

        val start = (baseStart - OVERLAP_MS).coerceAtLeast(minStart)

        return SyncWindow(
            startTimeMs = start.coerceAtMost(nowMs - 1L),
            endTimeMs = nowMs,
            savedLastSyncMs = saved
        )
    }
}

/**
 * Process-local single-flight guard backed by persisted lease state.
 *
 * WorkManager should normally serialize unique work, but manual ("Sync now")
 * and periodic (every 30 minutes) jobs use different unique work names, so
 * this guard prevents them from running concurrently and racing on the same
 * Huawei -> Health Connect write.
 *
 * Concurrency fix (v1.9.11): the previous implementation paired
 * `@Synchronized` (which only serializes calls on the *same JVM object*) with
 * `SharedPreferences.edit().apply()` (which commits asynchronously). Because
 * each `SyncWorker` instance constructed its own `SyncRunLease` via
 * `by lazy { SyncRunLease(applicationContext) }`, two concurrently-running
 * workers held two *different* lease objects, so `@Synchronized` provided no
 * real protection between them -- there was a real read-then-write race
 * window between checking the lease and persisting the new owner.
 *
 * This version closes that window two ways:
 *  1. [acquireLock] is a single [Mutex] instance held by the [AppContainer]
 *     singleton and shared by every [SyncRunLease] caller in the process, so
 *     concurrent callers actually serialize on the same lock object.
 *  2. The persisted state is written with a synchronous [SharedPreferences.Editor.commit]
 *     instead of the asynchronous `apply()`, so by the time [tryAcquire]
 *     returns `true`, the lease is guaranteed durably visible to any other
 *     reader (including a different process, in the unlikely event WorkManager
 *     ever runs two worker processes) immediately, not "eventually".
 */
class SyncRunLease(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    private val acquireLock = Mutex()

    suspend fun tryAcquire(owner: String, nowMs: Long, ttlMs: Long): Boolean = acquireLock.withLock {
        val currentUntil = prefs.getLong(HuaweiConfig.KEY_SYNC_LEASE_UNTIL_MS, 0L)
        val currentOwner = prefs.getString(HuaweiConfig.KEY_SYNC_LEASE_OWNER, null)

        if (currentUntil > nowMs && currentOwner != owner) {
            AppLogger.w(TAG, "Sync lease already held by $currentOwner until $currentUntil")
            return@withLock false
        }

        // Synchronous commit (not apply()): the caller must be able to rely on
        // this write being durably visible the instant tryAcquire returns true.
        val committed = prefs.edit()
            .putString(HuaweiConfig.KEY_SYNC_LEASE_OWNER, owner)
            .putLong(HuaweiConfig.KEY_SYNC_LEASE_UNTIL_MS, nowMs + ttlMs)
            .commit()

        if (!committed) {
            AppLogger.e(TAG, "Sync lease commit() failed (disk I/O issue); treating as not acquired")
        }

        committed
    }

    suspend fun release(owner: String) = acquireLock.withLock {
        val currentOwner = prefs.getString(HuaweiConfig.KEY_SYNC_LEASE_OWNER, null)
        if (currentOwner == owner) {
            prefs.edit()
                .remove(HuaweiConfig.KEY_SYNC_LEASE_OWNER)
                .remove(HuaweiConfig.KEY_SYNC_LEASE_UNTIL_MS)
                .commit()
        }
        Unit
    }
}

/** Identifies which dependency a circuit breaker failure belongs to, so Huawei
 *  Health Kit and Health Connect can fail/recover independently. */
enum class SyncDependency { HUAWEI, GOOGLE }

/**
 * Per-dependency circuit breaker (v1.9.11).
 *
 * Previously a single monolithic breaker tracked failures for the whole sync
 * pipeline. That meant a Huawei-side problem (e.g. the long-standing 50005
 * pending-approval state) and a Google-side problem (e.g. Health Connect
 * write denied) were indistinguishable in the failure count, even though
 * they are unrelated dependencies that can and do fail independently. A
 * [dependency]-scoped breaker means a healthy Health Connect doesn't get
 * dragged into "open" state by an unrelated, ongoing Huawei issue.
 */
class SyncCircuitBreaker(context: Context, private val dependency: SyncDependency) {
    private val prefs = context.applicationContext.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    private val failureThreshold = 3
    private val openDurationMs = 30L * 60L * 1000L

    private val failureCountKey = when (dependency) {
        SyncDependency.HUAWEI -> HuaweiConfig.KEY_SYNC_FAILURE_COUNT_HUAWEI
        SyncDependency.GOOGLE -> HuaweiConfig.KEY_SYNC_FAILURE_COUNT_GOOGLE
    }
    private val openUntilKey = when (dependency) {
        SyncDependency.HUAWEI -> HuaweiConfig.KEY_SYNC_CIRCUIT_OPEN_UNTIL_MS_HUAWEI
        SyncDependency.GOOGLE -> HuaweiConfig.KEY_SYNC_CIRCUIT_OPEN_UNTIL_MS_GOOGLE
    }

    fun isOpen(nowMs: Long): Boolean {
        val openUntil = prefs.getLong(openUntilKey, 0L)
        val open = openUntil > nowMs
        if (open) {
            AppLogger.w(TAG, "[$dependency] Sync circuit breaker open until $openUntil; graceful no-op")
        }
        return open
    }

    fun recordSuccess() {
        prefs.edit()
            .putInt(failureCountKey, 0)
            .putLong(openUntilKey, 0L)
            .apply()
    }

    fun recordFailure(nowMs: Long): Boolean {
        val failures = prefs.getInt(failureCountKey, 0) + 1
        val editor = prefs.edit().putInt(failureCountKey, failures)

        val opened = failures >= failureThreshold
        if (opened) {
            val openUntil = nowMs + openDurationMs
            editor.putLong(openUntilKey, openUntil)
            AppLogger.e(TAG, "[$dependency] Sync circuit opened after $failures failures; openUntil=$openUntil")
            SyncDiagnosticLog.record(prefs, "circuit_open", "$dependency breaker opened after $failures failures")
        } else {
            AppLogger.w(TAG, "[$dependency] Sync transient failure count=$failures/$failureThreshold")
        }

        editor.apply()
        return opened
    }
}

object SyncRetryPolicy {
    const val MAX_ATTEMPTS = 3
    private const val BASE_DELAY_MS = 1_000L
    private const val MAX_DELAY_MS = 30_000L

    /** Exponential backoff with full jitter (AWS-style): the delay is drawn
     *  uniformly from [BASE_DELAY_MS, min(exponential cap, MAX_DELAY_MS)], so
     *  concurrent retries (e.g. across multiple devices hitting the same
     *  backend, or this worker's own retry loop) don't all retry in lockstep
     *  and create a thundering-herd spike. */
    fun nextDelayMs(attemptIndex: Int): Long {
        val exponential = BASE_DELAY_MS * (1L shl attemptIndex.coerceIn(0, 5))
        val capped = min(exponential, MAX_DELAY_MS)
        return Random.nextLong(from = BASE_DELAY_MS, until = capped + 1L)
    }
}

sealed class SyncAttemptOutcome {
    data object Success : SyncAttemptOutcome()
    data object GracefulNoop : SyncAttemptOutcome()
    /** [dependency] identifies which side caused the failure, so the caller can
     *  charge it to the correct per-dependency circuit breaker. */
    data class RetryableFailure(val dependency: SyncDependency) : SyncAttemptOutcome()
    data object NonRetryableFailure : SyncAttemptOutcome()
}

/**
 * Bounded, persisted diagnostic log (v1.9.11).
 *
 * [AppLogger] keeps an in-memory ring buffer for the in-app Settings log
 * viewer, but it is lost the moment the process dies -- which is exactly
 * when understanding *why* the circuit breaker opened, or why a sync kept
 * failing, matters most (the person re-opens the app after a problem and
 * the in-memory history is already gone). This persists the last [MAX_ENTRIES]
 * structured events to SharedPreferences as a small bounded JSON array, so
 * they survive process death/restart without needing a database.
 */
object SyncDiagnosticLog {
    private const val MAX_ENTRIES = 40

    data class Entry(val timestampMs: Long, val event: String, val detail: String)

    fun record(prefs: SharedPreferences, event: String, detail: String) {
        try {
            val existing = readAll(prefs).toMutableList()
            existing.add(0, Entry(System.currentTimeMillis(), event, detail))
            val trimmed = existing.take(MAX_ENTRIES)

            val array = JSONArray()
            trimmed.forEach { entry ->
                array.put(
                    JSONObject().apply {
                        put("ts", entry.timestampMs)
                        put("event", entry.event)
                        put("detail", entry.detail)
                    }
                )
            }

            prefs.edit().putString(HuaweiConfig.KEY_DIAGNOSTIC_LOG_JSON, array.toString()).apply()
        } catch (e: Exception) {
            // Diagnostics must never be able to crash or block the sync path
            // they're trying to describe.
            AppLogger.e(TAG, "Failed to persist diagnostic log entry: ${e.message}", e)
        }
    }

    fun readAll(prefs: SharedPreferences): List<Entry> {
        val raw = prefs.getString(HuaweiConfig.KEY_DIAGNOSTIC_LOG_JSON, null) ?: return emptyList()
        return try {
            val array = JSONArray(raw)
            (0 until array.length()).mapNotNull { index ->
                val obj = array.optJSONObject(index) ?: return@mapNotNull null
                Entry(
                    timestampMs = obj.optLong("ts", 0L),
                    event = obj.optString("event", ""),
                    detail = obj.optString("detail", "")
                )
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "Diagnostic log is corrupt; resetting: ${e.message}", e)
            emptyList()
        }
    }
}
