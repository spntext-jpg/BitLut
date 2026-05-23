package com.openhealth.sync

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import androidx.lifecycle.lifecycleScope
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.ui.main.MainScreen
import com.openhealth.sync.ui.main.MainUiState
import com.openhealth.sync.ui.theme.OpenHealthSyncTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    
    private val googleHealthManager by lazy { GoogleHealthManager(this) }
    private var uiState by mutableStateOf(MainUiState())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            // Создаем триггер для вызова системного окна разрешений Health Connect
            val requestPermissionsLauncher = rememberLauncherForActivityResult(
                PermissionController.createRequestPermissionResultContract()
            ) { grantedPermissions ->
                val allGranted = grantedPermissions.containsAll(googleHealthManager.permissions)
                uiState = uiState.copy(
                    isGoogleConnected = allGranted,
                    syncStatus = if (allGranted) "Google Health Connect подключен" else "Доступ к Google Health отклонен"
                )
            }

            // Проверяем статус при запуске экрана
            LaunchedEffect(Unit) {
                checkGoogleStatus()
            }

            OpenHealthSyncTheme {
                MainScreen(
                    uiState = uiState,
                    onConnectHuawei = {
                        // Логика авторизации в облаке Huawei (следующий этап)
                        uiState = uiState.copy(isHuaweiConnected = !uiState.isHuaweiConnected)
                    },
                    onConnectGoogle = {
                        when (googleHealthManager.checkHealthConnectStatus()) {
                            HealthConnectClient.SDK_AVAILABLE -> {
                                // Запускаем системное окно запроса прав
                                requestPermissionsLauncher.launch(googleHealthManager.permissions)
                            }
                            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> {
                                Toast.makeText(this@MainActivity, "Необходимо обновить Google Health Connect", Toast.LENGTH_LONG).show()
                            }
                            else -> {
                                Toast.makeText(this@MainActivity, "Health Connect недоступен на этом устройстве. Установите его из Google Play.", Toast.LENGTH_LONG).show()
                            }
                        }
                    },
                    onSyncNow = {
                        uiState = uiState.copy(isSyncing = true, syncStatus = "Синхронизация данных...")
                    }
                )
            }
        }
    }

    private fun checkGoogleStatus() {
        lifecycleScope.launch {
            val isConnected = googleHealthManager.hasAllPermissions()
            uiState = uiState.copy(isGoogleConnected = isConnected)
        }
    }
}