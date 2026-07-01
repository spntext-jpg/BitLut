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
import androidx.work.WorkManager
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger
import java.util.UUID
import java.util.concurrent.TimeUnit

private const val TAG = "BackgroundSyncScheduler"

object BackgroundSyncScheduler {
    const val UNIQUE_SYNC_NOW = "bitlut_sync_now"
    const val UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync"

    const val SYNC_INTERVAL_MINUTES = 30L
    private const val SYNC_FLEX_MINUTES = 5L
    private const val INITIAL_BACKOFF_MINUTES = 10L

    private fun syncConstraints(): Constraints =
        Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

    fun schedulePeriodic(context: Context) {
        val request = PeriodicWorkRequestBuilder<SyncWorker>(
            SYNC_INTERVAL_MINUTES,
            TimeUnit.MINUTES,
            SYNC_FLEX_MINUTES,
            TimeUnit.MINUTES
        )
            .setConstraints(syncConstraints())
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                INITIAL_BACKOFF_MINUTES,
                TimeUnit.MINUTES
            )
            .addTag(HuaweiConfig.SYNC_WORKER_TAG)
            .build()

        // ExistingPeriodicWorkPolicy.UPDATE (not KEEP/REPLACE) is deliberate:
        // it lets a future app update change the periodic request's
        // constraints/backoff without requiring the existing schedule to be
        // cancelled first, while NOT resetting the next-run countdown the way
        // REPLACE would on every single app launch. Calling schedulePeriodic()
        // on every onCreate() (as MainActivity does) is therefore safe and
        // idempotent: it does not create duplicate periodic work, and it does
        // not keep pushing the 30-minute timer back every time the app opens.
        WorkManager.getInstance(context.applicationContext).enqueueUniquePeriodicWork(
            UNIQUE_PERIODIC_SYNC,
            ExistingPeriodicWorkPolicy.UPDATE,
            request
        )

        AppLogger.i(TAG, "Scheduled periodic Huawei -> Health Connect sync every ${SYNC_INTERVAL_MINUTES} minutes")
    }

    fun enqueueImmediateSync(context: Context): UUID {
        val request = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(syncConstraints())
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                INITIAL_BACKOFF_MINUTES,
                TimeUnit.MINUTES
            )
            // A manual "Sync now" / "Обновить статус" tap is an explicit,
            // foreground user action -- it should get system scheduling
            // priority instead of being queued behind ordinary background
            // work under Doze/App Standby. setExpedited requests this
            // priority; RUN_AS_NON_EXPEDITED_WORK_REQUEST is the documented
            // safe fallback if the app has exhausted its expedited-job quota
            // for the moment, so this never throws or blocks the request --
            // worst case it behaves exactly like before this change.
            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            .addTag(HuaweiConfig.SYNC_WORKER_TAG)
            .build()

        WorkManager.getInstance(context.applicationContext).enqueueUniqueWork(
            UNIQUE_SYNC_NOW,
            ExistingWorkPolicy.REPLACE,
            request
        )

        AppLogger.i(TAG, "Enqueued immediate (expedited) Huawei -> Health Connect sync: ${request.id}")
        return request.id
    }
}
