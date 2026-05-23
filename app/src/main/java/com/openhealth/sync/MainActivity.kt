package com.openhealth.sync

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.getValue
import com.openhealth.sync.ui.main.MainScreen
import com.openhealth.sync.ui.main.MainUiState
import com.openhealth.sync.ui.theme.OpenHealthSyncTheme

class MainActivity : ComponentActivity() {
    
    // Временное состояние экрана для проверки работы UI (позже перенесем в ViewModel)
    private var uiState by mutableStateOf(MainUiState())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            OpenHealthSyncTheme {
                MainScreen(
                    uiState = uiState,
                    onConnectHuawei = {
                        // Логика авторизации в облаке Huawei (напишем позже)
                        uiState = uiState.copy(isHuaweiConnected = !uiState.isHuaweiConnected)
                    },
                    onConnectGoogle = {
                        // Логика подключения к Google Health Connect
                        uiState = uiState.copy(isGoogleConnected = !uiState.isGoogleConnected)
                    },
                    onSyncNow = {
                        // Запуск ручной синхронизации
                        uiState = uiState.copy(isSyncing = true, syncStatus = "Синхронизация данных...")
                    }
                )
            }
        }
    }
}