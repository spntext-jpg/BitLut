package com.openhealth.sync.data

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger
import java.time.LocalDate
import java.time.format.DateTimeFormatter

private const val TAG = "AchievementsStore"

/**
 * A single all-time personal record: the best day for a given metric.
 * [date] is stored as ISO-8601 (yyyy-MM-dd) for stable, locale-independent
 * persistence and easy display formatting later.
 */
data class PersonalRecord(
    val value: Double,
    val date: LocalDate
)

data class StreakState(
    val currentStreakDays: Int,
    val longestStreakDays: Int,
    val lastCountedDate: LocalDate?
)

/**
 * Activity-only achievements: personal records and goal streaks (v1.9.12,
 * sprint 4). Deliberately does not track anything outside the already
 * approved Huawei scope (steps, distance, calories, workout minutes) --
 * no sleep/heart-rate/stress records, matching the same activity-only
 * boundary enforced by DashboardWidget.
 *
 * Health Connect's own aggregate queries only cover the range you ask for;
 * there is no "give me my best
 * day ever" query. So personal records are accumulated incrementally: every
 * time a fresh dashboard snapshot is read (manual refresh or the 30-minute
 * background sync), the day's totals are compared against the stored record
 * and updated if beaten. This means a record set before the app was first
 * installed won't retroactively appear, but every day going forward is
 * captured -- and critically, this requires no new Huawei scope or Health
 * Connect permission.
 */
class AchievementsStore(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    private val isoDate = DateTimeFormatter.ISO_LOCAL_DATE

    // ── Personal records ──────────────────────────────────────────────

    fun bestStepsDay(): PersonalRecord? = readRecord(KEY_BEST_STEPS_VALUE, KEY_BEST_STEPS_DATE)

    fun bestDistanceMetersDay(): PersonalRecord? = readRecord(KEY_BEST_DISTANCE_VALUE, KEY_BEST_DISTANCE_DATE)

    /**
     * Compares today's totals against stored records and updates them if
     * beaten. Returns the set of metrics that hit a new record today, so the
     * caller (e.g. a background sync worker) can surface a celebratory
     * notification. Safe to call multiple times per day: a record is only
     * ever raised, never lowered, and calling this again today with the same
     * or lower values is a no-op.
     */
    fun recordDailyTotals(
        date: LocalDate,
        stepsToday: Long,
        distanceMetersToday: Double
    ): Set<RecordKind> {
        val newRecords = mutableSetOf<RecordKind>()

        try {
            val editor = prefs.edit()

            val currentBestSteps = prefs.getFloat(KEY_BEST_STEPS_VALUE, 0f)
            if (stepsToday > currentBestSteps) {
                editor.putFloat(KEY_BEST_STEPS_VALUE, stepsToday.toFloat())
                editor.putString(KEY_BEST_STEPS_DATE, date.format(isoDate))
                newRecords.add(RecordKind.STEPS)
            }

            val currentBestDistance = prefs.getFloat(KEY_BEST_DISTANCE_VALUE, 0f)
            if (distanceMetersToday > currentBestDistance) {
                editor.putFloat(KEY_BEST_DISTANCE_VALUE, distanceMetersToday.toFloat())
                editor.putString(KEY_BEST_DISTANCE_DATE, date.format(isoDate))
                newRecords.add(RecordKind.DISTANCE)
            }

            editor.apply()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to update personal records: ${e.message}", e)
        }

        return newRecords
    }

    private fun readRecord(valueKey: String, dateKey: String): PersonalRecord? {
        val value = prefs.getFloat(valueKey, -1f)
        val dateStr = prefs.getString(dateKey, null)
        if (value < 0f || dateStr == null) return null

        return try {
            PersonalRecord(value = value.toDouble(), date = LocalDate.parse(dateStr, isoDate))
        } catch (e: Exception) {
            AppLogger.e(TAG, "Corrupt record date for $dateKey; ignoring: ${e.message}", e)
            null
        }
    }

    // ── Streak ─────────────────────────────────────────────────────────

    fun readStreak(): StreakState {
        val current = prefs.getInt(KEY_STREAK_CURRENT, 0)
        val longest = prefs.getInt(KEY_STREAK_LONGEST, 0)
        val lastDateStr = prefs.getString(KEY_STREAK_LAST_DATE, null)
        val lastDate = try {
            lastDateStr?.let { LocalDate.parse(it, isoDate) }
        } catch (e: Exception) {
            AppLogger.e(TAG, "Corrupt streak last-counted date; resetting: ${e.message}", e)
            null
        }
        return StreakState(current, longest, lastDate)
    }

    /**
     * Updates the streak given whether [date]'s goal was met. Idempotent per
     * day: calling this more than once for the same [date] does not double
     * count. A streak breaks (resets to 0 or 1) if [date] is more than one
     * day after [StreakState.lastCountedDate] and the goal wasn't met on the
     * skipped day(s) -- in practice this simply means "yesterday or today
     * continues the streak; any earlier gap breaks it".
     */
    fun updateStreak(date: LocalDate, goalMet: Boolean): StreakState {
        val state = readStreak()

        if (state.lastCountedDate == date) {
            // Already counted today (e.g. a second sync in the same day);
            // don't double-increment, but do allow a late goal completion
            // to upgrade a previously-missed day within the same sync cycle.
            if (goalMet && state.currentStreakDays == 0) {
                return persistStreak(currentStreakDays = 1, longestStreakDays = maxOf(state.longestStreakDays, 1), lastCountedDate = date)
            }
            return state
        }

        val isConsecutiveDay = state.lastCountedDate != null && date == state.lastCountedDate.plusDays(1)

        val newCurrent = when {
            !goalMet -> 0
            isConsecutiveDay -> state.currentStreakDays + 1
            else -> 1 // First day, or a gap of more than one day resets the streak.
        }

        val newLongest = maxOf(state.longestStreakDays, newCurrent)

        return persistStreak(currentStreakDays = newCurrent, longestStreakDays = newLongest, lastCountedDate = date)
    }

    private fun persistStreak(currentStreakDays: Int, longestStreakDays: Int, lastCountedDate: LocalDate): StreakState {
        try {
            prefs.edit()
                .putInt(KEY_STREAK_CURRENT, currentStreakDays)
                .putInt(KEY_STREAK_LONGEST, longestStreakDays)
                .putString(KEY_STREAK_LAST_DATE, lastCountedDate.format(isoDate))
                .apply()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to persist streak: ${e.message}", e)
        }
        return StreakState(currentStreakDays, longestStreakDays, lastCountedDate)
    }

    companion object {
        private const val KEY_BEST_STEPS_VALUE = "achv_best_steps_value"
        private const val KEY_BEST_STEPS_DATE = "achv_best_steps_date"
        private const val KEY_BEST_DISTANCE_VALUE = "achv_best_distance_value"
        private const val KEY_BEST_DISTANCE_DATE = "achv_best_distance_date"

        private const val KEY_STREAK_CURRENT = "achv_streak_current"
        private const val KEY_STREAK_LONGEST = "achv_streak_longest"
        private const val KEY_STREAK_LAST_DATE = "achv_streak_last_date"
    }
}

enum class RecordKind { STEPS, DISTANCE }
