package com.openhealth.sync.data.remote

import com.google.gson.annotations.SerializedName

data class HuaweiTokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("expires_in") val expiresIn: Long,
    @SerializedName("refresh_token") val refreshToken: String
)

data class HuaweiSampleData(
    val startTime: Long,
    val endTime: Long,
    val value: Int
)