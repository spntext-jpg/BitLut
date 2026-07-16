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
import androidx.health.connect.client.records.metadata.Metadata
import androidx.health.connect.client.request.AggregateRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.health.connect.client.units.Energy
import androidx.health.connect.client.units.Length
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
/** Sprint 2026-07-08: single quick retry delay for a transient permission-
 *  check failure -- see [GoogleHealthManager.grantedPermissionsOrEmpty]. */
private const val TRANSIENT_PERMISSION_RETRY_DELAY_MS = 400L
/** Sprint 2026-07-10: how long a permission-check result is trusted before
 *  a fresh one is required -- see [GoogleHealthManager.grantedPermissionsOrEmpty]. */
private const val PERMISSION_CACHE_TTL_MS = 3_000L

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

data class StepData(val startTimeMs: Long, val endTimeMs: Long, val count: Long)
data class DistanceData(val startTimeMs: Long, val endTimeMs: Long, val meters: Double)
data class FloorsData(val startTimeMs: Long, val endTimeMs: Long, val floors: Double)
data class ElevationData(val startTimeMs: Long, val endTimeMs: Long, val meters: Double)
data class ActiveCaloriesData(val startTimeMs: Long, val endTimeMs: Long, val kilocalories: Double)

data class ActivitySessionData(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val title: String = "Huawei activity",
    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT
)

data class GoogleDashboardSnapshot(
    val stepsToday: Long,
    val distanceMeters: Double,
    val caloriesKcal: Double,
    val workoutMinutesToday: Long,
    val activeHoursToday: Int,
    val recentWorkouts: List<ActivitySessionData>
)

class GoogleHealthManager(private val context: Context) : HealthConnectManager {

    private val zoneRules by lazy { ZoneId.systemDefault().rules }

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

    private suspend fun grantedPermissionsOrEmpty(): Set<String> {
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
                    AppLogger.e(TAG, "Permission snapshot failed twice; treating as denied: ${e2.message}", e2)
                    emptySet()
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
            "activitySessions" to writeActivitySessionsBatch(snapshot.activities)
        )

        val succeeded = results.filter { it.second }.map { it.first }.toSet()
        val failed = results.filterNot { it.second }.map { it.first }.toSet()

        if (failed.isNotEmpty()) {
            AppLogger.e(TAG, "writeSnapshot partial failure: ${failed.joinToString()}")
        }

        return WriteSnapshotResult(succeededCategories = succeeded, failedCategories = failed)
    }

    suspend fun writeStepsBatch(records: List<StepData>): Boolean {
        val valid = records
            .filter { it.count > 0 && it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                StepsRecord(
                    count = it.count,
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    metadata = bitlutMetadata("steps", start.toEpochMilli(), end.toEpochMilli())
                )
            }

        return replaceRecords("steps", valid, StepsRecord::class)
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

    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {
        val valid = records
            .filter { it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                ExerciseSessionRecord(
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    exerciseType = it.exerciseType,
                    title = it.title,
                    metadata = bitlutMetadata("exercise", start.toEpochMilli(), end.toEpochMilli())
                )
            }

        return replaceRecords("activitySessions", valid, ExerciseSessionRecord::class)
    }

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
                val clientRecordIds = chunk.mapNotNull { it.metadata.clientRecordId }
                if (clientRecordIds.isNotEmpty()) {
                    client.deleteRecords(recordType, emptyList(), clientRecordIds)
                }
                client.insertRecords(chunk)
            }
            AppLogger.i(TAG, "Replaced ${records.size} $label records")
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
            val startOfToday = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val now = Instant.now()

            // Sprint (2026-07-10): stepsToday/distanceMeters/caloriesKcal used
            // Health Connect's aggregate() API, which is a provider-side cache
            // that is only eventually consistent with recent writes -- it is
            // not guaranteed to reflect a just-inserted record immediately.
            // That is exactly why the dashboard looked stale until some
            // *other* app (e.g. Google Fit) happened to touch Health Connect
            // and force that cache to catch up: BitLut's own write was
            // landing correctly the whole time, but this read was trusting a
            // cache that hadn't caught up to it yet. readWorkoutMinutesToday()
            // / readActiveHoursToday() never had this problem because they
            // already read raw records and sum in-app instead of trusting the
            // aggregate cache -- these three now follow that exact same,
            // already-proven pattern.
            val stepsToday = client.readRecords(
                ReadRecordsRequest(
                    recordType = StepsRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            ).records.sumOf { it.count }

            val distanceMeters = client.readRecords(
                ReadRecordsRequest(
                    recordType = DistanceRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            ).records.sumOf { it.distance.inMeters }

            val caloriesKcal = client.readRecords(
                ReadRecordsRequest(
                    recordType = ActiveCaloriesBurnedRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            ).records.sumOf { it.energy.inKilocalories }

            // Sprint (2026-07-14): sleep/heart-rate/SpO2/stress and the
            // History-only stepsBars/workoutSummaries fields were removed
            // from GoogleDashboardSnapshot entirely (not just hardcoded to
            // empty/null) -- Huawei's individual-developer tier can't supply
            // the former, and History itself was removed from the bottom nav
            // in an earlier sprint, so both were dead weight kept only for
            // source compatibility. See CLAUDE.md for the platform-tier
            // rationale on sleep/HR/SpO2/stress specifically.
            GoogleDashboardSnapshot(
                stepsToday = stepsToday,
                distanceMeters = distanceMeters,
                caloriesKcal = caloriesKcal,
                workoutMinutesToday = readWorkoutMinutesToday(),
                activeHoursToday = readActiveHoursToday(),
                recentWorkouts = readRecentWorkouts(5)
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
     * Week-over-week comparison for the three activity-only metrics BitLut
     * already has approved access to. "Current week" is the last 7 days
     * including today (so it grows through the day rather than only
     * comparing complete weeks); "previous week" is the 7 days before that.
     * This intentionally does not require any new Huawei scope or Health
     * Connect permission -- it's a different aggregation of data BitLut
     * already reads for the dashboard screen.
     */
    override suspend fun readWeekOverWeekComparison(): WeekComparison? {
        val client = resolveClient() ?: return null
        return try {
            val today = LocalDate.now()
            val currentWeekStart = today.minusDays(6).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val currentWeekEnd = Instant.now()
            val previousWeekStart = today.minusDays(13).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val previousWeekEnd = currentWeekStart

            val currentAgg = client.aggregate(
                AggregateRequest(
                    metrics = setOf(
                        StepsRecord.COUNT_TOTAL,
                        DistanceRecord.DISTANCE_TOTAL,
                        ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL
                    ),
                    timeRangeFilter = TimeRangeFilter.between(currentWeekStart, currentWeekEnd)
                )
            )
            val previousAgg = client.aggregate(
                AggregateRequest(
                    metrics = setOf(
                        StepsRecord.COUNT_TOTAL,
                        DistanceRecord.DISTANCE_TOTAL,
                        ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL
                    ),
                    timeRangeFilter = TimeRangeFilter.between(previousWeekStart, previousWeekEnd)
                )
            )

            WeekComparison(
                currentWeekSteps = currentAgg[StepsRecord.COUNT_TOTAL] ?: 0L,
                previousWeekSteps = previousAgg[StepsRecord.COUNT_TOTAL] ?: 0L,
                currentWeekDistanceMeters = currentAgg[DistanceRecord.DISTANCE_TOTAL]?.inMeters ?: 0.0,
                previousWeekDistanceMeters = previousAgg[DistanceRecord.DISTANCE_TOTAL]?.inMeters ?: 0.0,
                currentWeekCaloriesKcal = currentAgg[ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL]?.inKilocalories ?: 0.0,
                previousWeekCaloriesKcal = previousAgg[ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL]?.inKilocalories ?: 0.0
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "readWeekOverWeekComparison denied; invalidating client cache: ${e.message}", e)
            invalidateClientCache()
            null
        } catch (e: Exception) {
            AppLogger.e(TAG, "readWeekOverWeekComparison failed: ${e.message}", e)
            null
        }
    }

    suspend fun readStepsToday(): Long {
        val client = resolveClient() ?: return 0L
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = Instant.now()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = StepsRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, end)
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
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
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
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
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
            client.readRecords(
                ReadRecordsRequest(
                    recordType = ExerciseSessionRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
                )
            ).records
                .sortedByDescending { it.startTime }
                .take(limit)
                .map {
                    ActivitySessionData(
                        startTimeMs = it.startTime.toEpochMilli(),
                        endTimeMs = it.endTime.toEpochMilli(),
                        title = it.title ?: exerciseTypeName(it.exerciseType),
                        exerciseType = it.exerciseType
                    )
                }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readRecentWorkouts failed: ${e.message}", e)
            emptyList()
        }
    }

    suspend fun readWorkoutMinutesToday(): Long {
        val client = resolveClient() ?: return 0L
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            client.readRecords(
                ReadRecordsRequest(
                    recordType = ExerciseSessionRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
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
                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
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
            "running", "run" -> "Бег"
            "cycling", "biking", "bike" -> "Велосипед"
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
            "skating" -> "Катание на коньках"
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

    private fun bitlutMetadata(
        type: String,
        startTimeMs: Long,
        endTimeMs: Long,
        discriminator: String = ""
    ): Metadata = Metadata(
        clientRecordId = generateRecordId(type, startTimeMs, endTimeMs, discriminator)
    )

    private fun offset(instant: Instant): ZoneOffset = zoneRules.getOffset(instant)
}
