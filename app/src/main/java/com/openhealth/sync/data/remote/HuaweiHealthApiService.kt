package com.openhealth.sync.data.remote

import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

/**
 * Retrofit interface for Huawei Health Kit data endpoints.
 * Base URL: https://health-api.cloud.huawei.com/
 *
 * The Authorization header is injected by NetworkClient's OkHttp interceptor —
 * callers never prepend "Bearer " manually.
 */
interface HuaweiHealthApiService {

    @POST("healthapi/v1/dataCollectors/read")
    suspend fun getHealthData(
        @Header("Authorization") bearerToken: String,
        @Body requestBody: HuaweiHealthRequest
    ): HuaweiHealthResponse
}
