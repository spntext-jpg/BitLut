package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig

/**
 * The reorderable/hideable cards on the Today screen, below the pinned Steps
 * hero card (Steps itself is not part of this list -- it always stays first,
 * it's the screen's anchor). Order here is only the fallback DEFAULT_ORDER;
 * the person's actual order/visibility lives in DashboardCardLayoutPrefs.
 */
enum class DashboardCardType(val key: String) {
    ACTIVITY_RINGS("activity_rings"),
    WORKOUT_LATEST("workout_latest"),
    WORKOUT_PREVIOUS("workout_previous"),
    LAST_7_DAYS("last_7_days"),
    PERSONAL_RECORDS("personal_records"),
    STREAK("streak");

    companion object {
        val DEFAULT_ORDER: List<DashboardCardType> = listOf(
            ACTIVITY_RINGS, WORKOUT_LATEST, WORKOUT_PREVIOUS, LAST_7_DAYS, PERSONAL_RECORDS, STREAK
        )

        fun fromKey(key: String): DashboardCardType? = values().firstOrNull { it.key == key }
    }
}

/**
 * Persists the person's chosen order and visibility for the reorderable
 * Today-screen cards, edited from the pencil icon on the Today screen
 * itself (not Settings -- this is a different surface from
 * WidgetVisibilityPrefs, which controls the home-screen Glance widget).
 *
 * Unknown keys from a saved order (e.g. a card type removed in a future
 * release) are silently dropped. A brand-new card type introduced in a
 * future update that isn't in the saved order yet is appended at the end,
 * so it doesn't get silently hidden from people who already customized
 * their layout before that update.
 */
class DashboardCardLayoutPrefs(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    /** Full ordered list (including hidden cards) -- used by the editor screen. */
    fun allCardsForEditor(): List<DashboardCardType> {
        val raw = prefs.getString(KEY_ORDER, null) ?: return DashboardCardType.DEFAULT_ORDER
        val saved = raw.split(",").mapNotNull { DashboardCardType.fromKey(it) }
        val missing = DashboardCardType.DEFAULT_ORDER.filter { it !in saved }
        return saved + missing
    }

    fun hiddenKeys(): Set<String> = prefs.getStringSet(KEY_HIDDEN, emptySet()).orEmpty()

    /** What the Today screen actually renders: ordered, with hidden cards filtered out. */
    fun orderedVisibleCards(): List<DashboardCardType> {
        val hidden = hiddenKeys()
        return allCardsForEditor().filter { it.key !in hidden }
    }

    fun setOrder(order: List<DashboardCardType>) {
        prefs.edit().putString(KEY_ORDER, order.joinToString(",") { it.key }).apply()
    }

    fun setHidden(type: DashboardCardType, hidden: Boolean) {
        val current = hiddenKeys().toMutableSet()
        if (hidden) current.add(type.key) else current.remove(type.key)
        prefs.edit().putStringSet(KEY_HIDDEN, current).apply()
    }

    companion object {
        private const val KEY_ORDER = "dashboard_card_order"
        private const val KEY_HIDDEN = "dashboard_card_hidden"
    }
}
