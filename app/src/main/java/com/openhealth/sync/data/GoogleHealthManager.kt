package com.openhealth.sync.data

import android.content.Context
import android.util.Log
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.StepsRecord
import java.time.Instant
import java.time.ZoneId

private const val TAG = "GoogleHealthManager"

/**
 * Manages all interaction with the Android Health Connect SDK:
 * SDK availability checks, permission queries, and writing records.
 *
 * Single Responsibility: Health Connect I/O only.
 * Uses batch insertRecords() — one IPC call per data type, not one per record.
 */
class GoogleHealthManager(private val context: Context) {

    // ── Permissions ────────────────────────────────────────────────────────────
    val permissions: Set<String> = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(HeartRateRecord::class)
    )

    // ── SDK client (private — callers use methods, not the client directly) ───
    private val healthConnectClient: HealthConnectClient? by lazy {
        if (HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE) {
            HealthConnectClient.getOrCreate(context)
        } else {
            Log.w(TAG, "Health Connect SDK not available on this device")
            null
        }
    }

    // Cached zone rules — avoids repeated timezone database lookups
    private val zoneRules by lazy { ZoneId.systemDefault().rules }

    // ── SDK Status ─────────────────────────────────────────────────────────────
    fun getSdkStatus(): Int = HealthConnectClient.getSdkStatus(context)

    // ── Permissions ────────────────────────────────────────────────────────────
    suspend fun hasAllPermissions(): Boolean {
        val client = healthConnectClient ?: return false
        return client.permissionController.getGrantedPermissions()
            .containsAll(permissions)
    }

    // ── Write operations (BATCH — single IPC call per data type) ──────────────

    /**
     * Writes a list of step records to Health Connect in a single batch call.
     * Skips records with count <= 0 or invalid time range.
     * Returns true if the batch insert succeeded.
     */
    suspend fun writeStepsBatch(records: List<StepData>): Boolean {
        val client = healthConnectClient ?: return false
        val validRecords = records
            .filter { it.count > 0 && it.startTimeMs < it.endTimeMs }
            .map { data ->
                val start = Instant.ofEpochMilli(data.startTimeMs)
                val end   = Instant.ofEpochMilli(data.endTimeMs)
                StepsRecord(
                    count = data.count,
                    startTime = start,
                    endTime = end,
                    startZoneOffset = zoneRules.getOffset(start),
                    endZoneOffset   = zoneRules.getOffset(end)
                )
            }
        if (validRecords.isEmpty()) {
            Log.d(TAG, "writeStepsBatch: no valid records to write")
            return true
        }
        return try {
            client.insertRecords(validRecords)
            Log.d(TAG, "writeStepsBatch: inserted ${validRecords.size} records")
            true
        } catch (e: Exception) {
            Log.e(TAG, "writeStepsBatch failed: ${e.message}", e)
            false
        }
    }

    /**
     * Writes a list of heart rate samples to Health Connect in a single batch call.
     * Each sample becomes a 1-second HeartRateRecord (minimum required interval).
     */
    suspend fun writeHeartRateBatch(records: List<HeartRateData>): Boolean {
        val client = healthConnectClient ?: return false
        val validRecords = records
            .filter { it.beatsPerMinute > 0 }
            .map { data ->
                val time = Instant.ofEpochMilli(data.timeMs)
                val end  = time.plusSeconds(1) // minimum Health Connect interval
                HeartRateRecord(
                    startTime = time,
                    endTime = end,
                    startZoneOffset = zoneRules.getOffset(time),
                    endZoneOffset   = zoneRules.getOffset(end),
                    samples = listOf(
                        HeartRateRecord.Sample(
                            time = time,
                            beatsPerMinute = data.beatsPerMinute
                        )
                    )
                )
            }
        if (validRecords.isEmpty()) {
            Log.d(TAG, "writeHeartRateBatch: no valid records to write")
            return true
        }
        return try {
            client.insertRecords(validRecords)
            Log.d(TAG, "writeHeartRateBatch: inserted ${validRecords.size} records")
            true
        } catch (e: Exception) {
            Log.e(TAG, "writeHeartRateBatch failed: ${e.message}", e)
            false
        }
    }
}

// ── Typed domain models passed to GoogleHealthManager ─────────────────────────
// These decouple GoogleHealthManager from Huawei-specific response models.

data class StepData(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val count: Long
)

data class HeartRateData(
    val timeMs: Long,
    val beatsPerMinute: Long
)
