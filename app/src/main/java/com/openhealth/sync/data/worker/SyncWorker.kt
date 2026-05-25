package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.openhealth.sync.SyncApplication
import com.openhealth.sync.util.AppLogger
import com.openhealth.sync.data.StepData

class SyncWorker(context: Context, workerParams: WorkerParameters) : CoroutineWorker(context, workerParams) {
    private val TAG = "SyncWorker"
    private val appContainer by lazy { (applicationContext as SyncApplication).container }

    override suspend fun doWork(): Result {
        AppLogger.i(TAG, "Запуск фоновой синхронизации...")
        return try {
            val googleManager = appContainer.googleHealthManager
            if (!googleManager.hasAllPermissions()) {
                AppLogger.w(TAG, "Пропуск Google Health: Нет прав доступа")
            } else {
                AppLogger.i(TAG, "Права Google Health подтверждены. Экспорт данных...")
                
                // Симуляция данных: экспорт 500 шагов за последний час в Google Health
                val endTime = System.currentTimeMillis()
                val startTime = endTime - 3600000 // 1 час назад
                val stepData = listOf(StepData(startTimeMs = startTime, endTimeMs = endTime, count = 500))
                
                val success = googleManager.writeStepsBatch(stepData)
                if (success) {
                    AppLogger.i(TAG, "✅ Успешно экспортировано 500 шагов в Google Health")
                } else {
                    AppLogger.e(TAG, "❌ Ошибка при экспорте шагов в Google Health")
                }
            }
            Result.success()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Критическая ошибка выполнения", e)
            Result.failure()
        }
    }
}
