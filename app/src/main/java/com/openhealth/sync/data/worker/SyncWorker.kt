package com.openhealth.sync.data.worker

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HeartRateData
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.StepData
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.remote.HuaweiHealthRequest
import com.openhealth.sync.data.remote.NetworkClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.IOException
import java.time.Instant
import java.time.temporal.ChronoUnit

private const val TAG = "SyncWorker"

/**
 * Background orchestrator: pulls health data from Huawei Cloud and writes
 * it to Google Health Connect.
 *
 * Key correctness guarantee: persists lastSyncTimestamp so each run only
 * fetches the DELTA since the last successful sync — never re-inserts data.
 *
 * Error policy:
 *   IOException (network)   → Result.retry()   (WorkManager will back off and try again)
 *   HttpException 4xx (auth)→ Result.failure()  (no point retrying with a bad token)
 *   No auth token           → Result.failure()  (user must re-authenticate)
 *   No HC permissions       → Result.retry()    (permissions might be granted later)
 */
class SyncWorker(
    context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    private val googleHealthManager = GoogleHealthManager(applicationContext)
    private val huaweiAuthManager   = HuaweiAuthManager(applicationContext)

    // ── SharedPreferences for persisting sync cursor ───────────────────────────
    // Re-uses HuaweiConfig.PREFS_NAME so we have one prefs file per app
    private val syncPrefs = applicationContext.getSharedPreferences(
        HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE
    )

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {

        // ── 1. Validate Huawei auth ────────────────────────────────────────────
        val token = huaweiAuthManager.getValidToken()
        if (token == null) {
            Log.e(TAG, "No valid Huawei token — user must re-authenticate")
            return@withContext Result.failure() // retry won't help — needs user action
        }

        // ── 2. Validate Google Health Connect permissions ──────────────────────
        if (!googleHealthManager.hasAllPermissions()) {
            Log.w(TAG, "Health Connect permissions not granted — will retry")
            return@withContext Result.retry()
        }

        // ── 3. Determine sync window ───────────────────────────────────────────
        val endTime   = Instant.now()
        // Read last successful sync time; default to 24h ago for first run
        val lastSyncMs = syncPrefs.getLong(
            HuaweiConfig.KEY_LAST_SYNC_MS,
            endTime.minus(24, ChronoUnit.HOURS).toEpochMilli()
        )
        val startTime = Instant.ofEpochMilli(lastSyncMs)

        Log.d(TAG, "Sync window: ${startTime} → ${endTime}")

        // ── 4. Fetch from Huawei ───────────────────────────────────────────────
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
            Log.e(TAG, "Huawei API HTTP $code error: ${e.message()}")
            return@withContext if (code in 400..499) {
                // 401 Unauthorized / 403 Forbidden — token issue, clear and force re-auth
                if (code == 401 || code == 403) huaweiAuthManager.clearTokens()
                Result.failure()
            } else {
                Result.retry() // 5xx server error — retry later
            }
        } catch (e: IOException) {
            Log.e(TAG, "Network error fetching Huawei data: ${e.message}")
            return@withContext Result.retry()
        }

        // ── 5. Map to domain models ────────────────────────────────────────────
        val steps = rawData.steps?.map { record ->
            StepData(
                startTimeMs = record.startTimeMs,
                endTimeMs   = record.endTimeMs ?: (record.startTimeMs + 60_000L),
                count       = record.value.toLong()
            )
        } ?: emptyList()

        val heartRates = rawData.heartRate?.map { record ->
            HeartRateData(
                timeMs          = record.timeMs ?: record.startTimeMs,
                beatsPerMinute  = record.value.toLong()
            )
        } ?: emptyList()

        // ── 6. Write to Health Connect (batch — one IPC call per type) ─────────
        val stepsOk     = googleHealthManager.writeStepsBatch(steps)
        val heartRateOk = googleHealthManager.writeHeartRateBatch(heartRates)

        // ── 7. Persist sync cursor only on full success ────────────────────────
        if (stepsOk && heartRateOk) {
            syncPrefs.edit()
                .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, endTime.toEpochMilli())
                .apply()
            Log.d(TAG, "Sync complete. Steps: ${steps.size}, HR samples: ${heartRates.size}")
            return@withContext Result.success()
        } else {
            Log.w(TAG, "Partial write failure — will retry. Steps OK: $stepsOk, HR OK: $heartRateOk")
            return@withContext Result.retry()
        }
    }
}
