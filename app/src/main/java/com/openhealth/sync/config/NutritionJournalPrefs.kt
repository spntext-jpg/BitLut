package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

/** Meal slots of the Nutrition journal. Stored by [key], so reordering is safe. */
enum class MealType(val key: String) {
    BREAKFAST("breakfast"),
    LUNCH("lunch"),
    DINNER("dinner"),
    SNACK("snack");

    companion object {
        /** Unknown or missing keys fall back to SNACK instead of dropping the entry. */
        fun fromKey(key: String?): MealType = values().firstOrNull { it.key == key } ?: SNACK
    }
}

/** One line of the journal. [epochDay] is the local calendar day (`LocalDate.toEpochDay()`). */
data class FoodEntry(
    val id: Long,
    val epochDay: Long,
    val meal: MealType,
    val name: String,
    val kcal: Int
)

/**
 * The Nutrition tab's food journal (stage 5 of docs/PRODUCT_ROADMAP.md).
 *
 * Local-only by design: entries are typed in by the person, live in this app's
 * private SharedPreferences file, are never uploaded, never written to Health
 * Connect (that would need a new permission) and are excluded from Android
 * backup (`android:allowBackup="false"`). It is a separate file from
 * `HuaweiConfig.PREFS_NAME`, so disconnecting or resetting the Huawei/Google
 * source never touches the journal.
 *
 * Data is small (a handful of entries per day), so the whole list is one JSON
 * array under one key. A corrupt value reads as an empty journal and is
 * replaced on the next write rather than crashing the tab.
 */
class NutritionJournalPrefs(context: Context) {

    private val prefs: SharedPreferences = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun loadAll(): List<FoodEntry> {
        val raw = prefs.getString(KEY_ENTRIES, null) ?: return emptyList()
        return try {
            parse(raw)
        } catch (_: JSONException) {
            emptyList()
        }
    }

    /** Adds one entry and returns the updated full list. Inputs are clamped to the limits below. */
    fun add(meal: MealType, epochDay: Long, name: String, kcal: Int): List<FoodEntry> {
        val current = loadAll()
        val id = maxOf(System.currentTimeMillis(), (current.maxOfOrNull { it.id } ?: 0L) + 1L)
        val entry = FoodEntry(
            id = id,
            epochDay = epochDay,
            meal = meal,
            name = name.trim().take(MAX_NAME_LENGTH),
            kcal = kcal.coerceIn(MIN_KCAL, MAX_KCAL)
        )
        return (current + entry).also { save(it) }
    }

    /** Removes the entry with [id] and returns the updated full list. */
    fun remove(id: Long): List<FoodEntry> {
        return loadAll().filterNot { it.id == id }.also { save(it) }
    }

    private fun parse(raw: String): List<FoodEntry> {
        val array = JSONArray(raw)
        val result = ArrayList<FoodEntry>(array.length())
        for (index in 0 until array.length()) {
            val item = array.optJSONObject(index) ?: continue
            val kcal = item.optInt(KEY_KCAL, 0)
            if (kcal <= 0) continue
            result.add(
                FoodEntry(
                    id = item.optLong(KEY_ID),
                    epochDay = item.optLong(KEY_DAY),
                    meal = MealType.fromKey(item.optString(KEY_MEAL)),
                    name = item.optString(KEY_NAME),
                    kcal = kcal
                )
            )
        }
        return result
    }

    private fun save(entries: List<FoodEntry>) {
        val array = JSONArray()
        for (entry in entries) {
            array.put(
                JSONObject()
                    .put(KEY_ID, entry.id)
                    .put(KEY_DAY, entry.epochDay)
                    .put(KEY_MEAL, entry.meal.key)
                    .put(KEY_NAME, entry.name)
                    .put(KEY_KCAL, entry.kcal)
            )
        }
        prefs.edit().putString(KEY_ENTRIES, array.toString()).apply()
    }

    companion object {
        const val MIN_KCAL = 1
        const val MAX_KCAL = 9999
        const val MAX_NAME_LENGTH = 60

        private const val PREFS_NAME = "bitlut_nutrition_journal"
        private const val KEY_ENTRIES = "entries"
        private const val KEY_ID = "id"
        private const val KEY_DAY = "day"
        private const val KEY_MEAL = "meal"
        private const val KEY_NAME = "name"
        private const val KEY_KCAL = "kcal"
    }
}
