package com.openhealth.sync.data

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.StepsRecord
import java.time.Instant
import java.time.ZoneOffset

class GoogleHealthManager(private val context: Context) {

    // Права доступа на запись
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

    // Проверка разрешений
    suspend fun hasAllPermissions(): Boolean {
        val client = healthConnectClient ?: return false
        val grantedPermissions = client.permissionController.getGrantedPermissions()
        return grantedPermissions.containsAll(permissions)
    }

    // 1. Запись шагов в Google Health Connect
    suspend fun writeSteps(count: Long, startTime: Instant, endTime: Instant): Boolean {
        val client = healthConnectClient ?: return false
        return try {
            val stepsRecord = StepsRecord(
                count = count,
                startTime = startTime,
                endTime = endTime,
                startZoneOffset = ZoneOffset.systemDefault().rules.getOffset(startTime),
                endZoneOffset = ZoneOffset.systemDefault().rules.getOffset(endTime)
            )
            client.insertRecords(listOf(stepsRecord))
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    // 2. Запись пульса в Google Health Connect
    suspend fun writeHeartRate(bpm: Long, time: Instant): Boolean {
        val client = healthConnectClient ?: return false
        return try {
            val heartRateRecord = HeartRateRecord(
                startTime = time,
                endTime = time.plusSeconds(1), // Минимальный интервал для замера пульса
                startZoneOffset = ZoneOffset.systemDefault().rules.getOffset(time),
                endZoneOffset = ZoneOffset.systemDefault().rules.getOffset(time),
                samples = listOf(
                    HeartRateRecord.Sample(
                        time = time,
                        beatsPerMinute = bpm
                    )
                )
            )
            client.insertRecords(listOf(heartRateRecord))
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
}