package com.openhealth.sync.data.remote

import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.POST
import retrofit2.http.Header
import retrofit2.http.Body

interface HuaweiApiService {

    // Обмен временного кода авторизации (Auth Code) на постоянные токены доступа
    @FormUrlEncoded
    @POST("https://oauth-login.cloud.huawei.com/oauth2/v3/token")
    suspend fun getAccessToken(
        @Field("grant_type") grantType: String = "authorization_code",
        @Field("client_id") clientId: String,
        @Field("client_secret") clientSecret: String,
        @Field("code") code: String,
        @Field("redirect_uri") redirectUri: String
    ): HuaweiTokenResponse

    // Обновление протухшего токена доступа через refresh_token в фоне
    @FormUrlEncoded
    @POST("https://oauth-login.cloud.huawei.com/oauth2/v3/token")
    suspend fun refreshAccessToken(
        @Field("grant_type") grantType: String = "refresh_token",
        @Field("client_id") clientId: String,
        @Field("client_secret") clientSecret: String,
        @Field("refresh_token") refreshToken: String
    ): HuaweiTokenResponse

    // Запрос исторических данных о здоровье за конкретный промежуток времени
    @POST("https://health-api.cloud.huawei.com/healthapi/v1/dataCollectors/read")
    suspend fun getHealthData(
        @Header("Authorization") bearerToken: String,
        @Body requestBody: Map<String, Any>
    ): Map<String, Any> // Возвращает сырой массив данных для последующего парсинга
}