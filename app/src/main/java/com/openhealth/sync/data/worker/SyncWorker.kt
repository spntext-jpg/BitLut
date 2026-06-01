package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.openhealth.sync.SyncApplication
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger
import com.openhealth.sync.platform.HmsCoreHelper

private const val TAG = "SyncWorker"
private const val DEFAULT_LOOKBACK_MS = 24L * 60L * 60L * 1000L
private const val MAX_LOOKBACK_MS = 7L * 24L * 60L * 60L * 1000L

class SyncWorker(context: Context, workerParams: WorkerParameters) : CoroutineWorker(context, workerParams) {
    private val appContainer by lazy { (applicationContext as SyncApplication).container }
    private val prefs by lazy {
        applicationContext.getSharedPreferences(HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE)
    }

    override suspend fun doWork(): Result {
        AppLogger.i(TAG, "Starting Huawei -> Health Connect sync")

        if (!HmsCoreHelper.isInstalled(applicationContext)) {
            AppLogger.w("SyncWorker", "HMS Core is missing; Huawei Health sync cannot start")
            return Result.failure()
        }

        val googleManager = appContainer.googleHealthManager
        val huaweiManager = appContainer.huaweiHealthManager

        if (!googleManager.hasAllPermissions()) {
            AppLogger.w(TAG, "Health Connect write permissions are missing")
            return Result.failure()
        }

        if (!huaweiManager.isAuthorized()) {
            AppLogger.w(TAG, "Huawei Health Kit is not authorized")
            return Result.failure()
        }

        val endTime = System.currentTimeMillis()
        val savedLastSync = prefs.getLong(HuaweiConfig.KEY_LAST_SYNC_MS, 0L)
        val fallbackStart = endTime - DEFAULT_LOOKBACK_MS
        val minStart = endTime - MAX_LOOKBACK_MS
        val startTime = when {
            savedLastSync <= 0L -> fallbackStart
            savedLastSync < minStart -> minStart
            else -> savedLastSync
        }

        return try {
            val snapshot = huaweiManager.readSnapshot(startTime, endTime)
            if (snapshot.isEmpty) {
                AppLogger.i(TAG, "No new Huawei samples found")
                prefs.edit().putLong(HuaweiConfig.KEY_LAST_SYNC_MS, endTime).apply()
                return Result.success()
            }

            val writeOk = googleManager.writeSnapshot(snapshot)

            if (writeOk) {
                prefs.edit().putLong(HuaweiConfig.KEY_LAST_SYNC_MS, endTime).apply()
                AppLogger.i(
                    TAG,
                    "Sync complete: steps=${snapshot.steps.size}, distances=${snapshot.distances.size}, floors=${snapshot.floors.size}, elevations=${snapshot.elevations.size}, activeCalories=${snapshot.activeCalories.size}, activities=${snapshot.activities.size}"
                )
                Result.success()
            } else {
                AppLogger.e(TAG, "Health Connect write failed")
                Result.retry()
            }
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "Permission/security failure during sync", e)
            Result.failure()
        } catch (e: IllegalArgumentException) {
            AppLogger.e(TAG, "Invalid sync window", e)
            Result.failure()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Transient sync failure", e)
            Result.retry()
        }
    }
}
