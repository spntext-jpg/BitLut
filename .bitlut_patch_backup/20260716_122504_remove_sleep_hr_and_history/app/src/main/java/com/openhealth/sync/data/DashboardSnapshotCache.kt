package com.openhealth.sync.data

import android.content.Context
import android.content.SharedPreferences
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
class DashboardSnapshotCache(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    /** Persists [snapshot] plus the moment it was captured (epoch millis). */
    fun save(snapshot: GoogleDashboardSnapshot) {
        try {
            val json = snapshotToJson(snapshot)
            prefs.edit()
                .putString(KEY_SNAPSHOT_JSON, json.toString())
                .putLong(KEY_SNAPSHOT_SAVED_AT_MS, System.currentTimeMillis())
                .apply()
            AppLogger.d(TAG, "Dashboard snapshot cached (stepsToday=${snapshot.stepsToday})")
        } catch (e: Exception) {
            // Caching is a best-effort optimization. A failure here must never
            // crash sync or the dashboard load path.
            AppLogger.e(TAG, "Failed to cache dashboard snapshot: ${e.message}", e)
        }
    }

    /** Returns the last cached snapshot, or null if none was ever saved or it is corrupt. */
    fun load(): CachedSnapshot? {
        val raw = prefs.getString(KEY_SNAPSHOT_JSON, null) ?: return null
        val savedAtMs = prefs.getLong(KEY_SNAPSHOT_SAVED_AT_MS, 0L)
        return try {
            val snapshot = snapshotFromJson(JSONObject(raw))
            CachedSnapshot(snapshot = snapshot, savedAtMs = savedAtMs)
        } catch (e: Exception) {
            AppLogger.e(TAG, "Cached dashboard snapshot is corrupt; ignoring: ${e.message}", e)
            null
        }
    }

    fun clear() {
        prefs.edit()
            .remove(KEY_SNAPSHOT_JSON)
            .remove(KEY_SNAPSHOT_SAVED_AT_MS)
            .apply()
    }

    private fun snapshotToJson(s: GoogleDashboardSnapshot): JSONObject = JSONObject().apply {
        put("stepsToday", s.stepsToday)
        put("distanceMeters", s.distanceMeters)
        put("caloriesKcal", s.caloriesKcal)
        put("workoutMinutesToday", s.workoutMinutesToday)
        put("activeHoursToday", s.activeHoursToday)
        put("sleepHours", s.sleepHours)
        put("sleepQualityScore", s.sleepQualityScore ?: JSONObject.NULL)
        put("heartRateBpm", s.heartRateBpm ?: JSONObject.NULL)
        put("stressScore", s.stressScore ?: JSONObject.NULL)
        put("spo2Percent", s.spo2Percent ?: JSONObject.NULL)
        put("stepsBars", barsToJson(s.stepsBars))
        put("sleepBars", barsToJson(s.sleepBars))
        put("heartRateBars", barsToJson(s.heartRateBars))
        put("heartRateTodayBars", barsToJson(s.heartRateTodayBars))
        put("recentWorkouts", workoutsToJson(s.recentWorkouts))
        put("workoutSummaries", summariesToJson(s.workoutSummaries))
    }

    private fun snapshotFromJson(o: JSONObject): GoogleDashboardSnapshot = GoogleDashboardSnapshot(
        stepsToday = o.optLong("stepsToday", 0L),
        distanceMeters = o.optDouble("distanceMeters", 0.0),
        caloriesKcal = o.optDouble("caloriesKcal", 0.0),
        workoutMinutesToday = o.optLong("workoutMinutesToday", 0L),
        activeHoursToday = o.optInt("activeHoursToday", 0),
        sleepHours = o.optDouble("sleepHours", 0.0),
        sleepQualityScore = o.optIntOrNull("sleepQualityScore"),
        heartRateBpm = o.optLongOrNull("heartRateBpm"),
        heartRateTodayBars = barsFromJson(o.optJSONArray("heartRateTodayBars")),
        stressScore = o.optIntOrNull("stressScore"),
        spo2Percent = o.optDoubleOrNull("spo2Percent"),
        stepsBars = barsFromJson(o.optJSONArray("stepsBars")),
        sleepBars = barsFromJson(o.optJSONArray("sleepBars")),
        heartRateBars = barsFromJson(o.optJSONArray("heartRateBars")),
        recentWorkouts = workoutsFromJson(o.optJSONArray("recentWorkouts")),
        workoutSummaries = summariesFromJson(o.optJSONArray("workoutSummaries"))
    )

    private fun barsToJson(bars: List<MetricBar>): JSONArray {
        val arr = JSONArray()
        bars.forEach { bar ->
            arr.put(JSONObject().apply {
                put("startDate", bar.startDate.toString())
                put("endDate", bar.endDate.toString())
                put("value", bar.value)
            })
        }
        return arr
    }

    private fun barsFromJson(arr: JSONArray?): List<MetricBar> {
        if (arr == null) return emptyList()
        val out = ArrayList<MetricBar>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            try {
                out.add(
                    MetricBar(
                        startDate = java.time.LocalDate.parse(item.getString("startDate")),
                        endDate = java.time.LocalDate.parse(item.getString("endDate")),
                        value = item.optDouble("value", 0.0)
                    )
                )
            } catch (_: Exception) {
                // Skip a single corrupt bar rather than discarding the whole cache entry.
            }
        }
        return out
    }

    private fun workoutsToJson(workouts: List<ActivitySessionData>): JSONArray {
        val arr = JSONArray()
        workouts.forEach { w ->
            arr.put(JSONObject().apply {
                put("startTimeMs", w.startTimeMs)
                put("endTimeMs", w.endTimeMs)
                put("title", w.title)
                put("exerciseType", w.exerciseType)
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
                    )
                )
            )
        }
        return out
    }

    private fun summariesToJson(summaries: List<WorkoutTypeSummary>): JSONArray {
        val arr = JSONArray()
        summaries.forEach { s ->
            arr.put(JSONObject().apply {
                put("exerciseType", s.exerciseType)
                put("displayName", s.displayName)
                put("sessionCount", s.sessionCount)
                put("totalDurationMinutes", s.totalDurationMinutes)
            })
        }
        return arr
    }

    private fun summariesFromJson(arr: JSONArray?): List<WorkoutTypeSummary> {
        if (arr == null) return emptyList()
        val out = ArrayList<WorkoutTypeSummary>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            out.add(
                WorkoutTypeSummary(
                    exerciseType = item.optInt("exerciseType", 0),
                    displayName = item.optString("displayName", ""),
                    sessionCount = item.optInt("sessionCount", 0),
                    totalDurationMinutes = item.optLong("totalDurationMinutes", 0L)
                )
            )
        }
        return out
    }

    private fun JSONObject.optIntOrNull(key: String): Int? =
        if (isNull(key) || !has(key)) null else optInt(key)

    private fun JSONObject.optLongOrNull(key: String): Long? =
        if (isNull(key) || !has(key)) null else optLong(key)

    private fun JSONObject.optDoubleOrNull(key: String): Double? =
        if (isNull(key) || !has(key)) null else optDouble(key)

    companion object {
        private const val KEY_SNAPSHOT_JSON = "dashboard_snapshot_cache_json"
        private const val KEY_SNAPSHOT_SAVED_AT_MS = "dashboard_snapshot_cache_saved_at_ms"
    }
}

/** A cached snapshot plus when it was captured, so the UI can show e.g. "updated 4m ago". */
data class CachedSnapshot(
    val snapshot: GoogleDashboardSnapshot,
    val savedAtMs: Long
)
