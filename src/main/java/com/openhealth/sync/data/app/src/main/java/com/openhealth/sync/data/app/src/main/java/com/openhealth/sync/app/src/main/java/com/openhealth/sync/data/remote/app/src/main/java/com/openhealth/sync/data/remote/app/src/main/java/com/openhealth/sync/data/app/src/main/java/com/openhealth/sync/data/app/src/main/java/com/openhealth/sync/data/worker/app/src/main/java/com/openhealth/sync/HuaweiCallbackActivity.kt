package com.openhealth.sync

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.remote.HuaweiApiService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class HuaweiCallbackActivity : Activity() {

    private val huaweiAuthManager by lazy { HuaweiAuthManager(this) }
    
    private val apiService: HuaweiApiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://oauth-login.cloud.huawei.com/")
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(HuaweiApiService::class.java)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val intentData = intent.data
        if (intentData != null && intentData.toString().startsWith("https://com.openhealth.sync/oauth_callback")) {
            val authCode = intentData.getQueryParameter("code")
            
            if (!authCode.isNullOrEmpty()) {
                // Запускаем асинхронный обмен кода на токены
                CoroutineScope(Dispatchers.Main).launch {
                    val success = exchangeCodeForTokens(authCode)
                    if (success) {
                        Toast.makeText(this@HuaweiCallbackActivity, "Huawei Cloud успешно подключен!", Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(this@HuaweiCallbackActivity, "Ошибка авторизации Huawei", Toast.LENGTH_LONG).show()
                    }
                    // Возвращаемся на главный экран
                    startActivity(Intent(this@HuaweiCallbackActivity, MainActivity::class.java).apply {
                        flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
                    })
                    finish()
                }
            } else {
                finish()
            }
        } else {
            finish()
        }
    }

    private suspend fun exchangeCodeForTokens(code: String): Boolean = withContext(Dispatchers.IO) {
        return@withContext try {
            val response = apiService.getAccessToken(
                clientId = "YOUR_HUAWEI_CLIENT_ID",
                clientSecret = "YOUR_HUAWEI_CLIENT_SECRET",
                code = code,
                redirectUri = "https://com.openhealth.sync/oauth_callback"
            )
            huaweiAuthManager.saveTokens(response.accessToken, response.refreshToken, response.expiresIn)
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
}