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
    suspend fun readDashboardSnapshot(): GoogleDashboardSnapshot?
    suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): WriteSnapshotResult

    /**
     * Compares the last 7 full days (including today, partial) against the
     * 7 days before that, for the activity-only metrics BitLut already has
     * approved access to (steps, distance, calories). Returns null only if
     * the underlying client is unavailable; a genuinely empty week still
     * returns a comparison with zero totals rather than null, so the caller
     * can render "no activity yet" rather than treating it as an error.
     */
    suspend fun readWeekOverWeekComparison(): WeekComparison?

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

/**
 * Week-over-week comparison for the three activity-only metrics BitLut has
 * approved access to. [currentWeekSteps]/[previousWeekSteps] etc. are raw
 * totals; percent-change helpers below handle the zero-previous-week edge
 * case (a jump from 0 to any positive number is "new activity", not a
 * mathematically undefined percentage).
 */
data class WeekComparison(
    val currentWeekSteps: Long,
    val previousWeekSteps: Long,
    val currentWeekDistanceMeters: Double,
    val previousWeekDistanceMeters: Double,
    val currentWeekCaloriesKcal: Double,
    val previousWeekCaloriesKcal: Double
) {
    /** Null return means "no baseline to compare against" (previous week was
     *  zero) -- the caller should render this as "first tracked week" rather
     *  than a percentage. */
    fun stepsPercentChange(): Int? = percentChange(previousWeekSteps.toDouble(), currentWeekSteps.toDouble())
    fun distancePercentChange(): Int? = percentChange(previousWeekDistanceMeters, currentWeekDistanceMeters)
    fun caloriesPercentChange(): Int? = percentChange(previousWeekCaloriesKcal, currentWeekCaloriesKcal)

    private fun percentChange(previous: Double, current: Double): Int? {
        if (previous <= 0.0) return null
        return (((current - previous) / previous) * 100.0).let {
            if (it.isFinite()) it.toInt() else null
        }
    }
}
