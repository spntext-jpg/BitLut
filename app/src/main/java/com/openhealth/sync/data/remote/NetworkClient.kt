package com.openhealth.sync.data.remote

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * Single source of Retrofit instances for the entire app.
 * Fixes: 3 separate inline Retrofit builders in HuaweiAuthManager,
 *        HuaweiCallbackActivity, and SyncWorker.
 */
object NetworkClient {

    val oauthService: HuaweiOAuthService by lazy {
        Retrofit.Builder()
            .baseUrl(HuaweiConfig.OAUTH_BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(HuaweiOAuthService::class.java)
    }

    val healthService: HuaweiHealthApiService by lazy {
        Retrofit.Builder()
            .baseUrl(HuaweiConfig.HEALTH_API_BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(HuaweiHealthApiService::class.java)
    }
}
