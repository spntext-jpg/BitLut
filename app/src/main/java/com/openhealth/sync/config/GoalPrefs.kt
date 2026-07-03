package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig

/**
 * User-configurable daily activity goals (v1.9.12, sprint 7). Activity-only,
 * matching the same boundary as DashboardWidget -- no sleep/heart-rate/stress
 * goals until Huawei approval scope expands.
 *
 * Defaults match what the dashboard already assumed before goals were
 * configurable (10,000 steps), so existing installs see no behavior change
 * until the person explicitly opens Settings and changes something.
 */
class GoalPrefs(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun stepsGoal(): Long = prefs.getLong(KEY_STEPS_GOAL, DEFAULT_STEPS_GOAL)
    fun setStepsGoal(value: Long) {
        require(value > 0) { "Steps goal must be positive" }
        prefs.edit().putLong(KEY_STEPS_GOAL, value).apply()
    }

    fun distanceGoalMeters(): Double = prefs.getFloat(KEY_DISTANCE_GOAL_METERS, DEFAULT_DISTANCE_GOAL_METERS.toFloat()).toDouble()
    fun setDistanceGoalMeters(value: Double) {
        require(value > 0) { "Distance goal must be positive" }
        prefs.edit().putFloat(KEY_DISTANCE_GOAL_METERS, value.toFloat()).apply()
    }

    fun activeMinutesGoal(): Int = prefs.getInt(KEY_ACTIVE_MINUTES_GOAL, DEFAULT_ACTIVE_MINUTES_GOAL)
    fun setActiveMinutesGoal(value: Int) {
        require(value > 0) { "Active minutes goal must be positive" }
        prefs.edit().putInt(KEY_ACTIVE_MINUTES_GOAL, value).apply()
    }

    fun caloriesGoalKcal(): Double = prefs.getFloat(KEY_CALORIES_GOAL, DEFAULT_CALORIES_GOAL.toFloat()).toDouble()
    fun setCaloriesGoalKcal(value: Double) {
        require(value > 0) { "Calories goal must be positive" }
        prefs.edit().putFloat(KEY_CALORIES_GOAL, value.toFloat()).apply()
    }

    companion object {
        private const val KEY_STEPS_GOAL = "goal_steps"
        private const val KEY_DISTANCE_GOAL_METERS = "goal_distance_meters"
        private const val KEY_ACTIVE_MINUTES_GOAL = "goal_active_minutes"
        private const val KEY_CALORIES_GOAL = "goal_calories_kcal"

        const val DEFAULT_STEPS_GOAL = 10_000L
        const val DEFAULT_DISTANCE_GOAL_METERS = 5_000.0
        const val DEFAULT_ACTIVE_MINUTES_GOAL = 30
        const val DEFAULT_CALORIES_GOAL = 500.0

        // Reasonable bounds for the Settings sliders/steppers -- prevents a
        // fat-fingered goal of 0 or 999999999 from producing a nonsensical
        // progress ring or an unreachable streak.
        val STEPS_GOAL_RANGE = 2_000L..30_000L
        val DISTANCE_GOAL_RANGE_METERS = 1_000.0..20_000.0
        val ACTIVE_MINUTES_GOAL_RANGE = 10..180
        val CALORIES_GOAL_RANGE = 100.0..2_000.0
    }
}
