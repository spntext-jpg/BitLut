package com.openhealth.sync.ui
import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HuaweiAuthManager
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
    val googleHealthManager: GoogleHealthManager,
    val huaweiAuthManager: HuaweiAuthManager,
    private val prefs: android.content.SharedPreferences
) : ViewModel() {
    private val _uiState = MutableStateFlow(SyncUiState())
    val uiState: StateFlow<SyncUiState> = _uiState.asStateFlow()

    init { loadInitialState() }

    fun refreshStatuses() {
        viewModelScope.launch {
            _uiState.update { it.copy(
                hasGooglePermissions = googleHealthManager.hasAllPermissions(),
                isHuaweiAuthorized = huaweiAuthManager.isAuthorized()
            )}
        }
    }

    private fun loadInitialState() {
        viewModelScope.launch {
            _uiState.update { it.copy(
                isGoogleAvailable = googleHealthManager.checkAvailability() == 1,
                lastSyncTime = prefs.getString("last_sync_time", "Нет данных") ?: "Нет данных"
            )}
            refreshStatuses()
        }
    }

    fun markSyncStarted() { _uiState.update { it.copy(isSyncing = true, syncStatus = "Синхронизация...") } }

    fun markSyncCompleted(success: Boolean) {
        val statusMsg = if (success) "Успешно" else "Ошибка сети"
        val time = if (success) SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()) else _uiState.value.lastSyncTime
        if (success) prefs.edit().putString("last_sync_time", time).apply()
        _uiState.update { it.copy(isSyncing = false, syncStatus = statusMsg, lastSyncTime = time) }
    }

    companion object {
        fun provideFactory(gm: GoogleHealthManager, hm: HuaweiAuthManager, ctx: Context): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                return SyncViewModel(gm, hm, ctx.getSharedPreferences("sync_prefs", Context.MODE_PRIVATE)) as T
            }
        }
    }
}
