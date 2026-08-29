package com.openhealth.sync.data.import

import android.content.Context
import android.net.Uri
import com.openhealth.sync.data.ActiveCaloriesData
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.DistanceData
import com.openhealth.sync.data.HuaweiHealthSnapshot
import com.openhealth.sync.data.HuaweiWorkoutTypeMapper
import com.openhealth.sync.data.StepData
import com.openhealth.sync.util.AppLogger
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.util.zip.ZipInputStream

private const val TAG = "HuaweiExportParser"
private const val MAX_SINGLE_JSON_BYTES = 16 * 1024 * 1024
private const val MAX_TOTAL_ZIP_JSON_BYTES = 64 * 1024 * 1024
private const val MAX_ZIP_ENTRIES = 10_000

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

private enum class ExportKind { STEPS, DISTANCE, CALORIES, ACTIVITY }

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

        return stream.use { parseStream(it, uri.lastPathSegment.orEmpty()) }
    }

    private fun parseStream(input: InputStream, fileName: String): HuaweiExportSummary {
        val steps = mutableListOf<StepData>()
        val distances = mutableListOf<DistanceData>()
        val calories = mutableListOf<ActiveCaloriesData>()
        val activities = mutableListOf<ActivitySessionData>()
        val filesFound = mutableListOf<String>()
        val filesSkipped = mutableListOf<String>()

        if (fileName.endsWith(".zip", ignoreCase = true)) {
            var entryCount = 0
            var totalJsonBytes = 0

            ZipInputStream(input.buffered()).use { zip ->
                var entry = zip.nextEntry
                while (entry != null) {
                    entryCount += 1
                    if (entryCount > MAX_ZIP_ENTRIES) {
                        throw IllegalArgumentException("Huawei archive contains too many entries")
                    }

                    val source = entry.name
                    val shortName = source.substringAfterLast('/').lowercase()
                    val kind = classify(shortName)

                    if (!entry.isDirectory && kind != null) {
                        val remainingBudget = MAX_TOTAL_ZIP_JSON_BYTES - totalJsonBytes
                        if (remainingBudget <= 0) {
                            throw IllegalArgumentException("Huawei archive JSON data exceeds the safe size limit")
                        }

                        val bytes = zip.readBytesBounded(minOf(MAX_SINGLE_JSON_BYTES, remainingBudget))
                        totalJsonBytes += bytes.size
                        parseRecognized(kind, bytes.toString(Charsets.UTF_8), source, steps, distances, calories, activities)
                        filesFound += source
                    } else if (!entry.isDirectory && shortName.endsWith(".json")) {
                        filesSkipped += source
                        AppLogger.d(TAG, "Skipped unrecognized JSON without loading it: $source")
                    }

                    zip.closeEntry()
                    entry = zip.nextEntry
                }
            }
        } else {
            val content = input.readBytesBounded(MAX_SINGLE_JSON_BYTES).toString(Charsets.UTF_8)
            val kind = classify(fileName.substringAfterLast('/').lowercase()) ?: inferKind(content)

            if (kind == null) {
                filesSkipped += fileName
            } else {
                parseRecognized(kind, content, fileName, steps, distances, calories, activities)
                filesFound += fileName
            }
        }

        val distinctSteps = steps.distinctBy { Triple(it.startTimeMs, it.endTimeMs, it.count) }
        val distinctDistances = distances.distinctBy { Triple(it.startTimeMs, it.endTimeMs, it.meters) }
        val distinctCalories = calories.distinctBy { Triple(it.startTimeMs, it.endTimeMs, it.kilocalories) }
        val distinctActivities = activities.distinctBy { Pair(it.startTimeMs, it.endTimeMs) }

        val snapshot = HuaweiHealthSnapshot(
            steps = distinctSteps,
            distances = distinctDistances,
            activeCalories = distinctCalories,
            activities = distinctActivities
        )

        AppLogger.i(
            TAG,
            "Parse complete: steps=${distinctSteps.size} distances=${distinctDistances.size} " +
                "calories=${distinctCalories.size} activities=${distinctActivities.size} " +
                "filesFound=${filesFound.size} filesSkipped=${filesSkipped.size}"
        )

        return HuaweiExportSummary(
            snapshot = snapshot,
            stepCount = distinctSteps.size,
            distanceCount = distinctDistances.size,
            calorieCount = distinctCalories.size,
            activityCount = distinctActivities.size,
            filesFound = filesFound,
            filesSkipped = filesSkipped
        )
    }

    private fun classify(fileName: String): ExportKind? = when (fileName) {
        in STEP_FILES -> ExportKind.STEPS
        in DISTANCE_FILES -> ExportKind.DISTANCE
        in CALORIE_FILES -> ExportKind.CALORIES
        in ACTIVITY_FILES -> ExportKind.ACTIVITY
        else -> null
    }

    private fun parseRecognized(
        kind: ExportKind,
        content: String,
        source: String,
        steps: MutableList<StepData>,
        distances: MutableList<DistanceData>,
        calories: MutableList<ActiveCaloriesData>,
        activities: MutableList<ActivitySessionData>
    ) {
        when (kind) {
            ExportKind.STEPS -> steps += parseStepJson(content, source)
            ExportKind.DISTANCE -> distances += parseDistanceJson(content, source)
            ExportKind.CALORIES -> calories += parseCalorieJson(content, source)
            ExportKind.ACTIVITY -> activities += parseActivityJson(content, source)
        }
    }

    private fun parseStepJson(content: String, source: String): List<StepData> =
        parseRecords(content, source, "steps") { parseStepRecord(it) }

    private fun parseDistanceJson(content: String, source: String): List<DistanceData> =
        parseRecords(content, source, "distance") { obj ->
            val start = obj.huaweiTime("startTime") ?: obj.huaweiTime("start_time") ?: return@parseRecords null
            val end = obj.huaweiTime("endTime") ?: obj.huaweiTime("end_time") ?: return@parseRecords null
            val meters = obj.positiveDouble("value", "distance", "meters") ?: return@parseRecords null
            if (start < end) DistanceData(start, end, meters) else null
        }

    private fun parseCalorieJson(content: String, source: String): List<ActiveCaloriesData> =
        parseRecords(content, source, "calories") { obj ->
            val start = obj.huaweiTime("startTime") ?: obj.huaweiTime("start_time") ?: return@parseRecords null
            val end = obj.huaweiTime("endTime") ?: obj.huaweiTime("end_time") ?: return@parseRecords null
            val kcal = obj.positiveDouble("value", "calories", "calorie", "kilocalories")
                ?: return@parseRecords null
            if (start < end) ActiveCaloriesData(start, end, kcal) else null
        }

    private fun parseActivityJson(content: String, source: String): List<ActivitySessionData> =
        parseRecords(content, source, "activities") { obj ->
            val start = obj.huaweiTime("startTime") ?: obj.huaweiTime("start_time") ?: return@parseRecords null
            val end = obj.huaweiTime("endTime") ?: obj.huaweiTime("end_time") ?: return@parseRecords null
            if (end - start < 60_000L) return@parseRecords null

            val rawType = sequenceOf(
                "sportTypeId",
                "sport_type_id",
                "sportType",
                "sport_type",
                "workoutType",
                "activityType",
                "type"
            ).map { key -> obj.optString(key, "") }
                .firstOrNull { it.isNotBlank() }

            val canonicalType = HuaweiWorkoutTypeMapper.canonicalName(rawType)
            val exerciseType = HuaweiWorkoutTypeMapper.healthConnectType(canonicalType)
                ?: return@parseRecords null
            val explicitName = sequenceOf("name", "title", "workoutName")
                .map { key -> obj.optString(key, "").trim() }
                .firstOrNull { it.isNotBlank() }
            val title = explicitName ?: canonicalType

            ActivitySessionData(
                startTimeMs = start,
                endTimeMs = end,
                title = title,
                exerciseType = exerciseType,
                distanceMeters = obj.positiveDouble(
                    "totalDistance",
                    "total_distance",
                    "distanceMeters",
                    "distance_meters",
                    "distance"
                ),
                totalCaloriesKcal = obj.positiveDouble(
                    "totalCalories",
                    "total_calories",
                    "calories",
                    "kilocalories",
                    "kcal"
                ),
                // Only accept keys whose unit is explicit. Older Huawei
                // exports contain altitude fields with model-dependent units.
                elevationMeters = obj.positiveDouble(
                    "elevationGainMeters",
                    "elevation_gain_meters",
                    "ascentMeters",
                    "ascent_meters"
                ),
                steps = obj.nonNegativeLong(
                    "totalSteps",
                    "total_steps",
                    "steps",
                    "stepCount",
                    "step_count"
                )?.takeIf { it > 0L }
            )
        }

    private fun parseStepRecord(obj: JSONObject): StepData? {
        val start = obj.huaweiTime("startTime") ?: obj.huaweiTime("start_time") ?: return null
        val end = obj.huaweiTime("endTime") ?: obj.huaweiTime("end_time") ?: return null
        val count = obj.nonNegativeLong("value", "steps", "count") ?: return null
        return if (count > 0L && start < end) StepData(start, end, count) else null
    }

    private inline fun <T> parseRecords(
        content: String,
        source: String,
        label: String,
        parse: (JSONObject) -> T?
    ): List<T> {
        return try {
            val array = recordsArray(content) ?: return emptyList()
            val results = ArrayList<T>(array.length())
            for (index in 0 until array.length()) {
                val obj = array.optJSONObject(index) ?: continue
                parse(obj)?.let(results::add)
            }
            AppLogger.i(TAG, "Parsed ${results.size} $label records from $source")
            results
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to parse $label from $source: ${e.message}")
            emptyList()
        }
    }

    private fun recordsArray(content: String): JSONArray? = when (val root = parseJsonRootFlexible(content)) {
        is JSONArray -> root
        is JSONObject -> sequenceOf("data", "records", "items", "list")
            .mapNotNull(root::optJSONArray)
            .firstOrNull()
        else -> null
    }

    private fun inferKind(content: String): ExportKind? {
        val array = recordsArray(content) ?: return null
        val sample = (0 until minOf(array.length(), 20))
            .mapNotNull(array::optJSONObject)
            .firstOrNull() ?: return null

        return when {
            sample.hasAny("steps", "stepCount", "step_count") -> ExportKind.STEPS
            sample.hasAny("distance", "meters", "metres") -> ExportKind.DISTANCE
            sample.hasAny("calories", "calorie", "kilocalories", "kcal") -> ExportKind.CALORIES
            sample.hasAny("sportType", "sport_type", "workoutType", "activityType") -> ExportKind.ACTIVITY
            else -> null
        }
    }

    private fun JSONObject.huaweiTime(key: String): Long? {
        val value = opt(key) ?: return null
        val raw = when (value) {
            is Number -> value.toLong()
            is String -> value.trim().toLongOrNull()
            else -> null
        }?.takeIf { it > 0L } ?: return null

        return if (raw < 10_000_000_000L) raw * 1000L else raw
    }

    private fun JSONObject.nonNegativeLong(vararg keys: String): Long? {
        for (key in keys) {
            val value = opt(key) ?: continue
            val parsed = when (value) {
                is Number -> value.toLong()
                is String -> value.trim().toLongOrNull()
                else -> null
            }
            if (parsed != null && parsed >= 0L) return parsed
        }
        return null
    }

    private fun JSONObject.positiveDouble(vararg keys: String): Double? {
        for (key in keys) {
            val value = opt(key) ?: continue
            val parsed = when (value) {
                is Number -> value.toDouble()
                is String -> value.trim().replace(',', '.').toDoubleOrNull()
                else -> null
            }
            if (parsed != null && parsed.isFinite() && parsed > 0.0) return parsed
        }
        return null
    }

    private fun JSONObject.hasAny(vararg keys: String): Boolean = keys.any(::has)

    private fun parseJsonRootFlexible(content: String): Any? {
        val trimmed = content.trimStart('\uFEFF', ' ', '\t', '\r', '\n')
        return try {
            JSONObject(trimmed)
        } catch (_: Exception) {
            try {
                JSONArray(trimmed)
            } catch (_: Exception) {
                null
            }
        }
    }

    private fun InputStream.readBytesBounded(maxBytes: Int): ByteArray {
        require(maxBytes > 0) { "Safe read budget is exhausted" }
        val output = ByteArrayOutputStream(minOf(maxBytes, 64 * 1024))
        val buffer = ByteArray(8 * 1024)
        var total = 0

        while (true) {
            val read = read(buffer)
            if (read < 0) break
            total += read
            if (total > maxBytes) {
                throw IllegalArgumentException("Huawei JSON entry exceeds the safe size limit")
            }
            output.write(buffer, 0, read)
        }
        return output.toByteArray()
    }
}
