package com.openhealth.sync.data.worker

import android.content.Context
import android.content.SharedPreferences
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.openhealth.sync.data.HeartRateData
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.StepData
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.remote.HuaweiHealthRequest
import com.openhealth.sync.data.remote.NetworkClient
import com.openhealth.sync.data.repository.GoogleHealthRepository
import com.openhealth.sync.data.repository.HealthDataRepository
import com.openhealth.sync.data.repository.TokenRepository
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.IOException
import java.time.Instant
import java.time.temporal.ChronoUnit

private const val TAG = "SyncWorker"

/**
 * Infrastructure component — its only job:
 *   1. Resolve dependencies (manual DI until Hilt is introduced)
 *   2. Call the domain orchestrator (SyncOrchestrator)
 *   3. Map result to WorkManager Result
 *
 * No business logic lives here.
 */
class SyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    // Manual DI — create dependencies here so they can be replaced in tests
    // by subclassing SyncWorker and overriding these vals
    private val tokenRepo: TokenRepository = HuaweiAuthManager(applicationContext)
    private val healthRepo: HealthDataRepository = GoogleHealthRepository(
        GoogleHealthManager(applicationContext)
    )
    private val syncPrefs: SharedPreferences = applicationContext.getSharedPreferences(
        HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE
    )

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        AppLogger.i(TAG, "Sync started")

        // ── Guard: Huawei token ───────────────────────────────────────────────
        val token = tokenRepo.getValidToken() ?: run {
            AppLogger.e(TAG, "No valid token — failure (user must re-auth)")
            return@withContext Result.failure()
        }

        // ── Guard: Health Connect permissions ─────────────────────────────────
        if (!healthRepo.hasWritePermissions()) {
            AppLogger.w(TAG, "HC permissions missing — retry")
            return@withContext Result.retry()
        }

        // ── Determine delta sync window ───────────────────────────────────────
        val endTime = Instant.now()
        val lastSyncMs = syncPrefs.getLong(
            HuaweiConfig.KEY_LAST_SYNC_MS,
            endTime.minus(24, ChronoUnit.HOURS).toEpochMilli()
        )
        val startTime = Instant.ofEpochMilli(lastSyncMs)
        AppLogger.i(TAG, "Sync window: $startTime → $endTime")

        // ── Fetch from Huawei ─────────────────────────────────────────────────
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
            AppLogger.e(TAG, "Huawei HTTP $code: ${e.message()}")
            if (code == 401 || code == 403) tokenRepo.clearTokens()
            return@withContext if (code in 400..499) Result.failure() else Result.retry()
        } catch (e: IOException) {
            AppLogger.e(TAG, "Network error: ${e.message}")
            return@withContext Result.retry()
        }

        // ── Map typed DTOs to domain models ───────────────────────────────────
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

        AppLogger.i(TAG, "Fetched: ${steps.size} step records, ${heartRates.size} HR records")

        // ── Write to Health Connect via repository abstraction ────────────────
        val stepsOk = healthRepo.writeSteps(steps)
        val hrOk    = healthRepo.writeHeartRate(heartRates)

        // ── Persist cursor only on full success ───────────────────────────────
        return@withContext if (stepsOk && hrOk) {
            syncPrefs.edit()
                .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, endTime.toEpochMilli())
                .apply()
            AppLogger.i(TAG, "Sync complete")
            Result.success()
        } else {
            AppLogger.w(TAG, "Partial failure — stepsOk=$stepsOk hrOk=$hrOk — retry")
            Result.retry()
        }
    }
}
