package com.openhealth.sync.data

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.config.DataSourcePrefs
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger
import org.json.JSONArray
import org.json.JSONObject

private const val TAG = "DashboardSnapshotCache"

/**
 * Persists the last successfully read [GoogleDashboardSnapshot] to disk so the
 * dashboard can render real, last-known data immediately on cold start instead
 * of flashing a "Connect Google Health" lock screen while the first async
 * Health Connect read is still in flight (or has transiently failed).
 *
 * This is a read-through cache only: it never invents data, never marks the
 * user as "permitted" by itself, and is always overwritten by a fresh
 * [GoogleDashboardSnapshot] as soon as one is successfully read. It exists
 * purely to bridge the gap between "app process started" and "first live
 * Health Connect read completed".
 *
 * Stored in the same SharedPreferences file the rest of BitLut already uses
 * ([HuaweiConfig.PREFS_NAME]) to avoid introducing a new dependency (Room/
 * DataStore) for what is fundamentally a single small JSON blob.
 */
class DashboardSnapshotCache(
    context: Context,
    private val dataSourcePrefs: DataSourcePrefs = DataSourcePrefs(context)
) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    /**
     * Persists the latest cache read time and separately tracks when the
     * underlying dashboard values last changed. Background refreshes therefore
     * keep cache freshness semantics intact without making the UI claim that
     * unchanged data became new simply because the app was opened.
     *
     * @return epoch millis when the currently displayed data first changed.
     */
    fun save(snapshot: GoogleDashboardSnapshot): Long {
        val previous = try { load() } catch (_: Exception) { null }
        val now = System.currentTimeMillis()
        val dataChangedAtMs = if (previous?.snapshot == snapshot && previous.dataChangedAtMs > 0L) {
            previous.dataChangedAtMs
        } else {
            now
        }

        return try {
            val json = snapshotToJson(snapshot)
            prefs.edit()
                .putString(sourceKey(KEY_SNAPSHOT_JSON), json.toString())
                .putLong(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS), now)
                .putLong(sourceKey(KEY_SNAPSHOT_DATA_CHANGED_AT_MS), dataChangedAtMs)
                .apply()
            AppLogger.d(TAG, "Dashboard snapshot cached (stepsToday=${snapshot.stepsToday}, dataChangedAtMs=$dataChangedAtMs)")
            dataChangedAtMs
        } catch (e: Exception) {
            // Caching is a best-effort optimization. A failure here must never
            // crash sync or the dashboard load path.
            AppLogger.e(TAG, "Failed to cache dashboard snapshot: ${e.message}", e)
            previous?.dataChangedAtMs ?: 0L
        }
    }

    /** Returns the last cached snapshot, or null if none was ever saved or it is corrupt. */
    fun load(): CachedSnapshot? {
        val raw = prefs.getString(sourceKey(KEY_SNAPSHOT_JSON), null) ?: return null
        val savedAtMs = prefs.getLong(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS), 0L)
        val dataChangedAtMs = prefs.getLong(sourceKey(KEY_SNAPSHOT_DATA_CHANGED_AT_MS), savedAtMs)
        return try {
            val snapshot = snapshotFromJson(JSONObject(raw))
            CachedSnapshot(snapshot = snapshot, savedAtMs = savedAtMs, dataChangedAtMs = dataChangedAtMs)
        } catch (e: Exception) {
            AppLogger.e(TAG, "Cached dashboard snapshot is corrupt; ignoring: ${e.message}", e)
            null
        }
    }

    fun clear() {
        prefs.edit()
            .remove(sourceKey(KEY_SNAPSHOT_JSON))
            .remove(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS))
            .remove(sourceKey(KEY_SNAPSHOT_DATA_CHANGED_AT_MS))
            .apply()
    }

    private fun sourceKey(base: String): String =
        "${base}_${dataSourcePrefs.selected().storageValue}"

    private fun snapshotToJson(s: GoogleDashboardSnapshot): JSONObject = JSONObject().apply {
        put("stepsToday", s.stepsToday)
        put("distanceMeters", s.distanceMeters)
        put("caloriesKcal", s.caloriesKcal)
        put("workoutMinutesToday", s.workoutMinutesToday)
        put("activeHoursToday", s.activeHoursToday)
        put("recentWorkouts", workoutsToJson(s.recentWorkouts))
        put("dailyActivity", dailyActivityToJson(s.dailyActivity))
    }

    private fun snapshotFromJson(o: JSONObject): GoogleDashboardSnapshot = GoogleDashboardSnapshot(
        stepsToday = o.optLong("stepsToday", 0L),
        distanceMeters = o.optDouble("distanceMeters", 0.0),
        caloriesKcal = o.optDouble("caloriesKcal", 0.0),
        workoutMinutesToday = o.optLong("workoutMinutesToday", 0L),
        activeHoursToday = o.optInt("activeHoursToday", 0),
        recentWorkouts = workoutsFromJson(o.optJSONArray("recentWorkouts")),
        dailyActivity = dailyActivityFromJson(o.optJSONArray("dailyActivity"))
    )

    private fun dailyActivityToJson(days: List<DailyActivitySummary>): JSONArray {
        val arr = JSONArray()
        days.forEach { day ->
            arr.put(JSONObject().apply {
                put("date", day.date.toString())
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
        return arr
    }

    private fun dailyActivityFromJson(arr: JSONArray?): List<DailyActivitySummary> {
        if (arr == null) return emptyList()
        val out = ArrayList<DailyActivitySummary>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            val date = try {
                java.time.LocalDate.parse(item.optString("date"))
            } catch (_: Exception) {
                continue
            }
            out.add(
                DailyActivitySummary(
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
            )
        }
        return out.sortedBy { it.date }
    }

    private fun workoutsToJson(workouts: List<ActivitySessionData>): JSONArray {
        val arr = JSONArray()
        workouts.forEach { w ->
            arr.put(JSONObject().apply {
                put("startTimeMs", w.startTimeMs)
                put("endTimeMs", w.endTimeMs)
                put("title", w.title)
                put("exerciseType", w.exerciseType)
                w.distanceMeters?.let { put("distanceMeters", it) }
                w.activeCaloriesKcal?.let { put("activeCaloriesKcal", it) }
                w.totalCaloriesKcal?.let { put("totalCaloriesKcal", it) }
                w.elevationMeters?.let { put("elevationMeters", it) }
                w.steps?.let { put("steps", it) }
            })
        }
        return arr
    }

    private fun workoutsFromJson(arr: JSONArray?): List<ActivitySessionData> {
        if (arr == null) return emptyList()
        val out = ArrayList<ActivitySessionData>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            out.add(
                ActivitySessionData(
                    startTimeMs = item.optLong("startTimeMs", 0L),
                    endTimeMs = item.optLong("endTimeMs", 0L),
                    title = item.optString("title", "Huawei activity"),
                    exerciseType = item.optInt(
                        "exerciseType",
                        androidx.health.connect.client.records.ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT
                    ),
                    distanceMeters = if (item.has("distanceMeters")) item.optDouble("distanceMeters") else null,
                    activeCaloriesKcal = if (item.has("activeCaloriesKcal")) item.optDouble("activeCaloriesKcal") else null,
                    totalCaloriesKcal = if (item.has("totalCaloriesKcal")) item.optDouble("totalCaloriesKcal") else null,
                    elevationMeters = if (item.has("elevationMeters")) item.optDouble("elevationMeters") else null,
                    steps = if (item.has("steps")) item.optLong("steps") else null
                )
            )
        }
        return out
    }

    companion object {
        private const val KEY_SNAPSHOT_JSON = "dashboard_snapshot_cache_json"
        private const val KEY_SNAPSHOT_SAVED_AT_MS = "dashboard_snapshot_cache_saved_at_ms"
        private const val KEY_SNAPSHOT_DATA_CHANGED_AT_MS = "dashboard_snapshot_data_changed_at_ms"
    }
}

/** Cache transport freshness and semantic data freshness are intentionally separate. */
data class CachedSnapshot(
    val snapshot: GoogleDashboardSnapshot,
    val savedAtMs: Long,
    val dataChangedAtMs: Long
)
