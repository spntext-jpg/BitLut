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
    val heartRates: List<HeartRateData>
) {
    val isEmpty: Boolean get() = steps.isEmpty() && heartRates.isEmpty()
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
        Scopes.HEALTHKIT_HEARTRATE_READ
    )

    fun isAuthorized(): Boolean = prefs.getBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, false)

    fun getAuthorizationIntent(): Intent = settingController.requestAuthorizationIntent(scopes, true)

    fun handleAuthorizationResult(data: Intent?): Boolean {
        val result = settingController.parseHealthKitAuthResultFromIntent(data)
        val success = result?.isSuccess == true
        prefs.edit().putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, success).apply()
        if (success) {
            AppLogger.i(TAG, "Huawei Health Kit authorization granted")
        } else {
            AppLogger.e(TAG, "Huawei Health Kit authorization failed: ${result?.errorCode ?: "no result"}")
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
        val heartRates = readHeartRates(startTimeMs, endTimeMs)
        AppLogger.i(TAG, "Huawei read complete: steps=${steps.size}, heartRates=${heartRates.size}")
        return HuaweiHealthSnapshot(steps = steps, heartRates = heartRates)
    }

    private suspend fun readSteps(startTimeMs: Long, endTimeMs: Long): List<StepData> {
        if (!HmsCoreHelper.isInstalled(context)) {
            AppLogger.e("HuaweiHealthManager", HmsCoreHelper.missingMessage())
            throw IllegalStateException(HmsCoreHelper.missingMessage())
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

    private suspend fun readHeartRates(startTimeMs: Long, endTimeMs: Long): List<HeartRateData> {
        val options = ReadOptions.Builder()
            .read(DataType.DT_INSTANTANEOUS_HEART_RATE)
            .setTimeRange(startTimeMs, endTimeMs, TimeUnit.MILLISECONDS)
            .build()

        val reply = dataController.read(options).awaitTask()
        return reply.sampleSets.flatMap { set ->
            set.samplePoints.mapNotNull { point -> point.toHeartRateDataOrNull() }
        }.filter { it.beatsPerMinute > 0 }
    }

    private fun SamplePoint.toStepDataOrNull(): StepData? = try {
        val count = getFieldValue(Field.FIELD_STEPS_DELTA).asIntValue().toLong()
        StepData(
            startTimeMs = getStartTime(TimeUnit.MILLISECONDS),
            endTimeMs = getEndTime(TimeUnit.MILLISECONDS),
            count = count
        )
    } catch (e: Exception) {
        AppLogger.w(TAG, "Skipping malformed Huawei step sample: ${e.message}")
        null
    }

    private fun SamplePoint.toHeartRateDataOrNull(): HeartRateData? = try {
        val bpm = getFieldValue(Field.FIELD_BPM).asDoubleValue().toLong()
        val time = getStartTime(TimeUnit.MILLISECONDS)
        HeartRateData(timeMs = time, beatsPerMinute = bpm)
    } catch (e: Exception) {
        AppLogger.w(TAG, "Skipping malformed Huawei heart-rate sample: ${e.message}")
        null
    }

    private suspend fun <T> Task<T>.awaitTask(): T = kotlinx.coroutines.suspendCancellableCoroutine { cont ->
        addOnSuccessListener { value -> cont.resume(value) }
        addOnFailureListener { error -> cont.cancel(error) }
    }
}
