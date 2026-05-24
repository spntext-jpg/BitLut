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
private const val HC_PLAY = "https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata"

class MainActivity : ComponentActivity() {

    private val googleManager by lazy { GoogleHealthManager(this) }
    private val huaweiManager by lazy { HuaweiAuthManager(this) }
    private var uiState by mutableStateOf(MainUiState())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppLogger.i(TAG, "Start — ${android.os.Build.MODEL} API${android.os.Build.VERSION.SDK_INT}")

        setContent {
            val permLauncher = rememberLauncherForActivityResult(
                PermissionController.createRequestPermissionResultContract()
            ) { granted ->
                val ok = granted.containsAll(googleManager.permissions)
                AppLogger.i(TAG, "HC permissions: ok=$ok granted=$granted")
                uiState = uiState.copy(
                    isGoogleConnected = ok,
                    syncStatus = if (ok) "Google Health подключён" else "Доступ отклонён"
                )
                if (ok) setupPeriodicSync()
            }

            LaunchedEffect(Unit) { refreshStatuses() }

            OpenHealthSyncTheme {
                MainScreen(
                    uiState = uiState,

                    onConnectGoogle = {
                        val status = uiState.healthConnectStatus
                        AppLogger.i(TAG, "onConnectGoogle: status=$status")
                        when (status) {
                            HealthConnectStatus.AVAILABLE ->
                                permLauncher.launch(googleManager.permissions)
                            HealthConnectStatus.NOT_INSTALLED,
                            HealthConnectStatus.NEEDS_UPDATE ->
                                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(HC_PLAY)))
                            HealthConnectStatus.NOT_SUPPORTED ->
                                Toast.makeText(this,
                                    "Health Connect не поддерживается", Toast.LENGTH_LONG).show()
                        }
                    },

                    onConnectHuawei = {
                        val configured = uiState.isHuaweiConfigured
                        val authorized = huaweiManager.isAuthorized()
                        AppLogger.i(TAG, "onConnectHuawei: configured=$configured authorized=$authorized")
                        if (!configured) {
                            Toast.makeText(this,
                                "Huawei API не настроен — замените CLIENT_ID в HuaweiConfig.kt",
                                Toast.LENGTH_LONG).show()
                        } else if (authorized) {
                            Toast.makeText(this, "Huawei Health уже подключён",
                                Toast.LENGTH_SHORT).show()
                        } else {
                            startActivity(Intent(Intent.ACTION_VIEW,
                                Uri.parse(huaweiManager.getAuthUrl())))
                        }
                    },

                    onSyncNow = { triggerManualSync() },

                    onToggleLogs = {
                        uiState = uiState.copy(showLogs = !uiState.showLogs)
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
            val hcStatus   = googleManager.getStatus()
            val googleOk   = if (hcStatus == HealthConnectStatus.AVAILABLE)
                                 googleManager.hasAllPermissions() else false
            val huaweiOk   = huaweiManager.isAuthorized()
            val configured = HuaweiConfig.CLIENT_ID != "YOUR_HUAWEI_CLIENT_ID"

            AppLogger.i(TAG, "Refresh: hc=$hcStatus google=$googleOk huawei=$huaweiOk configured=$configured")

            uiState = uiState.copy(
                healthConnectStatus = hcStatus,
                isGoogleConnected   = googleOk,
                isHuaweiConnected   = huaweiOk,
                isHuaweiConfigured  = configured,
                syncStatus = when {
                    googleOk && huaweiOk -> "Готово к синхронизации"
                    hcStatus == HealthConnectStatus.NOT_INSTALLED -> "Установите Google Health Connect"
                    hcStatus == HealthConnectStatus.NEEDS_UPDATE  -> "Обновите Google Health Connect"
                    !googleOk -> "Подключите Google Health"
                    else      -> "Подключите Huawei Health"
                }
            )
            if (googleOk && huaweiOk) setupPeriodicSync()
        }
    }

    private fun triggerManualSync() {
        AppLogger.i(TAG, "Manual sync")
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
