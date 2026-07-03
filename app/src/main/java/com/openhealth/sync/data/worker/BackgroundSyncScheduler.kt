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
import java.time.Duration
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.ZoneId
import java.util.UUID
import java.util.concurrent.TimeUnit

private const val TAG = "BackgroundSyncScheduler"

object BackgroundSyncScheduler {
    const val UNIQUE_SYNC_NOW = "bitlut_sync_now"
    const val UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync"
    const val UNIQUE_EVENING_REMINDER = "bitlut_evening_reminder"

    const val SYNC_INTERVAL_MINUTES = 30L
    private const val SYNC_FLEX_MINUTES = 5L
    private const val INITIAL_BACKOFF_MINUTES = 10L

    /** 20:00 local time -- late enough that the day's activity is mostly in
     *  the books, early enough to still be actionable ("go for a short walk
     *  to close the ring") rather than arriving as a pointless post-mortem. */
    private val EVENING_REMINDER_HOUR = LocalTime.of(20, 0)

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

    /**
     * Schedules the once-daily evening reminder (v1.9.12, sprint 4).
     *
     * WorkManager's PeriodicWorkRequest has no "run at a specific wall-clock
     * time" API -- only an interval plus an optional initial delay. This
     * computes the delay until the next occurrence of [EVENING_REMINDER_HOUR]
     * (today if it hasn't passed yet, otherwise tomorrow), then repeats every
     * 24 hours from there.
     *
     * Uses [ExistingPeriodicWorkPolicy.KEEP], not UPDATE: unlike sync (where
     * re-applying the same 30-minute interval on every app launch is a
     * harmless no-op), recomputing the initial delay here every time the app
     * opens would keep shifting an already-scheduled reminder later and
     * later, since "next 20:00 from right now" changes throughout the day.
     * KEEP leaves an already-scheduled reminder alone and only schedules a
     * fresh one if none exists yet.
     */
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

    private fun computeInitialDelayUntilEveningReminder(): Duration {
        val zone = ZoneId.systemDefault()
        val now = LocalDateTime.now(zone)
        val todayTarget = LocalDateTime.of(LocalDate.now(zone), EVENING_REMINDER_HOUR)
        val nextTarget = if (now.isBefore(todayTarget)) todayTarget else todayTarget.plusDays(1)
        return Duration.between(now, nextTarget)
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
