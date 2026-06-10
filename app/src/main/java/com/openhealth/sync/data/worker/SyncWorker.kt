package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.openhealth.sync.SyncApplication
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.util.AppLogger

private const val TAG = "SyncWorker"
private const val DEFAULT_LOOKBACK_MS = 24L * 60L * 60L * 1000L
private const val MAX_LOOKBACK_MS = 7L * 24L * 60L * 60L * 1000L
private const val HUAWEI_SCOPE_UNAUTHORIZED = 50005

class SyncWorker(context: Context, workerParams: WorkerParameters) : CoroutineWorker(context, workerParams) {
    private val appContainer by lazy { (applicationContext as SyncApplication).container }
    private val prefs by lazy {
        applicationContext.getSharedPreferences(HuaweiConfig.PREFS_NAME, Context.MODE_PRIVATE)
    }

    override suspend fun doWork(): Result {
        AppLogger.i(TAG, "Starting Huawei -> Health Connect sync")

        if (!HmsCoreHelper.isInstalled(applicationContext)) {
            AppLogger.e(TAG, "HMS Core is missing; Huawei Health sync cannot start")
            return Result.failure()
        }

        if (!HmsCoreHelper.isHuaweiHealthInstalled(applicationContext)) {
            AppLogger.e(TAG, "Huawei Health is missing; sync cannot read Huawei data")
            return Result.failure()
        }

        val googleManager = appContainer.googleHealthManager
        val huaweiManager = appContainer.huaweiHealthManager

        val googlePermissionsOk = googleManager.hasAllPermissions()
        val localHuaweiAuthorized = huaweiManager.isAuthorized()

        AppLogger.i(
            TAG,
            "Sync preflight: googlePermissions=$googlePermissionsOk localHuaweiAuthorized=$localHuaweiAuthorized"
        )

        if (!googlePermissionsOk) {
            AppLogger.e(TAG, "Health Connect write permissions are missing")
            return Result.failure()
        }

        // If Huawei approval is still pending (50005 known), skip Huawei sync entirely
        if (huaweiManager.isPendingApproval()) {
            AppLogger.w(TAG, "Huawei Health Kit approval pending — skipping Huawei sync. Data from Google Health is still available on Dashboard.")
            return Result.success()
        }

        if (!localHuaweiAuthorized) {
            AppLogger.w(TAG, "Local Huawei authorization flag is false — will attempt real API read to verify")
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

        AppLogger.i(
            TAG,
            "Sync window: start=$startTime end=$endTime savedLastSync=$savedLastSync"
        )

        return try {
            val snapshot = huaweiManager.readSnapshot(startTime, endTime)

            AppLogger.i(
                TAG,
                "Huawei snapshot: steps=${snapshot.steps.size}, distances=${snapshot.distances.size}, floors=${snapshot.floors.size}, elevations=${snapshot.elevations.size}, activeCalories=${snapshot.activeCalories.size}, activities=${snapshot.activities.size}"
            )

            if (snapshot.isEmpty) {
                AppLogger.w(
                    TAG,
                    "Huawei API read succeeded but returned no samples. Check that Huawei Health has data in the selected 24h window and that the device/watch has synced to Huawei Health."
                )
                prefs.edit()
                    .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, true)
                    .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, endTime)
                    .apply()
                return Result.success()
            }

            val writeOk = googleManager.writeSnapshot(snapshot)

            if (writeOk) {
                prefs.edit()
                    .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, true)
                    .putLong(HuaweiConfig.KEY_LAST_SYNC_MS, endTime)
                    .apply()

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
            if (e.message?.contains(HUAWEI_SCOPE_UNAUTHORIZED.toString()) == true) {
                huaweiManager.markAppGalleryVerificationRequired()
                AppLogger.e(
                    TAG,
                    "Huawei Health Kit blocked import with 50005. Root cause: AppGallery Health Kit verification is not approved for this package/release SHA-256/scope set. User permission inside Huawei Health is not enough until Huawei approves the app.",
                    e
                )
                return Result.failure()
            }

            AppLogger.e(
                TAG,
                "Huawei/Health Connect security failure. Revoke BitLut in Huawei Health, clear HMS Core cache, reopen BitLut and authorize again.",
                e
            )
            Result.failure()
        } catch (e: IllegalArgumentException) {
            AppLogger.e(TAG, "Invalid sync window", e)
            Result.failure()
        } catch (e: Exception) {
            AppLogger.e(
                TAG,
                "Huawei sync failed during real API read/write. This is the error Huawei reviewer needs to see.",
                e
            )
            Result.retry()
        }
    }
}
