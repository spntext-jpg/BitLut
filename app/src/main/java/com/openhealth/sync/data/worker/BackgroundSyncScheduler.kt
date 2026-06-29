package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
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
            .addTag(HuaweiConfig.SYNC_WORKER_TAG)
            .build()

        WorkManager.getInstance(context.applicationContext).enqueueUniqueWork(
            UNIQUE_SYNC_NOW,
            ExistingWorkPolicy.REPLACE,
            request
        )

        AppLogger.i(TAG, "Enqueued immediate Huawei -> Health Connect sync: ${request.id}")
        return request.id
    }
}
