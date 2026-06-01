package com.openhealth.sync.data

import android.app.Activity
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
import com.huawei.hms.hihealth.data.Scopes
import com.huawei.hms.hihealth.options.ReadOptions
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.util.AppLogger
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume

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

private data class HuaweiMetricSample(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val value: Double
)

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

    fun requestedScopeNames(): String =
        "HEALTHKIT_STEP_READ, HEALTHKIT_DISTANCE_READ, HEALTHKIT_ACTIVITY_READ, HEALTHKIT_ACTIVITY_RECORD_READ, HEALTHKIT_HISTORYDATA_OPEN_WEEK"

    fun isAuthorized(): Boolean =
        prefs.getBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, false)

    fun isPendingApproval(): Boolean =
        prefs.getBoolean(KEY_HUAWEI_PENDING_APPROVAL, false)

    fun getAuthorizationIntent(): Intent {
        AppLogger.i(TAG, "Requesting Huawei Health Kit authorization: ${requestedScopeNames()}")
        return settingController.requestAuthorizationIntent(scopes, true)
    }

    fun handleAuthorizationResult(resultCode: Int, data: Intent?): Boolean {
        if (data == null) {
            saveAuthorizationState(success = false, pendingApproval = false)
            AppLogger.e(TAG, "Huawei authorization returned no result intent")
            return false
        }

        val result = settingController.parseHealthKitAuthResultFromIntent(data)
        val success = result?.isSuccess == true
        val code = result?.errorCode
        val pendingApproval = code == HUAWEI_SCOPE_UNAUTHORIZED

        saveAuthorizationState(success = success, pendingApproval = pendingApproval)

        if (success) {
            AppLogger.i(TAG, "Huawei Health Kit authorization granted")
            return true
        }

        val hint = when (code) {
            HUAWEI_SCOPE_UNAUTHORIZED ->
                "Scope unauthorized. Verify Health Kit approval for every requested scope, release SHA-256, package name, Huawei App ID, agconnect-services.json, reviewer account, and HMS Core cache."

            HUAWEI_PRIVACY_NOT_ACCEPTED ->
                "Huawei Health privacy authorization was not accepted. Open Huawei Health, accept privacy terms, revoke BitLut access if visible, and authorize again."

            HUAWEI_CERT_MISMATCH ->
                "Certificate fingerprint mismatch. Check the release SHA-256 configured in AppGallery Connect."

            HUAWEI_INVALID_ARGS ->
                "Invalid HMS configuration. Check appid metadata, package name, and app/agconnect-services.json."

            HUAWEI_CERT_VERIFY_FAILED ->
                "Certificate verification failed. Check release signing certificate SHA-256."

            else ->
                "Check Health Kit enablement, all requested scopes, release SHA-256, App ID, agconnect-services.json, Huawei test account, HMS Core and Huawei Health versions."
        }

        if (pendingApproval) {
            AppLogger.w(TAG, "Huawei Health Kit authorization failed with 50005. $hint")
        } else {
            AppLogger.e(TAG, "Huawei Health Kit authorization failed: ${code ?: "no result"}. $hint")
        }

        return false
    }

    fun markAuthorizationUnknown() {
        saveAuthorizationState(success = false, pendingApproval = false)
    }

    suspend fun readSnapshot(startTimeMs: Long, endTimeMs: Long): HuaweiHealthSnapshot {
        require(startTimeMs < endTimeMs) { "startTimeMs must be before endTimeMs" }
        ensureRuntimeReady()

        AppLogger.i(TAG, "Reading real Huawei Health data from $startTimeMs to $endTimeMs")

        val snapshot = HuaweiHealthSnapshot(
            steps = readSteps(startTimeMs, endTimeMs),
            distances = readDistance(startTimeMs, endTimeMs),
            floors = readFloors(startTimeMs, endTimeMs),
            elevations = readElevation(startTimeMs, endTimeMs),
            activeCalories = readActiveCalories(startTimeMs, endTimeMs),
            activities = readActivitySessions(startTimeMs, endTimeMs)
        )

        AppLogger.i(
            TAG,
            "Huawei read complete: steps=${snapshot.steps.size}, distances=${snapshot.distances.size}, floors=${snapshot.floors.size}, elevations=${snapshot.elevations.size}, activeCalories=${snapshot.activeCalories.size}, activities=${snapshot.activities.size}"
        )

        return snapshot
    }

    private fun saveAuthorizationState(success: Boolean, pendingApproval: Boolean) {
        prefs.edit()
            .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, success)
            .putBoolean(KEY_HUAWEI_PENDING_APPROVAL, pendingApproval)
            .apply()
    }

    private fun ensureRuntimeReady() {
        if (!HmsCoreHelper.isInstalled(context)) {
            throw IllegalStateException(HmsCoreHelper.missingMessage)
        }

        if (!HmsCoreHelper.isHuaweiHealthInstalled(context)) {
            throw IllegalStateException("Huawei Health is required. Install Huawei Health, sign in, and try again.")
        }
    }

    private suspend fun readSteps(startTimeMs: Long, endTimeMs: Long): List<StepData> =
        readPoints(DataType.DT_CONTINUOUS_STEPS_DELTA, startTimeMs, endTimeMs, "steps")
            .mapNotNull { point ->
                val value = point.firstNumericValue(listOf(Field.FIELD_STEPS))?.toLong() ?: return@mapNotNull null
                val start = point.getStartTime(TimeUnit.MILLISECONDS)
                val end = point.getEndTime(TimeUnit.MILLISECONDS)

                if (value > 0L && start < end) StepData(start, end, value) else null
            }

    private suspend fun readDistance(startTimeMs: Long, endTimeMs: Long): List<DistanceData> {
        val type = firstDataType(
            "DT_CONTINUOUS_DISTANCE_DELTA",
            "DT_CONTINUOUS_DISTANCE_TOTAL",
            "DT_INSTANTANEOUS_DISTANCE"
        ) ?: return emptyListWithLog("distance", "Huawei SDK does not expose a supported distance DataType")

        val fields = fields(
            "FIELD_DISTANCE",
            "FIELD_DISTANCE_DELTA",
            "FIELD_DISTANCE_TOTAL"
        )

        return readMetric(type, fields, startTimeMs, endTimeMs, "distance")
            .mapNotNull { sample ->
                if (sample.value > 0.0 && sample.startTimeMs < sample.endTimeMs) {
                    DistanceData(sample.startTimeMs, sample.endTimeMs, sample.value)
                } else {
                    null
                }
            }
    }

    private suspend fun readFloors(startTimeMs: Long, endTimeMs: Long): List<FloorsData> {
        val type = firstDataType(
            "DT_CONTINUOUS_FLOORS_CLIMBED",
            "DT_CONTINUOUS_FLOORS_CLIMBED_DELTA",
            "DT_CONTINUOUS_FLOORS_ASCENDED"
        ) ?: return emptyListWithLog("floors", "Huawei SDK does not expose a supported floors DataType")

        val fields = fields(
            "FIELD_FLOORS",
            "FIELD_FLOORS_CLIMBED",
            "FIELD_FLOORS_DELTA"
        )

        return readMetric(type, fields, startTimeMs, endTimeMs, "floors")
            .mapNotNull { sample ->
                if (sample.value > 0.0 && sample.startTimeMs < sample.endTimeMs) {
                    FloorsData(sample.startTimeMs, sample.endTimeMs, sample.value)
                } else {
                    null
                }
            }
    }

    private suspend fun readElevation(startTimeMs: Long, endTimeMs: Long): List<ElevationData> {
        val type = firstDataType(
            "DT_CONTINUOUS_ALTITUDE_DELTA",
            "DT_CONTINUOUS_ASCEND_TOTAL",
            "DT_CONTINUOUS_ASCEND",
            "DT_INSTANTANEOUS_ALTITUDE",
            "DT_INSTANTANEOUS_HEIGHT"
        ) ?: return emptyListWithLog("elevation", "Huawei SDK does not expose a supported elevation/ascent DataType")

        val fields = fields(
            "FIELD_ALTITUDE",
            "FIELD_HEIGHT",
            "FIELD_ASCEND",
            "FIELD_ASCEND_TOTAL",
            "FIELD_ELEVATION_GAINED"
        )

        return readMetric(type, fields, startTimeMs, endTimeMs, "elevation")
            .mapNotNull { sample ->
                if (sample.value > 0.0 && sample.startTimeMs < sample.endTimeMs) {
                    ElevationData(sample.startTimeMs, sample.endTimeMs, sample.value)
                } else {
                    null
                }
            }
    }

    private suspend fun readActiveCalories(startTimeMs: Long, endTimeMs: Long): List<ActiveCaloriesData> {
        val type = firstDataType(
            "DT_CONTINUOUS_CALORIES_BURNT",
            "DT_CONTINUOUS_CALORIES_BURNED",
            "DT_INSTANTANEOUS_CALORIES_BURNT"
        ) ?: return emptyListWithLog("activeCalories", "Huawei SDK does not expose a supported active calories DataType")

        val fields = fields(
            "FIELD_CALORIES",
            "FIELD_CALORIES_TOTAL",
            "FIELD_CALORIE",
            "FIELD_KCAL"
        )

        return readMetric(type, fields, startTimeMs, endTimeMs, "activeCalories")
            .mapNotNull { sample ->
                if (sample.value > 0.0 && sample.startTimeMs < sample.endTimeMs) {
                    ActiveCaloriesData(sample.startTimeMs, sample.endTimeMs, sample.value)
                } else {
                    null
                }
            }
    }

    private suspend fun readActivitySessions(startTimeMs: Long, endTimeMs: Long): List<ActivitySessionData> {
        val type = firstDataType(
            "DT_CONTINUOUS_EXERCISE_INTENSITY",
            "DT_CONTINUOUS_ACTIVITY_FRAGMENT",
            "DT_INSTANTANEOUS_ACTIVITY_SAMPLE"
        ) ?: return emptyListWithLog("activitySessions", "Huawei SDK does not expose a supported activity session DataType")

        val fields = fields(
            "FIELD_EXERCISE_INTENSITY",
            "FIELD_ACTIVITY",
            "FIELD_ACTIVITY_TYPE",
            "FIELD_INTENSITY"
        )

        val samples = readMetric(type, fields, startTimeMs, endTimeMs, "activitySessions")
            .filter { it.value > 0.0 && it.startTimeMs < it.endTimeMs }
            .sortedBy { it.startTimeMs }

        if (samples.isEmpty()) return emptyList()

        val sessions = mutableListOf<ActivitySessionData>()
        var sessionStart = samples.first().startTimeMs
        var sessionEnd = samples.first().endTimeMs

        for (sample in samples.drop(1)) {
            val gapMs = sample.startTimeMs - sessionEnd
            if (gapMs <= ACTIVITY_SESSION_MAX_GAP_MS) {
                sessionEnd = maxOf(sessionEnd, sample.endTimeMs)
            } else {
                addSessionIfValid(sessions, sessionStart, sessionEnd)
                sessionStart = sample.startTimeMs
                sessionEnd = sample.endTimeMs
            }
        }

        addSessionIfValid(sessions, sessionStart, sessionEnd)
        return sessions
    }

    private fun addSessionIfValid(
        sessions: MutableList<ActivitySessionData>,
        startTimeMs: Long,
        endTimeMs: Long
    ) {
        if (endTimeMs - startTimeMs >= ACTIVITY_SESSION_MIN_DURATION_MS) {
            sessions.add(ActivitySessionData(startTimeMs, endTimeMs, "Huawei activity"))
        }
    }

    private suspend fun readMetric(
        type: DataType,
        fields: List<Field>,
        startTimeMs: Long,
        endTimeMs: Long,
        label: String
    ): List<HuaweiMetricSample> {
        if (fields.isEmpty()) {
            AppLogger.w(TAG, "Skipping $label: no supported Huawei fields found")
            return emptyList()
        }

        return readPoints(type, startTimeMs, endTimeMs, label)
            .mapNotNull { point ->
                val start = point.getStartTime(TimeUnit.MILLISECONDS)
                val end = point.getEndTime(TimeUnit.MILLISECONDS)
                val value = point.firstNumericValue(fields)

                if (value != null && value > 0.0 && start < end) {
                    HuaweiMetricSample(start, end, value)
                } else {
                    null
                }
            }
    }

    private suspend fun readPoints(
        type: DataType,
        startTimeMs: Long,
        endTimeMs: Long,
        label: String
    ): List<SamplePoint> {
        val options = ReadOptions.Builder()
            .read(type)
            .setTimeRange(startTimeMs, endTimeMs, TimeUnit.MILLISECONDS)
            .build()

        return try {
            val reply = dataController.read(options).awaitTask()
            val points = reply.sampleSets.flatMap { it.samplePoints }
            AppLogger.i(TAG, "Huawei $label read: ${points.size} points")
            points
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "Huawei $label read denied. Missing approved scope or user authorization.", e)
            throw e
        } catch (e: Exception) {
            AppLogger.w(TAG, "Huawei $label read skipped: ${e.message}")
            emptyList()
        }
    }

    private fun SamplePoint.firstNumericValue(fields: List<Field>): Double? {
        for (field in fields) {
            val raw = try {
                getFieldValue(field)
            } catch (_: Exception) {
                null
            }

            val numeric = raw.toNumericDouble()
            if (numeric != null) return numeric
        }

        return null
    }

    private fun Any?.toNumericDouble(): Double? {
        if (this == null) return null

        if (this is Number) return this.toDouble()

        for (method in VALUE_NUMERIC_METHODS) {
            val value = try {
                javaClass.getMethod(method).invoke(this)
            } catch (_: Exception) {
                null
            }

            if (value is Number) return value.toDouble()
        }

        return null
    }

    private fun firstDataType(vararg names: String): DataType? =
        names.firstNotNullOfOrNull { name ->
            staticField(DataType::class.java, name) as? DataType
        }

    private fun fields(vararg names: String): List<Field> =
        names.mapNotNull { name -> staticField(Field::class.java, name) as? Field }

    private fun staticField(clazz: Class<*>, name: String): Any? =
        try {
            clazz.getField(name).get(null)
        } catch (_: Exception) {
            null
        }

    private fun <T> emptyListWithLog(label: String, reason: String): List<T> {
        AppLogger.w(TAG, "Skipping $label: $reason")
        return emptyList()
    }

    private suspend fun <T> Task<T>.awaitTask(): T =
        kotlinx.coroutines.suspendCancellableCoroutine { cont ->
            addOnSuccessListener { value -> cont.resume(value) }
            addOnFailureListener { error -> cont.cancel(error) }
        }

    private companion object {
        const val KEY_HUAWEI_PENDING_APPROVAL = "huawei_pending_approval"

        const val HUAWEI_SCOPE_UNAUTHORIZED = 50005
        const val HUAWEI_PRIVACY_NOT_ACCEPTED = 50011
        const val HUAWEI_CERT_MISMATCH = 907135702
        const val HUAWEI_INVALID_ARGS = 907135000
        const val HUAWEI_CERT_VERIFY_FAILED = 6003

        const val ACTIVITY_SESSION_MIN_DURATION_MS = 60_000L
        const val ACTIVITY_SESSION_MAX_GAP_MS = 10L * 60L * 1000L

        val VALUE_NUMERIC_METHODS = listOf(
            "asIntValue",
            "asLongValue",
            "asFloatValue",
            "asDoubleValue"
        )
    }
}
