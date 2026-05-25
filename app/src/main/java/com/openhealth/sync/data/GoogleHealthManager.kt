package com.openhealth.sync.data

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.StepsRecord
import com.openhealth.sync.util.AppLogger
import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset

private const val TAG = "GoogleHealthManager"

// ONLY real Health Connect package names — NOT com.google.android.gms
// GMS is Google Play Services and has nothing to do with Health Connect
private val HC_PACKAGES = listOf(
    "com.google.android.apps.healthdata",   // Standalone APK from Play Store (Android 9-13)
    "com.google.android.health.connect"     // Integrated module (Android 14+)
)

enum class HealthConnectStatus {
    AVAILABLE,       // SDK ready, client works, permissions can be requested
    NOT_INSTALLED,   // HC APK not on device — send to Play Store
    NEEDS_UPDATE,    // HC installed but too old
    NOT_SUPPORTED    // Device/OS cannot run HC at all
}

class GoogleHealthManager(private val context: Context) {

    val permissions: Set<String> = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(HeartRateRecord::class)
    )

    private val zoneRules by lazy { ZoneId.systemDefault().rules }

    // Lazily create client — null means HC is not usable on this device
    val healthConnectClient: HealthConnectClient? by lazy {
        // Only attempt if SDK explicitly says available
        if (HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE) {
            try {
                HealthConnectClient.getOrCreate(context).also {
                    AppLogger.i(TAG, "HealthConnectClient created OK")
                }
            } catch (e: Exception) {
                AppLogger.e(TAG, "getOrCreate failed: ${e.message}")
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

        AppLogger.i(TAG, "getSdkStatus()=$sdkStatus " +
            "installedPackage=${installedPkg ?: "none"} " +
            "API=${Build.VERSION.SDK_INT} device=${Build.MODEL}")

        return when (sdkStatus) {
            HealthConnectClient.SDK_AVAILABLE -> {
                AppLogger.i(TAG, "HC: AVAILABLE (SDK confirms)")
                HealthConnectStatus.AVAILABLE
            }
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> {
                AppLogger.w(TAG, "HC: needs update (sdkStatus=2)")
                // Only treat as needing update, never as AVAILABLE
                // Even if a package exists, the SDK version is incompatible
                HealthConnectStatus.NEEDS_UPDATE
            }
            else -> {
                AppLogger.w(TAG, "HC: not available (sdkStatus=$sdkStatus)")
                if (installedPkg != null) HealthConnectStatus.NEEDS_UPDATE
                else HealthConnectStatus.NOT_INSTALLED
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
            AppLogger.e(TAG, "Permission check failed: ${e.message}")
            false
        }
    }

    suspend fun writeStepsBatch(records: List<StepData>): Boolean {
        val c = healthConnectClient ?: run {
            AppLogger.e(TAG, "writeStepsBatch: no client"); return false
        }
        val valid = records.filter { it.count > 0 && it.startTimeMs < it.endTimeMs }.map { d ->
            val start: Instant       = Instant.ofEpochMilli(d.startTimeMs)
            val end: Instant         = Instant.ofEpochMilli(d.endTimeMs)
            val startOff: ZoneOffset = zoneRules.getOffset(start)
            val endOff: ZoneOffset   = zoneRules.getOffset(end)
            StepsRecord(count = d.count, startTime = start, endTime = end,
                startZoneOffset = startOff, endZoneOffset = endOff)
        }
        if (valid.isEmpty()) return true
        return try {
            c.insertRecords(valid)
            AppLogger.d(TAG, "Wrote ${valid.size} step records")
            true
        } catch (e: Exception) {
            AppLogger.e(TAG, "writeStepsBatch failed: ${e.message}")
            false
        }
    }

    suspend fun writeHeartRateBatch(records: List<HeartRateData>): Boolean {
        val c = healthConnectClient ?: run {
            AppLogger.e(TAG, "writeHeartRateBatch: no client"); return false
        }
        val valid = records.filter { it.beatsPerMinute > 0 }.map { d ->
            val time: Instant        = Instant.ofEpochMilli(d.timeMs)
            val end: Instant         = time.plusSeconds(1)
            val startOff: ZoneOffset = zoneRules.getOffset(time)
            val endOff: ZoneOffset   = zoneRules.getOffset(end)
            HeartRateRecord(startTime = time, endTime = end,
                startZoneOffset = startOff, endZoneOffset = endOff,
                samples = listOf(HeartRateRecord.Sample(
                    time = time, beatsPerMinute = d.beatsPerMinute)))
        }
        if (valid.isEmpty()) return true
        return try {
            c.insertRecords(valid)
            AppLogger.d(TAG, "Wrote ${valid.size} HR records")
            true
        } catch (e: Exception) {
            AppLogger.e(TAG, "writeHeartRateBatch failed: ${e.message}")
            false
        }
    }
}

data class StepData(val startTimeMs: Long, val endTimeMs: Long, val count: Long)
data class HeartRateData(val timeMs: Long, val beatsPerMinute: Long)
