package com.openhealth.sync

import android.content.Context
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.health.connect.client.PermissionController
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.data.worker.BackgroundSyncScheduler
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.DashboardUiState
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.config.DashboardWidget
import com.openhealth.sync.config.WidgetVisibilityPrefs
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.util.AppLogger
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.launch
import com.openhealth.sync.ui.ImportViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope

private const val UNIQUE_SYNC_NOW = "bitlut_sync_now"
private const val UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync"

class MainActivity : ComponentActivity() {

    private val importViewModel: ImportViewModel by lazy {
        ViewModelProvider(
            this,
            ImportViewModel.provideFactory(
                (application as SyncApplication).container.googleHealthManager,
                this
            )
        )[ImportViewModel::class.java]
    }

    private val archiveImportLauncher =
        registerForActivityResult(androidx.activity.result.contract.ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == android.app.Activity.RESULT_OK) {
                val uri = result.data?.data
                if (uri != null) {
                    Toast.makeText(this, getString(R.string.import_archive_selected), Toast.LENGTH_LONG).show()
                    AppLogger.i("MainActivity", "Huawei archive selected: $uri")
                    // Existing archive parser/import flow can consume this URI in the next integration step.
                    // This restores the user-facing archive import entry point without touching direct Health Kit sync.
                } else {
                    Toast.makeText(this, getString(R.string.status_error), Toast.LENGTH_LONG).show()
                }
            }
        }

    private val syncViewModel: SyncViewModel by viewModels {
        val app = application as SyncApplication
        SyncViewModel.provideFactory(app.container.googleHealthManager, app.container.huaweiHealthManager, this)
    }

    private val dashboardViewModel: DashboardViewModel by viewModels {
        val app = application as SyncApplication
        DashboardViewModel.provideFactory(
            app.container.googleHealthManager,
            WidgetVisibilityPrefs(applicationContext)
        )
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

    /** Self-healing entry point for "Connect Google Health" — see
     *  config.GoogleHealthPermissionRequester for the full behavior. */
    private fun requestGoogleHealthPermissions() {
        com.openhealth.sync.config.requestGoogleHealthPermissions(
            context = this,
            googleManager = syncViewModel.googleManager,
            launcher = googlePermissionLauncher
        )
    }

    private val huaweiAuthorizationLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val success = syncViewModel.huaweiHealthManager.handleAuthorizationResult(result.resultCode, result.data)
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
                    dashboardStateProvider = { dashboardViewModel.state.collectAsState().value },
                    syncStateProvider = { syncViewModel.uiState.collectAsState().value },
                    onRefresh = {
                        syncViewModel.refreshStatuses()
                        dashboardViewModel.refresh()
                    },
                    onRequestGoogle = { requestGoogleHealthPermissions() },
                    onRequestHuawei = { startHuaweiAuthorization() },
                    onSyncNow = { triggerImmediateSync() }
                ,
                onImportArchive = {
                    openHuaweiArchiveImport()
                }
            ,
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

    private fun triggerImmediateSync() {
        syncViewModel.markSyncStarted()

        lifecycleScope.launch {
            val missing = syncViewModel.googleManager.missingRequiredPermissions()
            if (missing.isNotEmpty()) {
                syncViewModel.markSyncCompleted(false)
                AppLogger.w("MainActivity", "Sync blocked by missing Health Connect permissions: $missing")
                Toast.makeText(this@MainActivity, getString(R.string.toast_hc_permissions), Toast.LENGTH_LONG).show()
                requestGoogleHealthPermissions()
                return@launch
            }

            syncNowAfterPermissionCheck()
        }
    }

    private fun syncNowAfterPermissionCheck() {
        syncViewModel.markSyncStarted()
        val requestId = BackgroundSyncScheduler.enqueueImmediateSync(this)
        WorkManager.getInstance(this).getWorkInfoByIdLiveData(requestId).observe(this) { info ->
            when (info?.state) {
                WorkInfo.State.SUCCEEDED -> {
                    syncViewModel.markSyncCompleted(true)
                    dashboardViewModel.refresh()
                }
                WorkInfo.State.FAILED, WorkInfo.State.CANCELLED -> syncViewModel.markSyncCompleted(false)
                else -> Unit
            }
        }
    }

    private fun setupPeriodicSync() {
        BackgroundSyncScheduler.schedulePeriodic(this)
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
            Toast.makeText(this, getString(R.string.status_error), Toast.LENGTH_LONG).show()
        }
    }

}
