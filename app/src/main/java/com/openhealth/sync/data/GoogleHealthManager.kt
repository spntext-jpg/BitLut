package com.openhealth.sync.data

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
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
            AppLogger.w(TAG, "SDK not available — skipping client creation")
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

    suspend fun writeStepsBatch(records: List<StepData>): Boolean {
        val c = healthConnectClient ?: run {
            AppLogger.e(TAG, "writeStepsBatch: no client")
            return false
        }

        val valid = records
            .filter { it.count > 0 && it.startTimeMs < it.endTimeMs }
            .map { d ->
                val start: Instant = Instant.ofEpochMilli(d.startTimeMs)
                val end: Instant = Instant.ofEpochMilli(d.endTimeMs)
                val startOff: ZoneOffset = zoneRules.getOffset(start)
                val endOff: ZoneOffset = zoneRules.getOffset(end)

                StepsRecord(
                    count = d.count,
                    startTime = start,
                    endTime = end,
                    startZoneOffset = startOff,
                    endZoneOffset = endOff
                )
            }

        if (valid.isEmpty()) return true

        return try {
            c.insertRecords(valid)
            AppLogger.d(TAG, "Wrote ${valid.size} step records")
            true
        } catch (e: Exception) {
            AppLogger.e(TAG, "writeStepsBatch failed: ${e.message}", e)
            false
        }
    }

    suspend fun writeHeartRateBatch(records: List<HeartRateData>): Boolean {
        if (records.isNotEmpty()) {
            AppLogger.w(TAG, "Skipping ${records.size} heart-rate samples: Heart Rate scope is not approved yet")
        }
        return true
    }
}

data class StepData(val startTimeMs: Long, val endTimeMs: Long, val count: Long)
data class HeartRateData(val timeMs: Long, val beatsPerMinute: Long)
