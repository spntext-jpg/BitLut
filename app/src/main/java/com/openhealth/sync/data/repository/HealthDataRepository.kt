package com.openhealth.sync.data.repository

import com.openhealth.sync.data.StepData
import com.openhealth.sync.data.HeartRateData
import java.time.Instant

/**
 * Abstract contract for health data operations.
 *
 * The rest of the app talks only to this interface.
 * Adding Samsung Health or Fitbit = new implementation, zero changes elsewhere.
 * SyncWorker depends on this abstraction, not on GoogleHealthManager directly.
 */
interface HealthDataRepository {
    suspend fun writeSteps(records: List<StepData>): Boolean
    suspend fun writeHeartRate(records: List<HeartRateData>): Boolean
    suspend fun hasWritePermissions(): Boolean
}
