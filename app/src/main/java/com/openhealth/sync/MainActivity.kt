package com.openhealth.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.lifecycleScope
import androidx.work.*
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.remote.HuaweiConfig
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.ui.main.MainScreen
import com.openhealth.sync.ui.main.MainUiState
import com.openhealth.sync.ui.theme.OpenHealthSyncTheme
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

/**
 * Main entry point.
 *
 * UI state is owned here (single Activity app — ViewModel would be the next
 * step when complexity grows, but this is correct for current scope).
 *
 * Key fixes vs previous version:
 * - isSyncing is reset when WorkManager reports a finished state
 * - isHuaweiConnected reads from HuaweiAuthManager (SSOT), not a toggle
 * - onResume() refreshes both connection statuses after OAuth browser returns
 */
class MainActivity : ComponentActivity() {

    private val googleHealthManager by lazy { GoogleHealthManager(this) }
    private val huaweiAuthManager   by lazy { HuaweiAuthManager(this) }

    private var uiState by mutableStateOf(MainUiState())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            // Health Connect permission launcher
            val requestPermissionsLauncher = rememberLauncherForActivityResult(
                PermissionController.createRequestPermissionResultContract()
            ) { granted ->
                val allGranted = granted.containsAll(googleHealthManager.permissions)
                uiState = uiState.copy(
                    isGoogleConnected = allGranted,
                    syncStatus = if (allGranted)
                        "Google Health Connect подключен"
                    else
                        "Доступ к Health Connect отклонен"
                )
                if (allGranted) setupPeriodicSync()
            }

            LaunchedEffect(Unit) { refreshStatuses() }

            OpenHealthSyncTheme {
                MainScreen(
                    uiState = uiState,

                    onConnectHuawei = {
                        if (huaweiAuthManager.isAuthorized()) {
                            Toast.makeText(this, "Huawei уже подключен", Toast.LENGTH_SHORT).show()
                        } else {
                            // Open system browser for OAuth2 login — HuaweiCallbackActivity intercepts return
                            val intent = Intent(Intent.ACTION_VIEW,
                                Uri.parse(huaweiAuthManager.getAuthUrl()))
                            startActivity(intent)
                        }
                    },

                    onConnectGoogle = {
                        when (googleHealthManager.getSdkStatus()) {
                            HealthConnectClient.SDK_AVAILABLE ->
                                requestPermissionsLauncher.launch(googleHealthManager.permissions)
                            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED ->
                                Toast.makeText(this,
                                    "Обновите Google Health Connect", Toast.LENGTH_LONG).show()
                            else ->
                                Toast.makeText(this,
                                    "Health Connect недоступен на этом устройстве",
                                    Toast.LENGTH_LONG).show()
                        }
                    },

                    onSyncNow = {
                        triggerManualSync()
                    }
                )
            }
        }
    }

    // Refresh connection statuses when returning from the OAuth browser tab
    override fun onResume() {
        super.onResume()
        refreshStatuses()
    }

    /** Reads real auth state from both managers and updates UI. */
    private fun refreshStatuses() {
        lifecycleScope.launch {
            val isGoogleOk  = googleHealthManager.hasAllPermissions()
            val isHuaweiOk  = huaweiAuthManager.isAuthorized()
            uiState = uiState.copy(
                isGoogleConnected = isGoogleOk,
                isHuaweiConnected = isHuaweiOk,
                syncStatus = when {
                    isGoogleOk && isHuaweiOk -> "Все системы в норме"
                    !isHuaweiOk              -> "Требуется вход в Huawei"
                    else                     -> "Требуется доступ к Health Connect"
                }
            )
            if (isGoogleOk && isHuaweiOk) setupPeriodicSync()
        }
    }

    /**
     * Enqueues a one-time SyncWorker and observes its result to correctly
     * reset isSyncing back to false when done.
     */
    private fun triggerManualSync() {
        uiState = uiState.copy(isSyncing = true, syncStatus = "Синхронизация...")

        val request = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build())
            .build()

        val workManager = WorkManager.getInstance(this)
        workManager.enqueue(request)

        workManager.getWorkInfoByIdLiveData(request.id)
            .observe(this) { info ->
                if (info != null && info.state.isFinished) {
                    val succeeded = info.state == WorkInfo.State.SUCCEEDED
                    uiState = uiState.copy(
                        isSyncing  = false,
                        syncStatus = if (succeeded) "Все системы в норме" else "Ошибка синхронизации",
                        lastSyncTime = if (succeeded) "Только что" else uiState.lastSyncTime
                    )
                }
            }
    }

    /** Sets up hourly background sync via WorkManager (only registers once via KEEP policy). */
    private fun setupPeriodicSync() {
        val request = PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS)
            .setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build())
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            HuaweiConfig.SYNC_WORKER_TAG,
            ExistingPeriodicWorkPolicy.KEEP,
            request
        )
    }
}
