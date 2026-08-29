package com.openhealth.sync.data

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.config.DataSourcePrefs
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import org.json.JSONArray
import org.json.JSONObject

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
 * product boundary.
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
class AchievementsStore(
    context: Context,
    private val dataSourcePrefs: DataSourcePrefs = DataSourcePrefs(context)
) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    private val isoDate = DateTimeFormatter.ISO_LOCAL_DATE

    // ── Personal records and accumulated activity ───────────────

    fun bestStepsDay(): PersonalRecord? = readRecord(
        sourceKey(KEY_BEST_STEPS_VALUE),
        sourceKey(KEY_BEST_STEPS_DATE)
    )

    fun bestDistanceMetersDay(): PersonalRecord? = readRecord(
        sourceKey(KEY_BEST_DISTANCE_VALUE),
        sourceKey(KEY_BEST_DISTANCE_DATE)
    )

    fun bestCaloriesDay(): PersonalRecord? = readRecord(
        sourceKey(KEY_BEST_CALORIES_VALUE),
        sourceKey(KEY_BEST_CALORIES_DATE)
    )

    fun bestElevationMetersDay(): PersonalRecord? = readRecord(
        sourceKey(KEY_BEST_ELEVATION_VALUE),
        sourceKey(KEY_BEST_ELEVATION_DATE)
    )

    fun bestWorkoutDurationMinutes(): PersonalRecord? = readRecord(
        sourceKey(KEY_BEST_WORKOUT_VALUE),
        sourceKey(KEY_BEST_WORKOUT_DATE)
    )

    /**
     * Merges a bounded live Health Connect window into a source-specific
     * local daily ledger. Repeated refreshes are idempotent: values are merged
     * by maximum for the same date, so today's growing totals do not double
     * count and a later partial read cannot erase already observed activity.
     */
    fun mergeDailyActivity(days: List<DailyActivitySummary>): Set<RecordKind> {
        if (days.isEmpty()) return emptySet()

        return try {
            val history = readHistory()
            val newRecords = mutableSetOf<RecordKind>()
            val editor = prefs.edit()

            days.forEach { incoming ->
                val merged = mergeDay(history[incoming.date], incoming)
                history[incoming.date] = merged

                if (updateRecord(editor, KEY_BEST_STEPS_VALUE, KEY_BEST_STEPS_DATE, merged.steps.toDouble(), merged.date)) {
                    newRecords.add(RecordKind.STEPS)
                }
                if (updateRecord(editor, KEY_BEST_DISTANCE_VALUE, KEY_BEST_DISTANCE_DATE, merged.distanceMeters, merged.date)) {
                    newRecords.add(RecordKind.DISTANCE)
                }
                if (updateRecord(editor, KEY_BEST_CALORIES_VALUE, KEY_BEST_CALORIES_DATE, merged.caloriesKcal, merged.date)) {
                    newRecords.add(RecordKind.CALORIES)
                }
                if (updateRecord(editor, KEY_BEST_ELEVATION_VALUE, KEY_BEST_ELEVATION_DATE, merged.elevationMeters, merged.date)) {
                    newRecords.add(RecordKind.ELEVATION)
                }
                if (updateRecord(editor, KEY_BEST_WORKOUT_VALUE, KEY_BEST_WORKOUT_DATE, merged.longestWorkoutMinutes.toDouble(), merged.date)) {
                    newRecords.add(RecordKind.WORKOUT_DURATION)
                }
            }

            editor
                .putString(sourceKey(KEY_DAILY_HISTORY), historyToJson(history).toString())
                .apply()
            newRecords
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to merge accumulated activity: ${e.message}", e)
            emptySet()
        }
    }

    /** Backward-compatible entry point used by older sync paths. */
    fun recordDailyTotals(
        date: LocalDate,
        stepsToday: Long,
        distanceMetersToday: Double,
        caloriesKcalToday: Double = 0.0,
        elevationMetersToday: Double = 0.0,
        longestWorkoutMinutesToday: Long = 0L
    ): Set<RecordKind> = mergeDailyActivity(
        listOf(
            DailyActivitySummary(
                date = date,
                steps = stepsToday,
                distanceMeters = distanceMetersToday,
                caloriesKcal = caloriesKcalToday,
                elevationMeters = elevationMetersToday,
                longestWorkoutMinutes = longestWorkoutMinutesToday
            )
        )
    )

    private fun mergeDay(existing: DailyActivitySummary?, incoming: DailyActivitySummary): DailyActivitySummary {
        if (existing == null) return incoming
        return DailyActivitySummary(
            date = incoming.date,
            steps = maxOf(existing.steps, incoming.steps),
            distanceMeters = maxOf(existing.distanceMeters, incoming.distanceMeters),
            caloriesKcal = maxOf(existing.caloriesKcal, incoming.caloriesKcal),
            elevationMeters = maxOf(existing.elevationMeters, incoming.elevationMeters),
            floors = maxOf(existing.floors, incoming.floors),
            workoutMinutes = maxOf(existing.workoutMinutes, incoming.workoutMinutes),
            workoutCount = maxOf(existing.workoutCount, incoming.workoutCount),
            longestWorkoutMinutes = maxOf(existing.longestWorkoutMinutes, incoming.longestWorkoutMinutes)
        )
    }

    private fun updateRecord(
        editor: SharedPreferences.Editor,
        valueKeyBase: String,
        dateKeyBase: String,
        value: Double,
        date: LocalDate
    ): Boolean {
        if (value <= 0.0) return false
        val valueKey = sourceKey(valueKeyBase)
        val dateKey = sourceKey(dateKeyBase)
        val current = prefs.getFloat(valueKey, 0f).toDouble()
        if (value <= current) return false
        editor.putFloat(valueKey, value.toFloat())
        editor.putString(dateKey, date.format(isoDate))
        return true
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

    private fun readHistory(): MutableMap<LocalDate, DailyActivitySummary> {
        val raw = prefs.getString(sourceKey(KEY_DAILY_HISTORY), null) ?: return linkedMapOf()
        return try {
            val array = JSONArray(raw)
            val out = linkedMapOf<LocalDate, DailyActivitySummary>()
            for (i in 0 until array.length()) {
                val item = array.optJSONObject(i) ?: continue
                val date = LocalDate.parse(item.optString("date"), isoDate)
                out[date] = DailyActivitySummary(
                    date = date,
                    steps = item.optLong("steps", 0L),
                    distanceMeters = item.optDouble("distanceMeters", 0.0),
                    caloriesKcal = item.optDouble("caloriesKcal", 0.0),
                    elevationMeters = item.optDouble("elevationMeters", 0.0),
                    floors = item.optDouble("floors", 0.0),
                    workoutMinutes = item.optLong("workoutMinutes", 0L),
                    workoutCount = item.optInt("workoutCount", 0),
                    longestWorkoutMinutes = item.optLong("longestWorkoutMinutes", 0L)
                )
            }
            out
        } catch (e: Exception) {
            AppLogger.e(TAG, "Corrupt accumulated activity history; resetting: ${e.message}", e)
            linkedMapOf()
        }
    }

    private fun historyToJson(history: Map<LocalDate, DailyActivitySummary>): JSONArray {
        val array = JSONArray()
        history.values.sortedBy { it.date }.forEach { day ->
            array.put(JSONObject().apply {
                put("date", day.date.format(isoDate))
                put("steps", day.steps)
                put("distanceMeters", day.distanceMeters)
                put("caloriesKcal", day.caloriesKcal)
                put("elevationMeters", day.elevationMeters)
                put("floors", day.floors)
                put("workoutMinutes", day.workoutMinutes)
                put("workoutCount", day.workoutCount)
                put("longestWorkoutMinutes", day.longestWorkoutMinutes)
            })
        }
        return array
    }

    // ── Streak ─────────────────────────────────────────────────────────

    fun readStreak(): StreakState {
        val current = prefs.getInt(sourceKey(KEY_STREAK_CURRENT), 0)
        val longest = prefs.getInt(sourceKey(KEY_STREAK_LONGEST), 0)
        val lastDateStr = prefs.getString(sourceKey(KEY_STREAK_LAST_DATE), null)
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
                .putInt(sourceKey(KEY_STREAK_CURRENT), currentStreakDays)
                .putInt(sourceKey(KEY_STREAK_LONGEST), longestStreakDays)
                .putString(sourceKey(KEY_STREAK_LAST_DATE), lastCountedDate.format(isoDate))
                .apply()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to persist streak: ${e.message}", e)
        }
        return StreakState(currentStreakDays, longestStreakDays, lastCountedDate)
    }

    private fun sourceKey(base: String): String =
        "${base}_${dataSourcePrefs.selected().storageValue}"

    companion object {
        private const val KEY_BEST_STEPS_VALUE = "achv_best_steps_value"
        private const val KEY_BEST_STEPS_DATE = "achv_best_steps_date"
        private const val KEY_BEST_DISTANCE_VALUE = "achv_best_distance_value"
        private const val KEY_BEST_DISTANCE_DATE = "achv_best_distance_date"
        private const val KEY_BEST_CALORIES_VALUE = "achv_best_calories_value"
        private const val KEY_BEST_CALORIES_DATE = "achv_best_calories_date"
        private const val KEY_BEST_ELEVATION_VALUE = "achv_best_elevation_value"
        private const val KEY_BEST_ELEVATION_DATE = "achv_best_elevation_date"
        private const val KEY_BEST_WORKOUT_VALUE = "achv_best_workout_value"
        private const val KEY_BEST_WORKOUT_DATE = "achv_best_workout_date"
        private const val KEY_DAILY_HISTORY = "achv_daily_activity_history"

        private const val KEY_STREAK_CURRENT = "achv_streak_current"
        private const val KEY_STREAK_LONGEST = "achv_streak_longest"
        private const val KEY_STREAK_LAST_DATE = "achv_streak_last_date"
    }
}

enum class RecordKind { STEPS, DISTANCE, CALORIES, ELEVATION, WORKOUT_DURATION }