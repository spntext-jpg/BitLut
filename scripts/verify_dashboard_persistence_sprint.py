#!/usr/bin/env python3
"""
Verifies the v1.9.10 dashboard persistence and force-refresh sprint:

1. DashboardSnapshotCache exists and is SharedPreferences-backed (no Room/DataStore
   dependency added).
2. DashboardViewModel loads the cache synchronously on init and distinguishes
   "still loading" from "permissions confirmed missing" via showConnectLockScreen.
3. SyncWorker refreshes the dashboard cache after a successful background write,
   so the periodic 30-minute sync keeps cold-start data fresh.
4. MainActivity wires DashboardSnapshotCache into the DashboardViewModel factory.
5. The Settings "refresh status" button for Google Health now triggers a real
   sync (onSyncNow) instead of a no-op status-only refresh.
6. No regression of existing activity-only scope / no-fake-data guarantees.
"""
from pathlib import Path
import sys

errors = []


def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        errors.append(message)


cache = read("app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt")
dashboard_vm = read("app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt")
sync_worker = read("app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt")
main_activity = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
scheduler = read("app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt")

# 1. DashboardSnapshotCache
require("class DashboardSnapshotCache" in cache, "DashboardSnapshotCache class is missing")
require("HuaweiConfig.PREFS_NAME" in cache, "DashboardSnapshotCache must reuse the existing SharedPreferences file")
require("fun save(snapshot: GoogleDashboardSnapshot)" in cache, "DashboardSnapshotCache.save() is missing")
require("fun load(): CachedSnapshot?" in cache, "DashboardSnapshotCache.load() is missing")
require(
    "import androidx.room" not in cache and "import androidx.datastore" not in cache,
    "Cache must not introduce Room/DataStore (keep dependency footprint minimal)"
)

# 2. DashboardViewModel
require("DashboardSnapshotCache" in dashboard_vm, "DashboardViewModel must depend on DashboardSnapshotCache")
require("buildInitialState" in dashboard_vm, "DashboardViewModel must build its initial state from the cache synchronously")
require("snapshotCache.load()" in dashboard_vm, "DashboardViewModel must read the cache on init")
require("snapshotCache.save(snapshot)" in dashboard_vm, "DashboardViewModel must persist fresh snapshots to the cache")
require("showConnectLockScreen" in dashboard_vm, "DashboardUiState must expose showConnectLockScreen")
require("permissionsChecked" in dashboard_vm, "DashboardUiState must track whether permissions were actually checked yet")
require(
    "_state.update { it.copy(isLoading = false) }" in dashboard_vm,
    "load() must not silently fall through without resolving isLoading on a permission-check failure"
)

# 3. SyncWorker keeps the cache warm in the background
require("DashboardSnapshotCache" in sync_worker, "SyncWorker must refresh DashboardSnapshotCache after a successful write")
require("snapshotCache.save(freshSnapshot)" in sync_worker, "SyncWorker must persist a fresh snapshot after writing to Health Connect")
require(
    "refreshDashboardCacheAfterWrite" in sync_worker,
    "SyncWorker must call a dedicated, best-effort cache refresh step after a successful sync"
)

# 4. MainActivity wiring
require("DashboardSnapshotCache(applicationContext)" in main_activity, "MainActivity must construct DashboardSnapshotCache for the DashboardViewModel factory")

# 5. Settings force-refresh button
require(
    "onSecondaryAction = onSyncNow" in shell,
    "Google Health 'refresh status' button in Settings must trigger a real sync (onSyncNow), not a no-op refresh"
)
require("showConnectLockScreen" in shell, "FinalBitLutShell must use showConnectLockScreen instead of raw !hasPermissions")
require("DashboardLoadingCard" in shell, "FinalBitLutShell must show a neutral loading state before the lock screen on first-ever launch")

# 6. No regressions: periodic 30-minute background sync must remain untouched
require("SYNC_INTERVAL_MINUTES = 30L" in scheduler, "Background sync interval must remain 30 minutes")
require("ExistingPeriodicWorkPolicy.UPDATE" in scheduler, "Periodic sync must keep using UPDATE policy to avoid duplicate scheduling")

# 6b. No fake/placeholder data introduced anywhere touched by this sprint
for label, src in [
    ("DashboardSnapshotCache.kt", cache),
    ("DashboardViewModel.kt", dashboard_vm),
    ("SyncWorker.kt", sync_worker),
]:
    require("fakeData" not in src and "FAKE_DATA" not in src, f"{label} must not introduce fake/placeholder data")

if errors:
    print("Dashboard persistence sprint verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Dashboard persistence sprint verification passed.")
