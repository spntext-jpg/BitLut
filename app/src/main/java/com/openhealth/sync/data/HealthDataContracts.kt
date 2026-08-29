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

/**
 * Classification of *why* the last Huawei Health Kit authorization attempt
 * failed (sprint 2026-07-18, added after an AppGallery review rejection
 * whose only visible symptom -- a single generic toast -- could have meant
 * any of these). Each case maps to a distinct, actionable next step; see
 * HuaweiHealthManager's classifyFailure() for the exact HMS error code
 * mapping and CLAUDE.md for the platform-specific detail behind each one.
 */
enum class HuaweiAuthFailureReason {
    /** HMS code 50005. Huawei's own server-side review of this app's
     *  requested scopes hasn't completed yet -- purely a waiting state,
     *  not something fixable by changing app code or configuration. */
    SCOPE_PENDING_APPROVAL,

    /** HMS code 50011. The person hasn't accepted Huawei Health's own
     *  privacy terms yet -- resolved inside the Huawei Health app itself,
     *  not by BitLut. */
    PRIVACY_NOT_ACCEPTED,

    /** HMS codes 907135702 / 6003. The signing certificate this build was
     *  actually signed with doesn't match the SHA-256 fingerprint
     *  registered for Health Kit in AppGallery Connect -- very often
     *  caused by registering the local upload-key fingerprint instead of
     *  the certificate Huawei's own "App Signing" re-signs release builds
     *  with before a reviewer or end user ever sees them. */
    CERTIFICATE_MISMATCH,

    /** HMS code 907135000. Something in the Health Kit request itself
     *  (App ID, package name, agconnect-services.json) doesn't match
     *  what's registered in AppGallery Connect. */
    INVALID_CONFIGURATION,

    /** Any other/unrecognized failure, or no result intent at all. */
    UNKNOWN
}

interface HuaweiHealthReader {
    fun requestedScopeNames(): String
    fun isAuthorized(): Boolean
    fun isPendingApproval(): Boolean
    fun isAppGalleryVerificationRequired(): Boolean
    fun clearAppGalleryVerificationRequired()
    fun markAppGalleryVerificationRequired()
    fun lastAuthFailureReason(): HuaweiAuthFailureReason?
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
