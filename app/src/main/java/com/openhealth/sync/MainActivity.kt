package com.openhealth.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.lifecycleScope
import androidx.work.*
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HealthConnectStatus
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.ui.main.MainScreen
import com.openhealth.sync.ui.main.MainUiState
import com.openhealth.sync.ui.theme.OpenHealthSyncTheme
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

private const val TAG = "MainActivity"
private const val HC_PLAY =
    "https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata"

class MainActivity : ComponentActivity() {

    private val googleManager by lazy { GoogleHealthManager(this) }
    private val huaweiManager by lazy { HuaweiAuthManager(this) }
    private var uiState by mutableStateOf(MainUiState())

    // Set to true when user is sent to Play Store to install HC.
    // onResume checks this and auto-launches permissions if HC is now installed.
    private var pendingPermissionRequest = false
    private var requestPermissions: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppLogger.i(TAG, "Start — ${android.os.Build.MODEL} API${android.os.Build.VERSION.SDK_INT}")

        setContent {
            val launcher = rememberLauncherForActivityResult(
                PermissionController.createRequestPermissionResultContract()
            ) { granted ->
                val ok = granted.containsAll(googleManager.permissions)
                AppLogger.i(TAG, "HC permissions result: ok=$ok")
                uiState = uiState.copy(
                    isGoogleConnected = ok,
                    syncStatus = if (ok) "Google Health подключён" else "Доступ отклонён"
                )
                if (ok) setupPeriodicSync()
            }

            requestPermissions = { launcher.launch(googleManager.permissions) }

            LaunchedEffect(Unit) { refreshStatuses() }

            OpenHealthSyncTheme {
                MainScreen(
                    uiState = uiState,
                    onConnectGoogle  = { handleConnectGoogle() },
                    onConnectHuawei  = { handleConnectHuawei() },
                    onSyncNow        = { triggerManualSync() },
                    onToggleLogs     = { uiState = uiState.copy(showLogs = !uiState.showLogs) }
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        lifecycleScope.launch {
            refreshStatuses()
            // User returned from Play Store — if HC is now installed, launch permissions immediately
            if (pendingPermissionRequest &&
                uiState.healthConnectStatus == HealthConnectStatus.AVAILABLE) {
                AppLogger.i(TAG, "onResume: HC now installed — launching permission dialog")
                pendingPermissionRequest = false
                requestPermissions?.invoke()
            }
        }
    }

    private fun handleConnectGoogle() {
        val status = uiState.healthConnectStatus
        AppLogger.i(TAG, "handleConnectGoogle: status=$status")
        when (status) {
            HealthConnectStatus.AVAILABLE -> {
                AppLogger.i(TAG, "HC available — requesting permissions")
                requestPermissions?.invoke()
            }
            HealthConnectStatus.NOT_INSTALLED,
            HealthConnectStatus.NEEDS_UPDATE -> {
                pendingPermissionRequest = true
                AppLogger.i(TAG, "HC not installed — opening Play Store, pendingPermission=true")
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(HC_PLAY)))
            }
            HealthConnectStatus.NOT_SUPPORTED ->
                Toast.makeText(this,
                    "Health Connect не поддерживается на этом устройстве",
                    Toast.LENGTH_LONG).show()
        }
    }

    private fun handleConnectHuawei() {
        val configured = HuaweiConfig.isConfigured()
        val authorized = huaweiManager.isAuthorized()
        AppLogger.i(TAG, "handleConnectHuawei: configured=$configured authorized=$authorized")
        when {
            !configured -> Toast.makeText(this,
                "Huawei API не настроен.\n" +
                "Добавьте HUAWEI_CLIENT_ID в local.properties\n" +
                "или GitHub Actions Secrets.",
                Toast.LENGTH_LONG).show()
            authorized  -> Toast.makeText(this,
                "Huawei Health уже подключён", Toast.LENGTH_SHORT).show()
            else        -> startActivity(Intent(Intent.ACTION_VIEW,
                Uri.parse(huaweiManager.getAuthUrl())))
        }
    }

    private fun refreshStatuses() {
        lifecycleScope.launch {
            val hcStatus   = googleManager.getStatus()
            val googleOk   = hcStatus == HealthConnectStatus.AVAILABLE
                             && googleManager.hasAllPermissions()
            val huaweiOk   = huaweiManager.isAuthorized()
            val configured = HuaweiConfig.isConfigured()

            AppLogger.i(TAG, "Refresh: hc=$hcStatus google=$googleOk " +
                "huawei=$huaweiOk configured=$configured")

            uiState = uiState.copy(
                healthConnectStatus = hcStatus,
                isGoogleConnected   = googleOk,
                isHuaweiConnected   = huaweiOk,
                isHuaweiConfigured  = configured,
                syncStatus = when {
                    googleOk && huaweiOk -> "Готово к синхронизации"
                    hcStatus == HealthConnectStatus.NOT_INSTALLED ->
                        "Установите Google Health Connect"
                    hcStatus == HealthConnectStatus.NEEDS_UPDATE ->
                        "Обновите Google Health Connect"
                    !googleOk -> "Подключите Google Health"
                    else      -> "Подключите Huawei Health"
                }
            )
            if (googleOk && huaweiOk) setupPeriodicSync()
        }
    }

    private fun triggerManualSync() {
        AppLogger.i(TAG, "Manual sync triggered")
        uiState = uiState.copy(isSyncing = true, syncStatus = "Синхронизация...")
        val req = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        val wm = WorkManager.getInstance(this)
        wm.enqueue(req)
        wm.getWorkInfoByIdLiveData(req.id).observe(this) { info ->
            if (info?.state?.isFinished == true) {
                val ok = info.state == WorkInfo.State.SUCCEEDED
                AppLogger.i(TAG, "Sync done: ${info.state}")
                uiState = uiState.copy(
                    isSyncing    = false,
                    syncStatus   = if (ok) "Готово к синхронизации" else "Ошибка синхронизации",
                    lastSyncTime = if (ok) nowTime() else uiState.lastSyncTime
                )
            }
        }
    }

    private fun setupPeriodicSync() {
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            HuaweiConfig.SYNC_WORKER_TAG,
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS)
                .setConstraints(Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
        )
        AppLogger.d(TAG, "Periodic sync scheduled")
    }

    private fun nowTime() = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
}
