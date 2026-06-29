package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig

/**
 * Identifies a single toggleable widget on Summary/History, for the per-widget
 * visibility switches in Settings (e.g. "hide the Sleep widget").
 */
enum class DashboardWidget(val prefKey: String) {
    STEPS("widget_visible_steps"),
    CALORIES("widget_visible_calories"),
    WORKOUT_MINUTES("widget_visible_workout_minutes"),
    ACTIVE_HOURS("widget_visible_active_hours"),
    HEART_RATE("widget_visible_heart"),
    SLEEP("widget_visible_sleep"),
    STRESS("widget_visible_stress"),
    SPO2("widget_visible_spo2"),
    WORKOUTS("widget_visible_workouts")
}

/**
 * Persists which dashboard widgets the person has chosen to show or hide, via
 * Settings toggles. Reuses the app's existing bitlut_prefs SharedPreferences file
 * (see HuaweiConfig.PREFS_NAME) rather than introducing a second preferences store.
 *
 * All widgets default to visible — a fresh install or a key that was never written
 * shows the widget, matching the behavior before this toggle existed.
 */
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
