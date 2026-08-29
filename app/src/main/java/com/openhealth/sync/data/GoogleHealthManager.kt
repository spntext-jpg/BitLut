package com.openhealth.sync.data

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.Record
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.TotalCaloriesBurnedRecord
import androidx.health.connect.client.records.metadata.DataOrigin
import androidx.health.connect.client.records.metadata.Device
import androidx.health.connect.client.records.metadata.Metadata
import androidx.health.connect.client.request.AggregateRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.health.connect.client.units.Energy
import androidx.health.connect.client.units.Length
import com.openhealth.sync.config.DataSourcePrefs
import com.openhealth.sync.config.HealthPermissionPolicy
import com.openhealth.sync.util.AppLogger
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZoneOffset
import java.util.Locale
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlin.reflect.KClass

private const val TAG = "GoogleHealthManager"
private const val WRITE_BATCH_SIZE = 400
private const val DASHBOARD_HISTORY_DAYS = 30
private const val WORKOUT_DISTANCE_QUERY_PADDING_SECONDS = 2L * 60L * 60L
private const val MAX_WORKOUT_DISTANCE_SOURCE_RECORD_MS = 3L * 60L * 60L * 1000L
private const val MIN_RECOVERED_WORKOUT_DISTANCE_METERS = 25.0
private const val READ_PAGE_SIZE = 1000
/** Sprint 2026-07-08: single quick retry delay for a transient permission-
 *  check failure -- see [GoogleHealthManager.grantedPermissionsOrEmpty]. */
private const val TRANSIENT_PERMISSION_RETRY_DELAY_MS = 400L
/** Sprint 2026-07-10: how long a permission-check result is trusted before
 *  a fresh one is required -- see [GoogleHealthManager.grantedPermissionsOrEmpty]. */
private const val PERMISSION_CACHE_TTL_MS = 30_000L
private val SYNTHETIC_WORKOUT_TITLE = Regex("^sporthealth\\d+$", RegexOption.IGNORE_CASE)

private val HC_PACKAGES = listOf(
    "com.google.android.apps.healthdata",
    "com.google.android.health.connect"
)

enum class HealthConnectStatus {
    AVAILABLE,
    NOT_INSTALLED,
    NEEDS_UPDATE,
    NOT_SUPPORTED
}

data class StepData(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val count: Long,
    val sourceId: String? = null
)
data class DistanceData(val startTimeMs: Long, val endTimeMs: Long, val meters: Double)
data class FloorsData(val startTimeMs: Long, val endTimeMs: Long, val floors: Double)
data class ElevationData(val startTimeMs: Long, val endTimeMs: Long, val meters: Double)
data class ActiveCaloriesData(val startTimeMs: Long, val endTimeMs: Long, val kilocalories: Double)

data class ActivitySessionData(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val title: String = "Huawei activity",
    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT,
    val distanceMeters: Double? = null,
    val activeCaloriesKcal: Double? = null,
    val totalCaloriesKcal: Double? = null,
    val elevationMeters: Double? = null,
    val steps: Long? = null
)

/** One row of the CSV export (sprint 2026-07-14): a single calendar day's
 *  activity totals, read the same raw-records-and-sum way as "today" on the
 *  dashboard (see the comment on readDashboardSnapshot for why -- aggregate()
 *  is not used here either, for the same staleness reason). */
data class DailyTotal(
    val date: LocalDate,
    val steps: Long,
    val distanceMeters: Double,
    val caloriesKcal: Double
)

/**
 * One calendar day's activity totals used by the dashboard insights cards.
 * The same activity-only records BitLut already reads are regrouped locally;
 * no new Huawei or Health Connect permission is required.
 */
data class DailyActivitySummary(
    val date: LocalDate,
    val steps: Long = 0L,
    val distanceMeters: Double = 0.0,
    val caloriesKcal: Double = 0.0,
    val elevationMeters: Double = 0.0,
    val floors: Double = 0.0,
    val workoutMinutes: Long = 0L,
    val workoutCount: Int = 0,
    val longestWorkoutMinutes: Long = 0L
)

data class GoogleDashboardSnapshot(
    val stepsToday: Long,
    val distanceMeters: Double,
    val caloriesKcal: Double,
    val workoutMinutesToday: Long,
    val activeHoursToday: Int,
    val recentWorkouts: List<ActivitySessionData>,
    val dailyActivity: List<DailyActivitySummary> = emptyList()
)

class GoogleHealthManager(
    private val context: Context,
    private val dataSourcePrefs: DataSourcePrefs = DataSourcePrefs(context),
    private val workoutFilterPrefs: com.openhealth.sync.config.WorkoutFilterPrefs = com.openhealth.sync.config.WorkoutFilterPrefs(context)
) : HealthConnectManager {

    private val zoneRules by lazy { ZoneId.systemDefault().rules }

    // BITLUT_WORKOUT_INTEROP_V1
    // ExerciseSessionRecord intentionally does not carry distance/calorie/step
    // summary fields. Keep Huawei's authoritative ActivityRecord summary as a
    // small local sidecar keyed by the session interval so BitLut's dashboard
    // does not lose exact workout totals after reading the session back from
    // Health Connect. This cache is used only when Huawei/BitLut is the selected
    // source; Google Fit sessions continue to resolve from Health Connect.
    private val workoutSummaryPrefs = context.getSharedPreferences(
        "bitlut_workout_summary_v1",
        Context.MODE_PRIVATE
    )

    private fun selectedDataOrigins(): Set<DataOrigin> = setOf(
        DataOrigin(dataSourcePrefs.selectedOriginPackage(context.packageName))
    )

    private fun isHuaweiBridgeSourceSelected(): Boolean =
        dataSourcePrefs.selectedOriginPackage(context.packageName) == context.packageName

    /**
     * Self-healing replacement for the previous `by lazy { ... }` client cache.
     *
     * The previous implementation cached a `null` result forever the moment
     * `HealthConnectClient.getOrCreate()` failed once -- a single transient
     * failure (Health Connect provider not yet warmed up right after device
     * boot, OEM process death, etc.) would permanently disable Google Health
     * for the rest of the app process's lifetime, with no way to recover
     * short of force-stopping the app. That is the opposite of self-healing.
     *
     * This cache instead retries client creation on every access where the
     * cached value is null, so a later attempt (e.g. the next periodic sync,
     * 30 minutes later) gets a fresh chance once the underlying dependency
     * has recovered. A successful client is still cached and reused (no
     * repeated work on the hot path); only the failure case retries.
     *
     * [clientLock] serializes concurrent creation attempts (manual sync and
     * periodic sync can race) so we don't call `getOrCreate()` twice
     * concurrently from two coroutines.
     */
    private val cachedClient = AtomicReference<HealthConnectClient?>(null)
    private val clientLock = Mutex()

    /**
     * Sprint (2026-07-10): coalesce concurrent permission checks. Multiple
     * near-simultaneous callers (dashboard load, the resume-triggered
     * auto-sync preflight, a manual sync button's own preflight, and
     * SyncWorker's independent preflight inside the job it enqueues) used to
     * each hit the Health Connect provider separately. Under that load, a
     * transient IPC hiccup became more likely to happen twice in a row
     * (exhausting the previous single-retry safety net) -- exactly what
     * flashed "Connect Health Connect" over data that was actually fine, and
     * it got more frequent, not less, once sync-on-resume made these bursts
     * happen on every return to the app and every manual sync tap. A short
     * cache behind a mutex means a whole burst of calls within the TTL
     * shares one real result instead of each hitting the provider.
     */
    private val permissionCheckMutex = Mutex()
    private val cachedPermissions = AtomicReference<Pair<Set<String>, Long>?>(null)

    val healthConnectClient: HealthConnectClient?
        get() = cachedClient.get()

    /** Suspend-safe accessor that retries creation if the cache is currently empty. */
    private suspend fun resolveClient(): HealthConnectClient? {
        cachedClient.get()?.let { return it }

        return clientLock.withLock {
            // Re-check after acquiring the lock: another coroutine may have
            // already resolved the client while we were waiting.
            cachedClient.get()?.let { return@withLock it }

            if (HealthConnectClient.getSdkStatus(context) != HealthConnectClient.SDK_AVAILABLE) {
                AppLogger.w(TAG, "Health Connect SDK is not available")
                return@withLock null
            }

            try {
                val client = HealthConnectClient.getOrCreate(context)
                cachedClient.set(client)
                AppLogger.i(TAG, "HealthConnectClient created OK")
                client
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "getOrCreate failed; will retry on next access: ${e.message}", e)
                null
            }
        }
    }

    override fun invalidateClientCache() {
        val hadClient = cachedClient.getAndSet(null) != null
        cachedPermissions.set(null)
        if (hadClient) {
            AppLogger.w(TAG, "Health Connect client cache invalidated; will recreate on next access")
        }
    }

    override val permissions: Set<String> = HealthPermissionPolicy.requestPermissions

    override fun requiredPermissions(): Set<String> = HealthPermissionPolicy.syncPermissions

    override fun getStatus(): HealthConnectStatus {
        val sdkStatus = HealthConnectClient.getSdkStatus(context)
        val installedPackage = findInstalledHcPackage()

        AppLogger.i(
            TAG,
            "getSdkStatus()=$sdkStatus installedPackage=${installedPackage ?: "none"} API=${Build.VERSION.SDK_INT} device=${Build.MODEL}"
        )

        return when (sdkStatus) {
            HealthConnectClient.SDK_AVAILABLE -> HealthConnectStatus.AVAILABLE
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> HealthConnectStatus.NEEDS_UPDATE
            else -> if (installedPackage != null) HealthConnectStatus.NEEDS_UPDATE else HealthConnectStatus.NOT_INSTALLED
        }
    }

    fun findInstalledHcPackage(): String? {
        for (packageName in HC_PACKAGES) {
            try {
                context.packageManager.getPackageInfo(packageName, 0)
                AppLogger.d(TAG, "Found Health Connect package: $packageName")
                return packageName
            } catch (_: PackageManager.NameNotFoundException) {
                AppLogger.d(TAG, "Health Connect package not found: $packageName")
            }
        }
        return null
    }

    /**
     * Sprint 2026-08-27: opens Health Connect's own settings screen, from
     * which the user can reach "Manage data > Data sources and priority".
     * This is a distinct, separate consent step from the runtime read/write
     * permission grant BitLut already requests: Health Connect requires a
     * writing app to be explicitly added as a contributing data source for
     * each category (Steps, Distance, Exercise, etc.) before its records
     * count toward totals a reader relies on, even though the records exist
     * in the store and are visible to BitLut itself the moment the runtime
     * permission is granted. This was a plausible, previously-unaddressed
     * reason a third-party reader could show no BitLut-synced activity: the
     * permission grant alone does not guarantee BitLut is listed there.
     *
     * `ACTION_HEALTH_CONNECT_SETTINGS` (declared as
     * `androidx.health.ACTION_HEALTH_CONNECT_SETTINGS` in the manifest's
     * `<queries>` block already, for this exact purpose) opens Health
     * Connect's general settings screen; Health Connect does not currently
     * expose a stable, documented deep link straight into the data-sources
     * sub-screen, so this is the closest available entry point. The caller
     * (MainActivity) is responsible for wrapping startActivity in a
     * try/catch, matching the existing pattern for the Huawei authorization
     * intent below.
     */
    fun healthConnectSettingsIntent(): android.content.Intent =
        android.content.Intent(HealthConnectClient.ACTION_HEALTH_CONNECT_SETTINGS)

    private suspend fun grantedPermissionsOrEmpty(): Set<String> {
        val stalePermissions = cachedPermissions.get()?.first
        cachedPermissions.get()?.let { (granted, atMs) ->
            if (System.currentTimeMillis() - atMs < PERMISSION_CACHE_TTL_MS) return granted
        }
        return permissionCheckMutex.withLock {
            // Re-check after acquiring the lock: another caller may have just
            // refreshed this while we were waiting our turn -- most calls in
            // a burst will hit this and never touch the provider at all.
            cachedPermissions.get()?.let { (granted, atMs) ->
                if (System.currentTimeMillis() - atMs < PERMISSION_CACHE_TTL_MS) return@withLock granted
            }

            val client = resolveClient() ?: return@withLock emptySet()
            val granted = try {
                client.permissionController.getGrantedPermissions()
            } catch (e: CancellationException) {
                throw e
            } catch (e: SecurityException) {
                // A SecurityException here can mean the cached client reference is
                // stale (e.g. Health Connect was reinstalled/updated under us).
                // Invalidate so the next call gets a fresh client instead of
                // repeating the same failure forever.
                AppLogger.e(TAG, "Permission snapshot denied; invalidating client cache: ${e.message}", e)
                invalidateClientCache()
                emptySet()
            } catch (e: Exception) {
                // Sprint 2026-07-08: a single transient IPC hiccup here must not
                // be conflated with "permissions really are missing". One quick
                // retry absorbs the common transient case; only a second
                // consecutive failure is treated as a real denial.
                AppLogger.w(TAG, "Permission snapshot failed once, retrying: ${e.message}")
                try {
                    delay(TRANSIENT_PERMISSION_RETRY_DELAY_MS)
                    client.permissionController.getGrantedPermissions()
                } catch (e2: CancellationException) {
                    throw e2
                } catch (e2: Exception) {
                    if (stalePermissions != null) {
                        AppLogger.w(
                            TAG,
                            "Permission snapshot temporarily unavailable; preserving last-known permissions instead of treating a rate limit as denial: ${e2.message}"
                        )
                        stalePermissions
                    } else {
                        AppLogger.e(TAG, "Permission snapshot failed with no last-known state: ${e2.message}", e2)
                        throw e2
                    }
                }
            }
            cachedPermissions.set(granted to System.currentTimeMillis())
            granted
        }
    }

    override suspend fun missingRequiredPermissions(): Set<String> {
        return try {
            requiredPermissions() - grantedPermissionsOrEmpty()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "Missing permission check failed: ${e.message}", e)
            requiredPermissions()
        }
    }

    override suspend fun hasAllPermissions(): Boolean {
        return try {
            val granted = grantedPermissionsOrEmpty()
            AppLogger.d(TAG, "Granted Health Connect permissions: $granted")
            granted.containsAll(requiredPermissions())
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "Permission check failed: ${e.message}", e)
            false
        }
    }

    /**
     * Writes every category in [snapshot] independently and reports which
     * categories succeeded vs failed, instead of collapsing the whole write
     * into a single Boolean. This lets the caller (SyncWorker) advance the
     * sync cursor for categories that wrote successfully even if one
     * category -- e.g. floors, which several Huawei device/firmware
     * combinations don't expose at all -- keeps failing. Without this, a
     * single permanently-failing category would block the cursor for every
     * other category forever, retry after retry.
     */
    override suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): WriteSnapshotResult {
        val results = listOf(
            "steps" to writeStepsBatch(snapshot.steps),
            "distance" to writeDistanceBatch(snapshot.distances),
            "floors" to writeFloorsBatch(snapshot.floors),
            "elevation" to writeElevationBatch(snapshot.elevations),
            "activeCalories" to writeActiveCaloriesBatch(snapshot.activeCalories),
            "activitySessions" to writeActivitySessionsBatch(workoutFilterPrefs.apply(snapshot.activities))
        )

        val succeeded = results.filter { it.second }.map { it.first }.toSet()
        val failed = results.filterNot { it.second }.map { it.first }.toSet()

        if (failed.isNotEmpty()) {
            AppLogger.e(TAG, "writeSnapshot partial failure: ${failed.joinToString()}")
        }

        return WriteSnapshotResult(succeededCategories = succeeded, failedCategories = failed)
    }

    suspend fun writeStepsBatch(records: List<StepData>): Boolean {
        val validSourceRecords = records
            .filter { it.count > 0 && it.startTimeMs < it.endTimeMs }
        val version = System.currentTimeMillis()
        val valid = validSourceRecords.map {
            val start = Instant.ofEpochMilli(it.startTimeMs)
            val end = Instant.ofEpochMilli(it.endTimeMs)
            StepsRecord(
                count = it.count,
                startTime = start,
                endTime = end,
                startZoneOffset = offset(start),
                endZoneOffset = offset(end),
                metadata = if (it.sourceId != null) {
                    bitlutDailyStepMetadata(it.sourceId, version)
                } else {
                    bitlutMetadata("steps", start.toEpochMilli(), end.toEpochMilli(), version = version)
                }
            )
        }

        if (valid.isEmpty()) {
            AppLogger.i(TAG, "No steps records to write")
            return true
        }

        val isCompleteDailySummation = validSourceRecords.all { it.sourceId != null }
        if (!isCompleteDailySummation) {
            return replaceRecords("steps", valid, StepsRecord::class)
        }

        val client = resolveClient() ?: run {
            AppLogger.e(TAG, "write steps: no Health Connect client")
            return false
        }
        val deleteStart = valid.minOf { it.startTime }
        val deleteEnd = valid.maxOf { it.endTime }

        return try {
            // Time-range deletion is automatically restricted by Health
            // Connect to records owned by BitLut. This removes legacy raw
            // delta records before writing one authoritative Huawei daily
            // total per date, preventing old+new double counting.
            client.deleteRecords(
                StepsRecord::class,
                TimeRangeFilter.between(deleteStart, deleteEnd)
            )
            valid.chunked(WRITE_BATCH_SIZE).forEach { client.insertRecords(it) }
            AppLogger.i(
                TAG,
                "Reconciled Huawei daily steps in Health Connect: days=${valid.size} today=${valid.last().count} range=$deleteStart..$deleteEnd"
            )
            true
        } catch (e: CancellationException) {
            throw e
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "write steps denied by Health Connect permission policy: ${e.message}", e)
            invalidateClientCache()
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "daily steps reconciliation failed: ${e.message}", e)
            false
        }
    }

    private suspend fun writeDistanceBatch(records: List<DistanceData>): Boolean {
        val valid = records
            .filter { it.meters > 0.0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                DistanceRecord(
                    distance = Length.meters(it.meters),
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    metadata = bitlutMetadata("distance", start.toEpochMilli(), end.toEpochMilli())
                )
            }

        return replaceRecords("distance", valid, DistanceRecord::class)
    }

    private suspend fun writeFloorsBatch(records: List<FloorsData>): Boolean {
        val valid = records
            .filter { it.floors > 0.0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                FloorsClimbedRecord(
                    floors = it.floors,
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    metadata = bitlutMetadata("floors", start.toEpochMilli(), end.toEpochMilli())
                )
            }

        return replaceRecords("floors", valid, FloorsClimbedRecord::class)
    }

    private suspend fun writeElevationBatch(records: List<ElevationData>): Boolean {
        val valid = records
            .filter { it.meters > 0.0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                ElevationGainedRecord(
                    elevation = Length.meters(it.meters),
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    metadata = bitlutMetadata("elevation", start.toEpochMilli(), end.toEpochMilli())
                )
            }

        return replaceRecords("elevation", valid, ElevationGainedRecord::class)
    }

    private suspend fun writeActiveCaloriesBatch(records: List<ActiveCaloriesData>): Boolean {
        val valid = records
            .filter { it.kilocalories > 0.0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                ActiveCaloriesBurnedRecord(
                    energy = Energy.kilocalories(it.kilocalories),
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    metadata = bitlutMetadata("active_calories", start.toEpochMilli(), end.toEpochMilli())
                )
            }

        return replaceRecords("activeCalories", valid, ActiveCaloriesBurnedRecord::class)
    }

    private data class StoredWorkoutSummary(
        val distanceMeters: Double?,
        val totalCaloriesKcal: Double?,
        val elevationMeters: Double?,
        val steps: Long?
    )

    private fun workoutSummaryKey(startTimeMs: Long, endTimeMs: Long): String =
        "$startTimeMs:$endTimeMs"

    private fun persistWorkoutSummary(session: ActivitySessionData) {
        if (session.distanceMeters == null &&
            session.totalCaloriesKcal == null &&
            session.elevationMeters == null &&
            session.steps == null
        ) return

        val encoded = listOf(
            session.distanceMeters?.toString() ?: "x",
            session.totalCaloriesKcal?.toString() ?: "x",
            session.elevationMeters?.toString() ?: "x",
            session.steps?.toString() ?: "x"
        ).joinToString("|")

        workoutSummaryPrefs.edit()
            .putString(workoutSummaryKey(session.startTimeMs, session.endTimeMs), encoded)
            .apply()
    }

    private fun storedWorkoutSummary(startTimeMs: Long, endTimeMs: Long): StoredWorkoutSummary? {
        val raw = workoutSummaryPrefs.getString(workoutSummaryKey(startTimeMs, endTimeMs), null)
            ?: return null
        val parts = raw.split('|')
        if (parts.size != 4) return null
        return StoredWorkoutSummary(
            distanceMeters = parts[0].takeUnless { it == "x" }?.toDoubleOrNull(),
            totalCaloriesKcal = parts[1].takeUnless { it == "x" }?.toDoubleOrNull(),
            elevationMeters = parts[2].takeUnless { it == "x" }?.toDoubleOrNull(),
            steps = parts[3].takeUnless { it == "x" }?.toLongOrNull()
        )
    }

    private fun workoutFingerprint(session: ActivitySessionData): String {
        val source = listOf(
            session.exerciseType.toString(),
            session.title.trim(),
            session.distanceMeters?.toString() ?: "x",
            session.totalCaloriesKcal?.toString() ?: "x",
            session.elevationMeters?.toString() ?: "x",
            session.steps?.toString() ?: "x"
        ).joinToString("|")
        val digest = java.security.MessageDigest.getInstance("SHA-256")
            .digest(source.toByteArray(Charsets.UTF_8))
        return digest.take(12).joinToString("") { byte -> "%02x".format(byte.toInt() and 0xff) }
    }

    private fun workoutVersionKey(startTimeMs: Long, endTimeMs: Long): String =
        "record_version:$startTimeMs:$endTimeMs"

    /**
     * Keeps clientRecordVersion stable while the source workout is unchanged.
     * A new version is generated only when Huawei changes the workout summary.
     * This avoids making downstream readers re-process every old workout on
     * every background sync while still allowing real corrections to upsert.
     */
    private fun workoutRecordVersion(session: ActivitySessionData): Long {
        val key = workoutVersionKey(session.startTimeMs, session.endTimeMs)
        val fingerprint = workoutFingerprint(session)
        val stored = workoutSummaryPrefs.getString(key, null)
        val separator = stored?.indexOf('|') ?: -1
        val previousVersion = if (separator > 0) stored?.substring(0, separator)?.toLongOrNull() else null
        val previousFingerprint = if (separator > 0) stored?.substring(separator + 1) else null

        if (previousVersion != null && previousFingerprint == fingerprint) {
            return previousVersion
        }

        val version = maxOf(System.currentTimeMillis(), (previousVersion ?: 0L) + 1L)
        workoutSummaryPrefs.edit().putString(key, "$version|$fingerprint").apply()
        return version
    }

    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {
        // BITLUT_WORKOUT_HARDENING_V3
        val validSessions = records
            .asSequence()
            .filter { it.startTimeMs < it.endTimeMs }
            .distinctBy { Pair(it.startTimeMs, it.endTimeMs) }
            .sortedBy { it.startTimeMs }
            .toList()

        if (validSessions.isEmpty()) {
            AppLogger.i(TAG, "No activitySessions records to write")
            return true
        }

        val client = resolveClient() ?: run {
            AppLogger.e(TAG, "write activitySessions: no Health Connect client")
            return false
        }

        var allSucceeded = true
        var written = 0

        for (session in validSessions) {
            persistWorkoutSummary(session)
            val version = workoutRecordVersion(session)
            val start = Instant.ofEpochMilli(session.startTimeMs)
            val end = Instant.ofEpochMilli(session.endTimeMs)

            val exercise = ExerciseSessionRecord(
                startTime = start,
                endTime = end,
                startZoneOffset = offset(start),
                endZoneOffset = offset(end),
                exerciseType = session.exerciseType,
                title = session.title,
                metadata = bitlutWorkoutMetadata(
                    "exercise",
                    start.toEpochMilli(),
                    end.toEpochMilli(),
                    version = version
                )
            )

            // Health Connect models workout summaries as records sharing the
            // exercise interval. Insert the session and its calorie summary in
            // one request so readers never observe a newly-written bare session
            // before the associated summary arrives.
            val bundle = mutableListOf<Record>(exercise)
            val kcal = session.totalCaloriesKcal?.takeIf { it > 0.0 }
                ?: estimatedTotalCaloriesKcal(session.exerciseType, session.startTimeMs, session.endTimeMs)
            if (kcal != null && kcal > 0.0) {
                bundle += TotalCaloriesBurnedRecord(
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    energy = Energy.kilocalories(kcal),
                    // Keep the historical ID so old estimated calorie records
                    // are upgraded in place instead of duplicated.
                    metadata = bitlutWorkoutMetadata(
                        "exercise_calories_estimate",
                        start.toEpochMilli(),
                        end.toEpochMilli(),
                        version = version
                    )
                )
            }

            try {
                client.insertRecords(bundle)
                written += 1
            } catch (e: CancellationException) {
                throw e
            } catch (e: SecurityException) {
                AppLogger.e(TAG, "write activitySessions denied by Health Connect: ${e.message}", e)
                invalidateClientCache()
                throw e
            } catch (e: Exception) {
                // One malformed/overlapping Huawei session must not prevent
                // unrelated valid workouts in the same sync from being written.
                allSucceeded = false
                AppLogger.e(
                    TAG,
                    "Workout bundle write failed: start=${session.startTimeMs} end=${session.endTimeMs} " +
                        "type=${session.exerciseType} error=${e.message}",
                    e
                )
            }
        }

        AppLogger.i(TAG, "Workout bundles written: $written/${validSessions.size}")
        return allSucceeded
    }


    /**
     * MET-formula estimate of total calories burned for a workout, used only
     * to give third-party Health Connect readers something non-zero to
     * import (see the call site in [writeActivitySessionsBatch] for why).
     * Delegates to [com.openhealth.sync.util.WorkoutCalorieEstimator] (sprint
     * 2026-08-26 extraction) so this exact formula and MET table also back
     * the workout card's own calorie display -- see that object's own doc
     * comment for the full rationale, the formula, and why it is not
     * measured data.
     */
    private fun estimatedTotalCaloriesKcal(exerciseType: Int, startTimeMs: Long, endTimeMs: Long): Double? =
        com.openhealth.sync.util.WorkoutCalorieEstimator.estimateTotalCaloriesKcal(exerciseType, startTimeMs, endTimeMs)

    private suspend fun replaceRecords(
        label: String,
        records: List<Record>,
        recordType: KClass<out Record>
    ): Boolean {
        val client = resolveClient() ?: run {
            AppLogger.e(TAG, "write $label: no Health Connect client")
            return false
        }

        if (records.isEmpty()) {
            AppLogger.i(TAG, "No $label records to write")
            return true
        }

        return try {
            records.chunked(WRITE_BATCH_SIZE).forEach { chunk ->
                // insertRecords is an upsert when clientRecordId is stable and
                // clientRecordVersion is newer. Deleting an ID before its first
                // insert is what produced Health Connect's "invalid UID" error.
                client.insertRecords(chunk)
            }
            AppLogger.i(TAG, "Upserted ${records.size} $label records")
            true
        } catch (e: CancellationException) {
            throw e
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "write $label denied by Health Connect permission policy: ${e.message}", e)
            // A SecurityException here can also indicate a stale client reference
            // (e.g. Health Connect was reinstalled/updated under us). Invalidate
            // so the next sync attempt gets a fresh client rather than repeating
            // the same failure on every retry until the process restarts.
            invalidateClientCache()
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "write $label failed: ${e.message}", e)
            false
        }
    }

    override suspend fun readDashboardSnapshot(): GoogleDashboardSnapshot? {
        val client = resolveClient() ?: return null
        return try {
            AppLogger.i(
                TAG,
                "Reading dashboard source=${dataSourcePrefs.selected()} origins=${selectedDataOrigins()}"
            )

            // Read one compact activity window and regroup it locally by day.
            // This keeps all insight cards consistent with the raw records that
            // were just written, avoiding Health Connect aggregate-cache lag.
            val recentWorkouts = readRecentWorkouts(200)
            val activityWindow = readDailyActivitySummaries(
                client = client,
                daysBack = DASHBOARD_HISTORY_DAYS,
                workouts = recentWorkouts
            )
            val displayedWorkouts = enrichDisplayedWorkoutMetrics(
                client = client,
                workouts = activityWindow.workouts.take(2)
            )
            val today = LocalDate.now()
            val todayActivity = activityWindow.dailyActivity.firstOrNull { it.date == today }

            GoogleDashboardSnapshot(
                stepsToday = todayActivity?.steps ?: 0L,
                distanceMeters = todayActivity?.distanceMeters ?: 0.0,
                caloriesKcal = todayActivity?.caloriesKcal ?: 0.0,
                workoutMinutesToday = todayActivity?.workoutMinutes ?: 0L,
                activeHoursToday = 0,
                recentWorkouts = displayedWorkouts,
                dailyActivity = activityWindow.dailyActivity
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "readDashboardSnapshot denied; invalidating client cache: ${e.message}", e)
            invalidateClientCache()
            null
        } catch (e: Exception) {
            AppLogger.e(TAG, "readDashboardSnapshot failed; preserving previous UI snapshot: ${e.message}", e)
            null
        }
    }

    /**
     * Enriches only the workout cards that are actually displayed.
     *
     * Raw activity records are still used for the 30-day dashboard ledger, but
     * they are not a reliable primary source for per-session metrics: a bounded
     * newest-first page can legitimately omit records from an older workout.
     * Health Connect's aggregate API is designed for this exact case and
     * computes totals inside the exercise interval without paging raw records.
     *
     * The dashboard shows two workouts, so this adds at most two provider calls
     * per dashboard snapshot and keeps the quota-storm fix intact.
     */
    private suspend fun enrichDisplayedWorkoutMetrics(
        client: HealthConnectClient,
        workouts: List<ActivitySessionData>
    ): List<ActivitySessionData> = workouts.take(2).map { workout ->
        if (workout.endTimeMs <= workout.startTimeMs) return@map workout

        val start = Instant.ofEpochMilli(workout.startTimeMs)
        val end = Instant.ofEpochMilli(workout.endTimeMs)

        try {
            val aggregate = client.aggregate(
                AggregateRequest(
                    metrics = setOf(
                        StepsRecord.COUNT_TOTAL,
                        DistanceRecord.DISTANCE_TOTAL,
                        ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL,
                        TotalCaloriesBurnedRecord.ENERGY_TOTAL,
                        ElevationGainedRecord.ELEVATION_GAINED_TOTAL
                    ),
                    timeRangeFilter = TimeRangeFilter.between(start, end),
                    dataOriginFilter = selectedDataOrigins()
                )
            )

            val aggregateDistanceMeters = aggregate[DistanceRecord.DISTANCE_TOTAL]
                ?.inMeters
                ?.takeIf { it > 0.0 }
            val activeCaloriesKcal = aggregate[ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL]
                ?.inKilocalories
                ?.takeIf { it > 0.0 }
            val aggregateTotalCaloriesKcal = aggregate[TotalCaloriesBurnedRecord.ENERGY_TOTAL]
                ?.inKilocalories
                ?.takeIf { it > 0.0 }
            // For Huawei/BitLut, only the local ActivityRecord summary is
            // treated as real dashboard calorie data. The Health Connect
            // TotalCalories record may be the MET interoperability fallback.
            val totalCaloriesKcal = workout.totalCaloriesKcal
                ?: aggregateTotalCaloriesKcal.takeUnless { isHuaweiBridgeSourceSelected() }
            val elevationMeters = aggregate[ElevationGainedRecord.ELEVATION_GAINED_TOTAL]
                ?.inMeters
                ?.takeIf { it > 0.0 }
            val steps = aggregate[StepsRecord.COUNT_TOTAL]
                ?.takeIf { it > 0L }

            val recoveredDistanceMeters = if (
                aggregateDistanceMeters == null && workout.distanceMeters == null
            ) {
                recoverWorkoutDistanceFromRawRecords(client, workout)
            } else {
                null
            }
            // Sprint 2026-08-28: workout.distanceMeters (now populated by
            // HuaweiHealthManager directly from Huawei's own per-activity
            // sample data, scoped exactly to this session -- see the doc
            // comment on readActivitySessions there) is trusted FIRST, ahead
            // of the Health Connect aggregate. Previously the aggregate won
            // whenever it returned any non-null value, even a wrong one: a
            // real 28 km bike ride showed as 0.7 km on the dashboard because
            // a coarse, wide-window DistanceRecord partially overlapped the
            // session and the aggregate briefly returned a small non-null
            // total for that narrow overlap, before session-level data was
            // ever provided as a competing, more trustworthy source. The
            // aggregate and raw-overlap paths remain as fallbacks for
            // sessions Huawei didn't report per-activity distance for (e.g.
            // recorded by a different app, or an older/incomplete Huawei
            // record), where they're still better than nothing.
            val distanceMeters = workout.distanceMeters ?: aggregateDistanceMeters ?: recoveredDistanceMeters

            AppLogger.i(
                TAG,
                "Workout metrics resolved: type=${workout.exerciseType} " +
                    "start=${workout.startTimeMs} end=${workout.endTimeMs} " +
                    "distanceMeters=${distanceMeters ?: 0.0} " +
                    "distanceSource=${when {
                        workout.distanceMeters != null -> "session"
                        aggregateDistanceMeters != null -> "aggregate"
                        recoveredDistanceMeters != null -> "raw_overlap"
                        else -> "missing"
                    }} " +
                    "activeCaloriesKcal=${activeCaloriesKcal ?: 0.0} " +
                    "totalCaloriesKcal=${totalCaloriesKcal ?: 0.0} " +
                    "elevationMeters=${elevationMeters ?: 0.0} steps=${steps ?: 0L}"
            )

            workout.copy(
                distanceMeters = distanceMeters,
                activeCaloriesKcal = activeCaloriesKcal ?: workout.activeCaloriesKcal,
                totalCaloriesKcal = totalCaloriesKcal,
                elevationMeters = elevationMeters ?: workout.elevationMeters,
                steps = steps ?: workout.steps
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.w(
                TAG,
                "Workout metric aggregation failed for ${workout.startTimeMs}..${workout.endTimeMs}: ${e.message}"
            )
            workout
        }
    }

    /**
     * Conservative recovery for source distance intervals that cross an
     * exercise-session boundary. The provider query is widened only for the
     * two displayed workout cards, but attribution is still calculated against
     * the exact workout interval. Coarse records longer than three hours are
     * ignored so daily totals cannot be smeared into a workout.
     */
    private suspend fun recoverWorkoutDistanceFromRawRecords(
        client: HealthConnectClient,
        workout: ActivitySessionData
    ): Double? {
        val sessionStartMs = workout.startTimeMs
        val sessionEndMs = workout.endTimeMs
        if (sessionEndMs <= sessionStartMs) return null

        val queryStart = Instant.ofEpochMilli(sessionStartMs)
            .minusSeconds(WORKOUT_DISTANCE_QUERY_PADDING_SECONDS)
        val queryEnd = Instant.ofEpochMilli(sessionEndMs)
            .plusSeconds(WORKOUT_DISTANCE_QUERY_PADDING_SECONDS)

        val records = try {
            client.readRecords(
                ReadRecordsRequest(
                    recordType = DistanceRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(queryStart, queryEnd),
                    dataOriginFilter = selectedDataOrigins()
                )
            ).records
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.w(
                TAG,
                "Workout distance fallback failed for ${workout.startTimeMs}..${workout.endTimeMs}: ${e.message}"
            )
            return null
        }

        var recoveredMeters = 0.0
        var matchedRecords = 0

        records.forEach { record ->
            val recordStartMs = record.startTime.toEpochMilli()
            val recordEndMs = record.endTime.toEpochMilli()
            val recordDurationMs = recordEndMs - recordStartMs
            if (
                recordDurationMs <= 0L ||
                recordDurationMs > MAX_WORKOUT_DISTANCE_SOURCE_RECORD_MS
            ) {
                return@forEach
            }

            val overlapStartMs = maxOf(recordStartMs, sessionStartMs)
            val overlapEndMs = minOf(recordEndMs, sessionEndMs)
            if (overlapEndMs <= overlapStartMs) return@forEach

            val overlapFraction =
                (overlapEndMs - overlapStartMs).toDouble() / recordDurationMs.toDouble()
            val attributedMeters = record.distance.inMeters * overlapFraction
            if (attributedMeters > 0.0) {
                recoveredMeters += attributedMeters
                matchedRecords += 1
            }
        }

        val result = recoveredMeters.takeIf {
            it >= MIN_RECOVERED_WORKOUT_DISTANCE_METERS
        }

        AppLogger.i(
            TAG,
            "Workout distance fallback: start=$sessionStartMs end=$sessionEndMs " +
                "records=${records.size} matched=$matchedRecords recoveredMeters=${result ?: 0.0}"
        )

        return result
    }

    /**
     * Dashboard reads must stay quota-bounded. A previous sprint drained every
     * Health Connect page for five 30-day streams; a single UI refresh could
     * therefore expand into many provider calls, and overlapping refresh
     * triggers quickly exhausted Health Connect's request quota.
     *
     * For the dashboard we only need the newest records, especially for the
     * two latest workout cards. Read exactly one newest-first page per stream.
     * CSV export remains a separate explicit-user action and is intentionally
     * outside this hot path.
     */
    private suspend fun <T : Record> readBoundedRecentRecords(
        client: HealthConnectClient,
        recordType: KClass<T>,
        timeRangeFilter: TimeRangeFilter,
        dataOriginFilter: Set<DataOrigin>,
        pageSize: Int = READ_PAGE_SIZE
    ): List<T> = client.readRecords(
        ReadRecordsRequest(
            recordType = recordType,
            timeRangeFilter = timeRangeFilter,
            dataOriginFilter = dataOriginFilter,
            ascendingOrder = false,
            pageSize = pageSize.coerceIn(1, READ_PAGE_SIZE)
        )
    ).records

    private data class SessionMetricAccumulator(
        var steps: Double = 0.0,
        var distanceMeters: Double = 0.0,
        var activeCaloriesKcal: Double = 0.0,
        var elevationMeters: Double = 0.0
    )

    private data class DashboardActivityWindow(
        val dailyActivity: List<DailyActivitySummary>,
        val workouts: List<ActivitySessionData>
    )

    /**
     * Reads each already-approved activity stream once for the dashboard window,
     * groups it by day, and attributes overlapping records to the two workout
     * cards that are actually displayed. This avoids one Health Connect query
     * per workout and does not request any new health category.
     */
    private suspend fun readDailyActivitySummaries(
        client: HealthConnectClient,
        daysBack: Int,
        workouts: List<ActivitySessionData>
    ): DashboardActivityWindow {
        val safeDays = daysBack.coerceIn(14, 60)
        val zone = ZoneId.systemDefault()
        val today = LocalDate.now()
        val firstDay = today.minusDays((safeDays - 1).toLong())
        val dates = (0 until safeDays).map { firstDay.plusDays(it.toLong()) }
        val start = firstDay.atStartOfDay(zone).toInstant()
        val end = Instant.now()
        val range = TimeRangeFilter.between(start, end)
        val origins = selectedDataOrigins()

        val stepsByDay = dates.associateWith { 0L }.toMutableMap()
        val distanceByDay = dates.associateWith { 0.0 }.toMutableMap()
        val caloriesByDay = dates.associateWith { 0.0 }.toMutableMap()
        val elevationByDay = dates.associateWith { 0.0 }.toMutableMap()
        val floorsByDay = dates.associateWith { 0.0 }.toMutableMap()
        val workoutMinutesByDay = dates.associateWith { 0L }.toMutableMap()
        val workoutCountByDay = dates.associateWith { 0 }.toMutableMap()
        val longestWorkoutByDay = dates.associateWith { 0L }.toMutableMap()

        val displayedWorkouts = workouts.take(2)
        val sessionMetrics = displayedWorkouts.associate {
            Pair(it.startTimeMs, it.endTimeMs) to SessionMetricAccumulator()
        }.toMutableMap()

        fun dateOf(epochMs: Long): LocalDate =
            Instant.ofEpochMilli(epochMs).atZone(zone).toLocalDate()

        fun overlapFraction(recordStartMs: Long, recordEndMs: Long, session: ActivitySessionData): Double {
            if (recordEndMs <= recordStartMs || session.endTimeMs <= session.startTimeMs) return 0.0
            val overlapStart = maxOf(recordStartMs, session.startTimeMs)
            val overlapEnd = minOf(recordEndMs, session.endTimeMs)
            if (overlapEnd <= overlapStart) return 0.0
            return (overlapEnd - overlapStart).toDouble() / (recordEndMs - recordStartMs).toDouble()
        }

        readBoundedRecentRecords(
            client = client,
            recordType = StepsRecord::class,
            timeRangeFilter = range,
            dataOriginFilter = origins
        ).forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in stepsByDay) stepsByDay[date] = (stepsByDay[date] ?: 0L) + record.count
            val startMs = record.startTime.toEpochMilli()
            val endMs = record.endTime.toEpochMilli()
            displayedWorkouts.forEach { session ->
                val fraction = overlapFraction(startMs, endMs, session)
                if (fraction > 0.0) {
                    sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.steps =
                        (sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.steps ?: 0.0) + record.count.toDouble() * fraction
                }
            }
        }

        readBoundedRecentRecords(
            client = client,
            recordType = DistanceRecord::class,
            timeRangeFilter = range,
            dataOriginFilter = origins
        ).forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in distanceByDay) distanceByDay[date] = (distanceByDay[date] ?: 0.0) + record.distance.inMeters
            val startMs = record.startTime.toEpochMilli()
            val endMs = record.endTime.toEpochMilli()
            displayedWorkouts.forEach { session ->
                val fraction = overlapFraction(startMs, endMs, session)
                if (fraction > 0.0) {
                    sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.distanceMeters =
                        (sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.distanceMeters ?: 0.0) + record.distance.inMeters * fraction
                }
            }
        }

        readBoundedRecentRecords(
            client = client,
            recordType = ActiveCaloriesBurnedRecord::class,
            timeRangeFilter = range,
            dataOriginFilter = origins
        ).forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in caloriesByDay) caloriesByDay[date] = (caloriesByDay[date] ?: 0.0) + record.energy.inKilocalories
            val startMs = record.startTime.toEpochMilli()
            val endMs = record.endTime.toEpochMilli()
            displayedWorkouts.forEach { session ->
                val fraction = overlapFraction(startMs, endMs, session)
                if (fraction > 0.0) {
                    sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.activeCaloriesKcal =
                        (sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.activeCaloriesKcal ?: 0.0) + record.energy.inKilocalories * fraction
                }
            }
        }

        readBoundedRecentRecords(
            client = client,
            recordType = ElevationGainedRecord::class,
            timeRangeFilter = range,
            dataOriginFilter = origins
        ).forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in elevationByDay) elevationByDay[date] = (elevationByDay[date] ?: 0.0) + record.elevation.inMeters
            val startMs = record.startTime.toEpochMilli()
            val endMs = record.endTime.toEpochMilli()
            displayedWorkouts.forEach { session ->
                val fraction = overlapFraction(startMs, endMs, session)
                if (fraction > 0.0) {
                    sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.elevationMeters =
                        (sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.elevationMeters ?: 0.0) + record.elevation.inMeters * fraction
                }
            }
        }

        readBoundedRecentRecords(
            client = client,
            recordType = FloorsClimbedRecord::class,
            timeRangeFilter = range,
            dataOriginFilter = origins
        ).forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in floorsByDay) floorsByDay[date] = (floorsByDay[date] ?: 0.0) + record.floors
        }

        val rangeStartMs = start.toEpochMilli()
        workouts.asSequence()
            .filter { it.startTimeMs >= rangeStartMs && it.endTimeMs > it.startTimeMs }
            .distinctBy { Pair(it.startTimeMs, it.endTimeMs) }
            .forEach { workout ->
                val date = dateOf(workout.startTimeMs)
                if (date !in workoutMinutesByDay) return@forEach
                val duration = ((workout.endTimeMs - workout.startTimeMs) / 60_000L).coerceAtLeast(1L)
                workoutMinutesByDay[date] = (workoutMinutesByDay[date] ?: 0L) + duration
                workoutCountByDay[date] = (workoutCountByDay[date] ?: 0) + 1
                longestWorkoutByDay[date] = maxOf(longestWorkoutByDay[date] ?: 0L, duration)
            }

        val dailyActivity = dates.map { date ->
            DailyActivitySummary(
                date = date,
                steps = stepsByDay[date] ?: 0L,
                distanceMeters = distanceByDay[date] ?: 0.0,
                caloriesKcal = caloriesByDay[date] ?: 0.0,
                elevationMeters = elevationByDay[date] ?: 0.0,
                floors = floorsByDay[date] ?: 0.0,
                workoutMinutes = workoutMinutesByDay[date] ?: 0L,
                workoutCount = workoutCountByDay[date] ?: 0,
                longestWorkoutMinutes = longestWorkoutByDay[date] ?: 0L
            )
        }

        val enrichedWorkouts = workouts.map { workout ->
            val metrics = sessionMetrics[Pair(workout.startTimeMs, workout.endTimeMs)]
            if (metrics == null) {
                workout
            } else {
                workout.copy(
                    distanceMeters = workout.distanceMeters ?: metrics.distanceMeters.takeIf { it > 0.0 },
                    activeCaloriesKcal = workout.activeCaloriesKcal ?: metrics.activeCaloriesKcal.takeIf { it > 0.0 },
                    elevationMeters = workout.elevationMeters ?: metrics.elevationMeters.takeIf { it > 0.0 },
                    steps = workout.steps ?: metrics.steps.toLong().takeIf { it > 0L }
                )
            }
        }

        return DashboardActivityWindow(dailyActivity = dailyActivity, workouts = enrichedWorkouts)
    }

    suspend fun readStepsToday(): Long {
    suspend fun readStepsToday(): Long {
        val client = resolveClient() ?: return 0L
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = Instant.now()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = StepsRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, end),
                    dataOriginFilter = selectedDataOrigins()
                )
            ).records.sumOf { it.count }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readStepsToday failed: ${e.message}", e)
            0L
        }
    }

    suspend fun readDistanceToday(): Double {
        val client = resolveClient() ?: return 0.0
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = DistanceRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now()),
                    dataOriginFilter = selectedDataOrigins()
                )
            ).records.sumOf { it.distance.inMeters }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readDistanceToday failed: ${e.message}", e)
            0.0
        }
    }

    suspend fun readCaloriesToday(): Double {
        val client = resolveClient() ?: return 0.0
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = ActiveCaloriesBurnedRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now()),
                    dataOriginFilter = selectedDataOrigins()
                )
            ).records.sumOf { it.energy.inKilocalories }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readCaloriesToday failed: ${e.message}", e)
            0.0
        }
    }

    suspend fun readRecentWorkouts(limit: Int = 5): List<ActivitySessionData> {
        val client = resolveClient() ?: return emptyList()
        return try {
            val start = LocalDate.now().minusDays(30).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = Instant.now()
            readBoundedRecentRecords(
                client = client,
                recordType = ExerciseSessionRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, end),
                dataOriginFilter = selectedDataOrigins(),
                pageSize = limit.coerceIn(1, 100)
            )
                .take(limit)
                .map { record ->
                    val startTimeMs = record.startTime.toEpochMilli()
                    val endTimeMs = record.endTime.toEpochMilli()
                    val stored = if (isHuaweiBridgeSourceSelected()) {
                        storedWorkoutSummary(startTimeMs, endTimeMs)
                    } else {
                        null
                    }
                    ActivitySessionData(
                        startTimeMs = startTimeMs,
                        endTimeMs = endTimeMs,
                        title = workoutDisplayName(record.title, record.exerciseType),
                        exerciseType = record.exerciseType,
                        distanceMeters = stored?.distanceMeters,
                        totalCaloriesKcal = stored?.totalCaloriesKcal,
                        elevationMeters = stored?.elevationMeters,
                        steps = stored?.steps
                    )
                }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readRecentWorkouts failed: ${e.message}", e)
            emptyList()
        }
    }

    /**
     * Feeds the CSV export (sprint 2026-07-14). One row per calendar day,
     * oldest first, for the last [daysBack] days including today. Reads
     * plain per-day records and sums in-app -- exactly the readDashboardSnapshot
     * pattern, not aggregate() -- so an export taken right after a sync
     * shows the same numbers as the dashboard, not a stale cached total.
     *
     * Sequential (not parallel) by design: this only runs on an explicit,
     * infrequent user tap, so the ~3x daysBack Health Connect calls it makes
     * are not a rate-limit concern the way a call inside load() would be
     * (see CLAUDE.md Gotcha 4) -- correctness and simplicity here matter
     * more than shaving a second off a manual export.
     */
    suspend fun readDailyTotals(daysBack: Int = 30): List<DailyTotal> {
        val client = resolveClient() ?: return emptyList()
        val today = LocalDate.now()
        val zone = ZoneId.systemDefault()
        val out = ArrayList<DailyTotal>(daysBack)

        for (offset in (daysBack - 1) downTo 0) {
            val day = today.minusDays(offset.toLong())
            val dayStart = day.atStartOfDay(zone).toInstant()
            val dayEnd = day.plusDays(1).atStartOfDay(zone).toInstant()
            val range = TimeRangeFilter.between(dayStart, dayEnd)

            try {
                val steps = client.readRecords(
                    ReadRecordsRequest(
                        recordType = StepsRecord::class,
                        timeRangeFilter = range,
                        dataOriginFilter = selectedDataOrigins()
                    )
                ).records.sumOf { it.count }
                val distance = client.readRecords(
                    ReadRecordsRequest(
                        recordType = DistanceRecord::class,
                        timeRangeFilter = range,
                        dataOriginFilter = selectedDataOrigins()
                    )
                ).records.sumOf { it.distance.inMeters }
                val calories = client.readRecords(
                    ReadRecordsRequest(
                        recordType = ActiveCaloriesBurnedRecord::class,
                        timeRangeFilter = range,
                        dataOriginFilter = selectedDataOrigins()
                    )
                ).records.sumOf { it.energy.inKilocalories }
                out.add(DailyTotal(day, steps, distance, calories))
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "readDailyTotals failed for $day: ${e.message}", e)
                out.add(DailyTotal(day, 0L, 0.0, 0.0))
            }
        }

        return out
    }

    suspend fun readWorkoutMinutesToday(): Long {
        val client = resolveClient() ?: return 0L
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = ExerciseSessionRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now()),
                    dataOriginFilter = selectedDataOrigins()
                )
            ).records.sumOf {
                java.time.Duration.between(it.startTime, it.endTime).toMinutes().coerceAtLeast(0L)
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readWorkoutMinutesToday failed: ${e.message}", e)
            0L
        }
    }

    suspend fun readActiveHoursToday(): Int {
        val client = resolveClient() ?: return 0
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = StepsRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now()),
                    dataOriginFilter = selectedDataOrigins()
                )
            ).records
                .filter { it.count > 0 }
                .map { it.startTime.atZone(ZoneId.systemDefault()).hour }
                .toSet()
                .size
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readActiveHoursToday failed: ${e.message}", e)
            0
        }
    }

    private fun workoutDisplayName(rawTitle: String?, exerciseType: Int): String {
        val cleaned = rawTitle?.trim()
        if (cleaned.isNullOrBlank() || SYNTHETIC_WORKOUT_TITLE.matches(cleaned)) {
            return exerciseTypeName(exerciseType)
        }

        return localizeWorkoutName(
            cleaned.replace('_', ' ').replace('.', ' ')
        )
    }

    private fun exerciseTypeName(type: Int): String {
        val raw = when (type) {
            ExerciseSessionRecord.EXERCISE_TYPE_WALKING -> "walking"
            ExerciseSessionRecord.EXERCISE_TYPE_RUNNING -> "running"
            ExerciseSessionRecord.EXERCISE_TYPE_BIKING -> "cycling"
            ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER -> "open water swimming"
            ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL -> "pool swimming"
            ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING -> "strength training"
            ExerciseSessionRecord.EXERCISE_TYPE_YOGA -> "yoga"
            ExerciseSessionRecord.EXERCISE_TYPE_TENNIS -> "tennis"
            ExerciseSessionRecord.EXERCISE_TYPE_BASKETBALL -> "basketball"
            ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AMERICAN -> "american football"
            ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AUSTRALIAN -> "australian football"
            ExerciseSessionRecord.EXERCISE_TYPE_SOCCER -> "football"
            ExerciseSessionRecord.EXERCISE_TYPE_GOLF -> "golf"
            ExerciseSessionRecord.EXERCISE_TYPE_HIKING -> "hiking"
            ExerciseSessionRecord.EXERCISE_TYPE_ROWING -> "rowing"
            ExerciseSessionRecord.EXERCISE_TYPE_SKATING -> "skating"
            ExerciseSessionRecord.EXERCISE_TYPE_SKIING -> "skiing"
            ExerciseSessionRecord.EXERCISE_TYPE_SNOWBOARDING -> "snowboarding"
            ExerciseSessionRecord.EXERCISE_TYPE_VOLLEYBALL -> "volleyball"
            ExerciseSessionRecord.EXERCISE_TYPE_BADMINTON -> "badminton"
            ExerciseSessionRecord.EXERCISE_TYPE_BASEBALL -> "baseball"
            ExerciseSessionRecord.EXERCISE_TYPE_BOXING -> "boxing"
            ExerciseSessionRecord.EXERCISE_TYPE_DANCING -> "dancing"
            ExerciseSessionRecord.EXERCISE_TYPE_ELLIPTICAL -> "elliptical"
            ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING -> "hiit"
            ExerciseSessionRecord.EXERCISE_TYPE_PILATES -> "pilates"
            ExerciseSessionRecord.EXERCISE_TYPE_TABLE_TENNIS -> "table tennis"
            ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING -> "weightlifting"
            ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT -> "workout"
            else -> "workout"
        }
        return localizeWorkoutName(raw)
    }

    private fun localizeWorkoutName(name: String): String {
        val normalized = name.trim().lowercase(Locale.ROOT)
        val ru = Locale.getDefault().language == "ru"

        if (!ru) {
            return normalized.replaceFirstChar { it.titlecase(Locale.ROOT) }
        }

        return when (normalized) {
            "walking", "walk" -> "Ходьба"
            "indoor walking" -> "Ходьба в помещении"
            "running", "run" -> "Бег"
            "indoor running", "running machine", "treadmill running" -> "Беговая дорожка"
            "trail running" -> "Трейлраннинг"
            "marathon" -> "Марафон"
            "cycling", "biking", "bike" -> "Велосипед"
            "indoor cycling", "spinning" -> "Велотренировка"
            "open water swimming" -> "Плавание в открытой воде"
            "pool swimming", "swimming", "swim" -> "Плавание"
            "strength training" -> "Силовая тренировка"
            "weightlifting" -> "Тяжёлая атлетика"
            "yoga" -> "Йога"
            "tennis" -> "Теннис"
            "table tennis" -> "Настольный теннис"
            "basketball" -> "Баскетбол"
            "football", "soccer" -> "Футбол"
            "american football" -> "Американский футбол"
            "australian football" -> "Австралийский футбол"
            "golf" -> "Гольф"
            "hiking" -> "Поход"
            "rowing" -> "Гребля"
            "rowing machine" -> "Гребной тренажёр"
            "jumping rope" -> "Скакалка"
            "rock climbing", "mountain climbing" -> "Скалолазание"
            "crossfit" -> "Кроссфит"
            "functional training" -> "Функциональная тренировка"
            "physical training" -> "Физическая тренировка"
            "core training" -> "Тренировка корпуса"
            "skating", "ice skating", "roller skating" -> "Катание на коньках"
            "skiing" -> "Лыжи"
            "snowboarding" -> "Сноуборд"
            "volleyball" -> "Волейбол"
            "badminton" -> "Бадминтон"
            "baseball" -> "Бейсбол"
            "boxing" -> "Бокс"
            "dancing" -> "Танцы"
            "elliptical" -> "Эллиптический тренажёр"
            "hiit" -> "Интервальная тренировка"
            "pilates" -> "Пилатес"
            "workout", "other workout", "huawei activity", "activity" -> "Тренировка"
            else -> name.replaceFirstChar { it.titlecase(Locale.getDefault()) }
        }
    }

    private fun generateRecordId(
        type: String,
        startTimeMs: Long,
        endTimeMs: Long,
        discriminator: String = ""
    ): String {
        val suffix = discriminator
            .replace(Regex("[^A-Za-z0-9_-]"), "_")
            .take(64)
            .let { if (it.isBlank()) "" else "_$it" }

        return "bitlut_${type}_${startTimeMs}_${endTimeMs}${suffix}"
    }

    /**
     * Passive Huawei streams (daily steps, distance, floors, elevation, etc.)
     * are relayed as automatically recorded. Exercise ActivityRecords are a
     * separate case: Huawei documents them as data produced after the user
     * starts a workout, so session records and their associated workout
     * calories use [bitlutWorkoutMetadata] / ACTIVELY_RECORDED below. This
     * preserves the source recording semantics required by Health Connect
     * instead of describing how BitLut itself happened to relay the record.
     *
     * Sprint 2026-08-27: `manufacturer = "Huawei"` added (model deliberately
     * left unset). Per Health Connect's own metadata guidance, supplying
     * manufacturer/model -- not just `type` -- "helps with attribution in
     * reader applications, so users can understand which device or
     * application recorded their data," and is one of the plausible,
     * previously-unaddressed reasons a stricter third-party reader might
     * decline a record whose device info is empty beyond TYPE_UNKNOWN.
     * "Huawei" is used rather than a specific model because that much is
     * genuinely true regardless of which Huawei phone or wearable actually
     * recorded the data -- BitLut relays whatever Huawei Health already
     * attributed the activity to, and has no reliable per-record model
     * signal of its own to report. Guessing a specific model would not be
     * true in the same way, so `model` is deliberately left unset;
     * `Device.TYPE_UNKNOWN` remains correct for the same reason.
     */
    private val bitlutRecordingDevice = Device(type = Device.TYPE_UNKNOWN, manufacturer = "Huawei")

    private fun bitlutDailyStepMetadata(sourceId: String, version: Long): Metadata {
        val safeSourceId = sourceId
            .replace(Regex("[^A-Za-z0-9_-]"), "_")
            .take(64)
        return Metadata.autoRecorded(
            clientRecordId = "bitlut_steps_daily_$safeSourceId",
            clientRecordVersion = version,
            device = bitlutRecordingDevice
        )
    }

    private fun bitlutMetadata(
        type: String,
        startTimeMs: Long,
        endTimeMs: Long,
        discriminator: String = "",
        version: Long = 1L
    ): Metadata = Metadata.autoRecorded(
        clientRecordId = generateRecordId(type, startTimeMs, endTimeMs, discriminator),
        clientRecordVersion = version,
        device = bitlutRecordingDevice
    )

    private fun bitlutWorkoutMetadata(
        type: String,
        startTimeMs: Long,
        endTimeMs: Long,
        discriminator: String = "",
        version: Long = 1L
    ): Metadata = Metadata.activelyRecorded(
        clientRecordId = generateRecordId(type, startTimeMs, endTimeMs, discriminator),
        clientRecordVersion = version,
        device = bitlutRecordingDevice
    )

    private fun offset(instant: Instant): ZoneOffset = zoneRules.getOffset(instant)
}
