package com.openhealth.sync.ui

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HealthConnectStatus
import com.openhealth.sync.data.HuaweiHealthManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class SyncUiState(
    val isGoogleAvailable: Boolean = false,
    val hasGooglePermissions: Boolean = false,
    val isHuaweiAuthorized: Boolean = false,
    val isSyncing: Boolean = false,
    val syncStatus: String = "Ожидание действия",
    val lastSyncTime: String = "Нет данных"
)

class SyncViewModel(
    val googleManager: GoogleHealthManager,
    val huaweiHealthManager: HuaweiHealthManager,
    private val prefs: android.content.SharedPreferences
) : ViewModel() {

    private val _uiState = MutableStateFlow(SyncUiState())
    val uiState: StateFlow<SyncUiState> = _uiState.asStateFlow()

    init { refreshStatuses() }

    fun refreshStatuses() {
        viewModelScope.launch {
            val isAvailable = googleManager.getStatus() == HealthConnectStatus.AVAILABLE
            val hasPerms = googleManager.hasAllPermissions()
            val savedTime = prefs.getString("last_sync_time", "Нет данных") ?: "Нет данных"
            _uiState.update {
                it.copy(
                    isGoogleAvailable = isAvailable,
                    hasGooglePermissions = hasPerms,
                    isHuaweiAuthorized = huaweiHealthManager.isAuthorized(),
                    lastSyncTime = savedTime
                )
            }
        }
    }

    fun onHuaweiAuthorizationResult(success: Boolean) {
        _uiState.update {
            it.copy(
                isHuaweiAuthorized = success,
                syncStatus = if (success) "Huawei подключен" else "Ошибка авторизации Huawei"
            )
        }
    }

    fun markSyncStarted() {
        _uiState.update { it.copy(isSyncing = true, syncStatus = "Синхронизация...") }
    }

    fun markSyncCompleted(success: Boolean) {
        val statusMsg = if (success) "Успешно" else "Ошибка"
        val time = if (success) SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()) else _uiState.value.lastSyncTime
        if (success) prefs.edit().putString("last_sync_time", time).apply()
        _uiState.update { it.copy(isSyncing = false, syncStatus = statusMsg, lastSyncTime = time) }
        refreshStatuses()
    }

    companion object {
        fun provideFactory(
            googleManager: GoogleHealthManager,
            huaweiHealthManager: HuaweiHealthManager,
            context: Context
        ): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                val prefs = context.getSharedPreferences("sync_prefs", Context.MODE_PRIVATE)
                return SyncViewModel(googleManager, huaweiHealthManager, prefs) as T
            }
        }
    }
}
