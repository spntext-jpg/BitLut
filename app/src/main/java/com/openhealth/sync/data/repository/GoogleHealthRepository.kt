package com.openhealth.sync.data.repository

import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HeartRateData
import com.openhealth.sync.data.StepData

/**
 * Concrete implementation backed by Google Health Connect.
 * SyncWorker receives this as HealthDataRepository — it never imports
 * GoogleHealthManager directly.
 */
class GoogleHealthRepository(
    private val manager: GoogleHealthManager
) : HealthDataRepository {

    override suspend fun writeSteps(records: List<StepData>): Boolean =
        manager.writeStepsBatch(records)

    override suspend fun writeHeartRate(records: List<HeartRateData>): Boolean =
        manager.writeHeartRateBatch(records)

    override suspend fun hasWritePermissions(): Boolean =
        manager.hasAllPermissions()
}
