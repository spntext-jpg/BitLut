package com.openhealth.sync.data

import android.content.Context
import com.openhealth.sync.data.remote.HuaweiApiService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class HuaweiAuthManager(private val context: Context) {

    private val prefs = context.getSharedPreferences("huawei_auth_prefs", Context.MODE_PRIVATE)
    
    // Легковесная инициализация Retrofit-клиента для авторизации
    private val apiService: HuaweiApiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://oauth-login.cloud.huawei.com/")
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(HuaweiApiService::class.Companion::class.java)
    }

    // Твои будущие ключи приложения из консоли разработчика Huawei
    private val clientId = "YOUR_HUAWEI_CLIENT_ID"
    private val clientSecret = "YOUR_HUAWEI_CLIENT_SECRET"
    private val redirectUri = "https://com.openhealth.sync/oauth_callback"

    fun isAuthorized(): Boolean {
        return !prefs.getString("access_token", null).isNullOrEmpty()
    }

    fun getAccessToken(): String? {
        return prefs.getString("access_token", null)
    }

    // Сохранение токенов после успешного входа
    fun saveTokens(accessToken: String, refreshToken: String, expiresIn: Long) {
        val expireTime = System.currentTimeMillis() + (expiresIn * 1000)
        prefs.edit()
            .putString("access_token", accessToken)
            .putString("refresh_token", refreshToken)
            .putLong("expire_time", expireTime)
            .apply()
    }

    // Проверка, не протух ли токен, и его фоновое обновление по принципу KISS
    suspend fun refreshSessionIfNeeded(): String? = withContext(Dispatchers.IO) {
        val expireTime = prefs.getLong("expire_time", 0)
        val refreshToken = prefs.getString("refresh_token", null)
        val currentToken = prefs.getString("access_token", null)

        if (refreshToken == null) return@withContext null

        // Если до истечения токена осталось меньше 5 минут — обновляем
        if (System.currentTimeMillis() > (expireTime - 5 * 60 * 1000)) {
            try {
                val response = apiService.refreshAccessToken(
                    clientId = clientId,
                    clientSecret = clientSecret,
                    refreshToken = refreshToken
                )
                saveTokens(response.accessToken, response.refreshToken, response.expiresIn)
                return@withContext response.accessToken
            } catch (e: Exception) {
                e.printStackTrace()
                return@withContext null
            }
        }
        return@withContext currentToken
    }

    // Генерация красивой и чистой ссылки для входа пользователя через браузер/WebView
    fun getAuthUrl(): String {
        return "https://oauth-login.cloud.huawei.com/oauth2/v3/authorize" +
                "?response_type=code" +
                "&client_id=$clientId" +
                "&redirect_uri=$redirectUri" +
                "&scope=https://www.huawei.com/auth/healthkit.step.read+https://www.huawei.com/auth/healthkit.heartrate.read" +
                "&access_type=offline"
    }
}