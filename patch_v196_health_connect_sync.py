#!/usr/bin/env python3
from pathlib import Path

root = Path.cwd()


def read(path: str) -> str:
    return (root / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    if old not in content:
        raise SystemExit(f"Patch anchor not found in {path}: {old[:120]!r}")
    write(path, content.replace(old, new, 1))


# 1) Split required sync permissions from optional dashboard reads.
write(
    "app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt",
    """package com.openhealth.sync.config

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
 * Single source of truth for Health Connect permissions.
 *
 * Sync correctness rule:
 * - syncPermissions contains only the records BitLut must read/write for the
 *   Huawei -> Health Connect bridge.
 * - optionalDashboardReadPermissions are requested for a richer dashboard, but they
 *   must never block manual/background sync when a device/provider does not expose
 *   those categories or the user leaves them disabled.
 *
 * Activity Intensity is intentionally not requested until the project upgrades to a
 * Health Connect client version that supports it reliably.
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

    /** Required for Huawei -> Health Connect sync and for core dashboard data. */
    val syncPermissions: Set<String> = huaweiImportReadPermissions + importWritePermissions

    /** The UI asks for the full useful set, but sync preflight checks syncPermissions only. */
    val requestPermissions: Set<String> = syncPermissions + optionalDashboardReadPermissions

    val dashboardReadPermissions: Set<String> = huaweiImportReadPermissions + optionalDashboardReadPermissions

    // Backward-compatible aliases used by older screens/managers.
    val dashboardPermissions: Set<String> = requestPermissions
    val importPermissions: Set<String> = syncPermissions
    val allPermissions: Set<String> = requestPermissions
}
""",
)

# 2) Manifest: declare only permissions the app actually requests/uses.
manifest_path = "app/src/main/AndroidManifest.xml"
manifest = read(manifest_path)
for forbidden_line in [
    '    <uses-permission android:name="android.permission.health.WRITE_SLEEP" />\n',
    '        <uses-permission android:name="android.permission.health.READ_ACTIVITY_INTENSITY" />\n',
    '    <uses-permission android:name="android.permission.health.WRITE_ACTIVITY_INTENSITY" />\n',
    '    <uses-permission android:name="android.permission.health.WRITE_HEART_RATE" />\n',
]:
    manifest = manifest.replace(forbidden_line, "")
if "READ_OXYGEN_SATURATION" not in manifest:
    manifest = manifest.replace(
        '    <uses-permission android:name="android.permission.health.READ_SLEEP" />\n',
        '    <uses-permission android:name="android.permission.health.READ_SLEEP" />\n'
        '    <uses-permission android:name="android.permission.health.READ_OXYGEN_SATURATION" />\n'
        '    <uses-permission android:name="android.permission.health.READ_HEART_RATE_VARIABILITY" />\n',
        1,
    )
manifest = manifest.replace("\n<application", "\n\n<application")
write(manifest_path, manifest)

# 3) MainActivity: optional dashboard permissions must not show sync-blocking error.
replace_once(
    "app/src/main/java/com/openhealth/sync/MainActivity.kt",
    """        if (!granted.containsAll(syncViewModel.googleManager.permissions)) {
            Toast.makeText(this, getString(R.string.toast_hc_permissions), Toast.LENGTH_LONG).show()
        }
""",
    """        if (!granted.containsAll(syncViewModel.googleManager.requiredPermissions())) {
            Toast.makeText(this, getString(R.string.toast_hc_permissions), Toast.LENGTH_LONG).show()
        }
""",
)

# 4) GoogleHealthManager: idempotent replace-by-clientRecordId writes and optional dashboard reads.
ghm_path = "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
ghm = read(ghm_path)
if "import kotlin.reflect.KClass" not in ghm:
    ghm = ghm.replace(
        "import kotlinx.coroutines.CancellationException\n",
        "import kotlinx.coroutines.CancellationException\nimport kotlin.reflect.KClass\n",
        1,
    )
if "private const val WRITE_BATCH_SIZE" not in ghm:
    ghm = ghm.replace(
        'private const val TAG = "GoogleHealthManager"\n',
        'private const val TAG = "GoogleHealthManager"\nprivate const val WRITE_BATCH_SIZE = 400\n',
        1,
    )
old_permissions_block = """    fun requiredPermissions(): Set<String> = HealthPermissionPolicy.syncPermissions


    // permissions is the single set actually requested via the UI permission launcher
    // AND checked by hasAllPermissions() before SyncWorker attempts to write Huawei
    // data into Health Connect. It is the read+write superset
    // (HealthPermissionPolicy.syncPermissions) -- using a narrower read-only set here
    // was the root cause behind a whole series of permission gaps (Sleep, HeartRate,
    // Distance, Calories were each missing read access at different points), and more
    // importantly meant the Huawei->Health Connect write path could never succeed:
    // SyncWorker checks hasAllPermissions() before writeSnapshot(), but the UI never
    // requested write permissions at all.
    val permissions: Set<String> = HealthPermissionPolicy.requestPermissions
"""
new_permissions_block = """    fun requiredPermissions(): Set<String> = HealthPermissionPolicy.syncPermissions

    // The UI may request optional dashboard reads, but sync correctness depends only
    // on requiredPermissions(). Never use this broader request set for sync preflight.
    val permissions: Set<String> = HealthPermissionPolicy.requestPermissions
"""
if old_permissions_block not in ghm:
    raise SystemExit("Patch anchor not found in GoogleHealthManager permission block")
ghm = ghm.replace(old_permissions_block, new_permissions_block, 1)
old_missing_required = """    suspend fun missingRequiredPermissions(): Set<String> {
        val c = healthConnectClient ?: return requiredPermissions()
        return try {
            val granted = c.permissionController.getGrantedPermissions()
            requiredPermissions() - granted
        } catch (e: Exception) {
            AppLogger.e(TAG, "Missing permission check failed: ${e.message}", e)
            requiredPermissions()
        }
    }
"""
new_missing_required = """    private suspend fun grantedPermissionsOrEmpty(): Set<String> {
        val c = healthConnectClient ?: return emptySet()
        return try {
            c.permissionController.getGrantedPermissions()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Permission snapshot failed: ${e.message}", e)
            emptySet()
        }
    }

    private suspend fun isPermissionGranted(permission: String): Boolean =
        grantedPermissionsOrEmpty().contains(permission)

    suspend fun missingRequiredPermissions(): Set<String> {
        val c = healthConnectClient ?: return requiredPermissions()
        return try {
            val granted = c.permissionController.getGrantedPermissions()
            requiredPermissions() - granted
        } catch (e: Exception) {
            AppLogger.e(TAG, "Missing permission check failed: ${e.message}", e)
            requiredPermissions()
        }
    }
"""
if old_missing_required not in ghm:
    raise SystemExit("Patch anchor not found in GoogleHealthManager missingRequiredPermissions")
ghm = ghm.replace(old_missing_required, new_missing_required, 1)
for old, new in [
    ('return insertRecords("steps", valid)', 'return replaceRecords("steps", valid, StepsRecord::class)'),
    ('return insertRecords("distance", valid)', 'return replaceRecords("distance", valid, DistanceRecord::class)'),
    ('return insertRecords("floors", valid)', 'return replaceRecords("floors", valid, FloorsClimbedRecord::class)'),
    ('return insertRecords("elevation", valid)', 'return replaceRecords("elevation", valid, ElevationGainedRecord::class)'),
    ('return insertRecords("activeCalories", valid)', 'return replaceRecords("activeCalories", valid, ActiveCaloriesBurnedRecord::class)'),
    ('return insertRecords("activitySessions", valid)', 'return replaceRecords("activitySessions", valid, ExerciseSessionRecord::class)'),
]:
    if old not in ghm:
        raise SystemExit(f"Patch anchor not found in GoogleHealthManager write call: {old}")
    ghm = ghm.replace(old, new, 1)
old_insert = """    private suspend fun insertRecords(label: String, records: List<androidx.health.connect.client.records.Record>): Boolean {
        val c = healthConnectClient ?: run {
            AppLogger.e(TAG, "write $label: no client")
            return false
        }

        if (records.isEmpty()) {
            AppLogger.i(TAG, "No $label records to write")
            return true
        }

        return try {
            c.insertRecords(records)
            AppLogger.i(TAG, "Wrote ${records.size} $label records")
            true
        } catch (e: Exception) {
            AppLogger.e(TAG, "write $label failed: ${e.message}", e)
            false
        }
    }
"""
new_insert = """    private suspend fun replaceRecords(
        label: String,
        records: List<androidx.health.connect.client.records.Record>,
        recordType: KClass<out androidx.health.connect.client.records.Record>
    ): Boolean {
        val c = healthConnectClient ?: run {
            AppLogger.e(TAG, "write $label: no client")
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
                    c.deleteRecords(
                        recordType = recordType,
                        recordIdsList = emptyList(),
                        clientRecordIdsList = clientRecordIds
                    )
                }
                c.insertRecords(chunk)
            }
            AppLogger.i(TAG, "Replaced ${records.size} $label records")
            true
        } catch (e: CancellationException) {
            throw e
        } catch (e: SecurityException) {
            AppLogger.e(TAG, "write $label denied by Health Connect permission policy: ${e.message}", e)
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "write $label failed: ${e.message}", e)
            false
        }
    }
"""
if old_insert not in ghm:
    raise SystemExit("Patch anchor not found in GoogleHealthManager insertRecords")
ghm = ghm.replace(old_insert, new_insert, 1)
old_hr = """            val heartRateBpm = c.aggregate(
                AggregateRequest(
                    metrics = setOf(HeartRateRecord.BPM_AVG),
                    timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                )
            )[HeartRateRecord.BPM_AVG]

            GoogleDashboardSnapshot(
"""
new_hr = """            val granted = c.permissionController.getGrantedPermissions()
            val canReadHeartRate = granted.contains(HealthPermission.getReadPermission(HeartRateRecord::class))

            val heartRateBpm = if (canReadHeartRate) {
                try {
                    c.aggregate(
                        AggregateRequest(
                            metrics = setOf(HeartRateRecord.BPM_AVG),
                            timeRangeFilter = TimeRangeFilter.between(startOfToday, now)
                        )
                    )[HeartRateRecord.BPM_AVG]
                } catch (e: Exception) {
                    AppLogger.w(TAG, "Optional heart-rate aggregate skipped: ${e.message}")
                    null
                }
            } else {
                null
            }

            GoogleDashboardSnapshot(
"""
if old_hr not in ghm:
    raise SystemExit("Patch anchor not found in GoogleHealthManager heart-rate aggregate")
ghm = ghm.replace(old_hr, new_hr, 1)
for old, new in [
    (
        """    suspend fun readHeartRateTodayBars(): List<MetricBar> {
        val c = healthConnectClient ?: return emptyList()
        val today = LocalDate.now()
""",
        """    suspend fun readHeartRateTodayBars(): List<MetricBar> {
        if (!isPermissionGranted(HealthPermission.getReadPermission(HeartRateRecord::class))) return emptyList()
        val c = healthConnectClient ?: return emptyList()
        val today = LocalDate.now()
""",
    ),
    (
        """    suspend fun readLatestSpo2Percent(): Double? {
        val c = healthConnectClient ?: return null
        return try {
""",
        """    suspend fun readLatestSpo2Percent(): Double? {
        if (!isPermissionGranted(HealthPermission.getReadPermission(OxygenSaturationRecord::class))) return null
        val c = healthConnectClient ?: return null
        return try {
""",
    ),
    (
        """    suspend fun readStressScoreToday(): Int? {
        val c = healthConnectClient ?: return null
        return try {
""",
        """    suspend fun readStressScoreToday(): Int? {
        if (!isPermissionGranted(HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class))) return null
        val c = healthConnectClient ?: return null
        return try {
""",
    ),
    (
        """    suspend fun readSleepLastNight(): Double {
        val c = healthConnectClient ?: return 0.0
        return try {
""",
        """    suspend fun readSleepLastNight(): Double {
        if (!isPermissionGranted(HealthPermission.getReadPermission(SleepSessionRecord::class))) return 0.0
        val c = healthConnectClient ?: return 0.0
        return try {
""",
    ),
    (
        """    suspend fun readAverageHeartRateToday(): Long? {
        val c = healthConnectClient ?: return null
        return try {
""",
        """    suspend fun readAverageHeartRateToday(): Long? {
        if (!isPermissionGranted(HealthPermission.getReadPermission(HeartRateRecord::class))) return null
        val c = healthConnectClient ?: return null
        return try {
""",
    ),
    (
        """    suspend fun readSleepBars(daysBack: Int): List<MetricBar> {
        val c = healthConnectClient ?: return emptyList()
        val ranges = computeMetricBarRanges(daysBack)
""",
        """    suspend fun readSleepBars(daysBack: Int): List<MetricBar> {
        if (!isPermissionGranted(HealthPermission.getReadPermission(SleepSessionRecord::class))) return emptyList()
        val c = healthConnectClient ?: return emptyList()
        val ranges = computeMetricBarRanges(daysBack)
""",
    ),
    (
        """    suspend fun readHeartRateBars(daysBack: Int): List<MetricBar> {
        val c = healthConnectClient ?: return emptyList()
        val ranges = computeMetricBarRanges(daysBack)
""",
        """    suspend fun readHeartRateBars(daysBack: Int): List<MetricBar> {
        if (!isPermissionGranted(HealthPermission.getReadPermission(HeartRateRecord::class))) return emptyList()
        val c = healthConnectClient ?: return emptyList()
        val ranges = computeMetricBarRanges(daysBack)
""",
    ),
]:
    if old not in ghm:
        raise SystemExit(f"Patch anchor not found in GoogleHealthManager optional read: {old[:90]!r}")
    ghm = ghm.replace(old, new, 1)
write(ghm_path, ghm)

# 5) Static verification: update regression checks to match the intended v1.9.6 behavior.
verify_path = "scripts/verify_sync_reliability.py"
verify = read(verify_path)
old_policy_checks = """    if "val syncPermissions: Set<String> = dashboardReadPermissions + importWritePermissions" not in p:
        errors.append("syncPermissions must exclude optional dashboard-only permissions")
    if "val optionalDashboardReadPermissions: Set<String> = emptySet()" not in p:
        errors.append("Optional dashboard permissions must stay disabled until Huawei/Health Connect scope expansion is approved")
    if "val requestPermissions: Set<String> = syncPermissions" not in p:
        errors.append("UI permission request must not expand beyond approved sync permissions")
"""
new_policy_checks = """    if "val syncPermissions: Set<String> = huaweiImportReadPermissions + importWritePermissions" not in p:
        errors.append("syncPermissions must include only required Huawei import read/write permissions")
    if "val optionalDashboardReadPermissions: Set<String> = setOf(" not in p:
        errors.append("HealthPermissionPolicy must define optional dashboard read permissions")
    if "val requestPermissions: Set<String> = syncPermissions + optionalDashboardReadPermissions" not in p:
        errors.append("UI permission request should include optional dashboard permissions without blocking sync")
    if "HealthPermission.getWritePermission(SleepSessionRecord::class)" in p or "HealthPermission.getWritePermission(HeartRateRecord::class)" in p:
        errors.append("Huawei import write permissions must not request Sleep/HeartRate writes")
"""
if old_policy_checks not in verify:
    raise SystemExit("Patch anchor not found in verify_sync_reliability.py policy checks")
verify = verify.replace(old_policy_checks, new_policy_checks, 1)
old_google_checks = """    if "val permissions: Set<String> = HealthPermissionPolicy.requestPermissions" not in g:
        errors.append("GoogleHealthManager.permissions must request sync + optional dashboard permissions")
    if "granted.containsAll(requiredPermissions())" not in g:
        errors.append("hasAllPermissions must check only required sync permissions")
    if "missingRequiredPermissions" not in g:
        errors.append("GoogleHealthManager must expose missingRequiredPermissions() for sync preflight")
"""
new_google_checks = """    if "val permissions: Set<String> = HealthPermissionPolicy.requestPermissions" not in g:
        errors.append("GoogleHealthManager.permissions must request sync + optional dashboard permissions")
    if "granted.containsAll(requiredPermissions())" not in g:
        errors.append("hasAllPermissions must check only required sync permissions")
    if "missingRequiredPermissions" not in g:
        errors.append("GoogleHealthManager must expose missingRequiredPermissions() for sync preflight")
    if "replaceRecords(" not in g or "deleteRecords(" not in g or "clientRecordIdsList" not in g:
        errors.append("GoogleHealthManager must replace existing BitLut records by stable clientRecordId before insert")
    if "Optional heart-rate aggregate skipped" not in g:
        errors.append("Optional dashboard reads must not poison the whole dashboard snapshot")
"""
if old_google_checks not in verify:
    raise SystemExit("Patch anchor not found in verify_sync_reliability.py google checks")
verify = verify.replace(old_google_checks, new_google_checks, 1)
old_main_checks = """    if "missingRequiredPermissions()" not in m or "requestGoogleHealthPermissions()" not in m:
        errors.append("Sync Now must launch Health Connect permission request when required permissions are missing")
"""
new_main_checks = """    if "missingRequiredPermissions()" not in m or "requestGoogleHealthPermissions()" not in m:
        errors.append("Sync Now must launch Health Connect permission request when required permissions are missing")
    if "granted.containsAll(syncViewModel.googleManager.requiredPermissions())" not in m:
        errors.append("Permission callback must not treat optional dashboard permissions as sync blockers")

manifest_file = root / "app/src/main/AndroidManifest.xml"
if manifest_file.exists():
    manifest = manifest_file.read_text(encoding="utf-8")
    for forbidden in ["WRITE_SLEEP", "WRITE_HEART_RATE", "READ_ACTIVITY_INTENSITY", "WRITE_ACTIVITY_INTENSITY"]:
        if forbidden in manifest:
            errors.append(f"AndroidManifest must not declare unsupported/non-sync Health Connect permission: {forbidden}")
    for required_optional in ["READ_OXYGEN_SATURATION", "READ_HEART_RATE_VARIABILITY"]:
        if required_optional not in manifest:
            errors.append(f"AndroidManifest missing optional dashboard permission declaration: {required_optional}")
"""
if old_main_checks not in verify:
    raise SystemExit("Patch anchor not found in verify_sync_reliability.py main checks")
verify = verify.replace(old_main_checks, new_main_checks, 1)
write(verify_path, verify)

print("BitLut v1.9.6 Health Connect sync patch applied.")
