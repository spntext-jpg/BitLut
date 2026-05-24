package com.openhealth.sync.data

import android.content.Context
import android.util.Log
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.remote.NetworkClient
import com.openhealth.sync.data.repository.TokenRepository
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private const val TAG = "HuaweiAuthManager"

/**
 * Implements TokenRepository — single source of truth for Huawei session state.
 * All token reads/writes go through this class only.
 * HuaweiCallbackActivity and SyncWorker both use this via the TokenRepository interface.
 */
class HuaweiAuthManager(context: Context) : TokenRepository {

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

    override fun getAccessToken(): String? =
        prefs.getString(HuaweiConfig.KEY_ACCESS_TOKEN, null)

    override fun getRefreshToken(): String? =
        prefs.getString(HuaweiConfig.KEY_REFRESH_TOKEN, null)

    override fun getExpireTime(): Long =
        prefs.getLong(HuaweiConfig.KEY_EXPIRE_TIME, 0L)

    override fun isAuthorized(): Boolean =
        !getAccessToken().isNullOrEmpty()

    override fun saveTokens(accessToken: String, refreshToken: String, expiresIn: Long) {
        val expireTime = System.currentTimeMillis() + (expiresIn * 1000L)
        prefs.edit()
            .putString(HuaweiConfig.KEY_ACCESS_TOKEN, accessToken)
            .putString(HuaweiConfig.KEY_REFRESH_TOKEN, refreshToken)
            .putLong(HuaweiConfig.KEY_EXPIRE_TIME, expireTime)
            .apply()
        AppLogger.d(TAG, "Tokens saved, expires in ${expiresIn}s")
    }

    override fun clearTokens() {
        prefs.edit()
            .remove(HuaweiConfig.KEY_ACCESS_TOKEN)
            .remove(HuaweiConfig.KEY_REFRESH_TOKEN)
            .remove(HuaweiConfig.KEY_EXPIRE_TIME)
            .apply()
        AppLogger.w(TAG, "Tokens cleared")
    }

    override suspend fun getValidToken(): String? = withContext(Dispatchers.IO) {
        val refreshToken = getRefreshToken() ?: run {
            AppLogger.w(TAG, "No refresh token — user must re-authenticate")
            return@withContext null
        }
        val expireTime = getExpireTime()
        val needsRefresh = System.currentTimeMillis() >
            (expireTime - HuaweiConfig.TOKEN_REFRESH_THRESHOLD_MS)

        if (!needsRefresh) return@withContext getAccessToken()

        AppLogger.i(TAG, "Token expiring soon — refreshing")
        return@withContext try {
            val response = NetworkClient.oauthService.refreshAccessToken(
                clientId = HuaweiConfig.CLIENT_ID,
                clientSecret = HuaweiConfig.CLIENT_SECRET,
                refreshToken = refreshToken
            )
            if (response.isSuccess()) {
                saveTokens(
                    accessToken  = response.accessToken!!,
                    refreshToken = response.refreshToken ?: refreshToken,
                    expiresIn    = response.expiresIn ?: 3600L
                )
                AppLogger.i(TAG, "Token refreshed")
                response.accessToken
            } else {
                AppLogger.e(TAG, "Refresh failed: ${response.error} — ${response.errorDescription}")
                clearTokens()
                null
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "Network error during refresh: ${e.message}")
            getAccessToken() // keep current token on network error
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
