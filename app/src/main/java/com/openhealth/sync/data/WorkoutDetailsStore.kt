package com.openhealth.sync.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Health Connect's ExerciseSessionRecord carries the session identity but not
 * Huawei's ActivityRecord summary fields. Keep those activity-only details on
 * device and re-attach them when the dashboard reads the corresponding
 * BitLut-owned Health Connect session.
 */
internal class WorkoutDetailsStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun saveAll(records: List<ActivitySessionData>) {
        if (records.isEmpty()) return
        val editor = prefs.edit()
        records.forEach { record ->
            editor.putString(key(record.startTimeMs, record.endTimeMs), toJson(record).toString())
        }

        val cutoff = System.currentTimeMillis() - RETENTION_MS
        prefs.all.keys.forEach { storedKey ->
            val start = storedKey.removePrefix(KEY_PREFIX).substringBefore('_').toLongOrNull()
            if (start != null && start < cutoff) editor.remove(storedKey)
        }
        editor.apply()
    }

    fun enrich(session: ActivitySessionData): ActivitySessionData {
        val raw = prefs.getString(key(session.startTimeMs, session.endTimeMs), null) ?: return session
        return try {
            val json = JSONObject(raw)
            val activityKey = json.optString("activityKey", session.activityKey)
            val metricsJson = json.optJSONArray("metrics") ?: JSONArray()
            val metrics = ArrayList<WorkoutMetric>(metricsJson.length())
            for (index in 0 until metricsJson.length()) {
                val item = metricsJson.optJSONObject(index) ?: continue
                val metricKey = item.optString("key", "")
                val value = item.optDouble("value", Double.NaN)
                if (metricKey.isNotBlank() && value.isFinite() && value > 0.0) {
                    metrics.add(WorkoutMetric(metricKey, value))
                }
            }
            session.copy(
                activityKey = activityKey.ifBlank { session.activityKey },
                metrics = metrics
            )
        } catch (_: Exception) {
            session
        }
    }

    private fun toJson(record: ActivitySessionData): JSONObject = JSONObject().apply {
        put("activityKey", record.activityKey)
        put("metrics", JSONArray().apply {
            record.metrics.forEach { metric ->
                put(JSONObject().apply {
                    put("key", metric.key)
                    put("value", metric.value)
                })
            }
        })
    }

    private fun key(startTimeMs: Long, endTimeMs: Long): String =
        "$KEY_PREFIX${startTimeMs}_${endTimeMs}"

    private companion object {
        const val PREFS_NAME = "bitlut_workout_details"
        const val KEY_PREFIX = "workout_"
        const val RETENTION_MS = 90L * 24L * 60L * 60L * 1000L
    }
}
