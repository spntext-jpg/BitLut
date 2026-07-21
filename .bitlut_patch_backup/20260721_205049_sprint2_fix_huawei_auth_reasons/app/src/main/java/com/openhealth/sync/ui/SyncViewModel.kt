package com.openhealth.sync.ui
import com.openhealth.sync.data.HuaweiHealthReader
import com.openhealth.sync.data.HealthConnectManager

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.data.HealthConnectStatus
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
    val showImportScreen: Boolean = false,
    val hasGooglePermissions: Boolean = false,
    val needsPermissionRefresh: Boolean = false,
    val isHuaweiAuthorized: Boolean = false,
    val isHuaweiPendingApproval: Boolean = false,
    val isSyncing: Boolean = false,
    val syncStatus: String = "sync_status_idle",
    val lastSyncTime: String = "sync_no_data"
)

class SyncViewModel(
    val googleManager: HealthConnectManager,
    val huaweiHealthManager: HuaweiHealthReader,
    private val prefs: android.content.SharedPreferences
) : ViewModel() {

    private val _uiState = MutableStateFlow(SyncUiState())
    val uiState: StateFlow<SyncUiState> = _uiState.asStateFlow()

    init { refreshStatuses() }

    fun refreshStatuses() {
        viewModelScope.launch {
            val isAvailable = googleManager.getStatus() == HealthConnectStatus.AVAILABLE
            val hasPerms = googleManager.hasAllPermissions()
            val savedTime = prefs.getString("last_sync_time", "sync_no_data") ?: "sync_no_data"
            _uiState.update {
                it.copy(
                    isGoogleAvailable = isAvailable,
                    hasGooglePermissions = hasPerms,
                    needsPermissionRefresh = isAvailable && !hasPerms,
                    isHuaweiAuthorized = huaweiHealthManager.isAuthorized(),
                    isHuaweiPendingApproval = huaweiHealthManager.isPendingApproval(),
                    lastSyncTime = savedTime
                )
            }
        }
    }

    fun onHuaweiAuthorizationResult(success: Boolean) {
        _uiState.update {
            it.copy(
                isHuaweiAuthorized = success,
                syncStatus = if (success) "sync_status_success" else "sync_status_error"
            )
        }
    }

    fun showImportScreen() { _uiState.update { it.copy(showImportScreen = true) } }
    fun hideImportScreen() { _uiState.update { it.copy(showImportScreen = false) } }

    fun markSyncStarted() {
        _uiState.update { it.copy(isSyncing = true, syncStatus = "sync_status_syncing") }
    }

    fun markSyncCompleted(success: Boolean) {
        val statusMsg = if (success) "sync_status_success" else "sync_status_error"
        val time = if (success) SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()) else _uiState.value.lastSyncTime
        if (success) prefs.edit().putString("last_sync_time", time).apply()
        _uiState.update { it.copy(isSyncing = false, syncStatus = statusMsg, lastSyncTime = time) }
        refreshStatuses()
    }

    companion object {
        fun provideFactory(
            googleManager: HealthConnectManager,
            huaweiHealthManager: HuaweiHealthReader,
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
