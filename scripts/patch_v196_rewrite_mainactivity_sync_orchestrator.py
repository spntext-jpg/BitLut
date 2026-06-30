#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")

MAIN = ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
ORCHESTRATOR = ROOT / "app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt"
README = ROOT / "README.md"
CONTEXT = ROOT / "CONTEXT.md"
VERIFY = ROOT / "scripts/verify_mainactivity_sync_orchestrator_rewrite.py"

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def patch_orchestrator() -> None:
    if not ORCHESTRATOR.exists():
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
        } catch (e: CancellationException) {
            throw e
        } catch (t: Throwable) {
            AppLogger.e(TAG, "Manual sync failed: ${t.message}", t)
            onCompleted(false)
        }
    }
}
''')
        return

    text = read(ORCHESTRATOR)
    text = text.replace(
        "import com.openhealth.sync.data.GoogleHealthManager",
        "import com.openhealth.sync.data.HealthConnectManager"
    )
    if "import com.openhealth.sync.data.HealthConnectManager" not in text:
        text = text.replace(
            "import com.openhealth.sync.data.worker.BackgroundSyncScheduler",
            "import com.openhealth.sync.data.HealthConnectManager\nimport com.openhealth.sync.data.worker.BackgroundSyncScheduler"
        )
    text = text.replace(
        "private val googleManager: GoogleHealthManager",
        "private val googleManager: HealthConnectManager"
    )
    write(ORCHESTRATOR, text)

def patch_main() -> None:
    write(MAIN, '''package com.openhealth.sync

import android.app.Activity
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.lifecycleScope
import com.openhealth.sync.config.WidgetVisibilityPrefs
import com.openhealth.sync.domain.SyncOrchestrator
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.ImportViewModel
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.screens.FinalBitLutShell
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private val syncViewModel: SyncViewModel by viewModels {
        val app = application as SyncApplication
        SyncViewModel.provideFactory(
            app.container.googleHealthManager,
            app.container.huaweiHealthManager,
            this
        )
    }

    private val dashboardViewModel: DashboardViewModel by viewModels {
        val app = application as SyncApplication
        DashboardViewModel.provideFactory(
            app.container.googleHealthManager,
            WidgetVisibilityPrefs(applicationContext)
        )
    }

    private val importViewModel: ImportViewModel by lazy {
        ViewModelProvider(
            this,
            ImportViewModel.provideFactory(
                (application as SyncApplication).container.googleHealthManager,
                this
            )
        )[ImportViewModel::class.java]
    }

    private val syncOrchestrator: SyncOrchestrator by lazy {
        SyncOrchestrator(this, syncViewModel.googleManager)
    }

    private val archiveImportLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                val uri = result.data?.data
                if (uri != null) {
                    Toast.makeText(this, getString(R.string.import_archive_selected), Toast.LENGTH_LONG).show()
                    AppLogger.i("MainActivity", "Huawei archive selected: $uri")
                } else {
                    Toast.makeText(this, getString(R.string.status_error), Toast.LENGTH_LONG).show()
                }
            }
        }

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")
        syncViewModel.refreshStatuses()
        dashboardViewModel.refresh()

        if (!granted.containsAll(syncViewModel.googleManager.permissions)) {
            Toast.makeText(this, getString(R.string.toast_hc_permissions), Toast.LENGTH_LONG).show()
        }
    }

    private val huaweiAuthorizationLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            val success = syncViewModel.huaweiHealthManager.handleAuthorizationResult(
                result.resultCode,
                result.data
            )
            syncViewModel.onHuaweiAuthorizationResult(success)
            syncViewModel.refreshStatuses()

            Toast.makeText(
                this,
                if (success) getString(R.string.toast_huawei_connected) else getString(R.string.toast_huawei_pending),
                Toast.LENGTH_LONG
            ).show()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setupPeriodicSync()
        refreshUiStatusOnLaunch()

        setContent {
            BitLutExpressiveTheme {
                FinalBitLutShell(
                    dashboardStateProvider = {
                        dashboardViewModel.state.collectAsStateWithLifecycle().value
                    },
                    syncStateProvider = {
                        syncViewModel.uiState.collectAsStateWithLifecycle().value
                    },
                    onRefresh = {
                        syncViewModel.refreshStatuses()
                        dashboardViewModel.refresh()
                    },
                    onRequestGoogle = { requestGoogleHealthPermissions() },
                    onRequestHuawei = { startHuaweiAuthorization() },
                    onSyncNow = { triggerImmediateSync() },
                    onImportArchive = { openHuaweiArchiveImport() },
                    onHistoryRangeSelected = { days ->
                        dashboardViewModel.onHistoryRangeSelected(days)
                    },
                    onWidgetVisibilityChanged = { widget, visible ->
                        dashboardViewModel.setWidgetVisible(widget, visible)
                    },
                    importViewModel = importViewModel
                )
            }
        }
    }

    private fun refreshUiStatusOnLaunch() {
        syncViewModel.refreshStatuses()
        dashboardViewModel.refresh()
    }

    private fun requestGoogleHealthPermissions() {
        com.openhealth.sync.config.requestGoogleHealthPermissions(
            context = this,
            googleManager = syncViewModel.googleManager,
            launcher = googlePermissionLauncher
        )
    }

    private fun startHuaweiAuthorization() {
        try {
            if (!HmsCoreHelper.isInstalled(this)) {
                Toast.makeText(this, HmsCoreHelper.missingMessage, Toast.LENGTH_LONG).show()
                return
            }

            if (!HmsCoreHelper.isHuaweiHealthInstalled(this)) {
                Toast.makeText(this, getString(R.string.toast_huawei_health_missing), Toast.LENGTH_LONG).show()
                return
            }

            huaweiAuthorizationLauncher.launch(syncViewModel.huaweiHealthManager.getAuthorizationIntent())
        } catch (e: Exception) {
            AppLogger.e("MainActivity", "Huawei authorization start failed: ${e.message}", e)
            Toast.makeText(this, getString(R.string.toast_huawei_start_failed), Toast.LENGTH_LONG).show()
        }
    }

    private fun openHuaweiArchiveImport() {
        try {
            val intent = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(android.content.Intent.CATEGORY_OPENABLE)
                type = "*/*"
                putExtra(
                    android.content.Intent.EXTRA_MIME_TYPES,
                    arrayOf(
                        "application/zip",
                        "application/json",
                        "text/*",
                        "application/octet-stream"
                    )
                )
            }
            archiveImportLauncher.launch(intent)
        } catch (t: Throwable) {
            AppLogger.e("MainActivity", "Archive picker failed: ${t.message}", t)
            Toast.makeText(this, getString(R.string.status_error), Toast.LENGTH_LONG).show()
        }
    }

    private fun setupPeriodicSync() {
        syncOrchestrator.schedulePeriodic()
    }

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
}
''')

def patch_docs() -> None:
    note = """
## v1.9.6 MainActivity recovery

`MainActivity.kt` was clean-room rewritten after the Sync Orchestrator migration to remove a broken partial WorkManager block and restore:

- lifecycle-aware Compose state collection;
- Google Health permission flow;
- Huawei authorization flow;
- archive import picker;
- launch-time status refresh;
- periodic sync delegation;
- manual sync delegation through `SyncOrchestrator`.

`MainActivity` must not directly import WorkManager or `BackgroundSyncScheduler`.
""".strip()

    for doc in [README, CONTEXT]:
        if doc.exists():
            content = read(doc)
            if "## v1.9.6 MainActivity recovery" not in content:
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

main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")
orchestrator = read("app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("class MainActivity : ComponentActivity()" in main, "MainActivity class missing")
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
''')
    VERIFY.chmod(0o755)

def self_check() -> None:
    main = read(MAIN)
    errors = []

    for token in [
        "private fun refreshUiStatusOnLaunch()",
        "private fun requestGoogleHealthPermissions()",
        "private fun startHuaweiAuthorization()",
        "private fun openHuaweiArchiveImport()",
        "private fun setupPeriodicSync()",
        "private fun triggerImmediateSync()",
        "collectAsStateWithLifecycle",
        "syncOrchestrator.triggerImmediateSync(",
    ]:
        if token not in main:
            errors.append(f"MainActivity missing {token}")

    for forbidden in [
        "syncNowAfterPermissionCheck",
        "BackgroundSyncScheduler",
        "WorkManager.getInstance",
        "WorkInfo.State",
        "getWorkInfoByIdLiveData",
    ]:
        if forbidden in main:
            errors.append(f"MainActivity still contains {forbidden}")

    if errors:
        print("MainActivity rewrite patch failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

def main() -> None:
    patch_orchestrator()
    patch_main()
    patch_docs()
    write_verifier()
    self_check()
    print("Rewrote MainActivity with clean SyncOrchestrator integration.")

if __name__ == "__main__":
    main()
