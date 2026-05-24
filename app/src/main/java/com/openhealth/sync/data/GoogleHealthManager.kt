package com.openhealth.sync.data

import android.content.Context
import android.content.pm.PackageManager
import android.util.Log
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.StepsRecord
import java.time.Instant
import java.time.ZoneId

private const val TAG = "GoogleHealthManager"
private const val HC_PACKAGE = "com.google.android.apps.healthdata"

enum class HealthConnectStatus {
    AVAILABLE,
    NOT_INSTALLED,
    NEEDS_UPDATE,
    NOT_SUPPORTED
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
        AppLogger.i(TAG, "getSdkStatus() = $sdkStatus (AVAILABLE=3, UPDATE_REQUIRED=2, UNAVAILABLE=1)")

        return when (sdkStatus) {
            HealthConnectClient.SDK_AVAILABLE -> {
                AppLogger.i(TAG, "Health Connect: AVAILABLE")
                HealthConnectStatus.AVAILABLE
            }
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> {
                // On some Android 12 OEM builds (OnePlus/OPPO), the SDK returns
                // UPDATE_REQUIRED even when HC is installed and up to date.
                // Fall back to a direct package check as the source of truth.
                val installed = isHcPackageInstalled()
                AppLogger.w(TAG, "HC SDK says UPDATE_REQUIRED — package installed: $installed")
                if (installed) {
                    // Package is present — try to proceed as AVAILABLE
                    // The OEM just failed the signature check; the client usually still works
                    AppLogger.w(TAG, "Treating as AVAILABLE despite OEM signature mismatch")
                    HealthConnectStatus.AVAILABLE
                } else {
                    HealthConnectStatus.NEEDS_UPDATE
                }
            }
            else -> {
                val installed = isHcPackageInstalled()
                AppLogger.w(TAG, "HC SDK_UNAVAILABLE — package installed: $installed API: ${android.os.Build.VERSION.SDK_INT}")
                if (installed) HealthConnectStatus.NEEDS_UPDATE
                else HealthConnectStatus.NOT_INSTALLED
            }
        }
    }

    private fun isHcPackageInstalled(): Boolean {
        return try {
            context.packageManager.getPackageInfo(HC_PACKAGE, 0)
            true
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
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
            val s = Instant.ofEpochMilli(d.startTimeMs)
            val e = Instant.ofEpochMilli(d.endTimeMs)
            StepsRecord(d.count, s, e, zoneRules.getOffset(s), zoneRules.getOffset(e))
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
            val t = Instant.ofEpochMilli(d.timeMs)
            val e = t.plusSeconds(1)
            HeartRateRecord(t, e, zoneRules.getOffset(t), zoneRules.getOffset(e),
                listOf(HeartRateRecord.Sample(t, d.beatsPerMinute)))
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
