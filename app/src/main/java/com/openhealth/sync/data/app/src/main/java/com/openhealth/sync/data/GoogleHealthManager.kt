package com.openhealth.sync.data

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.StepsRecord

class GoogleHealthManager(private val context: Context) {

    // Запрашиваем права только на запись (Write), так как мы выступаем в роли моста
    val permissions = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(HeartRateRecord::class)
    )

    fun checkHealthConnectStatus(): Int {
        return HealthConnectClient.getSdkStatus(context)
    }

    val healthConnectClient: HealthConnectClient? by lazy {
        if (checkHealthConnectStatus() == HealthConnectClient.SDK_AVAILABLE) {
            HealthConnectClient.getOrCreate(context)
        } else {
            null
        }
    }

    // Проверяем, предоставлены ли все нужные разрешения
    async fun hasAllPermissions(): Boolean {
        val client = healthConnectClient ?: return false
        val grantedPermissions = client.permissionController.getGrantedPermissions()
        return grantedPermissions.containsAll(permissions)
    }
}