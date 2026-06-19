package com.openhealth.sync.config

import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord

/**
 * Single source of truth for Health Connect permissions.
 *
 * Coverage target mirrors Huawei Basic Sport Health Data:
 * - Step -> StepsRecord
 * - Distance, ascent & altitude -> Distance/Floors/Elevation records
 * - Active Hours / Daily Activity Summary -> Activity Intensity permission strings where supported
 * - Activity record / Activity -> ExerciseSessionRecord
 *
 * ActivityIntensityRecord is not referenced as a Kotlin class to keep the build compatible with
 * the current Health Connect dependency. The permission strings are still requested when the
 * installed Health Connect build supports them.
 */
object HealthPermissionPolicy {
    private const val READ_ACTIVITY_INTENSITY = "android.permission.health.READ_ACTIVITY_INTENSITY"
    private const val WRITE_ACTIVITY_INTENSITY = "android.permission.health.WRITE_ACTIVITY_INTENSITY"

    val dashboardReadPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class),
        HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
        READ_ACTIVITY_INTENSITY,
    )

    val importWritePermissions: Set<String> = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(DistanceRecord::class),
        HealthPermission.getWritePermission(FloorsClimbedRecord::class),
        HealthPermission.getWritePermission(ElevationGainedRecord::class),
        HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getWritePermission(ExerciseSessionRecord::class),
        HealthPermission.getWritePermission(SleepSessionRecord::class),
        HealthPermission.getWritePermission(HeartRateRecord::class),
        WRITE_ACTIVITY_INTENSITY,
    )

    /**
     * Request one broad, honest permission set so Google Health Connect is not narrower
     * than the Huawei Health Kit scope set.
     */
    val syncPermissions: Set<String> = dashboardReadPermissions + importWritePermissions

    // Backward-compatible aliases used by older screens/managers.
    val dashboardPermissions: Set<String> = syncPermissions
    val importPermissions: Set<String> = syncPermissions
    val allPermissions: Set<String> = syncPermissions
}
