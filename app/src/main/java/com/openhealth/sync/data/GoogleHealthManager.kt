package com.openhealth.sync.data

import android.content.Context
import android.content.Intent
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

// Every known package name for Health Connect across all Android versions and OEMs.
// We check ALL of them — first match wins.
private val HC_PACKAGES = listOf(
    "com.google.android.apps.healthdata",    // Play Store standalone (Android 9-13)
    "com.google.android.health.connect",     // Integrated build (Android 14+)
    "com.android.healthconnect.controller",  // Pixel system component
    "com.google.android.gms"                 // Some builds route through GMS
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

    // We attempt getOrCreate regardless of getSdkStatus() on API 31-33.
    // The SDK check is known to return wrong values on OEM builds.
    val healthConnectClient: HealthConnectClient? by lazy {
        try {
            HealthConnectClient.getOrCreate(context).also {
                AppLogger.i(TAG, "HealthConnectClient created successfully")
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "HealthConnectClient.getOrCreate failed: ${e.message}")
            null
        }
    }

    fun getStatus(): HealthConnectStatus {
        val sdkStatus    = HealthConnectClient.getSdkStatus(context)
        val installedPkg = findInstalledHcPackage()

        AppLogger.i(TAG, "getSdkStatus()=$sdkStatus " +
            "installedPackage=${installedPkg ?: "none"} " +
            "API=${Build.VERSION.SDK_INT} device=${Build.MODEL}")

        // On API 33 OEM builds the SDK status is unreliable.
        // Use package presence + client instantiation as the real signal.
        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.TIRAMISU) {
            // Try to instantiate the client directly — if it works, we're available
            val clientWorks = try {
                HealthConnectClient.getOrCreate(context)
                true
            } catch (e: Exception) {
                AppLogger.w(TAG, "getOrCreate failed: ${e.message}")
                false
            }
            if (clientWorks) {
                AppLogger.i(TAG, "HC: client works on API${Build.VERSION.SDK_INT} — AVAILABLE")
                return HealthConnectStatus.AVAILABLE
            }
        }

        return when (sdkStatus) {
            HealthConnectClient.SDK_AVAILABLE -> {
                AppLogger.i(TAG, "HC: AVAILABLE (SDK confirms)")
                HealthConnectStatus.AVAILABLE
            }
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> {
                if (installedPkg != null) {
                    AppLogger.w(TAG, "HC: pkg=$installedPkg installed but SDK says UPDATE — treating AVAILABLE")
                    HealthConnectStatus.AVAILABLE
                } else {
                    AppLogger.w(TAG, "HC: NEEDS_UPDATE, not installed")
                    HealthConnectStatus.NEEDS_UPDATE
                }
            }
            else -> {
                if (installedPkg != null) HealthConnectStatus.NEEDS_UPDATE
                else HealthConnectStatus.NOT_INSTALLED
            }
        }
    }

    /**
     * Scans all known Health Connect package names.
     * Also does a broad search for any installed package containing "healthconnect" or "healthdata".
     */
    fun findInstalledHcPackage(): String? {
        // Check known packages first
        for (pkg in HC_PACKAGES) {
            try {
                context.packageManager.getPackageInfo(pkg, 0)
                AppLogger.d(TAG, "Found HC package: $pkg")
                return pkg
            } catch (e: PackageManager.NameNotFoundException) {
                // continue
            }
        }

        // Broad scan — find ANY package with health-related name
        // This catches OEM-specific package names we don't know yet
        try {
            val allPackages = context.packageManager.getInstalledPackages(0)
            val healthPkgs = allPackages
                .map { it.packageName }
                .filter { pkg ->
                    (pkg.contains("healthconnect", ignoreCase = true) ||
                     pkg.contains("healthdata", ignoreCase = true) ||
                     pkg.contains("health.connect", ignoreCase = true)) &&
                    !pkg.contains("com.openhealth.sync") // exclude ourselves
                }
            AppLogger.i(TAG, "Broad health package scan found: $healthPkgs")
            return healthPkgs.firstOrNull()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Broad package scan failed: ${e.message}")
        }

        return null
    }

    suspend fun hasAllPermissions(): Boolean {
        val c = healthConnectClient ?: return false
        return try {
            val granted = c.permissionController.getGrantedPermissions()
            AppLogger.d(TAG, "Granted: $granted")
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
                samples = listOf(HeartRateRecord.Sample(time = time,
                    beatsPerMinute = d.beatsPerMinute)))
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
