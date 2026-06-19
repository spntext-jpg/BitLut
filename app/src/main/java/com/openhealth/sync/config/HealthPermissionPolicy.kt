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
 * Sprint scope: Basic Sport Health Data.
 * - Step -> StepsRecord
 * - Distance -> DistanceRecord
 * - Ascent -> FloorsClimbedRecord
 * - Altitude/elevation gain -> ElevationGainedRecord
 * - Daily activity calories -> ActiveCaloriesBurnedRecord
 * - Activity record / Activity -> ExerciseSessionRecord
 * - Sleep / heart are displayed on Summary and History when already available in Health Connect.
 *
 * Active hours / moderate-to-high intensity:
 * - Huawei exposes this in Daily Activity / Basic Sport data.
 * - Health Connect's direct representation is ActivityIntensityRecord, which is not in the stable
 *   1.1.x API line. Do not fake this as workouts. Enable only after the project intentionally moves
 *   to the Health Connect 1.2.x API line and verifies runtime feature support.
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
    )

    val huaweiImportReadWritePermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getWritePermission(DistanceRecord::class),
        HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getWritePermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class),
        HealthPermission.getWritePermission(ElevationGainedRecord::class),
        HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
        HealthPermission.getWritePermission(ExerciseSessionRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getWritePermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
    )

    val runtimePermissions: Set<String>
        get() = if (FeatureFlags.HUAWEI_IMPORT_ENABLED) {
            huaweiImportReadWritePermissions
        } else {
            dashboardReadPermissions
        }

    // Compatibility aliases for older call sites.
    val permissions: Set<String> get() = runtimePermissions
    val dashboardPermissions: Set<String> get() = dashboardReadPermissions
    val importPermissions: Set<String> get() = huaweiImportReadWritePermissions
}
