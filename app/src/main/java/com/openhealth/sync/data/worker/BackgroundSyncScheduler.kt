package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OutOfQuotaPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.time.Duration
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.ZoneId
import java.util.UUID
import java.util.concurrent.TimeUnit

private const val TAG = "BackgroundSyncScheduler"

object BackgroundSyncScheduler {
    const val UNIQUE_SYNC_NOW = "bitlut_sync_now_v2"
    private const val LEGACY_UNIQUE_SYNC_NOW = "bitlut_sync_now"
    const val UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync_v2"
    private const val LEGACY_UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync"
    const val UNIQUE_EVENING_REMINDER = "bitlut_evening_reminder"

    private const val KEY_MANUAL_QUEUE_V2_MIGRATED = "manual_sync_queue_v2_migrated"
    private const val KEY_PERIODIC_SYNC_V2_MIGRATED = "periodic_sync_v2_migrated"
    const val SYNC_INTERVAL_MINUTES = 30L
    private const val SYNC_FLEX_MINUTES = 5L
    private const val INITIAL_BACKOFF_MINUTES = 10L
    private val immediateEnqueueMutex = Mutex()
    private val EVENING_REMINDER_HOUR = LocalTime.of(20, 0)

    private fun syncConstraints(): Constraints =
        Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

    fun schedulePeriodic(context: Context) {
        clearLegacyManualQueueOnce(context)
        clearLegacyPeriodicSyncOnce(context)

        val request = PeriodicWorkRequestBuilder<SyncWorker>(
            SYNC_INTERVAL_MINUTES,
            TimeUnit.MINUTES,
            SYNC_FLEX_MINUTES,
            TimeUnit.MINUTES
        )
            .setConstraints(syncConstraints())
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, INITIAL_BACKOFF_MINUTES, TimeUnit.MINUTES)
            .addTag(HuaweiConfig.SYNC_WORKER_TAG)
            .addTag(HuaweiConfig.SYNC_ACTIVITY_TAG)
            .build()

        // schedulePeriodic() runs on every single cold launch (from
        // MainActivity.onCreate). ExistingPeriodicWorkPolicy.UPDATE
        // re-applies the request even when it is byte-for-byte identical to
        // what's already scheduled -- and WorkManager can cancel a
        // currently RUNNING instance of that periodic work to do so. A real
        // device log showed exactly this: "Sync cancelled by
        // WorkManager/system: Job was cancelled" firing in the same second
        // as schedulePeriodic()'s own log line, immediately followed by a
        // retry. KEEP is a true no-op when a non-cancelled
        // UNIQUE_PERIODIC_SYNC already exists, so it never touches an
        // in-flight run. clearLegacyPeriodicSyncOnce() above migrates any
        // existing installs off the old UPDATE-scheduled work once; if
        // SYNC_INTERVAL_MINUTES/constraints/backoff ever need to change in
        // a future release, bump UNIQUE_PERIODIC_SYNC to a new name (same
        // versioned-migration pattern) so existing installs adopt the new
        // schedule cleanly instead of relying on UPDATE to change a request
        // mid-run.
        WorkManager.getInstance(context.applicationContext).enqueueUniquePeriodicWork(
            UNIQUE_PERIODIC_SYNC,
            ExistingPeriodicWorkPolicy.KEEP,
            request
        )

        AppLogger.i(TAG, "Scheduled periodic Huawei -> Health Connect sync every ${SYNC_INTERVAL_MINUTES} minutes")
    }

    fun scheduleEveningReminder(context: Context) {
        val initialDelay = computeInitialDelayUntilEveningReminder()
        val request = PeriodicWorkRequestBuilder<EveningReminderWorker>(24, TimeUnit.HOURS)
            .setInitialDelay(initialDelay)
            .addTag(HuaweiConfig.SYNC_WORKER_TAG)
            .build()

        WorkManager.getInstance(context.applicationContext).enqueueUniquePeriodicWork(
            UNIQUE_EVENING_REMINDER,
            ExistingPeriodicWorkPolicy.KEEP,
            request
        )
        AppLogger.i(TAG, "Scheduled evening reminder; next run in ${initialDelay.toMinutes()} minutes")
    }

    private fun clearLegacyManualQueueOnce(context: Context) {
        val appContext = context.applicationContext
        val prefs = appContext.getSharedPreferences(HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE)
        if (prefs.getBoolean(KEY_MANUAL_QUEUE_V2_MIGRATED, false)) return
        WorkManager.getInstance(appContext).cancelUniqueWork(LEGACY_UNIQUE_SYNC_NOW)
        prefs.edit().putBoolean(KEY_MANUAL_QUEUE_V2_MIGRATED, true).apply()
        AppLogger.i(TAG, "Cleared legacy manual-sync queue; migrated to $UNIQUE_SYNC_NOW")
    }

    private fun clearLegacyPeriodicSyncOnce(context: Context) {
        val appContext = context.applicationContext
        val prefs = appContext.getSharedPreferences(HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE)
        if (prefs.getBoolean(KEY_PERIODIC_SYNC_V2_MIGRATED, false)) return
        WorkManager.getInstance(appContext).cancelUniqueWork(LEGACY_UNIQUE_PERIODIC_SYNC)
        prefs.edit().putBoolean(KEY_PERIODIC_SYNC_V2_MIGRATED, true).apply()
        AppLogger.i(TAG, "Cleared legacy periodic-sync schedule; migrated to $UNIQUE_PERIODIC_SYNC")
    }

    private fun computeInitialDelayUntilEveningReminder(): Duration {
        val zone = ZoneId.systemDefault()
        val now = LocalDateTime.now(zone)
        val todayTarget = LocalDateTime.of(LocalDate.now(zone), EVENING_REMINDER_HOUR)
        val nextTarget = if (now.isBefore(todayTarget)) todayTarget else todayTarget.plusDays(1)
        return Duration.between(now, nextTarget)
    }

    suspend fun enqueueImmediateSync(context: Context): UUID = immediateEnqueueMutex.withLock {
        val appContext = context.applicationContext
        val workManager = WorkManager.getInstance(appContext)

        // Use WorkManager's Flow API rather than the Guava ListenableFuture API.
        // This keeps the operation non-blocking and avoids exposing Guava on the
        // app compile classpath.
        val activeBefore = workManager
            .getWorkInfosForUniqueWorkFlow(UNIQUE_SYNC_NOW)
            .first()
            .firstOrNull { it.isActiveManualSync() }

        if (activeBefore != null) {
            AppLogger.i(
                TAG,
                "Manual sync already active; reusing work id=${activeBefore.id} state=${activeBefore.state}"
            )
            return@withLock activeBefore.id
        }

        val request = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(syncConstraints())
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, INITIAL_BACKOFF_MINUTES, TimeUnit.MINUTES)
            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            .addTag(HuaweiConfig.SYNC_WORKER_TAG)
            .addTag(HuaweiConfig.SYNC_ACTIVITY_TAG)
            .build()

        workManager.enqueueUniqueWork(
            UNIQUE_SYNC_NOW,
            ExistingWorkPolicy.KEEP,
            request
        )

        // Wait until WorkManager exposes either our accepted request or an
        // already-active request that won a race outside this process.
        val visibleWork = workManager
            .getWorkInfosForUniqueWorkFlow(UNIQUE_SYNC_NOW)
            .first { infos ->
                infos.any { info ->
                    info.id == request.id || info.isActiveManualSync()
                }
            }

        val actual = visibleWork.firstOrNull { it.id == request.id }
            ?: visibleWork.firstOrNull { it.isActiveManualSync() }
            ?: throw IllegalStateException(
                "WorkManager accepted manual sync but no active work is observable"
            )

        AppLogger.i(
            TAG,
            "Manual Huawei -> Health Connect sync work id=${actual.id} state=${actual.state}"
        )
        actual.id
    }

    private fun WorkInfo.isActiveManualSync(): Boolean = when (state) {
        WorkInfo.State.ENQUEUED,
        WorkInfo.State.RUNNING,
        WorkInfo.State.BLOCKED -> true
        WorkInfo.State.SUCCEEDED,
        WorkInfo.State.FAILED,
        WorkInfo.State.CANCELLED -> false
    }
}
