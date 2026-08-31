package com.openhealth.sync.data
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext

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
import com.huawei.hms.hihealth.options.ActivityRecordReadOptions
import com.huawei.hms.hihealth.options.ReadOptions
import com.huawei.hms.support.hwid.request.HuaweiIdAuthParamsHelper
import com.huawei.hms.support.hwid.request.HuaweiIdAuthParams
import com.huawei.hms.support.hwid.HuaweiIdAuthManager
import com.huawei.hms.support.api.entity.auth.Scope
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.util.AppLogger
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

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

private data class HuaweiWorkoutSummaryMetrics(
    val distanceMeters: Double? = null,
    val totalCaloriesKcal: Double? = null,
    val elevationMeters: Double? = null,
    val steps: Long? = null
)

class HuaweiHealthManager(
    private val context: Context,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) : HuaweiHealthReader {

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

    override fun requestedScopeNames(): String =
        "HEALTHKIT_STEP_READ, HEALTHKIT_DISTANCE_READ, HEALTHKIT_ACTIVITY_READ, HEALTHKIT_ACTIVITY_RECORD_READ, HEALTHKIT_HISTORYDATA_OPEN_WEEK"

    override fun isAuthorized(): Boolean =
        prefs.getBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, false)

    override fun isPendingApproval(): Boolean =
        prefs.getBoolean(KEY_HUAWEI_PENDING_APPROVAL, false)

    /**
     * Sprint 2026-07-18: the *specific* reason the last authorization
     * attempt failed, persisted separately from the isPendingApproval/
     * isAppGalleryVerificationRequired booleans above (which both only
     * ever fire for the 50005 case) so cert-mismatch/privacy/invalid-config
     * failures are distinguishable too -- see classifyFailure() below.
     */
    override fun lastAuthFailureReason(): HuaweiAuthFailureReason? {
        val raw = prefs.getString(KEY_HUAWEI_LAST_AUTH_FAILURE_REASON, null) ?: return null
        return try {
            HuaweiAuthFailureReason.valueOf(raw)
        } catch (_: IllegalArgumentException) {
            null
        }
    }

    override fun isAppGalleryVerificationRequired(): Boolean =
        prefs.getBoolean(KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED, false)

    override fun clearAppGalleryVerificationRequired() {
        prefs.edit()
            .putBoolean(KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED, false)
            .apply()
    }

    override fun markAppGalleryVerificationRequired() {
        prefs.edit()
            .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, false)
            .putBoolean(KEY_HUAWEI_PENDING_APPROVAL, true)
            .putBoolean(KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED, true)
            .apply()
    }

    override fun getAuthorizationIntent(): Intent {
        AppLogger.i(TAG, "Requesting Huawei Health Kit authorization via SettingController: ${requestedScopeNames()}")
        return settingController.requestAuthorizationIntent(scopes, true)
    }

    override fun getHuaweiIdAuthorizationIntent(): Intent {
        AppLogger.i(TAG, "Requesting Huawei ID Health Kit authorization: ${requestedScopeNames()}")

        val scopeList = scopes.map { Scope(it) }

        val authParams = HuaweiIdAuthParamsHelper(HuaweiIdAuthParams.DEFAULT_AUTH_REQUEST_PARAM)
            .setScopeList(scopeList)
            .setAccessToken()
            .createParams()

        return HuaweiIdAuthManager.getService(context, authParams).signInIntent
    }

    override fun handleAuthorizationResult(resultCode: Int, data: Intent?): Boolean {
        if (data == null) {
            saveAuthorizationState(success = false, pendingApproval = false, failureReason = HuaweiAuthFailureReason.UNKNOWN)
            AppLogger.e(TAG, "Huawei authorization returned no result intent")
            return false
        }

        val result = settingController.parseHealthKitAuthResultFromIntent(data)
        val success = result?.isSuccess == true
        val code = result?.errorCode
        val pendingApproval = code == HUAWEI_SCOPE_UNAUTHORIZED
        val failureReason = if (success) null else classifyFailure(code)

        saveAuthorizationState(success = success, pendingApproval = pendingApproval, failureReason = failureReason)

        if (success) {
            AppLogger.i(TAG, "Huawei Health Kit authorization granted")
            return true
        }

        val hint = when (code) {
            HUAWEI_SCOPE_UNAUTHORIZED ->
                "AppGallery verification required. Huawei Health Kit returned 50005: this app/release SHA-256/scope set is not approved server-side yet, even if the user granted permissions inside Huawei Health. Verify every requested scope, release SHA-256, package name, Huawei App ID, agconnect-services.json, reviewer account, and wait for HMS Core cache refresh."

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

    /**
     * Maps a raw HMS error code to the coarser [HuaweiAuthFailureReason]
     * bucket the UI (Settings card + toast) actually branches on. Kept
     * separate from the dev-facing `hint` strings in handleAuthorizationResult
     * above -- those stay verbose/technical for AppLogger and the hidden Log
     * Viewer; this feeds short, localized, end-user-facing copy instead.
     */
    private fun classifyFailure(code: Int?): HuaweiAuthFailureReason = when (code) {
        HUAWEI_SCOPE_UNAUTHORIZED -> HuaweiAuthFailureReason.SCOPE_PENDING_APPROVAL
        HUAWEI_PRIVACY_NOT_ACCEPTED -> HuaweiAuthFailureReason.PRIVACY_NOT_ACCEPTED
        HUAWEI_CERT_MISMATCH, HUAWEI_CERT_VERIFY_FAILED -> HuaweiAuthFailureReason.CERTIFICATE_MISMATCH
        HUAWEI_INVALID_ARGS -> HuaweiAuthFailureReason.INVALID_CONFIGURATION
        else -> HuaweiAuthFailureReason.UNKNOWN
    }

    override fun markAuthorizationUnknown() {
        saveAuthorizationState(success = false, pendingApproval = false, failureReason = null)
    }

    override suspend fun readSnapshot(startTimeMs: Long, endTimeMs: Long): HuaweiHealthSnapshot {
        return withContext(ioDispatcher) {
            require(startTimeMs < endTimeMs) { "startTimeMs must be before endTimeMs" }
            ensureRuntimeReady()

            AppLogger.i(TAG, "Reading real Huawei Health data from $startTimeMs to $endTimeMs")

            // The ordinary steps/distance cursor is intentionally incremental,
            // but workouts are sparse and the granted Huawei history scope is
            // exactly one week. Query the complete allowed workout window on
            // every run; Health Connect clientRecordId upserts make this safe
            // and idempotent while ensuring two-day-old workouts are not lost.
            val activityStartTimeMs = (endTimeMs - TimeUnit.DAYS.toMillis(ACTIVITY_HISTORY_WINDOW_DAYS))
                .coerceAtLeast(0L)
            AppLogger.i(
                TAG,
                "Huawei workout query window: start=$activityStartTimeMs end=$endTimeMs days=$ACTIVITY_HISTORY_WINDOW_DAYS"
            )

            // Sprint (2026-07-22): each category is read independently now, and
            // a SecurityException (50005) from ANY ONE of them no longer
            // aborts the whole snapshot. A real device log showed Huawei can
            // approve scopes incrementally: steps/distance/elevation
            // succeeded with real data while activeCalories alone still
            // returned 50005 in the very same sync attempt. Before this fix,
            // that one denied category threw all the way out of this
            // function (a data class constructor's arguments are evaluated
            // eagerly, left-to-right, so the already-successfully-read
            // steps/distance/elevation were discarded the moment a later
            // argument threw), and SyncWorker's catch block treated it
            // identically to a fully-unauthorized app -- wiping the
            // correctly-obtained isAuthorized=true flag back to false via
            // markAppGalleryVerificationRequired(). That regressed every
            // subsequent sync attempt back to a full graceful no-op, never
            // even trying to read data again, despite steps/distance
            // genuinely working. Now: a category-specific 50005 is caught
            // right here, logged, and that category alone is skipped (the
            // same graceful-degradation shape already used for floors on
            // SDKs that don't expose a floors DataType at all) --
            // authorization is only treated as fully denied if EVERY
            // category comes back denied with zero successes, which
            // re-throws below so SyncWorker's existing 50005 handling still
            // fires correctly for that genuine case. See CLAUDE.md Gotcha 14.
            var anySucceeded = false
            var anyScopeDenied = false
            val deniedCategories = mutableListOf<String>()

            suspend fun <T> readCategory(label: String, block: suspend () -> List<T>): List<T> {
                return try {
                    val result = block()
                    anySucceeded = true
                    result
                } catch (e: SecurityException) {
                    anyScopeDenied = true
                    deniedCategories.add(label)
                    AppLogger.w(
                        TAG,
                        "Huawei $label is not yet authorized for this account/app (50005) -- skipping just this category, not the whole sync."
                    )
                    emptyList()
                }
            }

            val steps = readCategory("steps") { readDailyStepTotals(endTimeMs) }
            val distances = readCategory("distance") { readDistance(startTimeMs, endTimeMs) }
            val floors = readCategory("floors") { readFloors(startTimeMs, endTimeMs) }
            val elevations = readCategory("elevation") { readElevation(startTimeMs, endTimeMs) }
            val activeCalories = readCategory("activeCalories") { readActiveCalories(startTimeMs, endTimeMs) }
            val activities = readCategory("activitySessions") { readActivitySessions(activityStartTimeMs, endTimeMs) }

            if (anyScopeDenied && !anySucceeded) {
                // Every category was scope-denied -- genuinely not authorized
                // at all yet, not a partial rollout. Re-throw so SyncWorker's
                // existing SecurityException/50005 handling fires exactly as
                // it did before this fix.
                throw SecurityException(
                    "$HUAWEI_SCOPE_UNAUTHORIZED: no Huawei Health category is authorized yet ($deniedCategories)"
                )
            }

            val snapshot = HuaweiHealthSnapshot(
                steps = steps,
                distances = distances,
                floors = floors,
                elevations = elevations,
                activeCalories = activeCalories,
                activities = activities
            )

            if (anyScopeDenied) {
                AppLogger.w(
                    TAG,
                    "Huawei read partially scope-denied (still pending approval for: $deniedCategories) -- proceeding with the categories that ARE authorized."
                )
            }

            AppLogger.i(
                TAG,
                "Huawei read complete: steps=${snapshot.steps.size}, distances=${snapshot.distances.size}, floors=${snapshot.floors.size}, elevations=${snapshot.elevations.size}, activeCalories=${snapshot.activeCalories.size}, activities=${snapshot.activities.size}"
            )

            snapshot
        }
    }

    private fun saveAuthorizationState(success: Boolean, pendingApproval: Boolean, failureReason: HuaweiAuthFailureReason?) {
        val editor = prefs.edit()
            .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, success)
            .putBoolean(KEY_HUAWEI_PENDING_APPROVAL, pendingApproval)
            .putBoolean(KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED, pendingApproval)
        if (failureReason != null) {
            editor.putString(KEY_HUAWEI_LAST_AUTH_FAILURE_REASON, failureReason.name)
        } else {
            editor.remove(KEY_HUAWEI_LAST_AUTH_FAILURE_REASON)
        }
        editor.apply()
    }

    private fun ensureRuntimeReady() {
        if (!HmsCoreHelper.isInstalled(context)) {
            throw IllegalStateException(HmsCoreHelper.missingMessage)
        }

        if (!HmsCoreHelper.isHuaweiHealthInstalled(context)) {
            throw IllegalStateException("Huawei Health is required. Install Huawei Health, sign in, and try again.")
        }
    }

    /**
     * The very first Huawei Health Kit call made after a cold app-process
     * start (or after the underlying HMS client has been idle long enough
     * to drop its connection) can race the client's own async connection
     * handshake and fail with a "client is not connected" style error, even
     * though nothing is actually broken -- a later call, moments later,
     * succeeds with no special handling at all. A real device log showed
     * this hitting two different Huawei controllers in the very same sync
     * attempt: the daily step summation failed with "50011: the client is
     * not connected", and the activity-records read failed right after it
     * and was logged as a 50005 scope denial -- but that same category
     * succeeded about 20 seconds later, in the very next sync attempt, with
     * no re-authorization happening in between. A genuine scope denial
     * can't resolve itself in 20 seconds; a connection race that clears up
     * once the HMS client finishes connecting can, which is a strong sign
     * that read was hitting the same race, just surfaced as a different
     * exception type by that particular Huawei controller. That same log
     * also showed a second sync attempt competing for the sync lease at
     * almost the same moment, which plausibly added the contention that
     * caused the race in the first place. This retries up to twice (three
     * attempts total) before giving up. SecurityException (genuine scope
     * denial, e.g. 50005) and CancellationException are rethrown
     * immediately on the very first attempt, untouched -- retrying either
     * of those would just delay a correct, final outcome, not fix anything.
     */
    private suspend fun <T> retryOnConnectionRace(block: suspend () -> T): T {
        var lastConnectionRaceError: Exception? = null
        for (attempt in 1..CONNECTION_RACE_MAX_ATTEMPTS) {
            try {
                return block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: SecurityException) {
                throw e
            } catch (e: Exception) {
                val looksLikeConnectionRace = e.message?.contains("not connected", ignoreCase = true) == true
                if (!looksLikeConnectionRace) throw e
                lastConnectionRaceError = e
                if (attempt < CONNECTION_RACE_MAX_ATTEMPTS) {
                    AppLogger.w(
                        TAG,
                        "Huawei Health Kit call failed with a client-not-connected style error " +
                            "(attempt $attempt/$CONNECTION_RACE_MAX_ATTEMPTS); " +
                            "retrying in ${CONNECTION_RACE_RETRY_DELAY_MS}ms: ${e.message}"
                    )
                    delay(CONNECTION_RACE_RETRY_DELAY_MS)
                }
            }
        }
        throw lastConnectionRaceError!!
    }

    private suspend fun readDailyStepTotals(endTimeMs: Long): List<StepData> {
        // Raw DT_CONTINUOUS_STEPS_DELTA samples are not the number shown by
        // Huawei Health. Huawei documents that wearable/Huawei Health workout
        // steps can exist only in daily/activity statistics and have no delta
        // samples at all. Query the official daily summation instead so BitLut
        // exports the same deduplicated total that Huawei Health displays.
        val stepFields = fields("FIELD_STEPS", "FIELD_STEPS_DELTA")
        if (stepFields.isEmpty()) {
            return emptyListWithLog("daily steps", "Huawei SDK exposes no supported step-total field")
        }

        val zone = ZoneId.systemDefault()
        val today = Instant.ofEpochMilli(endTimeMs).atZone(zone).toLocalDate()
        val firstDay = today.minusDays(ACTIVITY_HISTORY_WINDOW_DAYS - 1L)
        val startDate = firstDay.format(DateTimeFormatter.BASIC_ISO_DATE).toInt()
        val endDate = today.format(DateTimeFormatter.BASIC_ISO_DATE).toInt()

        AppLogger.i(
            TAG,
            "Querying Huawei daily step summation: startDate=$startDate endDate=$endDate"
        )

        val sampleSet = try {
            retryOnConnectionRace {
                dataController
                    .readDailySummation(DataType.DT_CONTINUOUS_STEPS_DELTA, startDate, endDate)
                    .awaitTask()
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "Huawei daily steps read denied", e)
            throw e
        } catch (e: Exception) {
            // Do not fall back to raw deltas here: mixing an incomplete delta
            // view with daily totals would recreate the dashboard mismatch.
            // Preserve the last correct Health Connect total and retry later.
            AppLogger.e(TAG, "Huawei daily step summation failed; preserving previous totals: ${e.message}", e)
            return emptyList()
        }

        val totalsByDay = linkedMapOf<LocalDate, Long>()
        for (point in sampleSet.samplePoints) {
            val count = point.firstNumericValue(stepFields)?.toLong() ?: continue
            val pointStart = point.getStartTime(TimeUnit.MILLISECONDS)
            if (count <= 0L || pointStart <= 0L) continue

            val day = Instant.ofEpochMilli(pointStart).atZone(zone).toLocalDate()
            if (day.isBefore(firstDay) || day.isAfter(today)) continue

            // readDailySummation returns statistical totals. If an OEM build
            // exposes duplicate collectors for the same day, choosing the max
            // avoids summing already-aggregated totals twice.
            totalsByDay[day] = maxOf(totalsByDay[day] ?: 0L, count)
        }

        val result = totalsByDay.entries
            .sortedBy { it.key }
            .map { (day, count) ->
                val start = day.atStartOfDay(zone).toInstant().toEpochMilli()
                val nextMidnight = day.plusDays(1).atStartOfDay(zone).toInstant().toEpochMilli()
                val end = if (day == today) minOf(endTimeMs, nextMidnight) else nextMidnight
                StepData(
                    startTimeMs = start,
                    endTimeMs = end,
                    count = count,
                    sourceId = day.format(DateTimeFormatter.BASIC_ISO_DATE)
                )
            }
            .filter { it.startTimeMs < it.endTimeMs }

        AppLogger.i(
            TAG,
            "Huawei daily step totals read: days=${result.size} today=${result.lastOrNull { it.sourceId == endDate.toString() }?.count ?: 0L} sevenDayTotal=${result.sumOf { it.count }}"
        )
        return result
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

    /**
     * Sprint 2026-08-28: previously, ActivitySessionData.distanceMeters was
     * never set here at all -- every workout card's distance came entirely
     * from GoogleHealthManager's post-hoc Health Connect matching (a strict
     * aggregate() over the exact session window, falling back to a
     * time-overlap-fraction split of nearby DistanceRecords). Both of those
     * approaches implicitly assume Huawei's own DT_CONTINUOUS_DISTANCE_DELTA
     * stream reports distance in samples whose own time window lines up with
     * the actual movement, which is false for Huawei's coarse background
     * delta samples: a real 28 km, ~2 hour bike ride was measured by a user
     * report showing the dashboard displaying only 0.7 km for that same
     * ride, a ~40x undercount consistent with a wide background sample
     * (its own reported window several times longer than the actual ride)
     * being credited only for the sliver of its window that happened to
     * geometrically overlap the session's exact start/end -- an artifact of
     * the overlap-fraction math, not of the underlying distance value itself
     * (which was correct in total, just attributed to the wrong time span).
     *
     * Huawei's own ActivityRecordsController API supports exactly the right
     * fix for this: `ActivityRecordReadOptions.Builder.read(DataType)` can
     * request additional detail data types to be returned scoped to each
     * individual ActivityRecord (this file already does this for
     * DT_CONTINUOUS_STEPS_DELTA below, per the pre-existing comment on why a
     * detail type is required for the record list to be returned at all),
     * and `ActivityRecordReply.getSampleSet(record)` returns exactly the
     * detail samples belonging to that one record -- not a separate
     * generic query needing manual time-window reconciliation. Real,
     * independently-confirmed Huawei sample code
     * (HealthKitActivityRecordControllerActivity.java, part of Huawei's own
     * hms-health-demo-java repository) shows this exact
     * getSampleSet(activityRecord) -> sampleSet.getSamplePoints() pattern
     * for reading per-record detail data.
     *
     * One piece of this is inferred rather than directly confirmed from a
     * Huawei-specific multi-type example: whether calling `.read(DataType)`
     * a second time (for distance, alongside the existing steps-delta call)
     * accumulates both requested types rather than replacing the first.
     * Google Fit's near-identical SessionReadRequest.Builder.read(DataType)
     * is documented as callable multiple times to accumulate types, and
     * this file's own existing comment already treats Huawei's `.read(...)`
     * as an additive detail-type request, so the pattern is used here on
     * that basis -- but this is exactly the kind of real Kotlin/HMS-SDK API
     * behavior the project's own rules say a sandbox cannot verify.
     * Paulo's real `assembleDebug` is the actual compile gate for this.
     *
     * Distance is summed per-record from real Huawei sample data scoped to
     * that exact activity, not prorated or estimated. A record with no
     * matching distance samples correctly yields null (displayed as "-"),
     * per the locked six-slot contract's "real data only" rule.
     */
    private suspend fun readActivitySessions(startTimeMs: Long, endTimeMs: Long): List<ActivitySessionData> {
        // Exercise records are not continuous intensity samples. Huawei's
        // supported API for workouts is ActivityRecordsController, covered by
        // the already-requested HEALTHKIT_ACTIVITY_RECORD_READ scope.
        val distanceDetailType = firstDataType(
            "DT_CONTINUOUS_DISTANCE_DELTA",
            "DT_CONTINUOUS_DISTANCE_TOTAL",
            "DT_INSTANTANEOUS_DISTANCE"
        )
        val distanceDetailFields = fields(
            "FIELD_DISTANCE",
            "FIELD_DISTANCE_DELTA",
            "FIELD_DISTANCE_TOTAL"
        )

        val optionsBuilder = ActivityRecordReadOptions.Builder()
            .setTimeInterval(startTimeMs, endTimeMs, TimeUnit.MILLISECONDS)
            .readActivityRecordsFromAllApps()
            // Carrying an approved detail type is required on some Huawei
            // Health builds for the record list to be returned at all.
            .read(DataType.DT_CONTINUOUS_STEPS_DELTA)

        if (distanceDetailType != null) {
            optionsBuilder.read(distanceDetailType)
        } else {
            AppLogger.w(TAG, "Skipping per-activity distance detail: Huawei SDK does not expose a supported distance DataType")
        }

        val options = optionsBuilder.build()

        AppLogger.i(
            TAG,
            "Querying Huawei activity records with steps-delta detail: start=$startTimeMs end=$endTimeMs"
        )

        val reply = retryOnConnectionRace {
            HuaweiHiHealth.getActivityRecordsController(context)
                .getActivityRecord(options)
                .awaitTask()
        }
        val records = reply.getActivityRecords().orEmpty()

        AppLogger.i(TAG, "Huawei activity records read: ${records.size}")

        return records.mapNotNull { record ->
            val start = activityRecordTime(record, "getStartTime") ?: return@mapNotNull null
            val end = activityRecordTime(record, "getEndTime") ?: return@mapNotNull null
            if (start <= 0L || end <= start) return@mapNotNull null

            val recordId = activityRecordString(record, "getId")
            val rawType = activityRecordString(record, "getActivityTypeId", "getActivityType")
            val rawName = activityRecordString(record, "getName")
            val canonicalType = HuaweiWorkoutTypeMapper.canonicalName(rawType)
            val exerciseType = HuaweiWorkoutTypeMapper.healthConnectType(canonicalType)
                ?: return@mapNotNull null
            val title = rawName
                ?.trim()
                ?.takeIf { it.isNotBlank() && !isSyntheticHuaweiActivityName(it, recordId) }
                ?: canonicalType
            val summary = readActivityRecordSummary(record)
            val recordDistanceMeters = summary.distanceMeters
                ?: readActivityRecordDistance(reply, record, distanceDetailFields)
            AppLogger.i(
                TAG,
                "Huawei activity mapped: type=${rawType ?: "unknown"} name=${rawName ?: "-"} canonical=$canonicalType " +
                    "start=$start end=$end distanceMeters=${recordDistanceMeters ?: "missing"} " +
                    "totalCaloriesKcal=${summary.totalCaloriesKcal ?: "missing"} " +
                    "elevationMeters=${summary.elevationMeters ?: "missing"} steps=${summary.steps ?: "missing"}"
            )

            ActivitySessionData(
                startTimeMs = start,
                endTimeMs = end,
                title = title,
                exerciseType = exerciseType,
                distanceMeters = recordDistanceMeters,
                totalCaloriesKcal = summary.totalCaloriesKcal,
                elevationMeters = summary.elevationMeters,
                steps = summary.steps
            )
        }.distinctBy { Pair(it.startTimeMs, it.endTimeMs) }
    }

    /**
     * Reads the statistical summary attached to a Huawei ActivityRecord.
     * Huawei documents these summary points as part of the exercise record
     * itself, so they do not require separate per-metric OAuth scopes. The
     * summary is the authoritative source for workout totals (distance,
     * calories, steps and ascent) and is preferred over coarse background
     * streams for dashboard workout cards.
     */
    private fun readActivityRecordSummary(record: Any): HuaweiWorkoutSummaryMetrics {
        val activitySummary = try {
            record.javaClass.getMethod("getActivitySummary").invoke(record)
        } catch (e: Exception) {
            AppLogger.w(TAG, "getActivitySummary failed for activity record: ${e.message}")
            null
        } ?: return HuaweiWorkoutSummaryMetrics()

        val points = try {
            @Suppress("UNCHECKED_CAST")
            activitySummary.javaClass.getMethod("getDataSummary").invoke(activitySummary) as? List<SamplePoint>
        } catch (e: Exception) {
            AppLogger.w(TAG, "getDataSummary failed for activity record: ${e.message}")
            null
        }.orEmpty()

        var distanceMeters: Double? = null
        var totalCaloriesKcal: Double? = null
        var elevationMeters: Double? = null
        var steps: Long? = null
        var stepsMatchedPointCount = 0

        // Sprint 2026-08-30 diagnostic: the 2026-08-29 sum-across-points fix
        // is confirmed correct for what it does, but a real-device report
        // still shows an undercount (2.5 km correctly summed via the
        // distance fallback path below, steps still far too low from this
        // summary-only path). Distance has a second, richer data source
        // (readActivityRecordDistance's raw getSampleSet(record) samples);
        // steps has no equivalent, and this project's own prior lesson
        // (see readDailyStepTotals()'s doc comment) already found raw
        // DT_CONTINUOUS_STEPS_DELTA samples unreliable for Huawei step
        // totals, so blindly adding a steps raw-stream fallback here would
        // repeat a category of fix already flagged as unsafe, without real
        // per-point evidence from this specific bug. Logging every raw
        // dataSummary point (type name + every field name/value, matched or
        // not) is a pure, zero-risk addition -- it changes no computed
        // value -- so the next real sync's logcat gives ground truth
        // (whether Huawei is only emitting one low-value steps.total point,
        // several points that our name/field matching silently rejects, or
        // a genuinely-authoritative-but-low total from Huawei's own side)
        // instead of guessing a third structural fix blind.
        points.forEach { point ->
            val dataType = try { point.dataType } catch (_: Exception) { null } ?: return@forEach
            val typeName = dataType.name.lowercase(Locale.ROOT)
            val values = dataType.fields.mapNotNull { field ->
                val numeric = try { point.getFieldValue(field).toNumericDouble() } catch (_: Exception) { null }
                numeric?.let { field.name.lowercase(Locale.ROOT) to it }
            }
            val positiveValues = values.filter { it.second > 0.0 }
            AppLogger.d(
                TAG,
                "Huawei activity summary point: type=$typeName fields=$values"
            )

            // Sprint 2026-08-29: Huawei's per-activity dataSummary can split
            // one metric across multiple SamplePoints of the same DataType
            // (e.g. one steps/calories/ascent point per walked segment
            // rather than one point for the whole activity -- the same
            // reason readActivityRecordDistance already sums every matching
            // sample point instead of taking the first). The previous
            // `positiveValues.firstOrNull()` here silently kept only the
            // first segment's value and discarded the rest, which is the
            // confirmed root cause of a real-device report: a walking
            // workout with a correct 2.5 km distance (summed via the
            // fallback path below) showing only 250 steps (the first
            // segment's point, not the activity total). Steps, calories,
            // and ascent are all additive across segments the same way
            // distance is, so all three now sum every matching point
            // instead of keeping only the first.
            when {
                "distance.total" in typeName -> {
                    val sum = positiveValues.sumOf { it.second }
                    if (sum > 0.0) {
                        distanceMeters = (distanceMeters ?: 0.0) + sum
                    }
                }
                "calories.burnt.total" in typeName || "calories.burned.total" in typeName -> {
                    val sum = positiveValues.sumOf { it.second }
                    if (sum > 0.0) {
                        totalCaloriesKcal = (totalCaloriesKcal ?: 0.0) + sum
                    }
                }
                "steps.total" in typeName -> {
                    stepsMatchedPointCount += 1
                    val sum = positiveValues.sumOf { it.second }.toLong()
                    if (sum > 0L) {
                        steps = (steps ?: 0L) + sum
                    }
                }
                "altitude.statistics" in typeName -> {
                    val sum = positiveValues
                        .filter { (fieldName, _) -> fieldName == "ascent_total" || "ascent" in fieldName }
                        .sumOf { it.second }
                    if (sum > 0.0) {
                        elevationMeters = (elevationMeters ?: 0.0) + sum
                    }
                }
            }
        }

        AppLogger.i(
            TAG,
            "Huawei activity summary steps diagnostic: totalPoints=${points.size} " +
                "stepsTotalPointsMatched=$stepsMatchedPointCount summedSteps=${steps ?: "missing"}"
        )

        return HuaweiWorkoutSummaryMetrics(
            distanceMeters = distanceMeters?.takeIf { it > 0.0 },
            totalCaloriesKcal = totalCaloriesKcal?.takeIf { it > 0.0 },
            elevationMeters = elevationMeters?.takeIf { it > 0.0 },
            steps = steps?.takeIf { it > 0L }
        )
    }

    /**
     * Sums real Huawei sample-point distance values scoped specifically to
     * [record], via ActivityRecordReply.getSampleSet(record) ->
     * SampleSet.samplePoints. Reuses the existing, already-working
     * SamplePoint.firstNumericValue(fields) extension (defined below,
     * proven in readMetric's own generic-stream distance reading) rather
     * than inventing new reflection for value extraction.
     *
     * getSampleSet itself is called via reflection rather than a typed
     * call: this file already imports SamplePoint, SampleSet, DataType,
     * and Field directly from com.huawei.hms.hihealth.data (confirmed
     * real, stable import paths, used elsewhere in this file), but
     * ActivityRecordReply's own import path was not independently
     * confirmed with the same certainty during this fix, so [reply] stays
     * untyped (Any) here rather than risk a wrong import breaking the
     * whole file. This mirrors activityRecordTime/activityRecordString's
     * existing reflection style for the same class of uncertainty.
     */
    private fun readActivityRecordDistance(
        reply: Any,
        record: Any,
        distanceFields: List<Field>
    ): Double? {
        if (distanceFields.isEmpty()) return null

        val sampleSets = try {
            @Suppress("UNCHECKED_CAST")
            reply.javaClass.methods
                .firstOrNull { it.name == "getSampleSet" && it.parameterCount == 1 }
                ?.invoke(reply, record) as? List<SampleSet>
        } catch (e: Exception) {
            AppLogger.w(TAG, "getSampleSet failed for activity record: ${e.message}")
            null
        } ?: return null

        var totalMeters = 0.0
        var matchedAny = false

        sampleSets.forEach { sampleSet ->
            sampleSet.samplePoints.forEach { point ->
                val value = point.firstNumericValue(distanceFields)
                if (value != null && value > 0.0) {
                    totalMeters += value
                    matchedAny = true
                }
            }
        }

        return totalMeters.takeIf { matchedAny && it > 0.0 }
    }

    private fun activityRecordTime(record: Any, methodName: String): Long? =
        try {
            (record.javaClass
                .getMethod(methodName, TimeUnit::class.java)
                .invoke(record, TimeUnit.MILLISECONDS) as? Number)
                ?.toLong()
        } catch (_: Exception) {
            null
        }

    private fun activityRecordString(record: Any, vararg methodNames: String): String? {
        for (methodName in methodNames) {
            val value = try {
                record.javaClass.getMethod(methodName).invoke(record)
            } catch (_: Exception) {
                null
            }
            if (value != null) return value.toString()
        }
        return null
    }

    private fun isSyntheticHuaweiActivityName(name: String, recordId: String?): Boolean {
        val trimmed = name.trim()
        return trimmed.equals(recordId, ignoreCase = true) ||
            SYNTHETIC_HUAWEI_ACTIVITY_NAME.matches(trimmed)
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

        return readPoints(type, startTimeMs, endTimeMs, label, dedupFields = fields)
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

    private suspend fun readPointsRaw(
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
        } catch (e: CancellationException) {
            // Never turn WorkManager/coroutine cancellation into an empty
            // health snapshot. Propagate it so the worker releases its lease
            // and does not advance the sync cursor with partial data.
            throw e
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "Huawei $label read denied. Missing approved scope or user authorization.", e)
            throw e
        } catch (e: Exception) {
            AppLogger.w(TAG, "Huawei $label read skipped: ${e.message}")
            emptyList()
        }
    }

    /**
     * Reads [type] over [startTimeMs]..[endTimeMs], splitting the range into
     * day-sized chunks for non-activity metrics (Huawei Health Kit can be
     * unreliable or slow on very wide single-shot reads for continuous
     * metrics like steps/distance/floors).
     *
     * Type-safety fix (v1.9.11): the previous implementation accumulated
     * results into a `MutableList<Any?>`, deduplicated with
     * `.distinctBy { it.toString() }`, and force-cast the result back to
     * `List<SamplePoint>` with `@Suppress("UNCHECKED_CAST")`. Three problems
     * with that: (1) `Any?` discards type safety for no reason -- the list
     * only ever held `SamplePoint`s; (2) `toString()`-based dedup is
     * incidental, not semantic -- two genuinely different samples that
     * happen to render identical strings would be wrongly collapsed into
     * one, silently dropping real health data, which is the single worst
     * kind of bug for an app whose entire purpose is accurate data transfer;
     * and (3) if a future HMS SDK version changes `SamplePoint.toString()`,
     * dedup quietly breaks with no compiler warning. This version keeps the
     * list properly typed throughout and deduplicates on the sample's actual
     * identity (start time, end time, and value) instead.
     */
    private suspend fun readPoints(
        type: DataType,
        startTimeMs: Long,
        endTimeMs: Long,
        label: String,
        dedupFields: List<Field> = emptyList()
    ): List<SamplePoint> {
        val descriptor = listOf(type.toString(), startTimeMs.toString(), endTimeMs.toString(), label).joinToString("|")
        if (shouldBypassChunkingForHuaweiRead(descriptor) || endTimeMs <= startTimeMs) {
            return readPointsRaw(type, startTimeMs, endTimeMs, label)
        }

        val windowMs = endTimeMs - startTimeMs
        if (windowMs <= HUAWEI_READ_CHUNK_MS) {
            return readPointsRaw(type, startTimeMs, endTimeMs, label)
        }

        val merged = mutableListOf<SamplePoint>()
        var chunkStart = startTimeMs
        var chunkIndex = 0

        while (chunkStart < endTimeMs) {
            val chunkEnd = minOf(chunkStart + HUAWEI_READ_CHUNK_MS, endTimeMs)
            AppLogger.d(TAG, "readPoints chunk #$chunkIndex: $chunkStart..$chunkEnd")

            // SecurityException / 50005 must propagate out of readPointsRaw
            // -- readSnapshot() is what decides (since 2026-07-22) whether a
            // single denied category is skipped or the whole read is
            // genuinely unauthorized; this function must not swallow it.
            merged.addAll(readPointsRaw(type, chunkStart, chunkEnd, label))

            chunkStart = chunkEnd
            chunkIndex += 1
        }

        // Adjacent chunk windows can each return the boundary sample (a point
        // whose time range straddles or sits exactly on a chunk edge), so the
        // merged list can contain genuine duplicates. Deduplicate on the
        // sample's actual identity -- its time range plus its numeric value
        // for the field(s) the caller actually reads -- rather than object
        // identity or string rendering. [dedupFields] defaults to FIELD_STEPS
        // when the caller doesn't pass anything more specific, since steps is
        // the only direct (non-readMetric) caller of this chunked path today.
        val fieldsForDedup = dedupFields.ifEmpty { listOf(Field.FIELD_STEPS) }
        val deduped = LinkedHashMap<SamplePointKey, SamplePoint>()
        for (point in merged) {
            val key = SamplePointKey(
                startTimeMs = point.getStartTime(TimeUnit.MILLISECONDS),
                endTimeMs = point.getEndTime(TimeUnit.MILLISECONDS),
                value = point.firstNumericValue(fieldsForDedup)
            )
            deduped.putIfAbsent(key, point)
        }

        AppLogger.i(
            TAG,
            "readPoints chunked result: chunks=$chunkIndex raw=${merged.size} deduped=${deduped.size}"
        )

        return deduped.values.toList()
    }

    private data class SamplePointKey(val startTimeMs: Long, val endTimeMs: Long, val value: Double?)

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
            addOnSuccessListener { value ->
                if (cont.isActive) cont.resume(value)
            }
            addOnFailureListener { error ->
                // A failed HMS Task is an API failure, not coroutine
                // cancellation. Preserve the original exception type so
                // 50005 remains classifiable as a SecurityException.
                if (cont.isActive) cont.resumeWithException(error)
            }
        }

    /**
     * Single source of truth for which reads bypass day-chunking (v1.9.11).
     *
     * The previous version of this file declared this exact function twice:
     * once as a regular member of [HuaweiHealthManager] and once again inside
     * its `private companion object`. Both compiled (Kotlin allows a member
     * function and a same-named companion-object function to coexist), but
     * one of the two was always dead code -- member function resolution wins
     * over the companion object here, so the companion copy never actually
     * ran. Keeping two near-identical implementations around is exactly the
     * kind of drift that causes real bugs later (someone fixes one copy and
     * not the other). There is now exactly one.
     */
    private fun shouldBypassChunkingForHuaweiRead(descriptor: String): Boolean {
        val normalized = descriptor.lowercase()
        return normalized.contains("activity") ||
            normalized.contains("exercise") ||
            normalized.contains("session") ||
            normalized.contains("sport") ||
            normalized.contains("workout")
    }

    private companion object {
        private const val HUAWEI_READ_CHUNK_MS: Long = 24L * 60L * 60L * 1000L
        private const val ACTIVITY_HISTORY_WINDOW_DAYS = 7L
        private const val CONNECTION_RACE_RETRY_DELAY_MS = 2_000L
        private const val CONNECTION_RACE_MAX_ATTEMPTS = 3
        private val SYNTHETIC_HUAWEI_ACTIVITY_NAME = Regex(
            "^sporthealth\\d+$",
            RegexOption.IGNORE_CASE
        )

        const val KEY_HUAWEI_PENDING_APPROVAL = "huawei_pending_approval"
        const val KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED = "huawei_appgallery_verification_required"
        const val KEY_HUAWEI_LAST_AUTH_FAILURE_REASON = "huawei_last_auth_failure_reason"

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
