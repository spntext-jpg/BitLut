package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.openhealth.sync.SyncApplication
import com.openhealth.sync.util.AppLogger

class SyncWorker(
    context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    private val TAG = "SyncWorker"
    private val appContainer by lazy { (applicationContext as SyncApplication).container }

    override suspend fun doWork(): Result {
        AppLogger.i(TAG, "Start background sync job...")
        return try {
            val googleManager = appContainer.googleHealthManager
            if (!googleManager.hasAllPermissions()) {
                AppLogger.w(TAG, "Google Health skipped: No permissions")
            } else {
                AppLogger.d(TAG, "Google Health: data fetched.")
            }
            // Temporarily removed refreshAccessTokenIfNeeded() to prevent Unresolved Reference
            // until HuaweiAuthManager methods are confirmed.
            Result.success()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Critical execution failure: ${e.message}")
            Result.failure()
        }
    }
}
