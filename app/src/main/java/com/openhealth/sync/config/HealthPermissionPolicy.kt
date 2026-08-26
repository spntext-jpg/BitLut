package com.openhealth.sync.config

import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.TotalCaloriesBurnedRecord

/**
 * BitLut v1.9.6 strict Health Connect permission policy.
 *
 * Huawei AppGallery approval currently covers activity/basic sport read-only data:
 * - Step
 * - Distance, ascent and altitude
 * - Active Hours
 * - Daily Activity Summary
 * - Activity record
 * - Activity
 *
 * Sleep, pulse, SpO2, HRV, stress and Activity Intensity are intentionally not
 * requested, not read and not written in this release.
 *
 * Sprint 2026-08-25 exception: TotalCaloriesBurnedRecord read+write was added
 * as a deliberate, user-approved one-off exception to this project's general
 * "no new Health Connect/Huawei permissions" rule. Huawei's activeCalories
 * category is permanently denied (error 50005) for this individual-developer
 * account, so BitLut's ExerciseSessionRecord writes previously carried no
 * calorie data at all. Several real third-party Health Connect readers
 * (documented pattern: MyFitnessPal requires calories, other apps require
 * distance) silently decline to import an exercise session with nothing
 * attached to it. TotalCaloriesBurnedRecord -- not the still-unavailable
 * ActiveCaloriesBurnedRecord -- lets BitLut attach a MET-formula estimate
 * (see GoogleHealthManager.estimatedTotalCaloriesKcal) so those readers have
 * something to import, without requesting any new Huawei scope.
 */
object HealthPermissionPolicy {
    val huaweiImportReadPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class),
        HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
        HealthPermission.getReadPermission(TotalCaloriesBurnedRecord::class),
    )

    val importWritePermissions: Set<String> = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(DistanceRecord::class),
        HealthPermission.getWritePermission(FloorsClimbedRecord::class),
        HealthPermission.getWritePermission(ElevationGainedRecord::class),
        HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getWritePermission(ExerciseSessionRecord::class),
        HealthPermission.getWritePermission(TotalCaloriesBurnedRecord::class),
    )

    val optionalDashboardReadPermissions: Set<String> = emptySet()

    val syncPermissions: Set<String> = huaweiImportReadPermissions + importWritePermissions
    val requestPermissions: Set<String> = syncPermissions
    val dashboardReadPermissions: Set<String> = huaweiImportReadPermissions

    val dashboardPermissions: Set<String> = dashboardReadPermissions
    val importPermissions: Set<String> = syncPermissions
    val allPermissions: Set<String> = requestPermissions

    fun isRequiredSyncPermission(permission: String): Boolean = permission in syncPermissions
    fun isOptionalDashboardPermission(permission: String): Boolean = false
}
