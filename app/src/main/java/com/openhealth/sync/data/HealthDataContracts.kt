package com.openhealth.sync.data

import android.content.Intent

/**
 * Thin contracts for ViewModel/test boundaries.
 *
 * Keep these interfaces activity-only for v1.9.6. Do not add sleep, pulse,
 * SpO2, HRV, stress or Activity Intensity until Huawei approval scope expands.
 */
interface HealthConnectManager {
    val permissions: Set<String>

    fun requiredPermissions(): Set<String>
    fun getStatus(): HealthConnectStatus

    suspend fun missingRequiredPermissions(): Set<String>
    suspend fun hasAllPermissions(): Boolean
    suspend fun readDashboardSnapshot(daysBack: Int): GoogleDashboardSnapshot?
    suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): WriteSnapshotResult

    /**
     * Forces re-resolution of the underlying Health Connect client on the next
     * access if it is currently unavailable/poisoned. Self-healing hook: call
     * this when a write/read unexpectedly fails so that a transient init
     * failure (e.g. Health Connect provider not yet ready right after device
     * boot) does not permanently disable Health Connect access for the
     * lifetime of the process. Implementations that don't cache the client
     * may treat this as a no-op.
     */
    fun invalidateClientCache()
}

interface HuaweiHealthReader {
    fun requestedScopeNames(): String
    fun isAuthorized(): Boolean
    fun isPendingApproval(): Boolean
    fun isAppGalleryVerificationRequired(): Boolean
    fun clearAppGalleryVerificationRequired()
    fun markAppGalleryVerificationRequired()
    fun getAuthorizationIntent(): Intent
    fun getHuaweiIdAuthorizationIntent(): Intent
    fun handleAuthorizationResult(resultCode: Int, data: Intent?): Boolean
    fun markAuthorizationUnknown()

    suspend fun readSnapshot(startTimeMs: Long, endTimeMs: Long): HuaweiHealthSnapshot
}

/**
 * Per-category outcome of a [HealthConnectManager.writeSnapshot] call.
 *
 * Replaces a plain `Boolean` so a single failing category (e.g. floors,
 * which several Huawei device/firmware combinations simply don't expose)
 * cannot block the sync cursor for categories that wrote successfully. The
 * sync cursor only needs to "rewind" for categories that actually failed,
 * not for the whole snapshot.
 */
data class WriteSnapshotResult(
    val succeededCategories: Set<String>,
    val failedCategories: Set<String>
) {
    val allSucceeded: Boolean get() = failedCategories.isEmpty()
    val anySucceeded: Boolean get() = succeededCategories.isNotEmpty()
    val allFailed: Boolean get() = succeededCategories.isEmpty() && failedCategories.isNotEmpty()

    companion object {
        val EMPTY = WriteSnapshotResult(emptySet(), emptySet())
    }
}
