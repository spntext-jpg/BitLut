package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig

/**
 * Activity-only dashboard widget visibility for BitLut v1.9.6.
 *
 * Unsupported optional metrics are intentionally absent:
 * pulse, sleep, stress, SpO2, HRV and Activity Intensity.
 */
enum class DashboardWidget(val prefKey: String) {
    STEPS("widget_visible_steps"),
    CALORIES("widget_visible_calories"),
    WORKOUT_MINUTES("widget_visible_workout_minutes"),
    ACTIVE_HOURS("widget_visible_active_hours"),
    WORKOUTS("widget_visible_workouts")
}

class WidgetVisibilityPrefs(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun isVisible(widget: DashboardWidget): Boolean =
        prefs.getBoolean(widget.prefKey, true)

    fun setVisible(widget: DashboardWidget, visible: Boolean) {
        prefs.edit().putBoolean(widget.prefKey, visible).apply()
    }

    fun snapshot(): Map<DashboardWidget, Boolean> =
        DashboardWidget.entries.associateWith { isVisible(it) }
}
