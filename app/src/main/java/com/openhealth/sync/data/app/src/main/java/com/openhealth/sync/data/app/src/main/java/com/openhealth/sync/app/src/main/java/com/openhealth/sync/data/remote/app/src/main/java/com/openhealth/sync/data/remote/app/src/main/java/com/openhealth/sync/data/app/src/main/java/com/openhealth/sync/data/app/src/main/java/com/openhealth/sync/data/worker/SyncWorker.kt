package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.remote.HuaweiApiService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.time.Instant
import java.time.temporal.ChronoUnit

class SyncWorker(
    context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    private val googleHealthManager = GoogleHealthManager(context)
    private val huaweiAuthManager = HuaweiAuthManager(context)

    private val huaweiApiService: HuaweiApiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://health-api.cloud.huawei.com/")
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(HuaweiApiService::class.java)
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        // 1. Проверяем авторизацию в Huawei и обновляем токен, если нужно
        val token = huaweiAuthManager.refreshSessionIfNeeded()
        if (token == null) {
            return@withContext Result.failure() // Нет авторизации — останавливаемся
        }

        // 2. Проверяем, есть ли доступы к Google Health Connect
        if (!googleHealthManager.hasAllPermissions()) {
            return@withContext Result.retry() // Права не выданы, попробуем позже
        }

        try {
            // Временной интервал: за последние 24 часа
            val endTime = Instant.now()
            val startTime = endTime.minus(24, ChronoUnit.HOURS)

            // Формируем строгий JSON-запрос для Huawei Health Cloud API
            val requestBody = mapOf(
                "startTime" to startTime.toEpochMilli(),
                "endTime" to endTime.toEpochMilli(),
                "dataType" to listOf(
                    "com.huawei.continuous.steps",
                    "com.huawei.continuous.heart_rate"
                )
            )

            val rawData = huaweiApiService.getHealthData(
                bearerToken = "Bearer $token",
                requestBody = requestBody
            )

            // Парсим и записываем шаги (Безопасное приведение типов)
            val stepRecords = rawData["steps"] as? List<*>
            stepRecords?.forEach { record ->
                val map = record as? Map<*, *>
                if (map != null) {
                    val count = (map["value"] as? Number)?.toLong() ?: 0L
                    val start = Instant.ofEpochMilli((map["startTime"] as? Number)?.toLong() ?: 0L)
                    val end = Instant.ofEpochMilli((map["endTime"] as? Number)?.toLong() ?: 0L)
                    
                    if (count > 0) {
                        googleHealthManager.writeSteps(count, start, end)
                    }
                }
            }

            // Парсим и записываем пульс
            val heartRecords = rawData["heart_rate"] as? List<*>
            heartRecords?.forEach { record ->
                val map = record as? Map<*, *>
                if (map != null) {
                    val bpm = (map["value"] as? Number)?.toLong() ?: 0L
                    val time = Instant.ofEpochMilli((map["time"] as? Number)?.toLong() ?: 0L)
                    
                    if (bpm > 0) {
                        googleHealthManager.writeHeartRate(bpm, time)
                    }
                }
            }

            return@withContext Result.success()
        } catch (e: Exception) {
            e.printStackTrace()
            return@withContext Result.retry() // Ошибка сети — WorkManager перенаправит задачу позже
        }
    }
}