package com.openhealth.sync.data.remote

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object NetworkClient {
    private const val HUAWEI_OAUTH_URL = "https://oauth-login.cloud.huawei.com/"
    
    val huaweiAuthService: HuaweiApiService by lazy {
        Retrofit.Builder()
            .baseUrl(HUAWEI_OAUTH_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(HuaweiApiService::class.java)
    }
}
