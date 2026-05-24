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
private const val HC_PACKAGE = "com.google.android.apps.healthdata"

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
        AppLogger.i(TAG, "getSdkStatus()=$sdkStatus device=${android.os.Build.MODEL} API=${android.os.Build.VERSION.SDK_INT}")
        return when (sdkStatus) {
            HealthConnectClient.SDK_AVAILABLE -> {
                AppLogger.i(TAG, "HC: AVAILABLE")
                HealthConnectStatus.AVAILABLE
            }
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> {
                val installed = isHcInstalled()
                AppLogger.w(TAG, "HC: UPDATE_REQUIRED, package installed=$installed")
                // OnePlus/OPPO Android 12 OEM returns UPDATE_REQUIRED even when HC is current.
                // If the package exists, treat as AVAILABLE — client.getOrCreate() still works.
                if (installed) HealthConnectStatus.AVAILABLE else HealthConnectStatus.NEEDS_UPDATE
            }
            else -> {
                val installed = isHcInstalled()
                AppLogger.w(TAG, "HC: UNAVAILABLE, package installed=$installed")
                if (installed) HealthConnectStatus.NEEDS_UPDATE else HealthConnectStatus.NOT_INSTALLED
            }
        }
    }

    private fun isHcInstalled(): Boolean = try {
        context.packageManager.getPackageInfo(HC_PACKAGE, 0)
        true
    } catch (e: PackageManager.NameNotFoundException) { false }

    suspend fun hasAllPermissions(): Boolean {
        val c = client ?: return false
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
        val c = client ?: run { AppLogger.e(TAG, "writeStepsBatch: no client"); return false }
        val valid = records.filter { it.count > 0 && it.startTimeMs < it.endTimeMs }.map { d ->
            val start: Instant    = Instant.ofEpochMilli(d.startTimeMs)
            val end: Instant      = Instant.ofEpochMilli(d.endTimeMs)
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
            val time: Instant     = Instant.ofEpochMilli(d.timeMs)
            val end: Instant      = time.plusSeconds(1)
            val startOff: ZoneOffset = zoneRules.getOffset(time)
            val endOff: ZoneOffset   = zoneRules.getOffset(end)
            HeartRateRecord(
                startTime = time,
                endTime = end,
                startZoneOffset = startOff,
                endZoneOffset = endOff,
                samples = listOf(HeartRateRecord.Sample(time = time, beatsPerMinute = d.beatsPerMinute))
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
