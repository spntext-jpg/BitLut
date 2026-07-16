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

main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")
orchestrator = read("app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("class MainActivity : ComponentActivity()" in main, "MainActivity class missing")
# FinalBitLutShell package/import guard
shell_file = Path("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
if shell_file.exists():
    shell_text = shell_file.read_text(encoding="utf-8")
    if "package com.openhealth.sync\n" in shell_text:
        require(
            "import com.openhealth.sync.ui.screens.FinalBitLutShell" not in main,
            "MainActivity must not import FinalBitLutShell from ui.screens when shell package is root"
        )

require("collectAsStateWithLifecycle" in main, "MainActivity must use lifecycle-aware collection")
require("private fun refreshUiStatusOnLaunch()" in main, "MainActivity missing launch refresh")
require("private fun requestGoogleHealthPermissions()" in main, "MainActivity missing Google permission flow")
require("private fun startHuaweiAuthorization()" in main, "MainActivity missing Huawei authorization flow")
require("private fun openHuaweiArchiveImport()" in main, "MainActivity missing archive import flow")
require("private fun setupPeriodicSync()" in main, "MainActivity missing periodic sync wrapper")
require("private fun triggerImmediateSync()" in main, "MainActivity missing manual sync wrapper")
require("syncOrchestrator.schedulePeriodic()" in main, "Periodic sync must delegate to SyncOrchestrator")
require("syncOrchestrator.triggerImmediateSync(" in main, "Manual sync must delegate to SyncOrchestrator")
require(main.count("setupPeriodicSync()") == 2, "setupPeriodicSync should appear once as call and once as function")
require("syncNowAfterPermissionCheck" not in main, "Broken legacy syncNowAfterPermissionCheck must be removed")

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

require("private val googleManager: HealthConnectManager" in orchestrator, "SyncOrchestrator must use HealthConnectManager interface")
require("BackgroundSyncScheduler.enqueueImmediateSync(appContext)" in orchestrator, "SyncOrchestrator must own immediate enqueue")
require("BackgroundSyncScheduler.schedulePeriodic(appContext)" in orchestrator, "SyncOrchestrator must own periodic scheduling")

if errors:
    print("MainActivity SyncOrchestrator rewrite verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("MainActivity SyncOrchestrator rewrite verification passed.")
