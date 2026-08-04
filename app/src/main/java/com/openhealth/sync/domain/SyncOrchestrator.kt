package com.openhealth.sync.domain

import android.content.Context
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.Observer
import androidx.lifecycle.lifecycleScope
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.openhealth.sync.data.HealthConnectManager
import com.openhealth.sync.data.worker.BackgroundSyncScheduler
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicLong

private const val TAG = "SyncOrchestrator"
private const val MIN_INTERVAL_BETWEEN_TRIGGERS_MS = 5_000L
private val LEASE_COLLISION_RETRY_DELAYS_MS = listOf(8_000L, 12_000L)

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
            enqueueAfterPermissionCheck(lifecycleOwner, onCompleted, onDashboardRefresh)
        } catch (e: CancellationException) {
            throw e
        } catch (t: Throwable) {
            AppLogger.e(TAG, "Manual sync preflight/enqueue failed: ${t.message}", t)
            onCompleted(false)
        }
    }

    private suspend fun enqueueAfterPermissionCheck(
        lifecycleOwner: LifecycleOwner,
        onCompleted: (Boolean) -> Unit,
        onDashboardRefresh: () -> Unit
    ) {
        val workId = BackgroundSyncScheduler.enqueueImmediateSync(appContext)
        val liveData = workManager.getWorkInfoByIdLiveData(workId)
        val observer = object : Observer<WorkInfo?> {
            override fun onChanged(info: WorkInfo?) {
                when (info?.state) {
                    WorkInfo.State.SUCCEEDED -> {
                        liveData.removeObserver(this)
                        val reason = info.outputData.getString("reason")
                        if (reason == "sync_already_running") {
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
                        liveData.removeObserver(this)
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
        liveData.observe(lifecycleOwner, observer)
    }
}
