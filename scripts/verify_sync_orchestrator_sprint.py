#!/usr/bin/env python3
from pathlib import Path
import sys

errors = []

def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

orchestrator = read("app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("class SyncOrchestrator(" in orchestrator, "SyncOrchestrator class missing")
require("private val googleManager: HealthConnectManager" in orchestrator, "Orchestrator must depend on HealthConnectManager interface")
require("fun schedulePeriodic()" in orchestrator, "Orchestrator must expose schedulePeriodic")
require("suspend fun triggerImmediateSync(" in orchestrator, "Orchestrator must expose triggerImmediateSync")
require("BackgroundSyncScheduler.schedulePeriodic(appContext)" in orchestrator, "Periodic scheduling must delegate to BackgroundSyncScheduler")
require("BackgroundSyncScheduler.enqueueImmediateSync(appContext)" in orchestrator, "Immediate sync must delegate to BackgroundSyncScheduler")
require("googleManager.missingRequiredPermissions()" in orchestrator, "Manual sync must preflight required Health Connect permissions")
require("WorkManager.getInstance(appContext)" in orchestrator, "Orchestrator must own WorkManager access")
require("getWorkInfoByIdLiveData(requestId).observe(lifecycleOwner)" in orchestrator, "Work observation must be lifecycle-owned")

require("private val syncOrchestrator: SyncOrchestrator by lazy" in main, "MainActivity must own SyncOrchestrator")
require("private fun setupPeriodicSync()" in main, "MainActivity missing setupPeriodicSync")
require("private fun triggerImmediateSync()" in main, "MainActivity missing triggerImmediateSync")
require("syncOrchestrator.schedulePeriodic()" in main, "setupPeriodicSync must delegate to orchestrator")
require("syncOrchestrator.triggerImmediateSync(" in main, "triggerImmediateSync must delegate to orchestrator")
require("requestGoogleHealthPermissions()" in main, "Missing permission flow must still open Health Connect request")

for forbidden in [
    "import androidx.work.WorkManager",
    "import androidx.work.WorkInfo",
    "import androidx.work.OneTimeWorkRequestBuilder",
    "import androidx.work.PeriodicWorkRequestBuilder",
    "import com.openhealth.sync.data.worker.BackgroundSyncScheduler",
    "BackgroundSyncScheduler",
    "WorkManager.getInstance",
    "WorkInfo.State",
    "getWorkInfoByIdLiveData",
]:
    require(forbidden not in main, f"MainActivity must not contain orchestration detail: {forbidden}")

if errors:
    print("Sync Orchestrator recovery verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Sync Orchestrator recovery verification passed.")
