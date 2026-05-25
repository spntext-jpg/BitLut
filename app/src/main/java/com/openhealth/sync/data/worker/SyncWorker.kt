package com.openhealth.sync.data.worker

import android.content.Context
import android.content.SharedPreferences
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HeartRateData
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.StepData
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.remote.HuaweiHealthRequest
import com.openhealth.sync.data.remote.NetworkClient
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.IOException
import java.time.Instant
import java.time.temporal.ChronoUnit

private const val TAG = "SyncWorker"

class SyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    private val googleManager = GoogleHealthManager(applicationContext)
    private val huaweiManager = HuaweiAuthManager(applicationContext)
    private val syncPrefs: SharedPreferences = applicationContext.getSharedPreferences(
        HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE
    )

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        AppLogger.i(TAG, "Sync started")

        // ── 1. Validate Huawei token ──────────────────────────────────────────
        val token = huaweiManager.getValidToken() ?: run {
            AppLogger.e(TAG, "No valid token — user must re-authenticate")
            return@withContext Result.failure()
        }

        // ── 2. Validate Health Connect permissions ────────────────────────────
        if (!googleManager.hasAllPermissions()) {
            AppLogger.w(TAG, "HC permissions not granted — will retry")
            return@withContext Result.retry()
        }

        // ── 3. Determine sync window ──────────────────────────────────────────
        val endTime = Instant.now()
        val lastSyncMs = syncPrefs.getLong(
            HuaweiConfig.KEY_LAST_SYNC_MS,
            endTime.minus(24, ChronoUnit.HOURS).toEpochMilli()
        )
        val startTime = Instant.ofEpochMilli(lastSyncMs)
        AppLogger.d(TAG, "Sync window: $startTime → $endTime")

        // ── 4. Fetch from Huawei Health API ───────────────────────────────────
        val rawData = try {
            NetworkClient.healthService.getHealthData(
                bearerToken = "Bearer $token",
                requestBody = HuaweiHealthRequest(
                    startTimeMs = startTime.toEpochMilli(),
                    endTimeMs   = endTime.toEpochMilli(),
                    dataTypes   = listOf(
                        "com.huawei.continuous.steps",
                        "com.huawei.continuous.heart_rate"
                    )
                )
            )
        } catch (e: HttpException) {
            val code = e.code()
            AppLogger.e(TAG, "Huawei API HTTP $code: ${e.message()}")
            if (code == 401 || code == 403) huaweiManager.clearTokens()
            return@withContext if (code in 400..499) Result.failure() else Result.retry()
        } catch (e: IOException) {
            AppLogger.e(TAG, "Network error: ${e.message}")
            return@withContext Result.retry()
        }

        // ── 5. Map to domain models ───────────────────────────────────────────
        val steps = rawData.steps?.map { r ->
            StepData(
                startTimeMs = r.startTimeMs,
                endTimeMs   = r.endTimeMs ?: (r.startTimeMs + 60_000L),
                count       = r.value.toLong()
            )
        } ?: emptyList()

        val heartRates = rawData.heartRate?.map { r ->
            HeartRateData(
                timeMs         = r.timeMs ?: r.startTimeMs,
                beatsPerMinute = r.value.toLong()
            )
        } ?: emptyList()

        AppLogger.d(TAG, "Fetched: ${steps.size} steps, ${heartRates.size} HR records")

        // ── 6. Write to Health Connect in batch ───────────────────────────────
        val stepsOk = googleManager.writeStepsBatch(steps)
        val hrOk    = googleManager.writeHeartRateBatch(heartRates)

        // ── 7. Persist sync cursor only on full success ───────────────────────
        return@withContext if (stepsOk && hrOk) {
            syncPrefs.edit()
                .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, endTime.toEpochMilli())
                .apply()
            AppLogger.i(TAG, "Sync complete ✓ steps=${steps.size} hr=${heartRates.size}")
            Result.success()
        } else {
            AppLogger.w(TAG, "Partial failure — retry. steps=$stepsOk hr=$hrOk")
            Result.retry()
        }
    }
}
