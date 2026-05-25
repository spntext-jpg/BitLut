package com.openhealth.sync.data

import android.content.Context
import android.content.pm.PackageManager
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.StepsRecord
import com.openhealth.sync.util.AppLogger
import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset

private const val TAG = "GoogleHealthManager"

// All known package names for Health Connect across Android versions and OEMs
private val HC_PACKAGES = listOf(
    "com.google.android.apps.healthdata",   // Standalone APK (Play Store, Android 9-13)
    "com.google.android.health.connect",    // Integrated (Android 14+, some OEM builds)
    "com.android.healthconnect.controller"  // System component on some Pixel builds
)

enum class HealthConnectStatus {
    AVAILABLE, NOT_INSTALLED, NEEDS_UPDATE, NOT_SUPPORTED
}

class GoogleHealthManager(private val context: Context) {

    val permissions: Set<String> = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(HeartRateRecord::class)
    )

    private val zoneRules by lazy { ZoneId.systemDefault().rules }

    private val client: HealthConnectClient? by lazy {
        if (getStatus() == HealthConnectStatus.AVAILABLE)
            HealthConnectClient.getOrCreate(context)
        else null
    }

    fun getStatus(): HealthConnectStatus {
        val sdkStatus = HealthConnectClient.getSdkStatus(context)
        val installedPkg = findInstalledHcPackage()

        AppLogger.i(TAG, "getSdkStatus()=$sdkStatus " +
            "installedPackage=${installedPkg ?: "none"} " +
            "device=${android.os.Build.MODEL} API=${android.os.Build.VERSION.SDK_INT}")

        return when (sdkStatus) {
            HealthConnectClient.SDK_AVAILABLE -> {
                AppLogger.i(TAG, "HC: AVAILABLE (SDK confirms)")
                HealthConnectStatus.AVAILABLE
            }
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> {
                // SDK says update required — but check if package actually exists.
                // OnePlus/OPPO Android 11-12: SDK lies, package is present and functional.
                if (installedPkg != null) {
                    AppLogger.w(TAG, "HC: SDK=UPDATE_REQUIRED but pkg=$installedPkg exists " +
                        "— treating as AVAILABLE (OEM signature mismatch workaround)")
                    HealthConnectStatus.AVAILABLE
                } else {
                    AppLogger.w(TAG, "HC: genuinely needs update — not installed")
                    HealthConnectStatus.NEEDS_UPDATE
                }
            }
            else -> {
                // SDK_UNAVAILABLE
                if (installedPkg != null) {
                    AppLogger.w(TAG, "HC: SDK_UNAVAILABLE but pkg=$installedPkg found — NEEDS_UPDATE")
                    HealthConnectStatus.NEEDS_UPDATE
                } else {
                    AppLogger.w(TAG, "HC: not installed anywhere")
                    HealthConnectStatus.NOT_INSTALLED
                }
            }
        }
    }

    /**
     * Scans all known Health Connect package names.
     * Returns the first installed one, or null if none found.
     */
    private fun findInstalledHcPackage(): String? {
        for (pkg in HC_PACKAGES) {
            try {
                context.packageManager.getPackageInfo(pkg, 0)
                AppLogger.d(TAG, "Found HC package: $pkg")
                return pkg
            } catch (e: PackageManager.NameNotFoundException) {
                AppLogger.d(TAG, "HC package not found: $pkg")
            }
        }
        return null
    }

    suspend fun hasAllPermissions(): Boolean {
        val c = client ?: return false
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
        val c = client ?: run { AppLogger.e(TAG, "writeStepsBatch: no client"); return false }
        val valid = records.filter { it.count > 0 && it.startTimeMs < it.endTimeMs }.map { d ->
            val start: Instant       = Instant.ofEpochMilli(d.startTimeMs)
            val end: Instant         = Instant.ofEpochMilli(d.endTimeMs)
            val startOff: ZoneOffset = zoneRules.getOffset(start)
            val endOff: ZoneOffset   = zoneRules.getOffset(end)
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
            AppLogger.e(TAG, "writeStepsBatch failed: ${e.message}")
            false
        }
    }

    suspend fun writeHeartRateBatch(records: List<HeartRateData>): Boolean {
        val c = client ?: run { AppLogger.e(TAG, "writeHeartRateBatch: no client"); return false }
        val valid = records.filter { it.beatsPerMinute > 0 }.map { d ->
            val time: Instant        = Instant.ofEpochMilli(d.timeMs)
            val end: Instant         = time.plusSeconds(1)
            val startOff: ZoneOffset = zoneRules.getOffset(time)
            val endOff: ZoneOffset   = zoneRules.getOffset(end)
            HeartRateRecord(
                startTime = time,
                endTime = end,
                startZoneOffset = startOff,
                endZoneOffset = endOff,
                samples = listOf(
                    HeartRateRecord.Sample(time = time, beatsPerMinute = d.beatsPerMinute)
                )
            )
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
