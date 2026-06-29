package com.openhealth.sync.data

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.LocalDate
import java.time.ZonedDateTime
import androidx.health.connect.client.units.Energy
import androidx.health.connect.client.units.Length
import com.openhealth.sync.util.AppLogger
import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset
import com.openhealth.sync.config.HealthPermissionPolicy
import java.util.Locale
import androidx.health.connect.client.records.metadata.Metadata
import androidx.health.connect.client.request.AggregateRequest
import kotlinx.coroutines.CancellationException

private const val TAG = "GoogleHealthManager"

private val HC_PACKAGES = listOf(
    "com.google.android.apps.healthdata",
    "com.google.android.health.connect"
)

enum class HealthConnectStatus {
    AVAILABLE,
    NOT_INSTALLED,
    NEEDS_UPDATE,
    NOT_SUPPORTED
}

data class StepData(val startTimeMs: Long, val endTimeMs: Long, val count: Long)
data class DistanceData(val startTimeMs: Long, val endTimeMs: Long, val meters: Double)
data class FloorsData(val startTimeMs: Long, val endTimeMs: Long, val floors: Double)
data class ElevationData(val startTimeMs: Long, val endTimeMs: Long, val meters: Double)
data class ActiveCaloriesData(val startTimeMs: Long, val endTimeMs: Long, val kilocalories: Double)
data class ActivitySessionData(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val title: String = "Huawei activity",
    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT
)
data class WorkoutTypeSummary(
    val exerciseType: Int,
    val displayName: String,
    val sessionCount: Int,
    val totalDurationMinutes: Long
)

data class GoogleDashboardSnapshot(
    val stepsToday: Long,
    val distanceMeters: Double,
    val caloriesKcal: Double,
    val sleepHours: Double,
    val heartRateBpm: Long?,
    val stepsBars: List<MetricBar>,
    val sleepBars: List<MetricBar>,
    val heartRateBars: List<MetricBar>,
    val recentWorkouts: List<ActivitySessionData>,
    val workoutSummaries: List<WorkoutTypeSummary>
)

/** One bar in a History bar-chart widget: an aggregated value over [startDate]..[endDate]. */
data class MetricBar(
    val startDate: LocalDate,
    val endDate: LocalDate,
    val value: Double
)

/**
 * Computes the exact (start, end) date range for each bar a History widget should show,
 * for a given [daysBack] range selection. This is the single source of truth for the
 * "7 days -> 7 daily bars, 30 days -> 5 ~6-day bars, 180 days -> 6 calendar months" etc.
 * bucketing table, used by every per-metric bar-aggregation function below so the bucket
 * boundaries can never drift between steps/heart-rate/sleep.
 *
 * Critically, this also bounds the number of aggregate() calls a refresh ever makes per
 * metric to at most 13 (the 90-day case) regardless of how large daysBack is — this is
 * what keeps History range changes from ever approaching Health Connect's documented
 * rate limits, no matter which range the person picks.
 */
fun computeMetricBarRanges(daysBack: Int, today: LocalDate = LocalDate.now()): List<Pair<LocalDate, LocalDate>> {
    return when (daysBack) {
        7 -> (0 until 7).map { i ->
            val d = today.minusDays((6 - i).toLong())
            d to d
        }
        14 -> (0 until 7).map { i ->
            val start = today.minusDays((13 - i * 2).toLong())
            val end = start.plusDays(1)
            start to end
        }
        30 -> bucketsOfEqualSize(daysBack, bucketCount = 5, today = today)
        60 -> bucketsOfEqualSize(daysBack, bucketCount = 8, today = today)
        90 -> bucketsOfEqualSize(daysBack, bucketCount = 13, today = today)
        180 -> calendarMonthBuckets(monthCount = 6, today = today)
        365 -> calendarMonthBuckets(monthCount = 12, today = today)
        else -> bucketsOfEqualSize(daysBack, bucketCount = (daysBack / 7).coerceIn(1, 13), today = today)
    }
}

/** Splits the last [totalDays] days into [bucketCount] buckets of (nearly) equal size,
 *  oldest-first, with any remainder days absorbed into the earliest buckets so the most
 *  recent bucket (today's) is never the odd-sized one. */
private fun bucketsOfEqualSize(totalDays: Int, bucketCount: Int, today: LocalDate): List<Pair<LocalDate, LocalDate>> {
    val startDate = today.minusDays((totalDays - 1).toLong())
    val baseSize = totalDays / bucketCount
    val remainder = totalDays % bucketCount
    val ranges = mutableListOf<Pair<LocalDate, LocalDate>>()
    var cursor = startDate
    for (i in 0 until bucketCount) {
        val size = baseSize + if (i < remainder) 1 else 0
        val end = cursor.plusDays((size - 1).toLong())
        ranges.add(cursor to end)
        cursor = end.plusDays(1)
    }
    return ranges
}

/** Builds [monthCount] real calendar-month buckets ending in the current month. */
private fun calendarMonthBuckets(monthCount: Int, today: LocalDate): List<Pair<LocalDate, LocalDate>> {
    return (0 until monthCount).map { i ->
        val monthStart = today.withDayOfMonth(1).minusMonths((monthCount - 1 - i).toLong())
        val monthEnd = monthStart.plusMonths(1).minusDays(1)
        monthStart to minOf(monthEnd, today)
    }
}

class GoogleHealthManager(private val context: Context) {

    private fun generateRecordId(
        type: String,
        startTimeMs: Long,
        endTimeMs: Long,
        discriminator: String = ""
    ): String {
        val suffix = discriminator
            .replace(Regex("[^A-Za-z0-9_-]"), "_")
            .take(64)
            .let { if (it.isBlank()) "" else "_$it" }
        return "bitlut_${type}_${startTimeMs}_${endTimeMs}${suffix}"
    }

    private fun bitlutMetadata(
        type: String,
        startTimeMs: Long,
        endTimeMs: Long,
        discriminator: String = ""
    ): Metadata = Metadata(
        clientRecordId = generateRecordId(type, startTimeMs, endTimeMs, discriminator)
    )

    fun requiredPermissions(): Set<String> = HealthPermissionPolicy.syncPermissions


    // permissions is the single set actually requested via the UI permission launcher
    // AND checked by hasAllPermissions() before SyncWorker attempts to write Huawei
    // data into Health Connect. It is the read+write superset
    // (HealthPermissionPolicy.syncPermissions) -- using a narrower read-only set here
    // was the root cause behind a whole series of permission gaps (Sleep, HeartRate,
    // Distance, Calories were each missing read access at different points), and more
    // importantly meant the Huawei->Health Connect write path could never succeed:
    // SyncWorker checks hasAllPermissions() before writeSnapshot(), but the UI never
    // requested write permissions at all.
    val permissions: Set<String> = requiredPermissions()

    private val zoneRules by lazy { ZoneId.systemDefault().rules }

    val healthConnectClient: HealthConnectClient? by lazy {
        if (HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE) {
            try {
                HealthConnectClient.getOrCreate(context).also {
                    AppLogger.i(TAG, "HealthConnectClient created OK")
                }
            } catch (e: Exception) {
                AppLogger.e(TAG, "getOrCreate failed: ${e.message}", e)
                null
            }
        } else {
            AppLogger.w(TAG, "SDK not available - skipping client creation")
            null
        }
    }

    fun getStatus(): HealthConnectStatus {
        val sdkStatus = HealthConnectClient.getSdkStatus(context)
        val installedPkg = findInstalledHcPackage()

        AppLogger.i(
            TAG,
            "getSdkStatus()=$sdkStatus installedPackage=${installedPkg ?: "none"} API=${Build.VERSION.SDK_INT} device=${Build.MODEL}"
        )

        return when (sdkStatus) {
            HealthConnectClient.SDK_AVAILABLE -> {
                AppLogger.i(TAG, "HC: AVAILABLE (SDK confirms)")
                HealthConnectStatus.AVAILABLE
            }
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> {
                AppLogger.w(TAG, "HC: needs update")
                HealthConnectStatus.NEEDS_UPDATE
            }
            else -> {
                AppLogger.w(TAG, "HC: not available")
                if (installedPkg != null) HealthConnectStatus.NEEDS_UPDATE else HealthConnectStatus.NOT_INSTALLED
            }
        }
    }

    fun findInstalledHcPackage(): String? {
        for (pkg in HC_PACKAGES) {
            try {
                context.packageManager.getPackageInfo(pkg, 0)
                AppLogger.d(TAG, "Found HC package: $pkg")
                return pkg
            } catch (e: PackageManager.NameNotFoundException) {
                AppLogger.d(TAG, "HC package not found: $pkg")
            }
        }
        AppLogger.d(TAG, "No HC package found on device")
        return null
    }

    suspend fun hasAllPermissions(): Boolean {
        val c = healthConnectClient ?: return false
        return try {
            val granted = c.permissionController.getGrantedPermissions()
            AppLogger.d(TAG, "Granted permissions: $granted")
            granted.containsAll(permissions)
        } catch (e: Exception) {
            AppLogger.e(TAG, "Permission check failed: ${e.message}", e)
            false
        }
    }

    suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): Boolean {
        val results = listOf(
            "steps" to writeStepsBatch(snapshot.steps),
            "distance" to writeDistanceBatch(snapshot.distances),
            "floors" to writeFloorsBatch(snapshot.floors),
            "elevation" to writeElevationBatch(snapshot.elevations),
            "activeCalories" to writeActiveCaloriesBatch(snapshot.activeCalories),
            "activitySessions" to writeActivitySessionsBatch(snapshot.activities)
        )
        val failed = results.filterNot { it.second }.map { it.first }
        if (failed.isNotEmpty()) {
            AppLogger.e(TAG, "writeSnapshot partial failure: ${failed.joinToString()}")
        }
        return failed.isEmpty()
    }

    suspend fun writeStepsBatch(records: List<StepData>): Boolean {
        val valid = records
            .filter { it.count > 0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                StepsRecord(
                    count = it.count,
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
            metadata = bitlutMetadata("steps", start.toEpochMilli(), end.toEpochMilli())
        )
            }

        return insertRecords("steps", valid)
    }

    private suspend fun writeDistanceBatch(records: List<DistanceData>): Boolean {
        val valid = records
            .filter { it.meters > 0.0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                DistanceRecord(
                    distance = Length.meters(it.meters),
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
            metadata = bitlutMetadata("distance", start.toEpochMilli(), end.toEpochMilli())
        )
            }

        return insertRecords("distance", valid)
    }

    private suspend fun writeFloorsBatch(records: List<FloorsData>): Boolean {
        val valid = records
            .filter { it.floors > 0.0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                FloorsClimbedRecord(
                    floors = it.floors,
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
            metadata = bitlutMetadata("floors", start.toEpochMilli(), end.toEpochMilli())
        )
            }

        return insertRecords("floors", valid)
    }

    private suspend fun writeElevationBatch(records: List<ElevationData>): Boolean {
        val valid = records
            .filter { it.meters > 0.0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                ElevationGainedRecord(
                    elevation = Length.meters(it.meters),
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
            metadata = bitlutMetadata("elevation", start.toEpochMilli(), end.toEpochMilli())
        )
            }

        return insertRecords("elevation", valid)
    }

    private suspend fun writeActiveCaloriesBatch(records: List<ActiveCaloriesData>): Boolean {
        val valid = records
            .filter { it.kilocalories > 0.0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                ActiveCaloriesBurnedRecord(
                    energy = Energy.kilocalories(it.kilocalories),
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
            metadata = bitlutMetadata("active_calories", start.toEpochMilli(), end.toEpochMilli())
        )
            }

        return insertRecords("activeCalories", valid)
    }

    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {
        val valid = records
            .filter { it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                ExerciseSessionRecord(
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    exerciseType = it.exerciseType,
                    title = it.title,
            metadata = bitlutMetadata("exercise", start.toEpochMilli(), end.toEpochMilli())
        )
            }

        return insertRecords("activitySessions", valid)
    }

    private suspend fun insertRecords(label: String, records: List<androidx.health.connect.client.records.Record>): Boolean {
        val c = healthConnectClient ?: run {
            AppLogger.e(TAG, "write $label: no client")
            return false
        }

        if (records.isEmpty()) {
            AppLogger.i(TAG, "No $label records to write")
            return true
        }

        return try {
            c.insertRecords(records)
            AppLogger.i(TAG, "Wrote ${records.size} $label records")
            true
        } catch (e: Exception) {
            AppLogger.e(TAG, "write $label failed: ${e.message}", e)
            false
        }
    }

    // ── Read methods for Dashboard ────────────────────────────────────────────

    /**
     * Atomic dashboard refresh used by DashboardViewModel.
     *
     * Older code read each widget independently and every read method swallowed Health
     * Connect errors by returning 0/empty values. A transient Health Connect IPC/rate
     * failure could therefore look exactly like "real empty data" and wipe the UI until
     * the next refresh. This method performs a mandatory current-day aggregate preflight
     * first; if Health Connect is temporarily unavailable, it returns null and the UI keeps
     * the last good snapshot instead of showing disappearing data.
     */
    suspend fun readDashboardSnapshot(daysBack: Int): GoogleDashboardSnapshot? {
        val c = healthConnectClient ?: return null
        return try {
            val startOfToday = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val now = Instant.now()

            val stepsToday = c.aggregate(
                AggregateRequest(
                    metrics = setOf(StepsRecord.COUNT_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[StepsRecord.COUNT_TOTAL] ?: 0L

            val distanceMeters = c.aggregate(
                AggregateRequest(
                    metrics = setOf(DistanceRecord.DISTANCE_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[DistanceRecord.DISTANCE_TOTAL]?.inMeters ?: 0.0

            val caloriesKcal = c.aggregate(
                AggregateRequest(
                    metrics = setOf(ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL]?.inKilocalories ?: 0.0

            val heartRateBpm = c.aggregate(
                AggregateRequest(
                    metrics = setOf(HeartRateRecord.BPM_AVG),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[HeartRateRecord.BPM_AVG]

            GoogleDashboardSnapshot(
                stepsToday = stepsToday,
                distanceMeters = distanceMeters,
                caloriesKcal = caloriesKcal,
                sleepHours = readSleepLastNight(),
                heartRateBpm = heartRateBpm,
                stepsBars = readStepsBars(daysBack),
                sleepBars = readSleepBars(daysBack),
                heartRateBars = readHeartRateBars(daysBack),
                recentWorkouts = readRecentWorkouts(5),
                workoutSummaries = readWorkoutSummariesByType(daysBack)
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readDashboardSnapshot failed; preserving previous UI snapshot: ${e.message}", e)
            null
        }
    }

    suspend fun readStepsToday(): Long {
        val c = healthConnectClient ?: return 0L
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = Instant.now()
            val req = ReadRecordsRequest(
                recordType = StepsRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, end)
            )
            c.readRecords(req).records.sumOf { it.count }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readStepsToday failed: ${e.message}")
            0L
        }
    }

    /**
     * Daily step totals for the last [daysBack] days (inclusive of today).
     *
     * Uses one aggregate() call per BAR (see computeMetricBarRanges), not per day —
     * this bounds the number of calls to at most 13 regardless of how large daysBack
     * is, which is what keeps History range changes from approaching Health Connect's
     * documented rate limits. (An earlier version of this function called aggregate()
     * once per day, which meant up to 365 sequential calls on a single refresh at the
     * widest range — that was traced to the intermittent "Connect Google Health"
     * regression: enough IPC pressure on the Health Connect service to disrupt the
     * permission check that runs at the start of every refresh.)
     *
     * For cumulative types like StepsRecord, aggregate() is also the documented-
     * correct choice over readRecords() + manual summing, since it avoids double
     * counting from multiple data sources.
     */
    suspend fun readStepsBars(daysBack: Int): List<MetricBar> {
        val c = healthConnectClient ?: return emptyList()
        val ranges = computeMetricBarRanges(daysBack)
        return ranges.map { (start, end) ->
            val rangeStart = start.atStartOfDay(ZoneId.systemDefault()).toInstant()
            val rangeEnd = end.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val steps = try {
                val response = c.aggregate(
                    AggregateRequest(
                        metrics = setOf(StepsRecord.COUNT_TOTAL),
                        timeRangeFilter = TimeRangeFilter.between(rangeStart, rangeEnd)
                    )
                )
                response[StepsRecord.COUNT_TOTAL] ?: 0L
            } catch (e: Exception) {
                AppLogger.e(TAG, "readStepsBars failed for $start..$end: ${e.message}")
                0L
            }
            MetricBar(start, end, steps.toDouble())
        }
    }

    suspend fun readDistanceToday(): Double {
        val c = healthConnectClient ?: return 0.0
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val req = ReadRecordsRequest(
                recordType = DistanceRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
            )
            c.readRecords(req).records.sumOf { it.distance.inMeters }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readDistanceToday failed: ${e.message}")
            0.0
        }
    }

    suspend fun readCaloriesToday(): Double {
        val c = healthConnectClient ?: return 0.0
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val req = ReadRecordsRequest(
                recordType = ActiveCaloriesBurnedRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
            )
            c.readRecords(req).records.sumOf { it.energy.inKilocalories }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readCaloriesToday failed: ${e.message}")
            0.0
        }
    }

    suspend fun readRecentWorkouts(limit: Int = 5): List<ActivitySessionData> {
        val c = healthConnectClient ?: return emptyList()
        return try {
            val start = LocalDate.now().minusDays(30).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val req = ReadRecordsRequest(
                recordType = ExerciseSessionRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
            )
            c.readRecords(req).records
                .sortedByDescending { it.startTime }
                .take(limit)
                .map {
                    ActivitySessionData(
                        startTimeMs = it.startTime.toEpochMilli(),
                        endTimeMs = it.endTime.toEpochMilli(),
                        title = it.title ?: exerciseTypeName(it.exerciseType),
                        exerciseType = it.exerciseType
                    )
                }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readRecentWorkouts failed: ${e.message}")
            emptyList()
        }
    }

    /**
     * Reads every ExerciseSessionRecord in the last [daysBack] days and groups them by
     * exercise type, computing session count and total duration per type. This backs the
     * workout-type widgets on the History screen (one widget per exercise type that has
     * at least one session in the selected range).
     *
     * Pagination note: uses a pageToken loop rather than a single readRecords call, since
     * Health Connect's default page size is 1000 records — comfortably enough for realistic
     * workout volumes even at the maximum 365-day range, but looping is the documented-correct
     * way to read raw records regardless of volume, so we don't silently drop data for a very
     * active user.
     */
    suspend fun readWorkoutSummariesByType(daysBack: Int): List<WorkoutTypeSummary> {
        val c = healthConnectClient ?: return emptyList()
        return try {
            val start = LocalDate.now().minusDays(daysBack.toLong() - 1)
                .atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = Instant.now()

            val allRecords = mutableListOf<ExerciseSessionRecord>()
            var pageToken: String? = null
            do {
                val req = ReadRecordsRequest(
                    recordType = ExerciseSessionRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, end),
                    pageToken = pageToken
                )
                val response = c.readRecords(req)
                allRecords.addAll(response.records)
                pageToken = response.pageToken
            } while (pageToken != null)

            allRecords
                .groupBy { it.exerciseType }
                .map { (type, sessions) ->
                    val totalMinutes = sessions.sumOf { session ->
                        java.time.Duration.between(session.startTime, session.endTime).toMinutes()
                    }
                    WorkoutTypeSummary(
                        exerciseType = type,
                        displayName = exerciseTypeName(type),
                        sessionCount = sessions.size,
                        totalDurationMinutes = totalMinutes
                    )
                }
                .sortedByDescending { it.totalDurationMinutes }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readWorkoutSummariesByType failed: ${e.message}")
            emptyList()
        }
    }

    private fun exerciseTypeName(type: Int): String {
        val raw = when (type) {
            ExerciseSessionRecord.EXERCISE_TYPE_WALKING -> "walking"
            ExerciseSessionRecord.EXERCISE_TYPE_RUNNING -> "running"
            ExerciseSessionRecord.EXERCISE_TYPE_BIKING -> "cycling"
            ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER -> "open water swimming"
            ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL -> "pool swimming"
            ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING -> "strength training"
            ExerciseSessionRecord.EXERCISE_TYPE_YOGA -> "yoga"
            ExerciseSessionRecord.EXERCISE_TYPE_TENNIS -> "tennis"
            ExerciseSessionRecord.EXERCISE_TYPE_BASKETBALL -> "basketball"
            ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AMERICAN -> "american football"
            ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AUSTRALIAN -> "australian football"
            ExerciseSessionRecord.EXERCISE_TYPE_SOCCER -> "football"
            ExerciseSessionRecord.EXERCISE_TYPE_GOLF -> "golf"
            ExerciseSessionRecord.EXERCISE_TYPE_HIKING -> "hiking"
            ExerciseSessionRecord.EXERCISE_TYPE_ROWING -> "rowing"
            ExerciseSessionRecord.EXERCISE_TYPE_SKATING -> "skating"
            ExerciseSessionRecord.EXERCISE_TYPE_SKIING -> "skiing"
            ExerciseSessionRecord.EXERCISE_TYPE_SNOWBOARDING -> "snowboarding"
            ExerciseSessionRecord.EXERCISE_TYPE_VOLLEYBALL -> "volleyball"
            ExerciseSessionRecord.EXERCISE_TYPE_BADMINTON -> "badminton"
            ExerciseSessionRecord.EXERCISE_TYPE_BASEBALL -> "baseball"
            ExerciseSessionRecord.EXERCISE_TYPE_BOXING -> "boxing"
            ExerciseSessionRecord.EXERCISE_TYPE_DANCING -> "dancing"
            ExerciseSessionRecord.EXERCISE_TYPE_ELLIPTICAL -> "elliptical"
            ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING -> "hiit"
            ExerciseSessionRecord.EXERCISE_TYPE_PILATES -> "pilates"
            ExerciseSessionRecord.EXERCISE_TYPE_TABLE_TENNIS -> "table tennis"
            ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING -> "weightlifting"
            ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT -> "workout"
            else -> "workout"
        }
        return localizeWorkoutName(raw)
    }

    private fun localizeWorkoutName(name: String): String {
        val normalized = name.trim().lowercase(Locale.ROOT)
        val ru = Locale.getDefault().language == "ru"
        if (!ru) return normalized.replaceFirstChar { it.titlecase(Locale.ROOT) }
        return when (normalized) {
            "walking", "walk" -> "Ходьба"
            "running", "run" -> "Бег"
            "cycling", "biking", "bike" -> "Велосипед"
            "open water swimming" -> "Плавание в открытой воде"
            "pool swimming", "swimming", "swim" -> "Плавание"
            "strength training" -> "Силовая тренировка"
            "weightlifting" -> "Тяжёлая атлетика"
            "yoga" -> "Йога"
            "tennis" -> "Теннис"
            "table tennis" -> "Настольный теннис"
            "basketball" -> "Баскетбол"
            "football", "soccer" -> "Футбол"
            "american football" -> "Американский футбол"
            "australian football" -> "Австралийский футбол"
            "golf" -> "Гольф"
            "hiking" -> "Поход"
            "rowing" -> "Гребля"
            "skating" -> "Катание на коньках"
            "skiing" -> "Лыжи"
            "snowboarding" -> "Сноуборд"
            "volleyball" -> "Волейбол"
            "badminton" -> "Бадминтон"
            "baseball" -> "Бейсбол"
            "boxing" -> "Бокс"
            "dancing" -> "Танцы"
            "elliptical" -> "Эллиптический тренажёр"
            "hiit" -> "Интервальная тренировка"
            "pilates" -> "Пилатес"
            "workout", "other workout", "huawei activity", "activity" -> "Тренировка"
            else -> name.replaceFirstChar { it.titlecase(Locale.getDefault()) }
        }
    }




    suspend fun readSleepLastNight(): Double {
        val c = healthConnectClient ?: return 0.0
        return try {
            val now = LocalDate.now()
            val start = now.minusDays(1).atTime(12, 0).atZone(ZoneId.systemDefault()).toInstant()
            val end = now.atTime(12, 0).atZone(ZoneId.systemDefault()).toInstant()
            val req = ReadRecordsRequest(
                recordType = SleepSessionRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, end)
            )
            val sessions = c.readRecords(req).records
            sessions.sumOf { it.endTime.toEpochMilli() - it.startTime.toEpochMilli() } / 3_600_000.0
        } catch (e: Exception) {
            AppLogger.e(TAG, "readSleepLastNight failed: ${e.message}")
            0.0
        }
    }



    suspend fun readAverageHeartRateToday(): Long? {
        val c = healthConnectClient ?: return null
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val req = ReadRecordsRequest(
                recordType = HeartRateRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
            )
            val samples = c.readRecords(req).records.flatMap { it.samples }
            if (samples.isEmpty()) null else samples.map { it.beatsPerMinute }.average().toLong()
        } catch (e: Exception) {
            AppLogger.e(TAG, "readAverageHeartRateToday failed: ${e.message}")
            null
        }
    }

    /**
     * Sleep duration (hours) per bar for the last [daysBack] days (see
     * computeMetricBarRanges for how daysBack maps to bar boundaries). Kept as a
     * single readRecords() call with manual per-bar clipping (not aggregate()) because
     * SleepSessionRecord volume is inherently low — realistically one session per
     * night — so even at the maximum 365-day range this never approaches the
     * per-record volume that made the step/heart-rate functions worth converting to
     * aggregate(). This was never part of the rate-limit issue (it was always exactly
     * one IPC call regardless of daysBack); converted to bars here purely so the
     * History bar-chart widget has matching bar boundaries across all three metrics.
     */
    suspend fun readSleepBars(daysBack: Int): List<MetricBar> {
        val c = healthConnectClient ?: return emptyList()
        val ranges = computeMetricBarRanges(daysBack)
        return try {
            val overallStart = ranges.first().first.atStartOfDay(ZoneId.systemDefault()).toInstant()
            val overallEnd = ranges.last().second.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val req = ReadRecordsRequest(
                recordType = SleepSessionRecord::class,
                timeRangeFilter = TimeRangeFilter.between(overallStart, overallEnd)
            )
            val records = c.readRecords(req).records
            ranges.map { (start, end) ->
                val rangeStart = start.atStartOfDay(ZoneId.systemDefault()).toInstant()
                val rangeEnd = end.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
                val hours = records
                    .filter { it.endTime > rangeStart && it.startTime < rangeEnd }
                    .sumOf { session ->
                        val clippedStart = maxOf(session.startTime, rangeStart)
                        val clippedEnd = minOf(session.endTime, rangeEnd)
                        (clippedEnd.toEpochMilli() - clippedStart.toEpochMilli()).coerceAtLeast(0L)
                    } / 3_600_000.0
                MetricBar(start, end, hours)
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readSleepBars failed: ${e.message}")
            emptyList()
        }
    }

    /**
     * Average heart rate per bar for the last [daysBack] days. Uses one aggregate()
     * call per BAR (see computeMetricBarRanges), not per day — same fix as
     * readStepsBars, bounding the call count to at most 13 regardless of range.
     */
    suspend fun readHeartRateBars(daysBack: Int): List<MetricBar> {
        val c = healthConnectClient ?: return emptyList()
        val ranges = computeMetricBarRanges(daysBack)
        return ranges.map { (start, end) ->
            val rangeStart = start.atStartOfDay(ZoneId.systemDefault()).toInstant()
            val rangeEnd = end.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val avg = try {
                val response = c.aggregate(
                    AggregateRequest(
                        metrics = setOf(HeartRateRecord.BPM_AVG),
                        timeRangeFilter = TimeRangeFilter.between(rangeStart, rangeEnd)
                    )
                )
                response[HeartRateRecord.BPM_AVG]?.toDouble() ?: 0.0
            } catch (e: Exception) {
                AppLogger.e(TAG, "readHeartRateBars failed for $start..$end: ${e.message}")
                0.0
            }
            MetricBar(start, end, avg)
        }
    }

    private fun offset(instant: Instant): ZoneOffset = zoneRules.getOffset(instant)
}
