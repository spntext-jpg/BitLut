package com.openhealth.sync.data

import android.content.Context
import android.util.Log
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.remote.NetworkClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private const val TAG = "HuaweiAuthManager"

/**
 * Manages Huawei OAuth2 session: token storage, refresh, and auth URL generation.
 * Uses EncryptedSharedPreferences so tokens are never stored in plaintext.
 *
 * Single Responsibility: token lifecycle management only.
 * Credentials and URLs come from HuaweiConfig (SSOT).
 * Network calls go through NetworkClient (DI-ready singleton).
 */
class HuaweiAuthManager(context: Context) {

    // ── Encrypted token storage ───────────────────────────────────────────────
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context,
        HuaweiConfig.PREFS_NAME,
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    // ── Public API ────────────────────────────────────────────────────────────

    fun isAuthorized(): Boolean =
        !prefs.getString(HuaweiConfig.KEY_ACCESS_TOKEN, null).isNullOrEmpty()

    fun getAccessToken(): String? =
        prefs.getString(HuaweiConfig.KEY_ACCESS_TOKEN, null)

    /** Saves tokens received after a successful OAuth exchange or refresh. */
    fun saveTokens(accessToken: String, refreshToken: String, expiresIn: Long) {
        val expireTime = System.currentTimeMillis() + (expiresIn * 1000L)
        prefs.edit()
            .putString(HuaweiConfig.KEY_ACCESS_TOKEN, accessToken)
            .putString(HuaweiConfig.KEY_REFRESH_TOKEN, refreshToken)
            .putLong(HuaweiConfig.KEY_EXPIRE_TIME, expireTime)
            .apply()
        Log.d(TAG, "Tokens saved. Expires in ${expiresIn}s")
    }

    /** Clears all tokens (for logout / re-auth). */
    fun clearTokens() {
        prefs.edit()
            .remove(HuaweiConfig.KEY_ACCESS_TOKEN)
            .remove(HuaweiConfig.KEY_REFRESH_TOKEN)
            .remove(HuaweiConfig.KEY_EXPIRE_TIME)
            .apply()
        Log.d(TAG, "Tokens cleared")
    }

    /**
     * Returns a valid access token, refreshing it proactively if it is about
     * to expire within TOKEN_REFRESH_THRESHOLD_MS.
     * Returns null if no refresh token exists (user must re-authenticate).
     */
    suspend fun getValidToken(): String? = withContext(Dispatchers.IO) {
        val expireTime = prefs.getLong(HuaweiConfig.KEY_EXPIRE_TIME, 0L)
        val refreshToken = prefs.getString(HuaweiConfig.KEY_REFRESH_TOKEN, null)
        val currentToken = prefs.getString(HuaweiConfig.KEY_ACCESS_TOKEN, null)

        // No refresh token → user must go through OAuth flow again
        if (refreshToken == null) {
            Log.w(TAG, "No refresh token — user must re-authenticate")
            return@withContext null
        }

        val needsRefresh = System.currentTimeMillis() > (expireTime - HuaweiConfig.TOKEN_REFRESH_THRESHOLD_MS)
        if (!needsRefresh) return@withContext currentToken

        Log.d(TAG, "Token expiring soon — refreshing...")
        return@withContext try {
            val response = NetworkClient.oauthService.refreshAccessToken(
                clientId = HuaweiConfig.CLIENT_ID,
                clientSecret = HuaweiConfig.CLIENT_SECRET,
                refreshToken = refreshToken
            )
            if (response.isSuccess()) {
                saveTokens(
                    accessToken = response.accessToken!!,
                    refreshToken = response.refreshToken ?: refreshToken, // keep old if not rotated
                    expiresIn = response.expiresIn ?: 3600L
                )
                Log.d(TAG, "Token refreshed successfully")
                response.accessToken
            } else {
                Log.e(TAG, "Token refresh failed: ${response.error} — ${response.errorDescription}")
                // Refresh token is invalid/revoked — clear everything, force re-auth
                clearTokens()
                null
            }
        } catch (e: Exception) {
            // Network error: keep existing token, caller will retry later
            Log.e(TAG, "Network error during token refresh: ${e.message}")
            currentToken
        }
    }

    /** Generates the Huawei OAuth2 authorization URL for browser-based login. */
    fun getAuthUrl(): String =
        "${HuaweiConfig.OAUTH_BASE_URL}oauth2/v3/authorize" +
        "?response_type=code" +
        "&client_id=${HuaweiConfig.CLIENT_ID}" +
        "&redirect_uri=${HuaweiConfig.REDIRECT_URI}" +
        "&scope=${HuaweiConfig.SCOPES}" +
        "&access_type=offline"
}
