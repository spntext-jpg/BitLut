package com.openhealth.sync.data

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.remote.NetworkClient
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private const val TAG = "HuaweiAuthManager"

/**
 * Manages Huawei OAuth2 session: token storage, refresh, and auth URL generation.
 *
 * Storage: standard SharedPreferences (MODE_PRIVATE).
 * Android's app sandbox prevents other apps from reading these files.
 * EncryptedSharedPreferences will be added once the stable 1.0.0 API is confirmed
 * compatible with the Health Connect dependency graph on API 33+.
 */
class HuaweiAuthManager(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun isAuthorized(): Boolean =
        !prefs.getString(HuaweiConfig.KEY_ACCESS_TOKEN, null).isNullOrEmpty()

    fun getAccessToken(): String? =
        prefs.getString(HuaweiConfig.KEY_ACCESS_TOKEN, null)

    fun saveTokens(accessToken: String, refreshToken: String, expiresIn: Long) {
        val expireTime = System.currentTimeMillis() + (expiresIn * 1000L)
        prefs.edit()
            .putString(HuaweiConfig.KEY_ACCESS_TOKEN, accessToken)
            .putString(HuaweiConfig.KEY_REFRESH_TOKEN, refreshToken)
            .putLong(HuaweiConfig.KEY_EXPIRE_TIME, expireTime)
            .apply()
        AppLogger.d(TAG, "Tokens saved. Expires in ${expiresIn}s")
    }

    fun clearTokens() {
        prefs.edit()
            .remove(HuaweiConfig.KEY_ACCESS_TOKEN)
            .remove(HuaweiConfig.KEY_REFRESH_TOKEN)
            .remove(HuaweiConfig.KEY_EXPIRE_TIME)
            .apply()
        AppLogger.d(TAG, "Tokens cleared")
    }

    suspend fun getValidToken(): String? = withContext(Dispatchers.IO) {
        val expireTime    = prefs.getLong(HuaweiConfig.KEY_EXPIRE_TIME, 0L)
        val refreshToken  = prefs.getString(HuaweiConfig.KEY_REFRESH_TOKEN, null)
        val currentToken  = prefs.getString(HuaweiConfig.KEY_ACCESS_TOKEN, null)

        if (refreshToken == null) {
            AppLogger.w(TAG, "No refresh token — user must re-authenticate")
            return@withContext null
        }

        val needsRefresh = System.currentTimeMillis() >
            (expireTime - HuaweiConfig.TOKEN_REFRESH_THRESHOLD_MS)
        if (!needsRefresh) return@withContext currentToken

        AppLogger.d(TAG, "Token expiring soon — refreshing")
        return@withContext try {
            val response = NetworkClient.oauthService.refreshAccessToken(
                clientId     = HuaweiConfig.CLIENT_ID,
                clientSecret = HuaweiConfig.CLIENT_SECRET,
                refreshToken = refreshToken
            )
            if (response.isSuccess()) {
                saveTokens(
                    accessToken  = response.accessToken!!,
                    refreshToken = response.refreshToken ?: refreshToken,
                    expiresIn    = response.expiresIn ?: 3600L
                )
                AppLogger.d(TAG, "Token refreshed successfully")
                response.accessToken
            } else {
                AppLogger.e(TAG, "Refresh failed: ${response.error} — ${response.errorDescription}")
                clearTokens()
                null
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "Network error during refresh: ${e.message}")
            currentToken
        }
    }

    fun getAuthUrl(): String =
        "${HuaweiConfig.OAUTH_BASE_URL}oauth2/v3/authorize" +
        "?response_type=code" +
        "&client_id=${HuaweiConfig.CLIENT_ID}" +
        "&redirect_uri=${HuaweiConfig.REDIRECT_URI}" +
        "&scope=${HuaweiConfig.SCOPES}" +
        "&access_type=offline"
}
