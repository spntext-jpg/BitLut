package com.openhealth.sync.data.repository

/**
 * Abstract contract for OAuth token storage.
 *
 * HuaweiAuthManager implements this.
 * Any change to storage backend (Room, DataStore, Keystore)
 * only requires a new implementation — callers are unaffected.
 */
interface TokenRepository {
    fun getAccessToken(): String?
    fun getRefreshToken(): String?
    fun getExpireTime(): Long
    fun saveTokens(accessToken: String, refreshToken: String, expiresIn: Long)
    fun clearTokens()
    fun isAuthorized(): Boolean
    suspend fun getValidToken(): String?
}
