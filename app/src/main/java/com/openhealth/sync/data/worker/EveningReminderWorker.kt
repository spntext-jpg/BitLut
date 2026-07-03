package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.openhealth.sync.R
import com.openhealth.sync.SyncApplication
import com.openhealth.sync.config.GoalPrefs
import com.openhealth.sync.data.AchievementsStore
import com.openhealth.sync.notifications.NotificationHelper
import com.openhealth.sync.util.AppLogger
import kotlin.math.max

private const val TAG = "EveningReminderWorker"

/**
 * Once-daily evening check-in (v1.9.12, sprint 4): looks at the cached
 * dashboard snapshot (already kept fresh by the 30-minute SyncWorker -- this
 * worker does not perform its own Health Connect read, it only reads what's
 * already been synced) and posts one of:
 *  - a nudge if the person is close to their steps goal ("1,200 steps to go")
 *  - a celebration if the goal was already met
 *  - nothing at all if there's no meaningful signal (e.g. no data yet, or
 *    already far past the goal with nothing new to say)
 *
 * Deliberately conservative about when to notify: this worker only ever
 * posts at most one notification per run, and only when there's something
 * genuinely useful to say -- unlike a naive "remind every evening no matter
 * what" implementation, which trains people to dismiss/ignore the channel.
 */
class EveningReminderWorker(context: Context, workerParams: WorkerParameters) : CoroutineWorker(context, workerParams) {

    private val appContainer by lazy { (applicationContext as SyncApplication).container }
    private val goalPrefs by lazy { GoalPrefs(applicationContext) }
    private val achievementsStore by lazy { AchievementsStore(applicationContext) }

    override suspend fun doWork(): Result {
        return try {
            val cached = appContainer.dashboardSnapshotCache.load()
            if (cached == null) {
                AppLogger.d(TAG, "No cached snapshot yet; skipping evening reminder")
                return Result.success(workDataOf("reason" to "no_data_yet"))
            }

            // Don't nag with stale data: if the cache is more than a few hours
            // old, background sync itself is likely having trouble (already
            // covered by SyncWorker's own self-healing), and an evening
            // reminder built on hours-old numbers would be actively wrong.
            val ageMs = System.currentTimeMillis() - cached.savedAtMs
            if (ageMs > STALE_THRESHOLD_MS) {
                AppLogger.d(TAG, "Cached snapshot too stale (${ageMs}ms); skipping evening reminder")
                return Result.success(workDataOf("reason" to "stale_data"))
            }

            val stepsGoal = goalPrefs.stepsGoal()
            val stepsToday = cached.snapshot.stepsToday
            val remaining = max(0L, stepsGoal - stepsToday)

            val streak = achievementsStore.readStreak()

            when {
                stepsToday >= stepsGoal -> {
                    val title = applicationContext.getString(R.string.notif_goal_reached_title)
                    val body = if (streak.currentStreakDays > 1) {
                        applicationContext.getString(R.string.notif_goal_reached_with_streak_body, streak.currentStreakDays)
                    } else {
                        applicationContext.getString(R.string.notif_goal_reached_body)
                    }
                    NotificationHelper.postEveningReminder(applicationContext, title, body)
                }

                remaining in 1..CLOSE_TO_GOAL_THRESHOLD -> {
                    val title = applicationContext.getString(R.string.notif_almost_there_title)
                    val body = applicationContext.getString(R.string.notif_almost_there_body, remaining)
                    NotificationHelper.postEveningReminder(applicationContext, title, body)
                }

                else -> {
                    // Not close enough to the goal for a nudge to feel
                    // encouraging rather than nagging; stay quiet today.
                    AppLogger.d(TAG, "No evening reminder needed today (remaining=$remaining)")
                }
            }

            Result.success(workDataOf("reason" to "evening_check_complete"))
        } catch (e: Exception) {
            // Notifications are a nice-to-have layer; never retry-storm this
            // worker or let it affect the core sync pipeline's health.
            AppLogger.e(TAG, "Evening reminder check failed: ${e.message}", e)
            Result.success(workDataOf("reason" to "error_swallowed"))
        }
    }

    companion object {
        private const val STALE_THRESHOLD_MS = 6L * 60L * 60L * 1000L
        private const val CLOSE_TO_GOAL_THRESHOLD = 3000L
    }
}
