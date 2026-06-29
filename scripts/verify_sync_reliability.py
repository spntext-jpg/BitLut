#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(".")
google = root / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
huawei = root / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"
dashboard_vm = root / "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt"
sync_worker = root / "app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt"
background_scheduler = root / "app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt"
sync_reliability = root / "app/src/main/java/com/openhealth/sync/data/worker/SyncReliability.kt"
main_activity = root / "app/src/main/java/com/openhealth/sync/MainActivity.kt"

errors = []

g = google.read_text(encoding="utf-8")

if "HealthPermissionPolicy.syncPermissions" not in g:
    errors.append("GoogleHealthManager.permissions must use HealthPermissionPolicy.syncPermissions")

if "clientRecordId" not in g or "generateRecordId" not in g:
    errors.append("GoogleHealthManager must assign stable Metadata.clientRecordId for dedupe/upsert safety")

record_types = [
    "StepsRecord",
    "DistanceRecord",
    "FloorsClimbedRecord",
    "ElevationGainedRecord",
    "ActiveCaloriesBurnedRecord",
    "ExerciseSessionRecord",
]

def find_call_end(text: str, open_paren: int) -> int:
    depth = 0
    i = open_paren
    in_string = False
    escape = False
    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1

for record in record_types:
    pos = 0
    while True:
        idx = g.find(record + "(", pos)
        if idx == -1:
            break
        end = find_call_end(g, idx + len(record))
        if end == -1:
            errors.append(f"Could not parse {record} constructor")
            break
        block = g[idx:end + 1]
        if "metadata" not in block or "bitlutMetadata" not in block:
            errors.append(f"{record} constructor missing bitlutMetadata(...)")
        pos = end + 1

if "readDashboardSnapshot" not in g or "GoogleDashboardSnapshot" not in g:
    errors.append("GoogleHealthManager must expose readDashboardSnapshot() with nullable stale-on-failure semantics")

if "readDashboardSnapshot failed; preserving previous UI snapshot" not in g:
    errors.append("Dashboard Health Connect read failures must be logged and surfaced as null, not zeros")

if "writeSnapshot" in g:
    m = re.search(r"suspend\s+fun\s+writeSnapshot\s*\([^)]*\)\s*:\s*Boolean\s*\{(.*?)\n\s*\}", g, re.S)
    if m and "&&" in m.group(1):
        errors.append("writeSnapshot should not be a chained && expression; isolate category writes")

if dashboard_vm.exists():
    d = dashboard_vm.read_text(encoding="utf-8")
    if "loadJob?.cancel()" not in d or "loadGeneration" not in d:
        errors.append("DashboardViewModel must cancel/sequence overlapping refresh jobs")
    if "snapshot == null" not in d or "current.copy(isLoading = false, hasPermissions = true)" not in d:
        errors.append("DashboardViewModel must preserve previous data when Health Connect snapshot read fails")
    if "withSnapshot" not in d or ".ifEmpty {" not in d:
        errors.append("DashboardViewModel must not replace existing history lists with transient empty results")

if huawei.exists():
    h = huawei.read_text(encoding="utf-8")
    if "MAX_LOOKBACK_MS" in h and "readChunk" not in h and "chunk" not in h.lower():
        print("Warning: Huawei read chunking guardrail not yet detected. Add daily chunking in P1.")


# Background sync reliability guardrails.
if background_scheduler.exists():
    bs = background_scheduler.read_text(encoding="utf-8")
    if "SYNC_INTERVAL_MINUTES = 30L" not in bs:
        errors.append("BackgroundSyncScheduler must request a 30-minute periodic cadence")
    if "PeriodicWorkRequestBuilder<SyncWorker>" not in bs:
        errors.append("BackgroundSyncScheduler must use native WorkManager periodic work")
    if "BackoffPolicy.EXPONENTIAL" not in bs:
        errors.append("BackgroundSyncScheduler must configure exponential WorkManager backoff")
    if "ExistingPeriodicWorkPolicy.UPDATE" not in bs:
        errors.append("Periodic sync must be unique and updateable")
else:
    errors.append("Missing BackgroundSyncScheduler.kt")

if sync_reliability.exists():
    sr = sync_reliability.read_text(encoding="utf-8")
    for token in ["SyncCircuitBreaker", "SyncRunLease", "SyncRetryPolicy", "SyncWindowPlanner", "OVERLAP_MS"]:
        if token not in sr:
            errors.append(f"SyncReliability.kt missing {token}")
else:
    errors.append("Missing SyncReliability.kt")

if sync_worker.exists():
    sw = sync_worker.read_text(encoding="utf-8")
    for token in ["withTimeout", "executeWithRetries", "tryAcquire", "circuitBreaker", "GracefulNoop", "RetryableFailure"]:
        if token not in sw:
            errors.append(f"SyncWorker missing reliability primitive: {token}")
    if "putLong(HuaweiConfig.KEY_LAST_SYNC_MS, window.endTimeMs)" not in sw:
        errors.append("SyncWorker must advance last_sync_ms only after successful Health Connect write")
    if "preserving last_sync_ms" not in sw:
        errors.append("SyncWorker must not advance last_sync_ms on empty Huawei snapshots")
else:
    errors.append("Missing SyncWorker.kt")

if main_activity.exists():
    ma = main_activity.read_text(encoding="utf-8")
    if "BackgroundSyncScheduler.schedulePeriodic(this)" not in ma:
        errors.append("MainActivity must delegate periodic scheduling to BackgroundSyncScheduler")
    if "BackgroundSyncScheduler.enqueueImmediateSync(this)" not in ma:
        errors.append("MainActivity must delegate immediate sync to BackgroundSyncScheduler")


# Permission regression guardrails for v1.9.6.
policy_file = root / "app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt"
google_file = root / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
main_file = root / "app/src/main/java/com/openhealth/sync/MainActivity.kt"

if policy_file.exists():
    p = policy_file.read_text(encoding="utf-8")
    if "optionalDashboardReadPermissions" not in p:
        errors.append("HealthPermissionPolicy must keep SpO2/HRV as optional dashboard permissions")
    if "val syncPermissions: Set<String> = dashboardReadPermissions + importWritePermissions" not in p:
        errors.append("syncPermissions must exclude optional dashboard-only permissions")
    if "val requestPermissions: Set<String> = syncPermissions + optionalDashboardReadPermissions" not in p:
        errors.append("UI permission request should include optional dashboard permissions without blocking sync")

if google_file.exists():
    g = google_file.read_text(encoding="utf-8")
    if "val permissions: Set<String> = HealthPermissionPolicy.requestPermissions" not in g:
        errors.append("GoogleHealthManager.permissions must request sync + optional dashboard permissions")
    if "granted.containsAll(requiredPermissions())" not in g:
        errors.append("hasAllPermissions must check only required sync permissions")
    if "missingRequiredPermissions" not in g:
        errors.append("GoogleHealthManager must expose missingRequiredPermissions() for sync preflight")

if main_file.exists():
    m = main_file.read_text(encoding="utf-8")
    if "missingRequiredPermissions()" not in m or "requestGoogleHealthPermissions()" not in m:
        errors.append("Sync Now must launch Health Connect permission request when required permissions are missing")

if errors:
    print("Sync reliability verification failed:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("Sync reliability verification passed.")
