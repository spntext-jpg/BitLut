package com.openhealth.sync.data.remote

import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.POST

/**
 * Retrofit interface for Huawei OAuth2 token endpoints.
 * Base URL: https://oauth-login.cloud.huawei.com/
 */
interface HuaweiOAuthService {

    @FormUrlEncoded
    @POST("oauth2/v3/token")
    suspend fun getAccessToken(
        @Field("grant_type") grantType: String = "authorization_code",
        @Field("client_id") clientId: String,
        @Field("client_secret") clientSecret: String,
        @Field("code") code: String,
        @Field("redirect_uri") redirectUri: String
    ): HuaweiTokenResponse

    @FormUrlEncoded
    @POST("oauth2/v3/token")
    suspend fun refreshAccessToken(
        @Field("grant_type") grantType: String = "refresh_token",
        @Field("client_id") clientId: String,
        @Field("client_secret") clientSecret: String,
        @Field("refresh_token") refreshToken: String
    ): HuaweiTokenResponse
}
