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

    /** Persists [snapshot] plus the moment it was captured (epoch millis). */
    fun save(snapshot: GoogleDashboardSnapshot) {
        try {
            val json = snapshotToJson(snapshot)
            prefs.edit()
                .putString(sourceKey(KEY_SNAPSHOT_JSON), json.toString())
                .putLong(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS), System.currentTimeMillis())
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
        val raw = prefs.getString(sourceKey(KEY_SNAPSHOT_JSON), null) ?: return null
        val savedAtMs = prefs.getLong(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS), 0L)
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
            .remove(sourceKey(KEY_SNAPSHOT_JSON))
            .remove(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS))
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
    }

    private fun snapshotFromJson(o: JSONObject): GoogleDashboardSnapshot = GoogleDashboardSnapshot(
        stepsToday = o.optLong("stepsToday", 0L),
        distanceMeters = o.optDouble("distanceMeters", 0.0),
        caloriesKcal = o.optDouble("caloriesKcal", 0.0),
        workoutMinutesToday = o.optLong("workoutMinutesToday", 0L),
        activeHoursToday = o.optInt("activeHoursToday", 0),
        recentWorkouts = workoutsFromJson(o.optJSONArray("recentWorkouts"))
    )

    private fun workoutsToJson(workouts: List<ActivitySessionData>): JSONArray {
        val arr = JSONArray()
        workouts.forEach { w ->
            arr.put(JSONObject().apply {
                put("startTimeMs", w.startTimeMs)
                put("endTimeMs", w.endTimeMs)
                put("title", w.title)
                put("exerciseType", w.exerciseType)
                put("activityKey", w.activityKey)
                put("metrics", JSONArray().apply {
                    w.metrics.forEach { metric ->
                        put(JSONObject().apply {
                            put("key", metric.key)
                            put("value", metric.value)
                        })
                    }
                })
            })
        }
        return arr
    }

    private fun workoutsFromJson(arr: JSONArray?): List<ActivitySessionData> {
        if (arr == null) return emptyList()
        val out = ArrayList<ActivitySessionData>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            val metricsJson = item.optJSONArray("metrics")
            val metrics = ArrayList<WorkoutMetric>(metricsJson?.length() ?: 0)
            if (metricsJson != null) {
                for (metricIndex in 0 until metricsJson.length()) {
                    val metric = metricsJson.optJSONObject(metricIndex) ?: continue
                    val key = metric.optString("key", "")
                    val value = metric.optDouble("value", Double.NaN)
                    if (key.isNotBlank() && value.isFinite() && value > 0.0) {
                        metrics.add(WorkoutMetric(key, value))
                    }
                }
            }

            out.add(
                ActivitySessionData(
                    startTimeMs = item.optLong("startTimeMs", 0L),
                    endTimeMs = item.optLong("endTimeMs", 0L),
                    title = item.optString("title", "Huawei activity"),
                    exerciseType = item.optInt(
                        "exerciseType",
                        androidx.health.connect.client.records.ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT
                    ),
                    activityKey = item.optString("activityKey", "workout"),
                    metrics = metrics
                )
            )
        }
        return out
    }

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
