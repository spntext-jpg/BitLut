package com.openhealth.sync.data

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.StepsRecord

class GoogleHealthManager(private val context: Context) {

    // Набор разрешений, которые приложение попросит у пользователя (Чтение не нужно, только Запись)
    val permissions = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(HeartRateRecord::class)
    )

    // Проверяем, поддерживает ли телефон Health Connect (доступен ли системный сервис)
    fun checkHealthConnectStatus(): Int {
        return HealthConnectClient.getSdkStatus(context)
    }

    // Инициализация клиента, если сервис доступен
    val healthConnectClient: HealthConnectClient? by lazy {
        if (checkHealthConnectStatus() == HealthConnectClient.SDK_AVAILABLE) {
            HealthConnectClient.getOrCreate(context)
        } else {
            null
        }
    }
}