package com.openhealth.sync.domain

import android.content.Context
import androidx.lifecycle.LifecycleOwner
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.openhealth.sync.data.HealthConnectManager
import com.openhealth.sync.data.worker.BackgroundSyncScheduler
import com.openhealth.sync.util.AppLogger
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.CancellationException
import java.util.concurrent.atomic.AtomicLong
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private const val TAG = "SyncOrchestrator"

/** Sprint (2026-07-10): a real device log showed 11+ manual/resume sync
 *  triggers inside 60 seconds, some just 1 second apart -- each one a full
 *  WorkManager enqueue plus a dashboard reload, which is exactly what blew
 *  through Health Connect's own rate limit and turned every subsequent read
 *  into a failure. Debouncing repeat triggers this close together is a
 *  direct, targeted fix for that -- it does not affect the 30-minute
 *  periodic worker, which is scheduled independently of this path. */
private const val MIN_INTERVAL_BETWEEN_TRIGGERS_MS = 5_000L

/** Grace periods for the lease-collision fix (sprint 2026-07-08): if this
 *  request's own sync was a no-op because a different worker already held
 *  the lease, refresh again after each of these delays instead of once,
 *  immediately, before that other worker's write has actually landed. */
private val LEASE_COLLISION_RETRY_DELAYS_MS = listOf(8_000L, 12_000L)

/**
 * UI-safe sync orchestration boundary.
 *
 * MainActivity should not know WorkManager details or sync permission preflight.
 * The orchestrator owns those mechanics and reports lifecycle-safe callbacks back
 * to the Activity/ViewModel layer.
 */
class SyncOrchestrator(
    context: Context,
    private val googleManager: HealthConnectManager
) {
    private val appContext = context.applicationContext
    private val workManager: WorkManager = WorkManager.getInstance(appContext)
    private val lastTriggeredAtMs = AtomicLong(0L)

    fun schedulePeriodic() {
        BackgroundSyncScheduler.schedulePeriodic(appContext)
    }

    suspend fun triggerImmediateSync(
        lifecycleOwner: LifecycleOwner,
        onStarted: () -> Unit,
        onMissingPermissions: (Set<String>) -> Unit,
        onCompleted: (Boolean) -> Unit,
        onDashboardRefresh: () -> Unit
    ) {
        val now = System.currentTimeMillis()
        val elapsedSinceLast = now - lastTriggeredAtMs.get()
        if (elapsedSinceLast < MIN_INTERVAL_BETWEEN_TRIGGERS_MS) {
            AppLogger.i(TAG, "Sync trigger debounced (last one ${elapsedSinceLast}ms ago)")
            return
        }
        lastTriggeredAtMs.set(now)

        onStarted()

        try {
            val missing = googleManager.missingRequiredPermissions()
            if (missing.isNotEmpty()) {
                AppLogger.w(TAG, "Manual sync blocked by missing Health Connect permissions: $missing")
                onCompleted(false)
                onMissingPermissions(missing)
                return
            }

            enqueueAfterPermissionCheck(
                lifecycleOwner = lifecycleOwner,
                onCompleted = onCompleted,
                onDashboardRefresh = onDashboardRefresh
            )
        } catch (e: CancellationException) {
            throw e
        } catch (t: Throwable) {
            AppLogger.e(TAG, "Manual sync preflight failed: ${t.message}", t)
            onCompleted(false)
        }
    }

    private fun enqueueAfterPermissionCheck(
        lifecycleOwner: LifecycleOwner,
        onCompleted: (Boolean) -> Unit,
        onDashboardRefresh: () -> Unit
    ) {
        val requestId = BackgroundSyncScheduler.enqueueImmediateSync(appContext)

        workManager.getWorkInfoByIdLiveData(requestId).observe(lifecycleOwner) { info ->
            when (info?.state) {
                WorkInfo.State.SUCCEEDED -> {
                    val reason = info.outputData.getString("reason")
                    if (reason == "sync_already_running") {
                        // This request did no real work itself -- a different worker
                        // (periodic, or another manual/launch trigger) already held the
                        // process-wide SyncRunLease and is doing the actual Huawei ->
                        // Health Connect write. WorkManager still reports THIS request as
                        // SUCCEEDED almost immediately, well before that other write
                        // finishes, so refreshing right now would just re-read the same
                        // stale data. Give the real sync a couple of grace periods to
                        // finish, refreshing again after each.
                        AppLogger.i(TAG, "Sync deferred to an already-running sync; scheduling follow-up refreshes")
                        onCompleted(true)
                        lifecycleOwner.lifecycleScope.launch {
                            for (delayMs in LEASE_COLLISION_RETRY_DELAYS_MS) {
                                delay(delayMs)
                                onDashboardRefresh()
                            }
                        }
                    } else {
                        AppLogger.i(TAG, "Manual sync completed successfully (reason=$reason)")
                        onCompleted(true)
                        onDashboardRefresh()
                    }
                }

                WorkInfo.State.FAILED,
                WorkInfo.State.CANCELLED -> {
                    AppLogger.e(TAG, "Manual sync failed state=${info.state}")
                    onCompleted(false)
                }

                WorkInfo.State.ENQUEUED,
                WorkInfo.State.RUNNING,
                WorkInfo.State.BLOCKED,
                null -> Unit
            }
        }
    }
}
