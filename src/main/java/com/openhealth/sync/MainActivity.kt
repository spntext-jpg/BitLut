package com.openhealth.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import androidx.lifecycle.lifecycleScope
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.work.*
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HuaweiAuthManager
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.ui.main.MainScreen
import com.openhealth.sync.ui.main.MainUiState
import com.openhealth.sync.ui.theme.OpenHealthSyncTheme
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {
    
    private val googleHealthManager by lazy { GoogleHealthManager(this) }
    private val huaweiAuthManager by lazy { HuaweiAuthManager(this) }
    private var uiState by mutableStateOf(MainUiState())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            val requestPermissionsLauncher = rememberLauncherForActivityResult(
                PermissionController.createRequestPermissionResultContract()
            ) { grantedPermissions ->
                val allGranted = grantedPermissions.containsAll(googleHealthManager.permissions)
                uiState = uiState.copy(isGoogleConnected = allGranted)
                if (allGranted) setupBackgroundSync()
            }

            LaunchedEffect(Unit) {
                refreshStatuses()
            }

            OpenHealthSyncTheme {
                MainScreen(
                    uiState = uiState,
                    onConnectHuawei = {
                        if (huaweiAuthManager.isAuthorized()) {
                            Toast.makeText(this, "Вы уже авторизованы в Huawei", Toast.LENGTH_SHORT).show()
                        } else {
                            // Открываем браузер для авторизации OAuth 2.0 по принципу KISS
                            val authUrl = huaweiAuthManager.getAuthUrl()
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(authUrl))
                            startActivity(intent)
                        }
                    },
                    onConnectGoogle = {
                        when (googleHealthManager.checkHealthConnectStatus()) {
                            HealthConnectClient.SDK_AVAILABLE -> {
                                requestPermissionsLauncher.launch(googleHealthManager.permissions)
                            }
                            else -> {
                                Toast.makeText(this, "Google Health Connect недоступен", Toast.LENGTH_LONG).show()
                            }
                        }
                    },
                    onSyncNow = {
                        // Ручной запуск SyncWorker «прямо сейчас» через интерфейс
                        uiState = uiState.copy(isSyncing = true, syncStatus = "Синхронизация данных...")
                        val oneTimeWorkRequest = OneTimeWorkRequestBuilder<SyncWorker>().build()
                        WorkManager.getInstance(this).enqueue(oneTimeWorkRequest)
                        
                        WorkManager.getInstance(this).getWorkInfoByIdLiveData(oneTimeWorkRequest.id)
                            .observe(this@MainActivity) { workInfo ->
                                if (workInfo != null && workInfo.state.isFinished) {
                                    uiState = uiState.copy(
                                        isSyncing = false,
                                        syncStatus = if (workInfo.state == WorkInfo.State.SUCCEEDED) "Все системы в норме" else "Ошибка синхронизации",
                                        lastSyncTime = "Только что"
                                    )
                                }
                            }
                    }
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        refreshStatuses()
    }

    private fun refreshStatuses() {
        lifecycleScope.launch {
            val isGoogleOk = googleHealthManager.hasAllPermissions()
            val isHuaweiOk = huaweiAuthManager.isAuthorized()
            
            uiState = uiState.copy(
                isGoogleConnected = isGoogleOk,
                isHuaweiConnected = isHuaweiOk,
                syncStatus = if (isGoogleOk && isHuaweiOk) "Все системы в норме" else "Требуется настройка аккаунтов"
            )

            if (isGoogleOk && isHuaweiOk) {
                setupBackgroundSync()
            }
        }
    }

    // Настройка автоматического фонового планировщика раз в 1 час
    private fun setupBackgroundSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED) // Только при наличии интернета
            .build()

        val periodicWorkRequest = PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS)
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "OpenHealthSyncWorker",
            ExistingPeriodicWorkPolicy.KEEP, // Если задача уже крутится — не перезапускать её
            periodicWorkRequest
        )
    }
}