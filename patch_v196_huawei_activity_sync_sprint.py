#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path.cwd()

def read(path):
    p = ROOT / path
    if not p.exists():
        raise SystemExit(f"Missing required file: {path}")
    return p.read_text(encoding="utf-8")

def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    print(f"patched {path}")

def replace_between(text, start_marker, end_marker, replacement):
    start = text.find(start_marker)
    if start == -1:
        raise SystemExit(f"Start marker not found: {start_marker}")
    end = text.find(end_marker, start)
    if end == -1:
        raise SystemExit(f"End marker not found: {end_marker}")
    return text[:start] + replacement + text[end:]

# 1) Single source of truth: Health Connect permissions aligned to approved Huawei activity/basic-sport scope.
write("app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt", '''package com.openhealth.sync.config

import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ElevationGainedRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.HeartRateVariabilityRmssdRecord
import androidx.health.connect.client.records.OxygenSaturationRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord

/**
 * Health Connect permission policy for BitLut v1.9.6.
 *
 * Production bridge contract:
 * Huawei Health Kit approval request is activity/basic sport READ only:
 * - Step
 * - Distance, ascent & altitude
 * - Active Hours
 * - Daily Activity Summary
 * - Activity record
 * - Activity
 *
 * Therefore Huawei -> Health Connect sync is allowed to depend only on the
 * activity/basic-sport records below. Sleep, heart-rate, SpO2 and HRV are optional
 * Google Health Connect dashboard reads; they must never block Huawei import/export.
 */
object HealthPermissionPolicy {

    val huaweiImportReadPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class),
        HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
    )

    val importWritePermissions: Set<String> = setOf(
        HealthPermission.getWritePermission(StepsRecord::class),
        HealthPermission.getWritePermission(DistanceRecord::class),
        HealthPermission.getWritePermission(FloorsClimbedRecord::class),
        HealthPermission.getWritePermission(ElevationGainedRecord::class),
        HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class),
        HealthPermission.getWritePermission(ExerciseSessionRecord::class),
    )

    val optionalDashboardReadPermissions: Set<String> = setOf(
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
        HealthPermission.getReadPermission(OxygenSaturationRecord::class),
        HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class),
    )

    /** Required for Huawei-derived activity import/export and core dashboard data. */
    val syncPermissions: Set<String> = huaweiImportReadPermissions + importWritePermissions

    /** UI request: required sync permissions plus optional dashboard-only reads. */
    val requestPermissions: Set<String> = syncPermissions + optionalDashboardReadPermissions

    /** Dashboard can read core activity plus optional health widgets when granted. */
    val dashboardReadPermissions: Set<String> = huaweiImportReadPermissions + optionalDashboardReadPermissions

    fun isRequiredSyncPermission(permission: String): Boolean = permission in syncPermissions

    fun isOptionalDashboardPermission(permission: String): Boolean = permission in optionalDashboardReadPermissions

    // Backward-compatible aliases used by older screens/managers.
    val dashboardPermissions: Set<String> = requestPermissions
    val importPermissions: Set<String> = syncPermissions
    val allPermissions: Set<String> = requestPermissions
}
''')

# 2) Manifest: declare required sync + optional reads only; no Health Connect writes for optional dashboard categories.
manifest_path = "app/src/main/AndroidManifest.xml"
manifest = read(manifest_path)
permission_block = '''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.ACTIVITY_RECOGNITION" />
    <uses-permission android:name="android.permission.INTERNET" />

    <!-- Health Connect required sync scope: Huawei activity/basic sport -> Google Health. -->
    <uses-permission android:name="android.permission.health.READ_STEPS" />
    <uses-permission android:name="android.permission.health.WRITE_STEPS" />
    <uses-permission android:name="android.permission.health.READ_DISTANCE" />
    <uses-permission android:name="android.permission.health.WRITE_DISTANCE" />
    <uses-permission android:name="android.permission.health.READ_FLOORS_CLIMBED" />
    <uses-permission android:name="android.permission.health.WRITE_FLOORS_CLIMBED" />
    <uses-permission android:name="android.permission.health.READ_ELEVATION_GAINED" />
    <uses-permission android:name="android.permission.health.WRITE_ELEVATION_GAINED" />
    <uses-permission android:name="android.permission.health.READ_ACTIVE_CALORIES_BURNED" />
    <uses-permission android:name="android.permission.health.WRITE_ACTIVE_CALORIES_BURNED" />
    <uses-permission android:name="android.permission.health.READ_EXERCISE" />
    <uses-permission android:name="android.permission.health.WRITE_EXERCISE" />

    <!-- Health Connect optional dashboard-only reads. Never required for sync. -->
    <uses-permission android:name="android.permission.health.READ_SLEEP" />
    <uses-permission android:name="android.permission.health.READ_HEART_RATE" />
    <uses-permission android:name="android.permission.health.READ_OXYGEN_SATURATION" />
    <uses-permission android:name="android.permission.health.READ_HEART_RATE_VARIABILITY" />
'''
q = manifest.find("    <queries>")
if q == -1:
    raise SystemExit("Manifest <queries> marker not found")
manifest = permission_block + manifest[q:]
write(manifest_path, manifest)

# 3) Google Health: remove corrupted duplicate dashboard method and make optional dashboard reads non-poisoning.
google_path = "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
g = read(google_path)
replacement = '''    // ── Read methods for Dashboard ────────────────────────────────────────────

    private suspend fun grantedPermissionSnapshot(): Set<String> = grantedPermissionsOrEmpty()

    private suspend fun <T> optionalDashboardRead(
        permission: String,
        label: String,
        defaultValue: T,
        block: suspend () -> T
    ): T {
        if (!grantedPermissionSnapshot().contains(permission)) {
            AppLogger.d(TAG, "Optional dashboard read skipped; permission missing: $label")
            return defaultValue
        }
        return try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            if (label == "heartRateBpm") {
                AppLogger.w(TAG, "Optional heart-rate aggregate skipped: ${e.message}")
            }
            AppLogger.w(TAG, "Optional dashboard read failed and was ignored: $label ${e.message}")
            defaultValue
        }
    }

    /**
     * Atomic dashboard refresh used by DashboardViewModel.
     *
     * Core activity metrics are read first. If Health Connect core reads fail, return
     * null so DashboardViewModel preserves the last good snapshot. Optional reads
     * (sleep, heart rate, SpO2, HRV/stress) are isolated and can never wipe the whole
     * dashboard or block Huawei sync/export.
     */
    suspend fun readDashboardSnapshot(daysBack: Int): GoogleDashboardSnapshot? {
        val c = healthConnectClient ?: return null
        return try {
            val startOfToday = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val now = Instant.now()

            val stepsToday = c.aggregate(
                AggregateRequest(
                    metrics = setOf(StepsRecord.COUNT_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[StepsRecord.COUNT_TOTAL] ?: 0L

            val distanceMeters = c.aggregate(
                AggregateRequest(
                    metrics = setOf(DistanceRecord.DISTANCE_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[DistanceRecord.DISTANCE_TOTAL]?.inMeters ?: 0.0

            val caloriesKcal = c.aggregate(
                AggregateRequest(
                    metrics = setOf(ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL]?.inKilocalories ?: 0.0

            val heartRatePermission = HealthPermission.getReadPermission(HeartRateRecord::class)
            val sleepPermission = HealthPermission.getReadPermission(SleepSessionRecord::class)
            val spo2Permission = HealthPermission.getReadPermission(OxygenSaturationRecord::class)
            val hrvPermission = HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class)

            val heartRateBpm = optionalDashboardRead<Long?>(heartRatePermission, "heartRateBpm", null) {
                c.aggregate(
                    AggregateRequest(
                        metrics = setOf(HeartRateRecord.BPM_AVG),
                        timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                    )
                )[HeartRateRecord.BPM_AVG]
            }

            GoogleDashboardSnapshot(
                stepsToday = stepsToday,
                distanceMeters = distanceMeters,
                caloriesKcal = caloriesKcal,
                workoutMinutesToday = readWorkoutMinutesToday(),
                activeHoursToday = readActiveHoursToday(),
                sleepHours = optionalDashboardRead(sleepPermission, "sleepHours", 0.0) { readSleepLastNight() },
                sleepQualityScore = optionalDashboardRead<Int?>(sleepPermission, "sleepQualityScore", null) { readSleepQualityScoreLastNight() },
                heartRateBpm = heartRateBpm,
                heartRateTodayBars = optionalDashboardRead(heartRatePermission, "heartRateTodayBars", emptyList()) { readHeartRateTodayBars() },
                stressScore = optionalDashboardRead<Int?>(hrvPermission, "stressScore", null) { readStressScoreToday() },
                spo2Percent = optionalDashboardRead<Double?>(spo2Permission, "spo2Percent", null) { readLatestSpo2Percent() },
                stepsBars = readStepsBars(daysBack),
                sleepBars = optionalDashboardRead(sleepPermission, "sleepBars", emptyList()) { readSleepBars(daysBack) },
                heartRateBars = optionalDashboardRead(heartRatePermission, "heartRateBars", emptyList()) { readHeartRateBars(daysBack) },
                recentWorkouts = readRecentWorkouts(5),
                workoutSummaries = readWorkoutSummariesByType(daysBack)
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readDashboardSnapshot failed; preserving previous UI snapshot: ${e.message}", e)
            null
        }
    }

'''
g = replace_between(g, "    // ── Read methods for Dashboard", "    suspend fun readStepsToday", replacement)
write(google_path, g)

# 4) Huawei Health: make approved scope contract explicit and immutable in code.
huawei_path = "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"
h = read(huawei_path)
old_scopes = '''    private val scopes = arrayOf(
        Scopes.HEALTHKIT_STEP_READ,
        Scopes.HEALTHKIT_DISTANCE_READ,
        Scopes.HEALTHKIT_ACTIVITY_READ,
        Scopes.HEALTHKIT_ACTIVITY_RECORD_READ,
        Scopes.HEALTHKIT_HISTORYDATA_OPEN_WEEK
    )

    fun requestedScopeNames(): String =
        "HEALTHKIT_STEP_READ, HEALTHKIT_DISTANCE_READ, HEALTHKIT_ACTIVITY_READ, HEALTHKIT_ACTIVITY_RECORD_READ, HEALTHKIT_HISTORYDATA_OPEN_WEEK"
'''
new_scopes = '''    /**
     * Huawei AppGallery approval-requested Health Kit scope set.
     *
     * Keep this READ-only and activity/basic-sport only until Huawei approves a new
     * scope request. Do not add sleep, heart rate, SpO2, HRV, body or profile scopes
     * here; those are optional Google Health Connect dashboard reads, not Huawei sync
     * dependencies.
     */
    private val scopes = arrayOf(
        Scopes.HEALTHKIT_STEP_READ,
        Scopes.HEALTHKIT_DISTANCE_READ,
        Scopes.HEALTHKIT_ACTIVITY_READ,
        Scopes.HEALTHKIT_ACTIVITY_RECORD_READ,
        Scopes.HEALTHKIT_HISTORYDATA_OPEN_WEEK
    )

    private val approvedScopeLabels = listOf(
        "Basic Sport Health Data (read)",
        "Step",
        "Distance, ascent & altitude",
        "Active Hours",
        "Daily Activity Summary",
        "Activity record",
        "Activity"
    )

    fun requestedScopeNames(): String = scopes.joinToString(", ")

    fun approvedScopeSummary(): String = approvedScopeLabels.joinToString(", ")
'''
if old_scopes in h:
    h = h.replace(old_scopes, new_scopes)
elif "approvedScopeSummary" in h:
    print("Huawei approved scope block already patched")
else:
    raise SystemExit("Huawei scope block not found; refusing blind patch")
h = h.replace(
    'AppLogger.i(TAG, "Requesting Huawei Health Kit authorization via SettingController: ${requestedScopeNames()}")',
    'AppLogger.i(TAG, "Requesting Huawei Health Kit authorization via SettingController: ${requestedScopeNames()} (${approvedScopeSummary()})")'
)
h = h.replace(
    'AppLogger.i(TAG, "Requesting Huawei ID Health Kit authorization: ${requestedScopeNames()}")',
    'AppLogger.i(TAG, "Requesting Huawei ID Health Kit authorization: ${requestedScopeNames()} (${approvedScopeSummary()})")'
)
write(huawei_path, h)

# 5) Verification script for this sprint.
write("scripts/verify_huawei_activity_sync_sprint.py", r'''#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path('.')
errors = []

def text(path):
    p = root / path
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding='utf-8')

policy = text('app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt')
huawei = text('app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt')
google = text('app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt')
main = text('app/src/main/java/com/openhealth/sync/MainActivity.kt')
manifest = text('app/src/main/AndroidManifest.xml')
requester = text('app/src/main/java/com/openhealth/sync/config/GoogleHealthPermissionRequester.kt')
worker = text('app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt')

# Huawei scope guardrails.
required_huawei = [
    'Scopes.HEALTHKIT_STEP_READ',
    'Scopes.HEALTHKIT_DISTANCE_READ',
    'Scopes.HEALTHKIT_ACTIVITY_READ',
    'Scopes.HEALTHKIT_ACTIVITY_RECORD_READ',
    'Scopes.HEALTHKIT_HISTORYDATA_OPEN_WEEK',
]
for token in required_huawei:
    if token not in huawei:
        errors.append(f'HuaweiHealthManager missing approved scope {token}')
for forbidden in ['HEALTHKIT_HEARTRATE', 'HEALTHKIT_SLEEP', 'HEALTHKIT_OXYGEN', 'HEALTHKIT_STRESS', 'HEALTHKIT_BODY']:
    if forbidden in huawei.upper():
        errors.append(f'HuaweiHealthManager must not request non-approved Huawei scope matching {forbidden}')
if 'approvedScopeSummary' not in huawei:
    errors.append('HuaweiHealthManager must expose approvedScopeSummary for auditability')
if 'requestAuthorizationIntent(scopes, true)' not in huawei:
    errors.append('Huawei connect button must open Huawei permission window through SettingController')

# Health Connect permission split.
for token in ['huaweiImportReadPermissions', 'importWritePermissions', 'optionalDashboardReadPermissions', 'syncPermissions', 'requestPermissions']:
    if token not in policy:
        errors.append(f'HealthPermissionPolicy missing {token}')
if 'val syncPermissions: Set<String> = huaweiImportReadPermissions + importWritePermissions' not in policy:
    errors.append('syncPermissions must be exactly required Huawei-derived activity read/write permissions')
if 'val requestPermissions: Set<String> = syncPermissions + optionalDashboardReadPermissions' not in policy:
    errors.append('UI permission request must include optional dashboard permissions without making them sync blockers')
for forbidden in ['getWritePermission(SleepSessionRecord::class)', 'getWritePermission(HeartRateRecord::class)', 'getWritePermission(OxygenSaturationRecord::class)', 'getWritePermission(HeartRateVariabilityRmssdRecord::class)']:
    if forbidden in policy:
        errors.append(f'Policy must not request optional dashboard write permission: {forbidden}')

# Manifest guardrails.
for required in [
    'READ_STEPS', 'WRITE_STEPS', 'READ_DISTANCE', 'WRITE_DISTANCE',
    'READ_FLOORS_CLIMBED', 'WRITE_FLOORS_CLIMBED',
    'READ_ELEVATION_GAINED', 'WRITE_ELEVATION_GAINED',
    'READ_ACTIVE_CALORIES_BURNED', 'WRITE_ACTIVE_CALORIES_BURNED',
    'READ_EXERCISE', 'WRITE_EXERCISE',
    'READ_SLEEP', 'READ_HEART_RATE', 'READ_OXYGEN_SATURATION', 'READ_HEART_RATE_VARIABILITY'
]:
    if required not in manifest:
        errors.append(f'AndroidManifest missing Health Connect permission {required}')
for forbidden in ['WRITE_SLEEP', 'WRITE_HEART_RATE', 'WRITE_OXYGEN_SATURATION', 'WRITE_HEART_RATE_VARIABILITY', 'READ_ACTIVITY_INTENSITY', 'WRITE_ACTIVITY_INTENSITY']:
    if forbidden in manifest:
        errors.append(f'AndroidManifest contains unsupported/non-MVP permission {forbidden}')

# Google sync writer: idempotent export into Health Connect.
if 'Metadata(' not in google or 'clientRecordId = generateRecordId' not in google:
    errors.append('GoogleHealthManager must assign stable Metadata.clientRecordId')
if 'deleteRecords(' not in google or 'clientRecordIdsList = clientRecordIds' not in google or 'insertRecords(chunk)' not in google:
    errors.append('GoogleHealthManager must replace old BitLut records by clientRecordId before insert')
for record in ['StepsRecord', 'DistanceRecord', 'FloorsClimbedRecord', 'ElevationGainedRecord', 'ActiveCaloriesBurnedRecord', 'ExerciseSessionRecord']:
    if record not in google:
        errors.append(f'GoogleHealthManager missing writer for {record}')

# Dashboard stability.
if google.count('suspend fun readDashboardSnapshot') != 1:
    errors.append('GoogleHealthManager must contain exactly one readDashboardSnapshot implementation')
for token in ['optionalDashboardRead', 'readDashboardSnapshot failed; preserving previous UI snapshot', 'stepsBars = readStepsBars(daysBack)']:
    if token not in google:
        errors.append(f'Dashboard stability guardrail missing {token}')
if 'hasAllPermissions' not in google or 'granted.containsAll(requiredPermissions())' not in google:
    errors.append('Health Connect sync preflight must check required sync permissions only')
if 'val permissions: Set<String> = HealthPermissionPolicy.requestPermissions' not in google:
    errors.append('Google connect button must request required + optional dashboard permissions')

# Buttons open permission windows.
if 'launcher.launch(googleManager.permissions)' not in requester:
    errors.append('Google Health connect action must launch the Health Connect permission sheet')
if 'requestGoogleHealthPermissions()' not in main or 'onRequestGoogle = { requestGoogleHealthPermissions() }' not in main:
    errors.append('MainActivity must wire Google connect button to permission request')
if 'huaweiAuthorizationLauncher.launch(syncViewModel.huaweiHealthManager.getAuthorizationIntent())' not in main:
    errors.append('MainActivity must wire Huawei connect button to Huawei authorization intent')
if 'missingRequiredPermissions()' not in main:
    errors.append('Manual sync must open Health Connect permission flow when required sync permissions are missing')

# Worker imports real Huawei data only and exports only after successful read.
for token in ['readSnapshot(window.startTimeMs, window.endTimeMs)', 'writeSnapshot(snapshot)', 'putLong(HuaweiConfig.KEY_LAST_SYNC_MS, window.endTimeMs)', 'preserving last_sync_ms']:
    if token not in worker:
        errors.append(f'SyncWorker missing production sync guardrail: {token}')

if errors:
    print('Huawei activity sync sprint verification failed:')
    for error in errors:
        print(' -', error)
    sys.exit(1)
print('Huawei activity sync sprint verification passed.')
''')

print("\nPatch complete. Run:")
print("python3 scripts/verify_huawei_activity_sync_sprint.py")
print("python3 scripts/verify_sync_reliability.py")
print("./gradlew :app:assembleDebug")
