package com.openhealth.sync.config

import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.HeartRateVariabilityRmssdRecord
import androidx.health.connect.client.records.OxygenSaturationRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord

/**
 * Single source of truth for Health Connect permissions.
 *
 * Coverage target mirrors Huawei Basic Sport Health Data:
 * - Step -> StepsRecord
 * - Distance, ascent & altitude -> Distance/Floors/Elevation records
 * - Activity record / Activity -> ExerciseSessionRecord
 *
 * Activity Intensity (READ_ACTIVITY_INTENSITY / WRITE_ACTIVITY_INTENSITY) is
 * intentionally NOT requested. AndroidX release notes confirm Activity
 * Intensity support was only added in connect-client 1.2.0-alpha03 ("Enable
 * support for activity intensity for Health Connect APK") -- this project
 * depends on 1.1.0-alpha11, which predates that support. The system
 * permission screen can still show a toggle for it (the on-device Health
 * Connect APK can be newer than this app's bundled client library), but
 * getGrantedPermissions() through the older client does not reliably
 * reflect it as granted even when the toggle is on. Including these two
 * permission strings made containsAll(permissions) permanently false --
 * every other permission could be genuinely granted and the app would
 * still report "not connected" and read nothing. Re-add these once the
 * project upgrades to connect-client 1.2.0 or newer.
 */
object HealthPermissionPolicy {

    val dashboardReadPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class),
        HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
        HealthPermission.getReadPermission(OxygenSaturationRecord::class),
        HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class),
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
