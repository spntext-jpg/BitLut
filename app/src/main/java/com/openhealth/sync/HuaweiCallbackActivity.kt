package com.openhealth.sync

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.remote.NetworkClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "HuaweiCallbackActivity"

/**
 * Transparent activity that intercepts the Huawei OAuth2 redirect URI,
 * extracts the authorization code, and delegates token exchange to
 * HuaweiAuthManager.
 *
 * Single Responsibility: URI parsing + UX feedback.
 * All credential and network logic lives in HuaweiAuthManager / NetworkClient.
 */
class HuaweiCallbackActivity : Activity() {

    private val authManager by lazy { HuaweiAuthManager(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val uri = intent?.data
        val authCode = uri?.getQueryParameter("code")

        if (authCode.isNullOrEmpty()) {
            Log.w(TAG, "OAuth callback received with no code. URI: $uri")
            finish()
            return
        }

        // lifecycleScope: coroutine is cancelled automatically if Activity is destroyed
        lifecycleScope.launch {
            val success = exchangeCodeForTokens(authCode)
            val message = if (success) {
                "Huawei Health Cloud подключен!"
            } else {
                "Ошибка авторизации Huawei. Попробуйте снова."
            }
            Toast.makeText(this@HuaweiCallbackActivity, message, Toast.LENGTH_SHORT).show()

            startActivity(
                Intent(this@HuaweiCallbackActivity, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
                }
            )
            finish()
        }
    }

    /**
     * Exchanges the OAuth authorization code for access + refresh tokens.
     * Delegates saving to HuaweiAuthManager.
     */
    private suspend fun exchangeCodeForTokens(code: String): Boolean =
        withContext(Dispatchers.IO) {
            return@withContext try {
                val response = NetworkClient.oauthService.getAccessToken(
                    clientId = HuaweiConfig.CLIENT_ID,
                    clientSecret = HuaweiConfig.CLIENT_SECRET,
                    code = code,
                    redirectUri = HuaweiConfig.REDIRECT_URI
                )
                if (response.isSuccess()) {
                    authManager.saveTokens(
                        accessToken = response.accessToken!!,
                        refreshToken = response.refreshToken ?: "",
                        expiresIn = response.expiresIn ?: 3600L
                    )
                    Log.d(TAG, "OAuth exchange successful")
                    true
                } else {
                    Log.e(TAG, "OAuth error: ${response.error} — ${response.errorDescription}")
                    false
                }
            } catch (e: Exception) {
                Log.e(TAG, "Network error during OAuth exchange: ${e.message}", e)
                false
            }
        }
}
