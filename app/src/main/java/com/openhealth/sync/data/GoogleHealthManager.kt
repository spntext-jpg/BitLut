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


    // Visible sprint mode: Google Health dashboard only.
    // Huawei import and Health Connect write pipeline stay in the codebase for post-approval enablement.
    // KISS: runtime UI asks only for the permissions needed by the current visible product.
    val dashboardPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class)
    )

    // Future Huawei import mode. Do not use at runtime until Huawei Health Kit approval is granted.
    val importPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getWritePermission(DistanceRecord::class),
        HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getWritePermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class),
        HealthPermission.getWritePermission(ElevationGainedRecord::class),
        HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
        HealthPermission.getWritePermission(ExerciseSessionRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getWritePermission(SleepSessionRecord::class)
    )

    val permissions: Set<String> = dashboardPermissions

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
    var ok = true
    ok = writeStepsBatch(snapshot.steps) && ok
    ok = writeDistanceBatch(snapshot.distances) && ok
    ok = writeFloorsBatch(snapshot.floors) && ok
    ok = writeElevationBatch(snapshot.elevations) && ok
    ok = writeActiveCaloriesBatch(snapshot.activeCalories) && ok
    ok = writeActivitySessionsBatch(snapshot.activities) && ok
    return ok
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
     * Uses one aggregate() call per day rather than a single aggregateGroupByPeriod
     * call. aggregateGroupByPeriod would be the more elegant single-call option, but
     * its per-bucket result object's exact start/end field could not be confirmed
     * against official documentation with full certainty, and this code ships close
     * to a store review window — so we use the AggregateRequest + response[metric]
     * pattern instead, which is documented verbatim in Android's official Health
     * Connect guide. The cost is daysBack calls instead of one, but these are local
     * IPC calls to the on-device Health Connect service, not network requests, so
     * this remains cheap even at the maximum 365-day range.
     *
     * For cumulative types like StepsRecord, aggregate() is also the documented-
     * correct choice over readRecords() + manual summing, since it avoids double
     * counting from multiple data sources.
     */
    suspend fun readDailySteps(daysBack: Int): List<Pair<LocalDate, Long>> {
        val c = healthConnectClient ?: return emptyList()
        val today = LocalDate.now()
        val startDate = today.minusDays((daysBack - 1).toLong())
        return (0 until daysBack).map { offset ->
            val date = startDate.plusDays(offset.toLong())
            val dayStart = date.atStartOfDay(ZoneId.systemDefault()).toInstant()
            val dayEnd = date.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val steps = try {
                val response = c.aggregate(
                    AggregateRequest(
                        metrics = setOf(StepsRecord.COUNT_TOTAL),
                        timeRangeFilter = TimeRangeFilter.between(dayStart, dayEnd)
                    )
                )
                response[StepsRecord.COUNT_TOTAL] ?: 0L
            } catch (e: Exception) {
                AppLogger.e(TAG, "readDailySteps failed for $date: ${e.message}")
                0L
            }
            date to steps
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
     * Daily sleep duration (hours) for the last [daysBack] days. Kept as readRecords()
     * with manual per-day clipping (not aggregate()) because SleepSessionRecord volume
     * is inherently low — realistically one session per night — so even at the maximum
     * 365-day range this never approaches the per-record volume that made the
     * equivalent step/heart-rate functions worth converting to aggregate() calls.
     */
    suspend fun readDailySleep(daysBack: Int): List<Pair<LocalDate, Double>> {
        val c = healthConnectClient ?: return emptyList()
        return try {
            val today = LocalDate.now()
            val startDate = today.minusDays((daysBack - 1).toLong())
            val start = startDate.atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = today.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val req = ReadRecordsRequest(
                recordType = SleepSessionRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, end)
            )
            val records = c.readRecords(req).records
            (0 until daysBack).map { offset ->
                val date = startDate.plusDays(offset.toLong())
                val dayStart = date.atStartOfDay(ZoneId.systemDefault()).toInstant()
                val dayEnd = date.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
                val hours = records
                    .filter { it.endTime > dayStart && it.startTime < dayEnd }
                    .sumOf { session ->
                        val clippedStart = maxOf(session.startTime, dayStart)
                        val clippedEnd = minOf(session.endTime, dayEnd)
                        (clippedEnd.toEpochMilli() - clippedStart.toEpochMilli()).coerceAtLeast(0L)
                    } / 3_600_000.0
                date to hours
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readDailySleep failed: ${e.message}")
            emptyList()
        }
    }

    /**
     * Daily average heart rate for the last [daysBack] days. Uses one aggregate()
     * call per day (HeartRateRecord.BPM_AVG) rather than reading all raw samples and
     * filtering per day — heart rate samples can be high-frequency (continuous
     * wearable sampling), so the old manual-filter approach risked the same
     * O(days x records) cost that was fixed for steps, and aggregate() is also the
     * officially recommended approach for this kind of statistical aggregation.
     */
    suspend fun readDailyAverageHeartRate(daysBack: Int): List<Pair<LocalDate, Long?>> {
        val c = healthConnectClient ?: return emptyList()
        val today = LocalDate.now()
        val startDate = today.minusDays((daysBack - 1).toLong())
        return (0 until daysBack).map { offset ->
            val date = startDate.plusDays(offset.toLong())
            val dayStart = date.atStartOfDay(ZoneId.systemDefault()).toInstant()
            val dayEnd = date.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val avg = try {
                val response = c.aggregate(
                    AggregateRequest(
                        metrics = setOf(HeartRateRecord.BPM_AVG),
                        timeRangeFilter = TimeRangeFilter.between(dayStart, dayEnd)
                    )
                )
                response[HeartRateRecord.BPM_AVG]
            } catch (e: Exception) {
                AppLogger.e(TAG, "readDailyAverageHeartRate failed for $date: ${e.message}")
                null
            }
            date to avg
        }
    }

    private fun offset(instant: Instant): ZoneOffset = zoneRules.getOffset(instant)
}
