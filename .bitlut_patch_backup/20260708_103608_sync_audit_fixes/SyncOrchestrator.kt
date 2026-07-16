package com.openhealth.sync.domain

import android.content.Context
import androidx.lifecycle.LifecycleOwner
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.openhealth.sync.data.HealthConnectManager
import com.openhealth.sync.data.worker.BackgroundSyncScheduler
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.CancellationException

private const val TAG = "SyncOrchestrator"

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
                    AppLogger.i(TAG, "Manual sync completed successfully")
                    onCompleted(true)
                    onDashboardRefresh()
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
