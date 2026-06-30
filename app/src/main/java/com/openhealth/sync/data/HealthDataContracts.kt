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
    suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): Boolean
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
