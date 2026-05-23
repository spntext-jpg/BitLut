package com.openhealth.sync.data.remote

import com.google.gson.annotations.SerializedName

// ── OAuth2 token response ─────────────────────────────────────────────────────
data class HuaweiTokenResponse(
    @SerializedName("access_token")  val accessToken: String?,
    @SerializedName("expires_in")   val expiresIn: Long?,
    @SerializedName("refresh_token") val refreshToken: String?,
    @SerializedName("error")        val error: String?,
    @SerializedName("error_description") val errorDescription: String?
) {
    /** Returns true only when the response is a valid successful token grant. */
    fun isSuccess(): Boolean = !accessToken.isNullOrEmpty() && error == null
}

// ── Health data request ────────────────────────────────────────────────────────
data class HuaweiHealthRequest(
    @SerializedName("startTime") val startTimeMs: Long,
    @SerializedName("endTime")   val endTimeMs: Long,
    @SerializedName("dataType")  val dataTypes: List<String>
)

// ── Health data response ──────────────────────────────────────────────────────
data class HuaweiHealthResponse(
    @SerializedName("steps")      val steps: List<HuaweiSampleRecord>?,
    @SerializedName("heart_rate") val heartRate: List<HuaweiSampleRecord>?,
    @SerializedName("sleep")      val sleep: List<HuaweiSampleRecord>?
)

data class HuaweiSampleRecord(
    @SerializedName("startTime") val startTimeMs: Long,
    @SerializedName("endTime")   val endTimeMs: Long?,   // null for point-in-time (heart rate)
    @SerializedName("time")      val timeMs: Long?,       // used by heart rate
    @SerializedName("value")     val value: Double
)
