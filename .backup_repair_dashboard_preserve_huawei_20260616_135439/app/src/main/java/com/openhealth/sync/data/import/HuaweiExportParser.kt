package com.openhealth.sync.data.import

import android.content.Context
import android.net.Uri
import com.openhealth.sync.data.ActiveCaloriesData
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.DistanceData
import com.openhealth.sync.data.HuaweiHealthSnapshot
import com.openhealth.sync.data.StepData
import com.openhealth.sync.util.AppLogger
import org.json.JSONArray
import org.json.JSONObject
import java.io.InputStream
import java.util.zip.ZipInputStream

private const val TAG = "HuaweiExportParser"

// Known Huawei Health export file names → data type
private val STEP_FILES = setOf(
    "motion_path_detail_count.json",
    "sport_health_step_count.json",
    "step_count.json",
    "com.huawei.health.step_count.json"
)

private val DISTANCE_FILES = setOf(
    "motion_path_detail_distance.json",
    "sport_health_distance.json",
    "distance.json",
    "com.huawei.health.distance.json"
)

private val CALORIE_FILES = setOf(
    "motion_path_detail_calories.json",
    "sport_health_calories.json",
    "calories.json",
    "com.huawei.health.calories.json"
)

private val ACTIVITY_FILES = setOf(
    "sport_health_activity_record.json",
    "activity_record.json",
    "workout_record.json",
    "com.huawei.health.activity_record.json"
)

data class HuaweiExportSummary(
    val snapshot: HuaweiHealthSnapshot,
    val stepCount: Int,
    val distanceCount: Int,
    val calorieCount: Int,
    val activityCount: Int,
    val filesFound: List<String>,
    val filesSkipped: List<String>
)

class HuaweiExportParser(private val context: Context) {

    fun parse(uri: Uri): HuaweiExportSummary {
        val stream = context.contentResolver.openInputStream(uri)
            ?: throw IllegalArgumentException("Cannot open file: $uri")

        return stream.use { parseStream(it, uri.lastPathSegment ?: "") }
    }

    private fun parseStream(input: InputStream, fileName: String): HuaweiExportSummary {
        val steps = mutableListOf<StepData>()
        val distances = mutableListOf<DistanceData>()
        val calories = mutableListOf<ActiveCaloriesData>()
        val activities = mutableListOf<ActivitySessionData>()
        val filesFound = mutableListOf<String>()
        val filesSkipped = mutableListOf<String>()

        // Huawei exports as ZIP — if not a zip, try parsing as raw JSON
        if (fileName.endsWith(".zip", ignoreCase = true)) {
            val zip = ZipInputStream(input.buffered())
            var entry = zip.nextEntry
            while (entry != null) {
                val entryName = entry.name.substringAfterLast("/").lowercase()
                val content = zip.readBytes().toString(Charsets.UTF_8)
                zip.closeEntry()

                when {
                    STEP_FILES.any { entryName == it } -> {
                        filesFound.add(entry.name)
                        steps += parseStepJson(content, entry.name)
                    }
                    DISTANCE_FILES.any { entryName == it } -> {
                        filesFound.add(entry.name)
                        distances += parseDistanceJson(content, entry.name)
                    }
                    CALORIE_FILES.any { entryName == it } -> {
                        filesFound.add(entry.name)
                        calories += parseCalorieJson(content, entry.name)
                    }
                    ACTIVITY_FILES.any { entryName == it } -> {
                        filesFound.add(entry.name)
                        activities += parseActivityJson(content, entry.name)
                    }
                    entryName.endsWith(".json") -> {
                        filesSkipped.add(entry.name)
                        AppLogger.d(TAG, "Skipped unrecognized JSON: ${entry.name}")
                    }
                }
                entry = zip.nextEntry
            }
        } else {
            // Single JSON file selected directly
            val content = input.readBytes().toString(Charsets.UTF_8)
            when {
                STEP_FILES.any { fileName.lowercase() == it } -> {
                    filesFound.add(fileName)
                    steps += parseStepJson(content, fileName)
                }
                DISTANCE_FILES.any { fileName.lowercase() == it } -> {
                    filesFound.add(fileName)
                    distances += parseDistanceJson(content, fileName)
                }
                else -> {
                    // Try steps as fallback for unknown JSON
                    val parsed = tryParseStepsGeneric(content)
                    if (parsed.isNotEmpty()) {
                        filesFound.add(fileName)
                        steps += parsed
                    } else {
                        filesSkipped.add(fileName)
                    }
                }
            }
        }

        val snapshot = HuaweiHealthSnapshot(
            steps = steps,
            distances = distances,
            activeCalories = calories,
            activities = activities
        )

        AppLogger.i(
            TAG,
            "Parse complete: steps=${steps.size} distances=${distances.size} calories=${calories.size} activities=${activities.size} filesFound=${filesFound.size} filesSkipped=${filesSkipped.size}"
        )

        return HuaweiExportSummary(
            snapshot = snapshot,
            stepCount = steps.size,
            distanceCount = distances.size,
            calorieCount = calories.size,
            activityCount = activities.size,
            filesFound = filesFound,
            filesSkipped = filesSkipped
        )
    }

    // ── Step parsers ──────────────────────────────────────────────────────────

    private fun parseStepJson(content: String, source: String): List<StepData> {
        return try {
            val json = JSONObject(content)
            val results = mutableListOf<StepData>()

            // Format A: { "data": [ { "startTime": ..., "endTime": ..., "value": ... } ] }
            if (json.has("data")) {
                val arr = json.getJSONArray("data")
                for (i in 0 until arr.length()) {
                    val obj = arr.getJSONObject(i)
                    val record = parseStepRecord(obj) ?: continue
                    results += record
                }
                AppLogger.i(TAG, "Parsed ${results.size} step records from $source (format A)")
                return results
            }

            // Format B: array at root [ { ... } ]
            AppLogger.w(TAG, "Unknown step JSON format in $source, trying root array")
            results
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to parse steps from $source: ${e.message}")
            emptyList()
        }
    }

    private fun tryParseStepsGeneric(content: String): List<StepData> {
        return try {
            when (val root = parseJsonRootFlexible(content)) {
                is JSONArray -> {
                    (0 until root.length()).mapNotNull { i ->
                        parseStepRecord(root.getJSONObject(i))
                    }
                }
                is JSONObject -> {
                    if (root.has("data")) {
                        val arr = root.getJSONArray("data")
                        (0 until arr.length()).mapNotNull { i ->
                            parseStepRecord(arr.getJSONObject(i))
                        }
                    } else emptyList()
                }
                else -> emptyList()
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    private fun parseStepRecord(obj: JSONObject): StepData? {
        return try {
            val start = obj.huaweiTime("startTime") ?: obj.huaweiTime("start_time") ?: return null
            val end = obj.huaweiTime("endTime") ?: obj.huaweiTime("end_time") ?: return null
            val count = obj.optLong("value", -1L)
                .takeIf { it >= 0 }
                ?: obj.optLong("steps", -1L)
                    .takeIf { it >= 0 }
                ?: return null

            if (count > 0L && start < end) StepData(start, end, count) else null
        } catch (_: Exception) {
            null
        }
    }

    // ── Distance parsers ──────────────────────────────────────────────────────

    private fun parseDistanceJson(content: String, source: String): List<DistanceData> {
        return try {
            val json = JSONObject(content)
            val results = mutableListOf<DistanceData>()

            if (json.has("data")) {
                val arr = json.getJSONArray("data")
                for (i in 0 until arr.length()) {
                    val obj = arr.getJSONObject(i)
                    val start = obj.huaweiTime("startTime") ?: continue
                    val end = obj.huaweiTime("endTime") ?: continue
                    val meters = obj.optDouble("value", -1.0)
                        .takeIf { it > 0.0 }
                        ?: obj.optDouble("distance", -1.0)
                            .takeIf { it > 0.0 }
                        ?: continue

                    if (start < end) results += DistanceData(start, end, meters)
                }
            }

            AppLogger.i(TAG, "Parsed ${results.size} distance records from $source")
            results
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to parse distance from $source: ${e.message}")
            emptyList()
        }
    }

    // ── Calorie parsers ───────────────────────────────────────────────────────

    private fun parseCalorieJson(content: String, source: String): List<ActiveCaloriesData> {
        return try {
            val json = JSONObject(content)
            val results = mutableListOf<ActiveCaloriesData>()

            if (json.has("data")) {
                val arr = json.getJSONArray("data")
                for (i in 0 until arr.length()) {
                    val obj = arr.getJSONObject(i)
                    val start = obj.huaweiTime("startTime") ?: continue
                    val end = obj.huaweiTime("endTime") ?: continue
                    val kcal = obj.optDouble("value", -1.0)
                        .takeIf { it > 0.0 }
                        ?: obj.optDouble("calories", -1.0)
                            .takeIf { it > 0.0 }
                        ?: continue

                    if (start < end) results += ActiveCaloriesData(start, end, kcal)
                }
            }

            AppLogger.i(TAG, "Parsed ${results.size} calorie records from $source")
            results
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to parse calories from $source: ${e.message}")
            emptyList()
        }
    }

    // ── Activity parsers ──────────────────────────────────────────────────────

    private fun parseActivityJson(content: String, source: String): List<ActivitySessionData> {
        return try {
            val json = JSONObject(content)
            val results = mutableListOf<ActivitySessionData>()

            val arr = when {
                json.has("data") -> json.getJSONArray("data")
                json.has("records") -> json.getJSONArray("records")
                else -> return emptyList()
            }

            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                val start = obj.huaweiTime("startTime") ?: obj.huaweiTime("start_time") ?: continue
                val end = obj.huaweiTime("endTime") ?: obj.huaweiTime("end_time") ?: continue
                if (end - start < 60_000L) continue

                val title = obj.optString("sportType", "")
                    .ifBlank { obj.optString("type", "Huawei activity") }

                results += ActivitySessionData(
                    startTimeMs = start,
                    endTimeMs = end,
                    title = title.ifBlank { "Huawei activity" }
                )
            }

            AppLogger.i(TAG, "Parsed ${results.size} activity records from $source")
            results
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to parse activities from $source: ${e.message}")
            emptyList()
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    // Huawei exports timestamps in seconds or milliseconds
    private fun JSONObject.huaweiTime(key: String): Long? {
        val raw = optLong(key, -1L).takeIf { it > 0L } ?: return null
        // Timestamps < 1e10 are in seconds, convert to ms
        return if (raw < 10_000_000_000L) raw * 1000L else raw
    }

    private fun parseJsonRootFlexible(content: String): Any? {
        return try { JSONObject(content) } catch (_: Exception) {
            try { JSONArray(content) } catch (_: Exception) { null }
        }
    }
}
