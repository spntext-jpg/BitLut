#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")

MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
POLICY = ROOT / "app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt"
GOOGLE = ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
README = ROOT / "README.md"
CONTEXT = ROOT / "CONTEXT.md"

VERIFY_FILES = [
    ROOT / "scripts/verify_health_coverage.py",
    ROOT / "scripts/verify_huawei_activity_sync_sprint.py",
    ROOT / "scripts/verify_sync_reliability.py",
]

ALLOWED_HEALTH_CONNECT_PERMISSIONS = [
    "READ_STEPS",
    "WRITE_STEPS",
    "READ_DISTANCE",
    "WRITE_DISTANCE",
    "READ_FLOORS_CLIMBED",
    "WRITE_FLOORS_CLIMBED",
    "READ_ELEVATION_GAINED",
    "WRITE_ELEVATION_GAINED",
    "READ_ACTIVE_CALORIES_BURNED",
    "WRITE_ACTIVE_CALORIES_BURNED",
    "READ_EXERCISE",
    "WRITE_EXERCISE",
]

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

# 1. Manifest: remove all Health Connect permissions, then add only approved activity scope.
manifest = read(MANIFEST)
manifest = re.sub(
    r'\s*<uses-permission\s+android:name="android\.permission\.health\.[A-Z_]+"\s*/>',
    "",
    manifest,
)

permission_block = (
    "\n"
    "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope. -->\n"
    + "".join(
        f'    <uses-permission android:name="android.permission.health.{permission}" />\n'
        for permission in ALLOWED_HEALTH_CONNECT_PERMISSIONS
    )
)

if "<queries>" in manifest:
    manifest = manifest.replace("<queries>", permission_block + "\n    <queries>", 1)
elif "<application" in manifest:
    manifest = manifest.replace("<application", permission_block + "\n    <application", 1)
else:
    raise RuntimeError("AndroidManifest.xml has no <queries> or <application> anchor")

manifest = re.sub(r"\n{3,}", "\n\n", manifest)
write(MANIFEST, manifest)

# 2. Policy: strict activity-only.
write(POLICY, '''package com.openhealth.sync.config

import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.StepsRecord

/**
 * BitLut v1.9.6 strict Health Connect permission policy.
 *
 * Huawei AppGallery approval currently covers activity/basic sport read-only data:
 * - Step
 * - Distance, ascent and altitude
 * - Active Hours
 * - Daily Activity Summary
 * - Activity record
 * - Activity
 *
 * Sleep, pulse, SpO2, HRV, stress and Activity Intensity are intentionally not
 * requested, not read and not written in this release.
 */
object HealthPermissionPolicy {
    val huaweiImportReadPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class),
        HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
    )

    val importWritePermissions: Set<String> = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(DistanceRecord::class),
        HealthPermission.getWritePermission(FloorsClimbedRecord::class),
        HealthPermission.getWritePermission(ElevationGainedRecord::class),
        HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getWritePermission(ExerciseSessionRecord::class),
    )

    val optionalDashboardReadPermissions: Set<String> = emptySet()

    val syncPermissions: Set<String> = huaweiImportReadPermissions + importWritePermissions
    val requestPermissions: Set<String> = syncPermissions
    val dashboardReadPermissions: Set<String> = huaweiImportReadPermissions

    val dashboardPermissions: Set<String> = dashboardReadPermissions
    val importPermissions: Set<String> = syncPermissions
    val allPermissions: Set<String> = requestPermissions

    fun isRequiredSyncPermission(permission: String): Boolean = permission in syncPermissions
    fun isOptionalDashboardPermission(permission: String): Boolean = false
}
''')

# 3. GoogleHealthManager: rewrite clean strict activity-only implementation.
write(GOOGLE, '''package com.openhealth.sync.data

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.Record
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.metadata.Metadata
import androidx.health.connect.client.request.AggregateRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.health.connect.client.units.Energy
import androidx.health.connect.client.units.Length
import com.openhealth.sync.config.HealthPermissionPolicy
import com.openhealth.sync.util.AppLogger
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZoneOffset
import java.util.Locale
import kotlinx.coroutines.CancellationException
import kotlin.reflect.KClass

private const val TAG = "GoogleHealthManager"
private const val WRITE_BATCH_SIZE = 400

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
    val workoutMinutesToday: Long,
    val activeHoursToday: Int,
    val sleepHours: Double,
    val sleepQualityScore: Int?,
    val heartRateBpm: Long?,
    val heartRateTodayBars: List<MetricBar>,
    val stressScore: Int?,
    val spo2Percent: Double?,
    val stepsBars: List<MetricBar>,
    val sleepBars: List<MetricBar>,
    val heartRateBars: List<MetricBar>,
    val recentWorkouts: List<ActivitySessionData>,
    val workoutSummaries: List<WorkoutTypeSummary>
)

data class MetricBar(
    val startDate: LocalDate,
    val endDate: LocalDate,
    val value: Double
)

fun computeMetricBarRanges(daysBack: Int, today: LocalDate = LocalDate.now()): List<Pair<LocalDate, LocalDate>> {
    return when (daysBack) {
        7 -> (0 until 7).map { index ->
            val day = today.minusDays((6 - index).toLong())
            day to day
        }
        14 -> (0 until 7).map { index ->
            val start = today.minusDays((13 - index * 2).toLong())
            start to start.plusDays(1)
        }
        30 -> bucketsOfEqualSize(daysBack, bucketCount = 5, today = today)
        60 -> bucketsOfEqualSize(daysBack, bucketCount = 8, today = today)
        90 -> bucketsOfEqualSize(daysBack, bucketCount = 13, today = today)
        180 -> calendarMonthBuckets(monthCount = 6, today = today)
        365 -> calendarMonthBuckets(monthCount = 12, today = today)
        else -> bucketsOfEqualSize(daysBack, bucketCount = (daysBack / 7).coerceIn(1, 13), today = today)
    }
}

private fun bucketsOfEqualSize(totalDays: Int, bucketCount: Int, today: LocalDate): List<Pair<LocalDate, LocalDate>> {
    val safeDays = totalDays.coerceAtLeast(1)
    val safeBuckets = bucketCount.coerceAtLeast(1)
    val startDate = today.minusDays((safeDays - 1).toLong())
    val baseSize = safeDays / safeBuckets
    val remainder = safeDays % safeBuckets
    val ranges = mutableListOf<Pair<LocalDate, LocalDate>>()
    var cursor = startDate

    for (index in 0 until safeBuckets) {
        val size = (baseSize + if (index < remainder) 1 else 0).coerceAtLeast(1)
        val end = cursor.plusDays((size - 1).toLong())
        ranges.add(cursor to minOf(end, today))
        cursor = end.plusDays(1)
        if (cursor > today) break
    }

    return ranges
}

private fun calendarMonthBuckets(monthCount: Int, today: LocalDate): List<Pair<LocalDate, LocalDate>> {
    return (0 until monthCount).map { index ->
        val monthStart = today.withDayOfMonth(1).minusMonths((monthCount - 1 - index).toLong())
        val monthEnd = monthStart.plusMonths(1).minusDays(1)
        monthStart to minOf(monthEnd, today)
    }
}

class GoogleHealthManager(private val context: Context) {

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
            AppLogger.w(TAG, "Health Connect SDK is not available")
            null
        }
    }

    val permissions: Set<String> = HealthPermissionPolicy.requestPermissions

    fun requiredPermissions(): Set<String> = HealthPermissionPolicy.syncPermissions

    fun getStatus(): HealthConnectStatus {
        val sdkStatus = HealthConnectClient.getSdkStatus(context)
        val installedPackage = findInstalledHcPackage()

        AppLogger.i(
            TAG,
            "getSdkStatus()=$sdkStatus installedPackage=${installedPackage ?: "none"} API=${Build.VERSION.SDK_INT} device=${Build.MODEL}"
        )

        return when (sdkStatus) {
            HealthConnectClient.SDK_AVAILABLE -> HealthConnectStatus.AVAILABLE
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> HealthConnectStatus.NEEDS_UPDATE
            else -> if (installedPackage != null) HealthConnectStatus.NEEDS_UPDATE else HealthConnectStatus.NOT_INSTALLED
        }
    }

    fun findInstalledHcPackage(): String? {
        for (packageName in HC_PACKAGES) {
            try {
                context.packageManager.getPackageInfo(packageName, 0)
                AppLogger.d(TAG, "Found Health Connect package: $packageName")
                return packageName
            } catch (_: PackageManager.NameNotFoundException) {
                AppLogger.d(TAG, "Health Connect package not found: $packageName")
            }
        }
        return null
    }

    private suspend fun grantedPermissionsOrEmpty(): Set<String> {
        val client = healthConnectClient ?: return emptySet()
        return try {
            client.permissionController.getGrantedPermissions()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Permission snapshot failed: ${e.message}", e)
            emptySet()
        }
    }

    suspend fun missingRequiredPermissions(): Set<String> {
        return try {
            requiredPermissions() - grantedPermissionsOrEmpty()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Missing permission check failed: ${e.message}", e)
            requiredPermissions()
        }
    }

    suspend fun hasAllPermissions(): Boolean {
        return try {
            val granted = grantedPermissionsOrEmpty()
            AppLogger.d(TAG, "Granted Health Connect permissions: $granted")
            granted.containsAll(requiredPermissions())
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

        return replaceRecords("steps", valid, StepsRecord::class)
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

        return replaceRecords("distance", valid, DistanceRecord::class)
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

        return replaceRecords("floors", valid, FloorsClimbedRecord::class)
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

        return replaceRecords("elevation", valid, ElevationGainedRecord::class)
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

        return replaceRecords("activeCalories", valid, ActiveCaloriesBurnedRecord::class)
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

        return replaceRecords("activitySessions", valid, ExerciseSessionRecord::class)
    }

    private suspend fun replaceRecords(
        label: String,
        records: List<Record>,
        recordType: KClass<out Record>
    ): Boolean {
        val client = healthConnectClient ?: run {
            AppLogger.e(TAG, "write $label: no Health Connect client")
            return false
        }

        if (records.isEmpty()) {
            AppLogger.i(TAG, "No $label records to write")
            return true
        }

        return try {
            records.chunked(WRITE_BATCH_SIZE).forEach { chunk ->
                val clientRecordIds = chunk.mapNotNull { it.metadata.clientRecordId }
                if (clientRecordIds.isNotEmpty()) {
                    client.deleteRecords(recordType, emptyList(), clientRecordIds)
                }
                client.insertRecords(chunk)
            }
            AppLogger.i(TAG, "Replaced ${records.size} $label records")
            true
        } catch (e: CancellationException) {
            throw e
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "write $label denied by Health Connect permission policy: ${e.message}", e)
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "write $label failed: ${e.message}", e)
            false
        }
    }

    suspend fun readDashboardSnapshot(daysBack: Int): GoogleDashboardSnapshot? {
        val client = healthConnectClient ?: return null
        return try {
            val startOfToday = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val now = Instant.now()

            val stepsToday = client.aggregate(
                AggregateRequest(
                    metrics = setOf(StepsRecord.COUNT_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[StepsRecord.COUNT_TOTAL] ?: 0L

            val distanceMeters = client.aggregate(
                AggregateRequest(
                    metrics = setOf(DistanceRecord.DISTANCE_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[DistanceRecord.DISTANCE_TOTAL]?.inMeters ?: 0.0

            val caloriesKcal = client.aggregate(
                AggregateRequest(
                    metrics = setOf(ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL]?.inKilocalories ?: 0.0

            GoogleDashboardSnapshot(
                stepsToday = stepsToday,
                distanceMeters = distanceMeters,
                caloriesKcal = caloriesKcal,
                workoutMinutesToday = readWorkoutMinutesToday(),
                activeHoursToday = readActiveHoursToday(),
                sleepHours = 0.0,
                sleepQualityScore = null,
                heartRateBpm = null,
                heartRateTodayBars = emptyList(),
                stressScore = null,
                spo2Percent = null,
                stepsBars = readStepsBars(daysBack),
                sleepBars = emptyList(),
                heartRateBars = emptyList(),
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
        val client = healthConnectClient ?: return 0L
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = Instant.now()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = StepsRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, end)
                )
            ).records.sumOf { it.count }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readStepsToday failed: ${e.message}", e)
            0L
        }
    }

    suspend fun readStepsBars(daysBack: Int): List<MetricBar> {
        val client = healthConnectClient ?: return emptyList()
        val ranges = computeMetricBarRanges(daysBack)
        return ranges.map { (start, end) ->
            val rangeStart = start.atStartOfDay(ZoneId.systemDefault()).toInstant()
            val rangeEnd = end.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val steps = try {
                val response = client.aggregate(
                    AggregateRequest(
                        metrics = setOf(StepsRecord.COUNT_TOTAL),
                        timeRangeFilter = TimeRangeFilter.between(rangeStart, rangeEnd)
                    )
                )
                response[StepsRecord.COUNT_TOTAL] ?: 0L
            } catch (e: Exception) {
                AppLogger.e(TAG, "readStepsBars failed for $start..$end: ${e.message}", e)
                0L
            }
            MetricBar(start, end, steps.toDouble())
        }
    }

    suspend fun readDistanceToday(): Double {
        val client = healthConnectClient ?: return 0.0
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = DistanceRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
                )
            ).records.sumOf { it.distance.inMeters }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readDistanceToday failed: ${e.message}", e)
            0.0
        }
    }

    suspend fun readCaloriesToday(): Double {
        val client = healthConnectClient ?: return 0.0
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = ActiveCaloriesBurnedRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
                )
            ).records.sumOf { it.energy.inKilocalories }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readCaloriesToday failed: ${e.message}", e)
            0.0
        }
    }

    suspend fun readRecentWorkouts(limit: Int = 5): List<ActivitySessionData> {
        val client = healthConnectClient ?: return emptyList()
        return try {
            val start = LocalDate.now().minusDays(30).atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = ExerciseSessionRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
                )
            ).records
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
            AppLogger.e(TAG, "readRecentWorkouts failed: ${e.message}", e)
            emptyList()
        }
    }

    suspend fun readWorkoutSummariesByType(daysBack: Int): List<WorkoutTypeSummary> {
        val client = healthConnectClient ?: return emptyList()
        return try {
            val start = LocalDate.now().minusDays(daysBack.toLong().coerceAtLeast(1L) - 1L)
                .atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = Instant.now()

            val allRecords = mutableListOf<ExerciseSessionRecord>()
            var pageToken: String? = null

            do {
                val response = client.readRecords(
                    ReadRecordsRequest(
                        recordType = ExerciseSessionRecord::class,
                        timeRangeFilter = TimeRangeFilter.between(start, end),
                        pageToken = pageToken
                    )
                )
                allRecords.addAll(response.records)
                pageToken = response.pageToken
            } while (pageToken != null)

            allRecords
                .groupBy { it.exerciseType }
                .map { (type, sessions) ->
                    val totalMinutes = sessions.sumOf { session ->
                        java.time.Duration.between(session.startTime, session.endTime).toMinutes().coerceAtLeast(0L)
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
            AppLogger.e(TAG, "readWorkoutSummariesByType failed: ${e.message}", e)
            emptyList()
        }
    }

    suspend fun readWorkoutMinutesToday(): Long {
        val client = healthConnectClient ?: return 0L
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = ExerciseSessionRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
                )
            ).records.sumOf {
                java.time.Duration.between(it.startTime, it.endTime).toMinutes().coerceAtLeast(0L)
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readWorkoutMinutesToday failed: ${e.message}", e)
            0L
        }
    }

    suspend fun readActiveHoursToday(): Int {
        val client = healthConnectClient ?: return 0
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = StepsRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
                )
            ).records
                .filter { it.count > 0 }
                .map { it.startTime.atZone(ZoneId.systemDefault()).hour }
                .toSet()
                .size
        } catch (e: Exception) {
            AppLogger.e(TAG, "readActiveHoursToday failed: ${e.message}", e)
            0
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

        if (!ru) {
            return normalized.replaceFirstChar { it.titlecase(Locale.ROOT) }
        }

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

    private fun offset(instant: Instant): ZoneOffset = zoneRules.getOffset(instant)
}
''')

# 4. Verifiers: strict activity-only.
strict_verifier = r'''#!/usr/bin/env python3
from pathlib import Path
import re
import sys

errors = []

def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

manifest = read("app/src/main/AndroidManifest.xml")
policy = read("app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt")
google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
huawei = read("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")

allowed = [
    "READ_STEPS",
    "WRITE_STEPS",
    "READ_DISTANCE",
    "WRITE_DISTANCE",
    "READ_FLOORS_CLIMBED",
    "WRITE_FLOORS_CLIMBED",
    "READ_ELEVATION_GAINED",
    "WRITE_ELEVATION_GAINED",
    "READ_ACTIVE_CALORIES_BURNED",
    "WRITE_ACTIVE_CALORIES_BURNED",
    "READ_EXERCISE",
    "WRITE_EXERCISE",
]

for permission in allowed:
    if f"android.permission.health.{permission}" not in manifest:
        errors.append(f"Manifest missing {permission}")

for forbidden in [
    "READ_SLEEP",
    "WRITE_SLEEP",
    "READ_HEART_RATE",
    "WRITE_HEART_RATE",
    "READ_OXYGEN_SATURATION",
    "WRITE_OXYGEN_SATURATION",
    "READ_HEART_RATE_VARIABILITY",
    "WRITE_HEART_RATE_VARIABILITY",
    "READ_ACTIVITY_INTENSITY",
    "WRITE_ACTIVITY_INTENSITY",
]:
    if f"android.permission.health.{forbidden}" in manifest:
        errors.append(f"Manifest must not declare {forbidden}")

permissions = re.findall(r"android\.permission\.health\.([A-Z_]+)", manifest)
duplicates = sorted({p for p in permissions if permissions.count(p) > 1})
if duplicates:
    errors.append(f"Manifest has duplicate Health Connect permissions: {duplicates}")

for token in [
    "huaweiImportReadPermissions",
    "importWritePermissions",
    "optionalDashboardReadPermissions: Set<String> = emptySet()",
    "syncPermissions",
    "requestPermissions: Set<String> = syncPermissions",
    "dashboardReadPermissions",
]:
    if token not in policy:
        errors.append(f"HealthPermissionPolicy missing strict token: {token}")

for forbidden in [
    "SleepSessionRecord",
    "HeartRateRecord",
    "HeartRateVariabilityRmssdRecord",
    "OxygenSaturationRecord",
    "READ_SLEEP",
    "WRITE_SLEEP",
    "READ_HEART_RATE",
    "WRITE_HEART_RATE",
    "OXYGEN_SATURATION",
    "HEART_RATE_VARIABILITY",
    "ACTIVITY_INTENSITY",
]:
    if forbidden in policy:
        errors.append(f"HealthPermissionPolicy must not contain {forbidden}")

for forbidden in [
    "SleepSessionRecord",
    "HeartRateRecord",
    "HeartRateVariabilityRmssdRecord",
    "OxygenSaturationRecord",
        "readSleepLastNight",
    "readSleepQualityScoreLastNight",
    "readSleepBars",
    "readHeartRateTodayBars",
    "readHeartRateBars",
    "readAverageHeartRateToday",
    "readLatestSpo2Percent",
    "readStressScoreToday",
    "isPermissionGranted",
]:
    if forbidden in google:
        errors.append(f"GoogleHealthManager must not contain {forbidden}")

if google.count("private suspend fun insertRecords(") != 0:
    errors.append("GoogleHealthManager must not contain legacy insertRecords helper")

if google.count("private suspend fun replaceRecords(") != 1:
    errors.append("GoogleHealthManager must contain exactly one replaceRecords helper")

if "deleteRecords(recordType, emptyList(), clientRecordIds)" not in google:
    errors.append("GoogleHealthManager must delete by clientRecordId before insert")

if "insertRecords(chunk)" not in google:
    errors.append("GoogleHealthManager must insert chunked records")

for token in [
    "HEALTHKIT_STEP_READ",
    "HEALTHKIT_DISTANCE_READ",
    "HEALTHKIT_ACTIVITY_READ",
    "HEALTHKIT_ACTIVITY_RECORD_READ",
]:
    if token not in huawei:
        errors.append(f"HuaweiHealthManager missing approved Huawei scope {token}")

for forbidden in [
    "HEALTHKIT_SLEEP",
    "HEALTHKIT_HEARTRATE",
    "HEALTHKIT_BLOODOXYGEN",
    "HEALTHKIT_STRESS",
]:
    if forbidden in huawei.upper():
        errors.append(f"HuaweiHealthManager must not request {forbidden}")

if "requestGoogleHealthPermissions()" not in main:
    errors.append("MainActivity must wire Google connect button to permission request")

if errors:
    print("Strict Huawei activity sync verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Strict Huawei activity sync verification passed.")
'''

for verifier in VERIFY_FILES:
    write(verifier, strict_verifier)
    verifier.chmod(0o755)

# 5. README / CONTEXT notes.
scope_note = """
## BitLut v1.9.6 strict health-data scope

BitLut v1.9.6 is locked to the Huawei Health approval scope requested in AppGallery:

- Step
- Distance, ascent and altitude
- Active Hours
- Daily Activity Summary
- Activity record
- Activity

The app does not request, read, write or infer sleep, pulse, SpO2, HRV, stress or Activity Intensity data in this release.

Health Connect export is limited to Huawei-derived activity/basic sport records: `StepsRecord`, `DistanceRecord`, `FloorsClimbedRecord`, `ElevationGainedRecord`, `ActiveCaloriesBurnedRecord` and `ExerciseSessionRecord`.
"""

for doc in [README, CONTEXT]:
    if doc.exists():
        content = read(doc)
        if "## BitLut v1.9.6 strict health-data scope" not in content:
            content = content.rstrip() + "\n\n" + scope_note.strip() + "\n"
        write(doc, content)

# 6. Self-check.
app_combined = "\n".join([
    read(MANIFEST),
    read(POLICY),
    read(GOOGLE),
])

forbidden_app_terms = [
    "SleepSessionRecord",
    "HeartRateRecord",
    "HeartRateVariabilityRmssdRecord",
    "OxygenSaturationRecord",
        "readSleepLastNight",
    "readSleepQualityScoreLastNight",
    "readSleepBars",
    "readHeartRateTodayBars",
    "readHeartRateBars",
    "readAverageHeartRateToday",
    "readLatestSpo2Percent",
    "readStressScoreToday",
    "isPermissionGranted",
    "android.permission.health.READ_SLEEP",
    "android.permission.health.WRITE_SLEEP",
    "android.permission.health.READ_HEART_RATE",
    "android.permission.health.WRITE_HEART_RATE",
    "android.permission.health.READ_OXYGEN_SATURATION",
    "android.permission.health.WRITE_OXYGEN_SATURATION",
    "android.permission.health.READ_HEART_RATE_VARIABILITY",
    "android.permission.health.WRITE_HEART_RATE_VARIABILITY",
    "android.permission.health.READ_ACTIVITY_INTENSITY",
    "android.permission.health.WRITE_ACTIVITY_INTENSITY",
]

bad = [term for term in forbidden_app_terms if term in app_combined]
if bad:
    print("Patch failed. Forbidden app terms remain:")
    for term in bad:
        print(" -", term)
    raise SystemExit(1)

print("Rewrote Health Connect integration to strict activity-only scope.")
