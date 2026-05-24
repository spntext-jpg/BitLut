package com.openhealth.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.remote.NetworkClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "HuaweiCallbackActivity"

class HuaweiCallbackActivity : AppCompatActivity() {

    private val authManager by lazy { HuaweiAuthManager(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val code = intent?.data?.getQueryParameter("code")
        if (code.isNullOrEmpty()) {
            Log.w(TAG, "OAuth callback: no code in URI ${intent?.data}")
            finish()
            return
        }

        lifecycleScope.launch {
            val success = exchangeCodeForTokens(code)
            Toast.makeText(
                this@HuaweiCallbackActivity,
                if (success) "Huawei Health подключен!" else "Ошибка авторизации Huawei",
                Toast.LENGTH_SHORT
            ).show()
            startActivity(
                Intent(this@HuaweiCallbackActivity, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
                }
            )
            finish()
        }
    }

    private suspend fun exchangeCodeForTokens(code: String): Boolean =
        withContext(Dispatchers.IO) {
            try {
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
                    true
                } else {
                    Log.e(TAG, "OAuth error: ${response.error} — ${response.errorDescription}")
                    false
                }
            } catch (e: Exception) {
                Log.e(TAG, "Network error: ${e.message}", e)
                false
            }
        }
}
