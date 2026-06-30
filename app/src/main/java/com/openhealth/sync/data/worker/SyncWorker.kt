package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.openhealth.sync.SyncApplication
import com.openhealth.sync.data.DashboardSnapshotCache
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.withTimeout

private const val TAG = "SyncWorker"
private const val HUAWEI_SCOPE_UNAUTHORIZED = 50005
private const val WORKER_TIMEOUT_MS = 9L * 60L * 1000L
private const val LEASE_TTL_MS = 10L * 60L * 1000L

class SyncWorker(context: Context, workerParams: WorkerParameters) : CoroutineWorker(context, workerParams) {
    private val appContainer by lazy { (applicationContext as SyncApplication).container }
    private val prefs by lazy {
        applicationContext.getSharedPreferences(HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE)
    }
    private val lease by lazy { SyncRunLease(applicationContext) }
    private val circuitBreaker by lazy { SyncCircuitBreaker(applicationContext) }
    private val snapshotCache by lazy { DashboardSnapshotCache(applicationContext) }

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

        if (circuitBreaker.isOpen(startedAt)) {
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
                    circuitBreaker.recordSuccess()
                    Result.success(workDataOf("reason" to "sync_success"))
                }

                SyncAttemptOutcome.GracefulNoop -> {
                    // Missing dependency, missing permission, or Huawei approval pending.
                    // This should not poison WorkManager with permanent failures.
                    circuitBreaker.recordSuccess()
                    Result.success(workDataOf("reason" to "graceful_noop"))
                }

                SyncAttemptOutcome.NonRetryableFailure -> {
                    circuitBreaker.recordSuccess()
                    Result.success(workDataOf("reason" to "non_retryable_user_action_required"))
                }

                SyncAttemptOutcome.RetryableFailure -> {
                    val opened = circuitBreaker.recordFailure(System.currentTimeMillis())
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
            val opened = circuitBreaker.recordFailure(System.currentTimeMillis())
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
        var lastOutcome: SyncAttemptOutcome = SyncAttemptOutcome.RetryableFailure

        repeat(SyncRetryPolicy.MAX_ATTEMPTS) { attempt ->
            lastOutcome = runSingleAttempt()

            when (lastOutcome) {
                SyncAttemptOutcome.Success,
                SyncAttemptOutcome.GracefulNoop,
                SyncAttemptOutcome.NonRetryableFailure -> return lastOutcome

                SyncAttemptOutcome.RetryableFailure -> {
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
            return SyncAttemptOutcome.GracefulNoop
        }

        if (!localHuaweiAuthorized) {
            AppLogger.w(TAG, "Huawei not locally authorized; sync degraded to no-op")
            return SyncAttemptOutcome.GracefulNoop
        }

        val now = System.currentTimeMillis()
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

            val writeOk = googleManager.writeSnapshot(snapshot)

            if (!writeOk) {
                AppLogger.e(TAG, "Health Connect write returned partial/failed result")
                return SyncAttemptOutcome.RetryableFailure
            }

            prefs.edit()
                .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, true)
                .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, window.endTimeMs)
                .apply()

            AppLogger.i(
                TAG,
                "Sync complete: steps=${snapshot.steps.size}, distances=${snapshot.distances.size}, floors=${snapshot.floors.size}, elevations=${snapshot.elevations.size}, activeCalories=${snapshot.activeCalories.size}, activities=${snapshot.activities.size}"
            )

            refreshDashboardCacheAfterWrite(googleManager)

            SyncAttemptOutcome.Success
        } catch (e: SecurityException) {
            if (e.message?.contains(HUAWEI_SCOPE_UNAUTHORIZED.toString()) == true) {
                huaweiManager.markAppGalleryVerificationRequired()
                AppLogger.e(
                    TAG,
                    "Huawei Health Kit blocked import with 50005. AppGallery Health Kit approval/cache is still pending for this package/release SHA-256/scope set.",
                    e
                )
                return SyncAttemptOutcome.NonRetryableFailure
            }

            AppLogger.e(
                TAG,
                "Security failure during sync. User action is required: re-check Health Connect/Huawei permissions.",
                e
            )
            SyncAttemptOutcome.NonRetryableFailure
        } catch (e: IllegalArgumentException) {
            AppLogger.e(TAG, "Invalid sync state; resetting last_sync_ms for self-healing", e)
            prefs.edit()
                .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, 0L)
                .apply()
            SyncAttemptOutcome.RetryableFailure
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "Transient Huawei/Health Connect sync failure", e)
            SyncAttemptOutcome.RetryableFailure
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
     * WorkManager run.
     */
    private suspend fun refreshDashboardCacheAfterWrite(googleManager: com.openhealth.sync.data.HealthConnectManager) {
        try {
            val freshSnapshot = googleManager.readDashboardSnapshot(daysBack = 7)
            if (freshSnapshot != null) {
                snapshotCache.save(freshSnapshot)
                AppLogger.d(TAG, "Dashboard snapshot cache refreshed after background sync")
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to refresh dashboard cache after background sync: ${e.message}", e)
        }
    }
}
