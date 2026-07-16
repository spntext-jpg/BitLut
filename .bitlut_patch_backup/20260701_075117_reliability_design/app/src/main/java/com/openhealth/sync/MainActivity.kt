package com.openhealth.sync

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
import com.openhealth.sync.data.DashboardSnapshotCache
import com.openhealth.sync.domain.SyncOrchestrator
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.ImportViewModel
import com.openhealth.sync.ui.SyncViewModel
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
            WidgetVisibilityPrefs(applicationContext),
            DashboardSnapshotCache(applicationContext)
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
