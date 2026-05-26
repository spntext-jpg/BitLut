package com.openhealth.sync.data

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import com.huawei.hmf.tasks.Task
import com.huawei.hms.hihealth.DataController
import com.huawei.hms.hihealth.HuaweiHiHealth
import com.huawei.hms.hihealth.SettingController
import com.huawei.hms.hihealth.data.DataType
import com.huawei.hms.hihealth.data.Field
import com.huawei.hms.hihealth.data.SamplePoint
import com.huawei.hms.hihealth.data.SampleSet
import com.huawei.hms.hihealth.data.Scopes
import com.huawei.hms.hihealth.options.ReadOptions
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.util.AppLogger
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import com.openhealth.sync.platform.HmsCoreHelper

private const val TAG = "HuaweiHealthManager"

data class HuaweiHealthSnapshot(
    val steps: List<StepData>,
    val distances: List<DistanceData> = emptyList(),
    val floors: List<FloorsData> = emptyList(),
    val elevations: List<ElevationData> = emptyList(),
    val activeCalories: List<ActiveCaloriesData> = emptyList(),
    val activities: List<ActivitySessionData> = emptyList()
) {
    val isEmpty: Boolean
        get() = steps.isEmpty() &&
            distances.isEmpty() &&
            floors.isEmpty() &&
            elevations.isEmpty() &&
            activeCalories.isEmpty() &&
            activities.isEmpty()
}

class HuaweiHealthManager(private val context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    private val settingController: SettingController by lazy {
        HuaweiHiHealth.getSettingController(context)
    }

    private val dataController: DataController by lazy {
        HuaweiHiHealth.getDataController(context)
    }

    private val scopes = arrayOf(
        Scopes.HEALTHKIT_STEP_READ,
        Scopes.HEALTHKIT_DISTANCE_READ,
        Scopes.HEALTHKIT_ACTIVITY_READ,
        Scopes.HEALTHKIT_ACTIVITY_RECORD_READ,
        Scopes.HEALTHKIT_HISTORYDATA_OPEN_WEEK
    )

    fun isAuthorized(): Boolean = prefs.getBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, false)

    fun isPendingApproval(): Boolean = prefs.getBoolean("huawei_pending_approval", false)

    fun getAuthorizationIntent(): Intent = settingController.requestAuthorizationIntent(scopes, true)

    fun handleAuthorizationResult(data: Intent?): Boolean {
        val result = settingController.parseHealthKitAuthResultFromIntent(data)
        val success = result?.isSuccess == true
        val code = result?.errorCode
        val isPending = code == 50005
        prefs.edit()
            .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, success)
            .putBoolean("huawei_pending_approval", isPending)
            .apply()

        if (success) {
            AppLogger.i(TAG, "Huawei Health Kit authorization granted")
        } else {
            val hint = when (code) {
                50005 -> "Scope unauthorized — Health Service Kit approval pending (up to 15 working days). This is expected, no action needed."
                50011 -> "Huawei Health privacy/authorization was not accepted. Open Huawei Health > Me > Privacy management > HUAWEI Health Kit, then revoke BitLut authorization and try again."
                907135702 -> "Certificate fingerprint mismatch. Check SHA-256 in AppGallery Connect."
                907135000 -> "Invalid HMS arguments. Check appid metadata, package name, and agconnect-services.json."
                else -> "Check Health Kit enablement, SHA-256, agconnect-services.json, and test account permissions."
            }
            if (isPending) {
                AppLogger.w(TAG, "Huawei Health Kit authorization pending approval: ${code}. $hint")
            } else {
                AppLogger.e(TAG, "Huawei Health Kit authorization failed: ${code ?: "no result"}. $hint")
            }
        }

        return success
    }


    fun markAuthorizationUnknown() {
        prefs.edit().putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, false).apply()
    }

    suspend fun readSnapshot(startTimeMs: Long, endTimeMs: Long): HuaweiHealthSnapshot {
        require(startTimeMs < endTimeMs) { "startTimeMs must be before endTimeMs" }
        AppLogger.i(TAG, "Reading Huawei Health data from $startTimeMs to $endTimeMs")
        val steps = readSteps(startTimeMs, endTimeMs)

        // Production MVP:
        // Huawei scopes are already requested for distance/ascent/activity/history,
        // but we only write non-empty datasets after we safely map Huawei fields.
        // This keeps the app production-safe during Huawei approval and prevents fake data.
        val distances = emptyList<DistanceData>()
        val floors = emptyList<FloorsData>()
        val elevations = emptyList<ElevationData>()
        val activeCalories = emptyList<ActiveCaloriesData>()
        val activities = emptyList<ActivitySessionData>()

        AppLogger.i(
            TAG,
            "Huawei read complete: steps=${steps.size}, distances=${distances.size}, floors=${floors.size}, elevations=${elevations.size}, activeCalories=${activeCalories.size}, activities=${activities.size}"
        )

        return HuaweiHealthSnapshot(
            steps = steps,
            distances = distances,
            floors = floors,
            elevations = elevations,
            activeCalories = activeCalories,
            activities = activities
        )
    }

    private suspend fun readSteps(startTimeMs: Long, endTimeMs: Long): List<StepData> {
        if (!HmsCoreHelper.isInstalled(context)) {
            AppLogger.e("HuaweiHealthManager", HmsCoreHelper.missingMessage)
            throw IllegalStateException(HmsCoreHelper.missingMessage)
        }

        val options = ReadOptions.Builder()
            .read(DataType.DT_CONTINUOUS_STEPS_DELTA)
            .setTimeRange(startTimeMs, endTimeMs, TimeUnit.MILLISECONDS)
            .build()

        val reply = dataController.read(options).awaitTask()
        return reply.sampleSets.flatMap { set ->
            set.samplePoints.mapNotNull { point -> point.toStepDataOrNull() }
        }.filter { it.count > 0 && it.startTimeMs < it.endTimeMs }
    }


    private fun SamplePoint.toStepDataOrNull(): StepData? {
        return try {
            val start = getStartTime(TimeUnit.MILLISECONDS)
            val end = getEndTime(TimeUnit.MILLISECONDS)

            val value = fieldValueMap["steps"] ?: return null

            val count = when (value) {
                is Int -> value.toLong()
                is Long -> value
                is Float -> value.toLong()
                is Double -> value.toLong()
                else -> return null
            }

            if (count <= 0L || start >= end) return null

            StepData(
                startTimeMs = start,
                endTimeMs = end,
                count = count
            )
        } catch (_: Exception) {
            null
        }
    }

    private suspend fun <T> Task<T>.awaitTask(): T = kotlinx.coroutines.suspendCancellableCoroutine { cont ->
        addOnSuccessListener { value -> cont.resume(value) }
        addOnFailureListener { error -> cont.cancel(error) }
    }
}
