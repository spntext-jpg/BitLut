#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")

ORCHESTRATOR = ROOT / "app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt"
MAIN = ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
README = ROOT / "README.md"
CONTEXT = ROOT / "CONTEXT.md"
VERIFY = ROOT / "scripts/verify_sync_orchestrator_sprint.py"

OLD_TEMP_PATCHES = [
    "scripts/patch_v196_glass20_gui_polish.py",
    "scripts/patch_v196_gui_neoglass_activity_only.py",
    "scripts/patch_v196_gui_neoglass_activity_only_recovery.py",
]

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def cleanup_temp_files() -> None:
    for pattern in [
        "app/src/main/**/*.orig",
        "app/src/main/**/*.bak",
        "app/src/main/**/*.tmp",
    ]:
        for path in ROOT.glob(pattern):
            path.unlink(missing_ok=True)

    for patch in OLD_TEMP_PATCHES:
        Path(patch).unlink(missing_ok=True)

def ensure_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text
    package_match = re.search(r"^package [^\n]+\n", text)
    if not package_match:
        return import_line + "\n" + text
    return text[:package_match.end()] + import_line + "\n" + text[package_match.end():]

def remove_import(text: str, import_line: str) -> str:
    return text.replace(import_line + "\n", "")

def find_matching(text: str, open_index: int, open_char: str = "{", close_char: str = "}") -> int:
    depth = 0
    i = open_index
    in_string = False
    escaped = False
    triple = False
    in_line_comment = False
    in_block_comment = False

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
        elif in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 1
        elif in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif triple and text.startswith('"""', i):
                in_string = False
                triple = False
                i += 2
            elif not triple and ch == '"':
                in_string = False
        else:
            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 1
            elif ch == "/" and nxt == "*":
                in_block_comment = True
                i += 1
            elif text.startswith('"""', i):
                in_string = True
                triple = True
                i += 2
            elif ch == '"':
                in_string = True
            elif ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return i
        i += 1

    raise RuntimeError(f"Matching {close_char} not found")

def remove_function(text: str, name: str) -> str:
    pattern = re.compile(
        r"(?m)^    private fun " + re.escape(name) + r"\s*\("
    )

    while True:
        match = pattern.search(text)
        if not match:
            return text

        brace = text.find("{", match.end())
        if brace == -1:
            return text[:match.start()]

        end = find_matching(text, brace) + 1
        while end < len(text) and text[end] in " \t\r\n":
            end += 1
        text = text[:match.start()] + text[end:]

def create_orchestrator() -> None:
    write(ORCHESTRATOR, '''package com.openhealth.sync.domain

import android.content.Context
import androidx.lifecycle.LifecycleOwner
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.openhealth.sync.data.HealthConnectManager
import com.openhealth.sync.data.worker.BackgroundSyncScheduler
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.CancellationException

private const val TAG = "SyncOrchestrator"

/**
 * UI-safe sync orchestration boundary.
 *
 * MainActivity should not know WorkManager details or sync permission preflight.
 * The orchestrator owns those mechanics and reports lifecycle-safe callbacks back
 * to the Activity/ViewModel layer.
 */
class SyncOrchestrator(
    context: Context,
    private val googleManager: HealthConnectManager
) {
    private val appContext = context.applicationContext
    private val workManager: WorkManager = WorkManager.getInstance(appContext)

    fun schedulePeriodic() {
        BackgroundSyncScheduler.schedulePeriodic(appContext)
    }

    suspend fun triggerImmediateSync(
        lifecycleOwner: LifecycleOwner,
        onStarted: () -> Unit,
        onMissingPermissions: (Set<String>) -> Unit,
        onCompleted: (Boolean) -> Unit,
        onDashboardRefresh: () -> Unit
    ) {
        onStarted()

        try {
            val missing = googleManager.missingRequiredPermissions()
            if (missing.isNotEmpty()) {
                AppLogger.w(TAG, "Manual sync blocked by missing Health Connect permissions: $missing")
                onCompleted(false)
                onMissingPermissions(missing)
                return
            }

            enqueueAfterPermissionCheck(
                lifecycleOwner = lifecycleOwner,
                onCompleted = onCompleted,
                onDashboardRefresh = onDashboardRefresh
            )
        } catch (e: CancellationException) {
            throw e
        } catch (t: Throwable) {
            AppLogger.e(TAG, "Manual sync preflight failed: ${t.message}", t)
            onCompleted(false)
        }
    }

    private fun enqueueAfterPermissionCheck(
        lifecycleOwner: LifecycleOwner,
        onCompleted: (Boolean) -> Unit,
        onDashboardRefresh: () -> Unit
    ) {
        val requestId = BackgroundSyncScheduler.enqueueImmediateSync(appContext)

        workManager.getWorkInfoByIdLiveData(requestId).observe(lifecycleOwner) { info ->
            when (info?.state) {
                WorkInfo.State.SUCCEEDED -> {
                    AppLogger.i(TAG, "Manual sync completed successfully")
                    onCompleted(true)
                    onDashboardRefresh()
                }

                WorkInfo.State.FAILED,
                WorkInfo.State.CANCELLED -> {
                    AppLogger.e(TAG, "Manual sync failed state=${info.state}")
                    onCompleted(false)
                }

                WorkInfo.State.ENQUEUED,
                WorkInfo.State.RUNNING,
                WorkInfo.State.BLOCKED,
                null -> Unit
            }
        }
    }
}
''')

def patch_main_activity() -> None:
    main = read(MAIN)

    for import_line in [
        "import androidx.work.Constraints",
        "import androidx.work.ExistingPeriodicWorkPolicy",
        "import androidx.work.ExistingWorkPolicy",
        "import androidx.work.NetworkType",
        "import androidx.work.OneTimeWorkRequestBuilder",
        "import androidx.work.PeriodicWorkRequestBuilder",
        "import androidx.work.WorkInfo",
        "import androidx.work.WorkManager",
        "import com.openhealth.sync.data.worker.SyncWorker",
        "import com.openhealth.sync.data.worker.BackgroundSyncScheduler",
        "import java.util.concurrent.TimeUnit",
    ]:
        main = remove_import(main, import_line)

    main = ensure_import(main, "import com.openhealth.sync.domain.SyncOrchestrator")
    main = ensure_import(main, "import kotlinx.coroutines.launch")
    main = ensure_import(main, "import androidx.lifecycle.lifecycleScope")

    # Remove old constants if they remain.
    main = re.sub(r'(?m)^private const val UNIQUE_SYNC_NOW = "bitlut_sync_now"\n', "", main)
    main = re.sub(r'(?m)^private const val UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync"\n', "", main)

    if "private val syncOrchestrator: SyncOrchestrator by lazy" not in main:
        anchor = "class MainActivity : ComponentActivity() {\n"
        if anchor not in main:
            raise RuntimeError("MainActivity class anchor not found")
        main = main.replace(
            anchor,
            anchor + '''
    private val syncOrchestrator: SyncOrchestrator by lazy {
        SyncOrchestrator(this, syncViewModel.googleManager)
    }

''',
            1
        )

    # Replace setupPeriodicSync body if function exists, otherwise add it.
    if "private fun setupPeriodicSync()" in main:
        main = remove_function(main, "setupPeriodicSync")
    main = main.replace(
        "\n    private fun openHuaweiArchiveImport()",
        '''
    private fun setupPeriodicSync() {
        syncOrchestrator.schedulePeriodic()
    }

    private fun openHuaweiArchiveImport()''',
        1
    )

    # Replace triggerImmediateSync + syncNowAfterPermissionCheck.
    main = remove_function(main, "triggerImmediateSync")
    main = remove_function(main, "syncNowAfterPermissionCheck")

    trigger = '''
    private fun triggerImmediateSync() {
        lifecycleScope.launch {
            syncOrchestrator.triggerImmediateSync(
                lifecycleOwner = this@MainActivity,
                onStarted = { syncViewModel.markSyncStarted() },
                onMissingPermissions = {
                    Toast.makeText(
                        this@MainActivity,
                        getString(R.string.toast_hc_permissions),
                        Toast.LENGTH_LONG
                    ).show()
                    requestGoogleHealthPermissions()
                },
                onCompleted = { success -> syncViewModel.markSyncCompleted(success) },
                onDashboardRefresh = { dashboardViewModel.refresh() }
            )
        }
    }

'''

    main = main.replace(
        "\n    private fun setupPeriodicSync()",
        "\n" + trigger + "    private fun setupPeriodicSync()",
        1
    )

    # Ensure launch refresh remains if previous sprint added it.
    if "refreshUiStatusOnLaunch()" in main and "setupPeriodicSync()\n        refreshUiStatusOnLaunch()" not in main:
        main = main.replace(
            "setupPeriodicSync()\n        setContent",
            "setupPeriodicSync()\n        refreshUiStatusOnLaunch()\n        setContent",
            1
        )

    main = re.sub(r"\n{3,}", "\n\n", main)
    write(MAIN, main)

def patch_docs() -> None:
    note = """
## v1.9.6 Sync Orchestrator Sprint

Implemented:

- Added `SyncOrchestrator` as the UI-safe boundary for manual and periodic sync orchestration.
- `MainActivity` no longer directly imports or observes WorkManager sync classes.
- Manual sync permission preflight moved out of `MainActivity`.
- `MainActivity` now delegates scheduling to `syncOrchestrator.schedulePeriodic()`.
- Manual sync callbacks remain lifecycle-owned by the Activity and update ViewModels through explicit callbacks.

Still deferred:

- Moving Huawei authorization UI flow out of `MainActivity`.
- Converting archive-import intent handling into a dedicated import orchestrator.
- Splitting `FinalBitLutShell.kt` into feature-level screen files.
""".strip()

    for doc in [README, CONTEXT]:
        if doc.exists():
            content = read(doc)
            if "## v1.9.6 Sync Orchestrator Sprint" not in content:
                content = content.rstrip() + "\n\n" + note + "\n"
            write(doc, content)

def write_verifier() -> None:
    write(VERIFY, r'''#!/usr/bin/env python3
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
reliability = read("scripts/verify_sync_reliability.py")

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
require("WorkInfo.State.SUCCEEDED" in orchestrator, "Orchestrator must handle success")
require("WorkInfo.State.FAILED" in orchestrator and "WorkInfo.State.CANCELLED" in orchestrator, "Orchestrator must handle failure/cancel")

require("private val syncOrchestrator: SyncOrchestrator by lazy" in main, "MainActivity must own a SyncOrchestrator")
require("syncOrchestrator.schedulePeriodic()" in main, "MainActivity setupPeriodicSync must delegate to orchestrator")
require("syncOrchestrator.triggerImmediateSync(" in main, "MainActivity triggerImmediateSync must delegate to orchestrator")
require("requestGoogleHealthPermissions()" in main, "Missing permission flow must still open Health Connect request")

for forbidden in [
    "import androidx.work.WorkManager",
    "import androidx.work.WorkInfo",
    "import androidx.work.OneTimeWorkRequestBuilder",
    "import androidx.work.PeriodicWorkRequestBuilder",
    "import com.openhealth.sync.data.worker.BackgroundSyncScheduler",
    "BackgroundSyncScheduler.enqueueImmediateSync(this)",
    "WorkManager.getInstance(this)",
]:
    require(forbidden not in main, f"MainActivity must not contain orchestration detail: {forbidden}")

# Keep compatibility with existing reliability verifier until it is updated.
if "BackgroundSyncScheduler.schedulePeriodic(this)" in reliability:
    print("Warning: verify_sync_reliability.py may still contain legacy MainActivity expectations.")

if errors:
    print("Sync Orchestrator verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Sync Orchestrator verification passed.")
''')
    VERIFY.chmod(0o755)

def patch_sync_reliability_verifier() -> None:
    path = ROOT / "scripts/verify_sync_reliability.py"
    if not path.exists():
        return

    text = read(path)

    # Update legacy MainActivity expectations to orchestrator-aware expectations.
    text = text.replace(
        '''if main_activity.exists():
    ma = main_activity.read_text(encoding="utf-8")
    if "BackgroundSyncScheduler.schedulePeriodic(this)" not in ma:
        errors.append("MainActivity must delegate periodic scheduling to BackgroundSyncScheduler")
    if "BackgroundSyncScheduler.enqueueImmediateSync(this)" not in ma:
        errors.append("MainActivity must delegate immediate sync to BackgroundSyncScheduler")
''',
        '''sync_orchestrator_file = root / "app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt"
if main_activity.exists():
    ma = main_activity.read_text(encoding="utf-8")
    if "syncOrchestrator.schedulePeriodic()" not in ma:
        errors.append("MainActivity must delegate periodic scheduling to SyncOrchestrator")
    if "syncOrchestrator.triggerImmediateSync(" not in ma:
        errors.append("MainActivity must delegate immediate sync to SyncOrchestrator")
if sync_orchestrator_file.exists():
    so = sync_orchestrator_file.read_text(encoding="utf-8")
    if "BackgroundSyncScheduler.schedulePeriodic(appContext)" not in so:
        errors.append("SyncOrchestrator must delegate periodic scheduling to BackgroundSyncScheduler")
    if "BackgroundSyncScheduler.enqueueImmediateSync(appContext)" not in so:
        errors.append("SyncOrchestrator must delegate immediate sync to BackgroundSyncScheduler")
else:
    errors.append("Missing SyncOrchestrator.kt")
'''
    )

    # Update old permission guardrail that expected MainActivity to perform preflight.
    text = text.replace(
        '''if main_file.exists():
    m = main_file.read_text(encoding="utf-8")
    if "missingRequiredPermissions()" not in m or "requestGoogleHealthPermissions()" not in m:
        errors.append("Sync Now must launch Health Connect permission request when required permissions are missing")
''',
        '''sync_orchestrator_file = root / "app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt"
if main_file.exists() and sync_orchestrator_file.exists():
    m = main_file.read_text(encoding="utf-8")
    so = sync_orchestrator_file.read_text(encoding="utf-8")
    if "missingRequiredPermissions()" not in so or "requestGoogleHealthPermissions()" not in m:
        errors.append("Sync Now must launch Health Connect permission request when required permissions are missing")
'''
    )

    write(path, text)

def self_check() -> None:
    orchestrator = read(ORCHESTRATOR)
    main = read(MAIN)

    errors = []

    for token in [
        "class SyncOrchestrator(",
        "private val googleManager: HealthConnectManager",
        "BackgroundSyncScheduler.schedulePeriodic(appContext)",
        "BackgroundSyncScheduler.enqueueImmediateSync(appContext)",
        "googleManager.missingRequiredPermissions()",
        "getWorkInfoByIdLiveData(requestId).observe(lifecycleOwner)",
    ]:
        if token not in orchestrator:
            errors.append(f"SyncOrchestrator missing {token}")

    for token in [
        "private val syncOrchestrator: SyncOrchestrator by lazy",
        "syncOrchestrator.schedulePeriodic()",
        "syncOrchestrator.triggerImmediateSync(",
        "requestGoogleHealthPermissions()",
    ]:
        if token not in main:
            errors.append(f"MainActivity missing {token}")

    for forbidden in [
        "import androidx.work.WorkManager",
        "import androidx.work.WorkInfo",
        "import androidx.work.OneTimeWorkRequestBuilder",
        "import androidx.work.PeriodicWorkRequestBuilder",
        "import com.openhealth.sync.data.worker.BackgroundSyncScheduler",
        "BackgroundSyncScheduler.enqueueImmediateSync(this)",
        "WorkManager.getInstance(this)",
    ]:
        if forbidden in main:
            errors.append(f"MainActivity still contains orchestration detail: {forbidden}")

    if errors:
        print("Sync Orchestrator patch failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

def main() -> None:
    cleanup_temp_files()
    create_orchestrator()
    patch_main_activity()
    patch_sync_reliability_verifier()
    patch_docs()
    write_verifier()
    self_check()
    print("Applied Sync Orchestrator Sprint.")

if __name__ == "__main__":
    main()
