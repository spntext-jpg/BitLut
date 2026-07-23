package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.openhealth.sync.SyncApplication
import com.openhealth.sync.data.GoogleDashboardSnapshot
import com.openhealth.sync.data.HealthConnectManager
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.util.AppLogger
import androidx.glance.appwidget.updateAll
import com.openhealth.sync.widget.HomeWidget
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.withTimeout

private const val TAG = "SyncWorker"
private const val HUAWEI_SCOPE_UNAUTHORIZED = 50005
private const val WORKER_TIMEOUT_MS = 9L * 60L * 1000L
private const val LEASE_TTL_MS = 10L * 60L * 1000L
private const val SYNC_INTEGRITY_BACKFILL_KEY = "sync_integrity_backfill_20260723"

class SyncWorker(context: Context, workerParams: WorkerParameters) : CoroutineWorker(context, workerParams) {
    private val appContainer by lazy { (applicationContext as SyncApplication).container }
    private val prefs by lazy {
        applicationContext.getSharedPreferences(HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE)
    }

    // Shared, process-wide lease -- see AppContainer.syncRunLease for why this
    // must NOT be a fresh `SyncRunLease(...)` instance per worker.
    private val lease get() = appContainer.syncRunLease

    private val huaweiCircuitBreaker by lazy { SyncCircuitBreaker(applicationContext, SyncDependency.HUAWEI) }
    private val googleCircuitBreaker by lazy { SyncCircuitBreaker(applicationContext, SyncDependency.GOOGLE) }
    private val snapshotCache get() = appContainer.dashboardSnapshotCache
    private val achievementsStore get() = appContainer.achievementsStore
    private val goalPrefs get() = appContainer.goalPrefs

    override suspend fun doWork(): Result {
        val owner = id.toString()
        val startedAt = System.currentTimeMillis()

        AppLogger.i(TAG, "Starting resilient Huawei -> Health Connect sync owner=$owner attempt=$runAttemptCount")

        if (!lease.tryAcquire(owner, startedAt, LEASE_TTL_MS)) {
            // Another periodic/manual worker is already running. This is a safe no-op:
            // the active worker owns the catch-up window and idempotent writes.
            return Result.success(
                workDataOf("reason" to "sync_already_running")
            )
        }

        // Either breaker being open is enough to skip this cycle gracefully:
        // there is no point attempting a Huawei read if Huawei itself is the
        // thing that's been failing, nor a Health Connect write if Health
        // Connect is the one that's been failing. Each breaker still tracks
        // and recovers independently, so a Huawei-only outage does not
        // penalize a healthy Health Connect dependency's failure count, and
        // vice versa.
        if (huaweiCircuitBreaker.isOpen(startedAt) || googleCircuitBreaker.isOpen(startedAt)) {
            lease.release(owner)
            return Result.success(
                workDataOf("reason" to "circuit_breaker_open")
            )
        }

        return try {
            val outcome = withTimeout(WORKER_TIMEOUT_MS) {
                executeWithRetries()
            }

            when (outcome) {
                SyncAttemptOutcome.Success -> {
                    huaweiCircuitBreaker.recordSuccess()
                    googleCircuitBreaker.recordSuccess()
                    Result.success(workDataOf("reason" to "sync_success"))
                }

                SyncAttemptOutcome.GracefulNoop -> {
                    // Missing dependency, missing permission, or Huawei approval pending.
                    // This should not poison WorkManager with permanent failures.
                    huaweiCircuitBreaker.recordSuccess()
                    googleCircuitBreaker.recordSuccess()
                    Result.success(workDataOf("reason" to "graceful_noop"))
                }

                SyncAttemptOutcome.NonRetryableFailure -> {
                    huaweiCircuitBreaker.recordSuccess()
                    googleCircuitBreaker.recordSuccess()
                    Result.success(workDataOf("reason" to "non_retryable_user_action_required"))
                }

                is SyncAttemptOutcome.RetryableFailure -> {
                    val breaker = if (outcome.dependency == SyncDependency.HUAWEI) huaweiCircuitBreaker else googleCircuitBreaker
                    val opened = breaker.recordFailure(System.currentTimeMillis())
                    if (opened) {
                        Result.success(workDataOf("reason" to "circuit_opened_after_failures"))
                    } else {
                        Result.retry()
                    }
                }
            }
        } catch (e: CancellationException) {
            AppLogger.w(TAG, "Sync cancelled by WorkManager/system: ${e.message}")
            throw e
        } catch (t: Throwable) {
            AppLogger.e(TAG, "Unexpected sync panic recovered by worker boundary", t)
            SyncDiagnosticLog.record(prefs, "panic", t.message ?: t::class.java.simpleName)
            // An uncategorized panic could originate from either side; charge it
            // to Huawei's breaker since a Huawei read is the first step of every
            // attempt and therefore the most common source of unexpected throws.
            val opened = huaweiCircuitBreaker.recordFailure(System.currentTimeMillis())
            if (opened) {
                Result.success(workDataOf("reason" to "panic_circuit_opened"))
            } else {
                Result.retry()
            }
        } finally {
            lease.release(owner)
        }
    }

    private suspend fun executeWithRetries(): SyncAttemptOutcome {
        var lastOutcome: SyncAttemptOutcome = SyncAttemptOutcome.RetryableFailure(SyncDependency.HUAWEI)

        repeat(SyncRetryPolicy.MAX_ATTEMPTS) { attempt ->
            lastOutcome = runSingleAttempt()

            when (lastOutcome) {
                SyncAttemptOutcome.Success,
                SyncAttemptOutcome.GracefulNoop,
                SyncAttemptOutcome.NonRetryableFailure -> return lastOutcome

                is SyncAttemptOutcome.RetryableFailure -> {
                    if (attempt < SyncRetryPolicy.MAX_ATTEMPTS - 1) {
                        val delayMs = SyncRetryPolicy.nextDelayMs(attempt)
                        AppLogger.w(TAG, "Retryable sync failure; retrying in ${delayMs}ms attempt=${attempt + 2}/${SyncRetryPolicy.MAX_ATTEMPTS}")
                        delay(delayMs)
                    }
                }
            }
        }

        return lastOutcome
    }

    private suspend fun runSingleAttempt(): SyncAttemptOutcome {
        if (!HmsCoreHelper.isInstalled(applicationContext)) {
            AppLogger.e(TAG, "HMS Core is missing; sync degraded to no-op")
            return SyncAttemptOutcome.GracefulNoop
        }

        if (!HmsCoreHelper.isHuaweiHealthInstalled(applicationContext)) {
            AppLogger.e(TAG, "Huawei Health is missing; sync degraded to no-op")
            return SyncAttemptOutcome.GracefulNoop
        }

        val googleManager = appContainer.googleHealthManager
        val huaweiManager = appContainer.huaweiHealthManager

        val googlePermissionsOk = googleManager.hasAllPermissions()
        val localHuaweiAuthorized = huaweiManager.isAuthorized()

        AppLogger.i(
            TAG,
            "Sync preflight: googlePermissions=$googlePermissionsOk localHuaweiAuthorized=$localHuaweiAuthorized"
        )

        if (!googlePermissionsOk) {
            AppLogger.e(TAG, "Health Connect permissions missing; sync degraded to no-op")
            return SyncAttemptOutcome.GracefulNoop
        }

        if (huaweiManager.isPendingApproval()) {
            AppLogger.w(TAG, "Huawei Health Kit approval pending (50005); sync degraded to no-op")
            // Sprint (2026-07-16): refresh the dashboard cache/widget here too,
            // not just on a full Huawei sync success. Health Connect can
            // already contain real data from other apps (Google Fit, Samsung
            // Health, the device's own step counter) regardless of Huawei's
            // approval state -- BitLut just wasn't writing to it. Without this,
            // the Today screen still updates fine (DashboardViewModel.load()
            // does its own live readDashboardSnapshot() call, unaffected by
            // this), but the home screen widget -- which only ever reads the
            // cache this function writes -- would show "not synced yet"
            // forever until Huawei's review completes, even if there's real
            // step data sitting in Health Connect the whole time.
            refreshDashboardCacheAfterWrite(googleManager)
            return SyncAttemptOutcome.GracefulNoop
        }

        if (!localHuaweiAuthorized) {
            AppLogger.w(TAG, "Huawei not locally authorized; sync degraded to no-op")
            refreshDashboardCacheAfterWrite(googleManager)
            return SyncAttemptOutcome.GracefulNoop
        }

        val now = System.currentTimeMillis()
        val needsIntegrityBackfill = !prefs.getBoolean(SYNC_INTEGRITY_BACKFILL_KEY, false)
        if (needsIntegrityBackfill) {
            // Older builds advanced last_sync_ms even when distance failed with
            // "invalid UID". Reset once so the repaired idempotent writer gets
            // a full catch-up window instead of only the normal overlap.
            prefs.edit()
                .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, 0L)
                .putBoolean(SYNC_INTEGRITY_BACKFILL_KEY, true)
                .apply()
            AppLogger.i(TAG, "Applied one-time sync integrity backfill cursor reset")
        }

        prefs.edit()
            .putLong(HuaweiConfig.KEY_LAST_SYNC_ATTEMPT_MS, now)
            .apply()

        val window = SyncWindowPlanner.plan(prefs, now)

        AppLogger.i(
            TAG,
            "Sync window: start=${window.startTimeMs} end=${window.endTimeMs} savedLastSync=${window.savedLastSyncMs}"
        )

        return try {
            val snapshot = huaweiManager.readSnapshot(window.startTimeMs, window.endTimeMs)

            AppLogger.i(
                TAG,
                "Huawei snapshot: steps=${snapshot.steps.size}, distances=${snapshot.distances.size}, floors=${snapshot.floors.size}, elevations=${snapshot.elevations.size}, activeCalories=${snapshot.activeCalories.size}, activities=${snapshot.activities.size}"
            )

            if (snapshot.isEmpty) {
                // Do not advance last_sync_ms here. Huawei Health can return an empty window
                // before the watch has pushed late data into Huawei Health. Keeping the cursor
                // preserves catch-up correctness.
                prefs.edit()
                    .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, true)
                    .apply()

                AppLogger.w(TAG, "Huawei returned empty snapshot; preserving last_sync_ms for catch-up safety")
                return SyncAttemptOutcome.Success
            }

            val writeResult = googleManager.writeSnapshot(snapshot)

            if (writeResult.allFailed) {
                AppLogger.e(TAG, "Health Connect write failed for every category: ${writeResult.failedCategories.joinToString()}")
                SyncDiagnosticLog.record(prefs, "write_failed_all", writeResult.failedCategories.joinToString())
                // A stale/poisoned client is a likely cause of an across-the-board
                // failure. Invalidate so the next retry (this attempt's backoff,
                // or the next periodic run) gets a fresh client instead of
                // repeating the same failure forever.
                googleManager.invalidateClientCache()
                return SyncAttemptOutcome.RetryableFailure(SyncDependency.GOOGLE)
            }

            val failedWithData = writeResult.failedCategories.filterTo(mutableSetOf()) { category ->
                when (category) {
                    "steps" -> snapshot.steps.isNotEmpty()
                    "distance" -> snapshot.distances.isNotEmpty()
                    "floors" -> snapshot.floors.isNotEmpty()
                    "elevation" -> snapshot.elevations.isNotEmpty()
                    "activeCalories" -> snapshot.activeCalories.isNotEmpty()
                    "activitySessions" -> snapshot.activities.isNotEmpty()
                    else -> true
                }
            }

            if (failedWithData.isNotEmpty()) {
                // Never advance the cursor past real source records that did
                // not reach Health Connect. Stable client IDs make retrying the
                // categories that already succeeded safe and idempotent.
                AppLogger.e(
                    TAG,
                    "Health Connect rejected record-bearing categories; preserving cursor and retrying: " +
                        failedWithData.joinToString()
                )
                SyncDiagnosticLog.record(
                    prefs,
                    "write_partial_retry",
                    "failedWithData=${failedWithData.joinToString()}"
                )
                googleManager.invalidateClientCache()
                val freshSnapshot = refreshDashboardCacheAfterWrite(googleManager)
                updateAchievements(freshSnapshot)
                return SyncAttemptOutcome.RetryableFailure(SyncDependency.GOOGLE)
            }

            if (!writeResult.allSucceeded) {
                AppLogger.w(
                    TAG,
                    "Health Connect reported failures only for categories with no source records: " +
                        writeResult.failedCategories.joinToString()
                )
            }

            prefs.edit()
                .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, true)
                .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, window.endTimeMs)
                .apply()

            AppLogger.i(
                TAG,
                "Sync complete: steps=${snapshot.steps.size}, distances=${snapshot.distances.size}, floors=${snapshot.floors.size}, elevations=${snapshot.elevations.size}, activeCalories=${snapshot.activeCalories.size}, activities=${snapshot.activities.size}"
            )
            SyncDiagnosticLog.record(prefs, "sync_success", "steps=${snapshot.steps.size} distances=${snapshot.distances.size}")

            val freshSnapshot = refreshDashboardCacheAfterWrite(googleManager)
            updateAchievements(freshSnapshot)

            SyncAttemptOutcome.Success
        } catch (e: SecurityException) {
            if (e.message?.contains(HUAWEI_SCOPE_UNAUTHORIZED.toString()) == true) {
                huaweiManager.markAppGalleryVerificationRequired()
                AppLogger.e(
                    TAG,
                    "Huawei Health Kit blocked import with 50005. AppGallery Health Kit approval/cache is still pending for this package/release SHA-256/scope set.",
                    e
                )
                SyncDiagnosticLog.record(prefs, "huawei_50005", "AppGallery Health Kit approval pending")
                return SyncAttemptOutcome.NonRetryableFailure
            }

            AppLogger.e(
                TAG,
                "Security failure during sync. User action is required: re-check Health Connect/Huawei permissions.",
                e
            )
            SyncDiagnosticLog.record(prefs, "security_exception", e.message ?: "")
            SyncAttemptOutcome.NonRetryableFailure
        } catch (e: IllegalArgumentException) {
            AppLogger.e(TAG, "Invalid sync state; resetting last_sync_ms for self-healing", e)
            SyncDiagnosticLog.record(prefs, "illegal_argument_reset_cursor", e.message ?: "")
            prefs.edit()
                .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, 0L)
                .apply()
            SyncAttemptOutcome.RetryableFailure(SyncDependency.HUAWEI)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "Transient Huawei/Health Connect sync failure", e)
            SyncDiagnosticLog.record(prefs, "transient_failure", e.message ?: e::class.java.simpleName)
            SyncAttemptOutcome.RetryableFailure(SyncDependency.HUAWEI)
        }
    }

    /**
     * After a successful Huawei -> Health Connect write, also refresh the local
     * dashboard snapshot cache. Without this, periodic background sync (every
     * ~30 minutes) would keep Health Connect itself up to date, but the app's
     * cold-start cache would only ever be refreshed when the user had the app
     * open -- defeating the point of background sync from the user's
     * perspective ("data never seems to update unless I open the app").
     *
     * Best-effort only: any failure here is logged and swallowed so it can
     * never turn a successful Health Connect write into a retried/failed
     * WorkManager run. Returns the fresh snapshot (or null on failure) so the
     * caller can reuse it for achievements tracking without a second read.
     */
    private suspend fun refreshDashboardCacheAfterWrite(googleManager: HealthConnectManager): GoogleDashboardSnapshot? {
        return try {
            val freshSnapshot = googleManager.readDashboardSnapshot()
            if (freshSnapshot != null) {
                snapshotCache.save(freshSnapshot)
                AppLogger.d(TAG, "Dashboard snapshot cache refreshed after background sync")
                // Sprint (2026-07-14): the home screen widget reads this same
                // cache (see HomeWidget.kt) rather than calling Health Connect
                // itself, so it needs an explicit nudge to re-render with the
                // now-fresh numbers -- Glance widgets don't observe
                // SharedPreferences changes on their own. Runs after every
                // successful sync regardless of trigger (periodic, the
                // Settings "Sync now" button, or a tap on the widget itself),
                // since they all funnel through this one function -- a single
                // source of truth instead of updating the widget separately
                // from each trigger site.
                HomeWidget().updateAll(applicationContext)
            }
            freshSnapshot
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to refresh dashboard cache after background sync: ${e.message}", e)
            null
        }
    }

    /**
     * Updates activity-only personal records and the daily-goal streak from
     * the freshly-synced snapshot (v1.9.12, sprint 4). Best-effort: any
     * failure here is logged and swallowed for the same reason as the cache
     * refresh above -- achievement bookkeeping must never turn a successful
     * sync into a retried/failed WorkManager run.
     */
    private fun updateAchievements(freshSnapshot: GoogleDashboardSnapshot?) {
        if (freshSnapshot == null) return

        try {
            val today = java.time.LocalDate.now()
            val newRecords = achievementsStore.recordDailyTotals(
                date = today,
                stepsToday = freshSnapshot.stepsToday,
                distanceMetersToday = freshSnapshot.distanceMeters
            )
            if (newRecords.isNotEmpty()) {
                AppLogger.i(TAG, "New personal record(s) today: ${newRecords.joinToString()}")
                SyncDiagnosticLog.record(prefs, "new_personal_record", newRecords.joinToString())
            }

            val stepsGoal = goalPrefs.stepsGoal()
            val goalMet = stepsGoal > 0 && freshSnapshot.stepsToday >= stepsGoal
            val streak = achievementsStore.updateStreak(today, goalMet)
            AppLogger.d(TAG, "Streak after sync: current=${streak.currentStreakDays} longest=${streak.longestStreakDays}")
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to update achievements after sync: ${e.message}", e)
        }
    }
}
