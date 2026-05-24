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
private const val HC_PLAY_URI =
    "https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata"

class MainActivity : ComponentActivity() {

    private val googleHealthManager by lazy { GoogleHealthManager(this) }
    private val huaweiAuthManager   by lazy { HuaweiAuthManager(this) }

    // mutableStateOf at class level — survives recomposition
    private var uiState by mutableStateOf(MainUiState())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppLogger.i(TAG, "App started — ${android.os.Build.MODEL} API${android.os.Build.VERSION.SDK_INT}")

        setContent {
            val permLauncher = rememberLauncherForActivityResult(
                PermissionController.createRequestPermissionResultContract()
            ) { granted ->
                val allGranted = granted.containsAll(googleHealthManager.permissions)
                AppLogger.i(TAG, "HC permissions granted=$allGranted")
                uiState = uiState.copy(
                    isGoogleConnected = allGranted,
                    syncStatus = if (allGranted) "Google Health подключён" else "Доступ отклонён"
                )
                if (allGranted) setupPeriodicSync()
            }

            LaunchedEffect(Unit) { refreshStatuses() }

            OpenHealthSyncTheme {
                MainScreen(
                    uiState = uiState,

                    onConnectGoogle = {
                        AppLogger.i(TAG, "onConnectGoogle: hcStatus=${uiState.healthConnectStatus}")
                        when (uiState.healthConnectStatus) {
                            HealthConnectStatus.AVAILABLE ->
                                permLauncher.launch(googleHealthManager.permissions)
                            HealthConnectStatus.NOT_INSTALLED,
                            HealthConnectStatus.NEEDS_UPDATE -> {
                                AppLogger.i(TAG, "Opening Play Store for Health Connect")
                                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(HC_PLAY_URI)))
                            }
                            HealthConnectStatus.NOT_SUPPORTED ->
                                Toast.makeText(this,
                                    "Health Connect не поддерживается на этом устройстве",
                                    Toast.LENGTH_LONG).show()
                        }
                    },

                    onConnectHuawei = {
                        // NOTE: no early return — use explicit branching
                        val configured = HuaweiConfig.CLIENT_ID != "YOUR_HUAWEI_CLIENT_ID"
                        AppLogger.i(TAG, "onConnectHuawei: configured=$configured authorized=${huaweiAuthManager.isAuthorized()}")
                        if (!configured) {
                            Toast.makeText(
                                this,
                                "Huawei API не настроен.\nЗамените CLIENT_ID в HuaweiConfig.kt",
                                Toast.LENGTH_LONG
                            ).show()
                        } else if (huaweiAuthManager.isAuthorized()) {
                            Toast.makeText(this, "Huawei Health уже подключён", Toast.LENGTH_SHORT).show()
                        } else {
                            AppLogger.i(TAG, "Launching Huawei OAuth")
                            startActivity(Intent(Intent.ACTION_VIEW,
                                Uri.parse(huaweiAuthManager.getAuthUrl())))
                        }
                    },

                    onSyncNow = { triggerManualSync() },

                    onToggleLogs = {
                        uiState = uiState.copy(showLogs = !uiState.showLogs)
                        AppLogger.d(TAG, "Log viewer toggled: ${uiState.showLogs}")
                    }
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refreshStatuses()
    }

    private fun refreshStatuses() {
        lifecycleScope.launch {
            val hcStatus  = googleHealthManager.getStatus()
            val googleOk  = if (hcStatus == HealthConnectStatus.AVAILABLE)
                                googleHealthManager.hasAllPermissions()
                            else false
            val huaweiOk  = huaweiAuthManager.isAuthorized()
            val configured = HuaweiConfig.CLIENT_ID != "YOUR_HUAWEI_CLIENT_ID"

            AppLogger.i(TAG, "Refresh: hcStatus=$hcStatus googleOk=$googleOk huaweiOk=$huaweiOk configured=$configured")

            uiState = uiState.copy(
                healthConnectStatus = hcStatus,
                isGoogleConnected   = googleOk,
                isHuaweiConnected   = huaweiOk,
                isHuaweiConfigured  = configured,
                syncStatus = when {
                    googleOk && huaweiOk          -> "Готово к синхронизации"
                    hcStatus == HealthConnectStatus.NOT_INSTALLED -> "Установите Google Health Connect"
                    hcStatus == HealthConnectStatus.NEEDS_UPDATE  -> "Обновите Google Health Connect"
                    !googleOk                     -> "Подключите Google Health"
                    else                          -> "Подключите Huawei Health"
                }
            )
            if (googleOk && huaweiOk) setupPeriodicSync()
        }
    }

    private fun triggerManualSync() {
        AppLogger.i(TAG, "Manual sync triggered")
        uiState = uiState.copy(isSyncing = true, syncStatus = "Синхронизация...")
        val request = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        val wm = WorkManager.getInstance(this)
        wm.enqueue(request)
        wm.getWorkInfoByIdLiveData(request.id).observe(this) { info ->
            if (info != null && info.state.isFinished) {
                val ok = info.state == WorkInfo.State.SUCCEEDED
                AppLogger.i(TAG, "Sync finished: ${info.state}")
                uiState = uiState.copy(
                    isSyncing    = false,
                    syncStatus   = if (ok) "Готово к синхронизации" else "Ошибка синхронизации",
                    lastSyncTime = if (ok) nowTime() else uiState.lastSyncTime
                )
            }
        }
    }

    private fun setupPeriodicSync() {
        val req = PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS)
            .setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            HuaweiConfig.SYNC_WORKER_TAG,
            ExistingPeriodicWorkPolicy.KEEP,
            req
        )
        AppLogger.d(TAG, "Periodic sync scheduled")
    }

    private fun nowTime() =
        SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
}
