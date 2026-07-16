package com.openhealth.sync.data.worker

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger
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

class SyncRunLease(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    /**
     * Process-local single-flight guard backed by persisted lease state.
     * WorkManager should normally serialize unique work, but manual and periodic jobs
     * have different unique names. This guard prevents cross-entry overlap.
     */
    @Synchronized
    fun tryAcquire(owner: String, nowMs: Long, ttlMs: Long): Boolean {
        val currentUntil = prefs.getLong(HuaweiConfig.KEY_SYNC_LEASE_UNTIL_MS, 0L)
        val currentOwner = prefs.getString(HuaweiConfig.KEY_SYNC_LEASE_OWNER, null)

        if (currentUntil > nowMs && currentOwner != owner) {
            AppLogger.w(TAG, "Sync lease already held by $currentOwner until $currentUntil")
            return false
        }

        prefs.edit()
            .putString(HuaweiConfig.KEY_SYNC_LEASE_OWNER, owner)
            .putLong(HuaweiConfig.KEY_SYNC_LEASE_UNTIL_MS, nowMs + ttlMs)
            .apply()

        return true
    }

    @Synchronized
    fun release(owner: String) {
        val currentOwner = prefs.getString(HuaweiConfig.KEY_SYNC_LEASE_OWNER, null)
        if (currentOwner == owner) {
            prefs.edit()
                .remove(HuaweiConfig.KEY_SYNC_LEASE_OWNER)
                .remove(HuaweiConfig.KEY_SYNC_LEASE_UNTIL_MS)
                .apply()
        }
    }
}

class SyncCircuitBreaker(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    private val failureThreshold = 3
    private val openDurationMs = 30L * 60L * 1000L

    fun isOpen(nowMs: Long): Boolean {
        val openUntil = prefs.getLong(HuaweiConfig.KEY_SYNC_CIRCUIT_OPEN_UNTIL_MS, 0L)
        val open = openUntil > nowMs
        if (open) {
            AppLogger.w(TAG, "Sync circuit breaker open until $openUntil; graceful no-op")
        }
        return open
    }

    fun recordSuccess() {
        prefs.edit()
            .putInt(HuaweiConfig.KEY_SYNC_FAILURE_COUNT, 0)
            .putLong(HuaweiConfig.KEY_SYNC_CIRCUIT_OPEN_UNTIL_MS, 0L)
            .apply()
    }

    fun recordFailure(nowMs: Long): Boolean {
        val failures = prefs.getInt(HuaweiConfig.KEY_SYNC_FAILURE_COUNT, 0) + 1
        val editor = prefs.edit().putInt(HuaweiConfig.KEY_SYNC_FAILURE_COUNT, failures)

        val opened = failures >= failureThreshold
        if (opened) {
            val openUntil = nowMs + openDurationMs
            editor.putLong(HuaweiConfig.KEY_SYNC_CIRCUIT_OPEN_UNTIL_MS, openUntil)
            AppLogger.e(TAG, "Sync circuit opened after $failures failures; openUntil=$openUntil")
        } else {
            AppLogger.w(TAG, "Sync transient failure count=$failures/$failureThreshold")
        }

        editor.apply()
        return opened
    }
}

object SyncRetryPolicy {
    const val MAX_ATTEMPTS = 3
    private const val BASE_DELAY_MS = 1_000L
    private const val MAX_DELAY_MS = 30_000L

    fun nextDelayMs(attemptIndex: Int): Long {
        val exponential = BASE_DELAY_MS * (1L shl attemptIndex.coerceIn(0, 5))
        val capped = min(exponential, MAX_DELAY_MS)
        return Random.nextLong(from = BASE_DELAY_MS, until = capped + 1L)
    }
}

sealed class SyncAttemptOutcome {
    data object Success : SyncAttemptOutcome()
    data object GracefulNoop : SyncAttemptOutcome()
    data object RetryableFailure : SyncAttemptOutcome()
    data object NonRetryableFailure : SyncAttemptOutcome()
}
