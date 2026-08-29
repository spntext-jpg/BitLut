package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig

/**
 * The one user-configurable daily goal BitLut currently exposes and consumes.
 * Keeping this steps-only avoids persisting decorative goals with no UI or
 * downstream behavior.
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

    companion object {
        private const val KEY_STEPS_GOAL = "goal_steps"

        const val DEFAULT_STEPS_GOAL = 10_000L
        val STEPS_GOAL_RANGE = 2_000L..30_000L
    }
}
