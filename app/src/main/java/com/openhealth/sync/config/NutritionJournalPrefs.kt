package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.flow.map
import org.json.JSONArray
import org.json.JSONObject

enum class MealType(val key: String) {
    BREAKFAST("breakfast"), LUNCH("lunch"), DINNER("dinner"), SNACK("snack");
    companion object {
        fun fromKey(key: String?): MealType = entries.firstOrNull { it.key == key } ?: SNACK
    }
}

/** Nutrients are a snapshot at logging time, never recomputed after a catalog update. */
data class FoodEntry(
    val id: Long,
    val epochDay: Long,
    val meal: MealType,
    val name: String,
    val kcal: Double,
    val grams: Double? = null,
    val protein: Double? = null,
    val fat: Double? = null,
    val carbs: Double? = null,
    val foodId: String? = null
) {
    val hasMacros: Boolean get() = protein != null && fat != null && carbs != null
}

data class NutritionTotals(
    val kcal: Double,
    val protein: Double,
    val fat: Double,
    val carbs: Double,
    val unknownMacros: Int,
    val entries: Int
) {
    companion object {
        fun of(entries: List<FoodEntry>) = NutritionTotals(
            kcal = entries.sumOf { it.kcal }, protein = entries.sumOf { it.protein ?: 0.0 },
            fat = entries.sumOf { it.fat ?: 0.0 }, carbs = entries.sumOf { it.carbs ?: 0.0 },
            unknownMacros = entries.count { !it.hasMacros }, entries = entries.size
        )
    }
}

data class NutritionJournalState(val entries: List<FoodEntry> = emptyList(), val goalKcal: Int = 0, val storageError: Boolean = false)

/** Local only. Same preference file/key as the original journal; v1 entries migrate on read. */
class NutritionJournalPrefs(context: Context) {
    private val prefs: SharedPreferences = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun loadAll(): List<FoodEntry> = decode(prefs.getString(KEY_ENTRIES, null) ?: "[]")

    fun state(): Flow<NutritionJournalState> = callbackFlow {
        val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, _ -> trySend(Unit) }
        prefs.registerOnSharedPreferenceChangeListener(listener)
        trySend(Unit)
        awaitClose { prefs.unregisterOnSharedPreferenceChangeListener(listener) }
    }.map {
        try {
            NutritionJournalState(loadAll(), prefs.getInt("goal_kcal", 0))
        } catch (_: Exception) {
            // Fail closed: a damaged journal is never replaced with an empty one.
            NutritionJournalState(storageError = true)
        }
    }.flowOn(Dispatchers.IO)

    fun setGoal(goal: Int) {
        require(goal in 0..MAX_KCAL)
        check(prefs.edit().putInt("goal_kcal", goal).commit()) { "Nutrition goal could not be saved" }
    }

    fun upsert(entry: FoodEntry) = synchronized(lock) {
        validate(entry)
        val current = loadAll()
        val id = if (entry.id > 0) entry.id else maxOf(System.currentTimeMillis(), (current.maxOfOrNull { it.id } ?: 0) + 1)
        val saved = entry.copy(id = id, name = entry.name.trim().take(MAX_NAME_LENGTH))
        val updated = current.filterNot { it.id == id } + saved
        check(prefs.edit().putString(KEY_ENTRIES, encode(updated)).commit()) { "Nutrition entry could not be saved" }
    }

    fun remove(id: Long) = synchronized(lock) {
        val updated = loadAll().filterNot { it.id == id }
        check(prefs.edit().putString(KEY_ENTRIES, encode(updated)).commit()) { "Nutrition entry could not be removed" }
    }

    companion object {
        const val MIN_KCAL = 0
        const val MAX_KCAL = 9999
        const val MAX_NAME_LENGTH = 100
        private const val PREFS_NAME = "bitlut_nutrition_journal"
        private const val KEY_ENTRIES = "entries"
        private val lock = Any()

        internal fun validate(entry: FoodEntry) {
            require(entry.kcal.isFinite() && entry.kcal in 0.0..MAX_KCAL.toDouble())
            require(entry.grams == null || entry.grams.isFinite() && entry.grams > 0 && entry.grams <= 5000)
            require(listOf(entry.protein, entry.fat, entry.carbs).all { it == null || it.isFinite() && it in 0.0..5000.0 })
            require(entry.grams == null || listOfNotNull(entry.protein, entry.fat, entry.carbs).sum() <= entry.grams + 0.5)
        }

        internal fun decode(raw: String): List<FoodEntry> {
            val array = JSONArray(raw)
            return (0 until array.length()).map { index ->
                val item = array.getJSONObject(index)
                fun optional(key: String) = if (!item.has(key) || item.isNull(key)) null else item.getDouble(key)
                FoodEntry(
                    id = item.getLong("id"), epochDay = item.getLong("day"),
                    meal = MealType.fromKey(item.optString("meal")), name = item.optString("name"), kcal = item.getDouble("kcal"),
                    grams = optional("grams"), protein = optional("protein"), fat = optional("fat"), carbs = optional("carbs"),
                    foodId = item.optString("foodId").takeIf { it.isNotBlank() }
                ).also(::validate)
            }
        }

        internal fun encode(entries: List<FoodEntry>): String = JSONArray().apply {
            entries.forEach { entry ->
                validate(entry)
                put(JSONObject().put("id", entry.id).put("day", entry.epochDay).put("meal", entry.meal.key)
                    .put("name", entry.name).put("kcal", entry.kcal).put("grams", entry.grams)
                    .put("protein", entry.protein).put("fat", entry.fat).put("carbs", entry.carbs).put("foodId", entry.foodId))
            }
        }.toString()
    }
}
