package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.remote.HuaweiConfig

/**
 * Lets the person exclude specific workout types, or workouts shorter than a
 * minimum duration, from being written to Health Connect as discrete
 * ExerciseSessionRecord entries -- e.g. "don't sync walks under 5 minutes".
 *
 * This only filters the workout SESSION entries themselves. Steps, distance,
 * and calories for that same time window come from Huawei's separate
 * continuous data streams (see GoogleHealthManager.writeSnapshot()) and are
 * completely unaffected by this filter -- a filtered-out walk still counts
 * toward the day's step total, it just doesn't show up as its own workout
 * card. No new Huawei scope or Health Connect permission is involved: this
 * is purely app-side filtering of data that's already being read.
 *
 * Defaults to "everything syncs" (0-minute minimum, nothing excluded), so
 * existing installs see no behavior change until the person explicitly
 * opens Settings and changes something.
 */
class WorkoutFilterPrefs(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun minDurationMinutes(): Int = prefs.getInt(KEY_MIN_DURATION_MINUTES, 0)

    fun setMinDurationMinutes(value: Int) {
        require(value >= 0) { "Minimum duration cannot be negative" }
        prefs.edit().putInt(KEY_MIN_DURATION_MINUTES, value).apply()
    }

    fun excludedExerciseTypes(): Set<Int> =
        prefs.getStringSet(KEY_EXCLUDED_EXERCISE_TYPES, emptySet())
            .orEmpty()
            .mapNotNull { it.toIntOrNull() }
            .toSet()

    fun setExcludedExerciseTypes(types: Set<Int>) {
        prefs.edit()
            .putStringSet(KEY_EXCLUDED_EXERCISE_TYPES, types.map { it.toString() }.toSet())
            .apply()
    }

    /** Applied right before a freshly-read batch of sessions is written to Health Connect. */
    fun apply(sessions: List<ActivitySessionData>): List<ActivitySessionData> {
        val minDurationMs = minDurationMinutes() * 60_000L
        val excluded = excludedExerciseTypes()
        if (minDurationMs <= 0L && excluded.isEmpty()) return sessions
        return sessions.filter { session ->
            val durationMs = session.endTimeMs - session.startTimeMs
            durationMs >= minDurationMs && session.exerciseType !in excluded
        }
    }

    companion object {
        private const val KEY_MIN_DURATION_MINUTES = "workout_filter_min_duration_minutes"
        private const val KEY_EXCLUDED_EXERCISE_TYPES = "workout_filter_excluded_exercise_types"

        /** Preset chips offered in Settings for the minimum-duration filter. */
        val MIN_DURATION_PRESETS_MINUTES = listOf(0, 5, 10, 15, 30)
    }
}
