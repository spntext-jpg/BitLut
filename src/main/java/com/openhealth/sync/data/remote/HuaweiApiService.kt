package com.openhealth.sync.data.remote

import retrofit2.http.POST
import retrofit2.http.FormUrlEncoded
import retrofit2.http.Field

interface HuaweiApiService {
    @FormUrlEncoded
    @POST("oauth2/v3/token")
    suspend fun getToken(
        @Field("grant_type") grantType: String,
        @Field("client_id") clientId: String,
        @Field("client_secret") clientSecret: String,
        @Field("code") code: String,
        @Field("redirect_uri") redirectUri: String
    ): Any // Заменим Any на конкретный DTO при рефакторинге маппинга
}
