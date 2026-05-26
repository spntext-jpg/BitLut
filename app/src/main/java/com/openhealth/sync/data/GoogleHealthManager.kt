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
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.units.Energy
import androidx.health.connect.client.units.Length
import com.openhealth.sync.util.AppLogger
import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset

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

class GoogleHealthManager(private val context: Context) {

    val permissions: Set<String> = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(DistanceRecord::class),
        HealthPermission.getWritePermission(FloorsClimbedRecord::class),
        HealthPermission.getWritePermission(ElevationGainedRecord::class),
        HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getWritePermission(ExerciseSessionRecord::class)
    )

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
        val stepsOk = writeStepsBatch(snapshot.steps)
        val distanceOk = writeDistanceBatch(snapshot.distances)
        val floorsOk = writeFloorsBatch(snapshot.floors)
        val elevationOk = writeElevationBatch(snapshot.elevations)
        val caloriesOk = writeActiveCaloriesBatch(snapshot.activeCalories)
        val sessionsOk = writeActivitySessionsBatch(snapshot.activities)

        AppLogger.i(
            TAG,
            "Write summary: steps=$stepsOk distance=$distanceOk floors=$floorsOk elevation=$elevationOk calories=$caloriesOk sessions=$sessionsOk"
        )

        return stepsOk && distanceOk && floorsOk && elevationOk && caloriesOk && sessionsOk
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
                    endZoneOffset = offset(end)
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
                    endZoneOffset = offset(end)
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
                    endZoneOffset = offset(end)
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
                    endZoneOffset = offset(end)
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
                    endZoneOffset = offset(end)
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
                    title = it.title
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

    private fun offset(instant: Instant): ZoneOffset = zoneRules.getOffset(instant)
}
