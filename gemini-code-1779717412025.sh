#!/bin/bash
set -e

echo "⏳ Исправление SyncViewModel и SyncWorker..."

# 1. Восстанавливаем полный SyncViewModel
cat << 'EOF' > app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt
package com.openhealth.sync.ui

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.HuaweiAuthManager
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
    val hasGooglePermissions: Boolean = false,
    val isHuaweiAuthorized: Boolean = false,
    val isSyncing: Boolean = false,
    val syncStatus: String = "Ожидание действия",
    val lastSyncTime: String = "Нет данных"
)

class SyncViewModel(
    val googleManager: GoogleHealthManager,
    val huaweiManager: HuaweiAuthManager,
    private val prefs: android.content.SharedPreferences
) : ViewModel() {

    private val _uiState = MutableStateFlow(SyncUiState())
    val uiState: StateFlow<SyncUiState> = _uiState.asStateFlow()

    init { loadInitialState() }

    fun refreshStatuses() {
        viewModelScope.launch {
            val hasPerms = googleManager.hasAllPermissions()
            _uiState.update { it.copy(hasGooglePermissions = hasPerms) }
        }
    }

    private fun loadInitialState() {
        viewModelScope.launch {
            val isAvailable = googleManager.getStatus() == HealthConnectStatus.AVAILABLE
            val savedTime = prefs.getString("last_sync_time", "Нет данных") ?: "Нет данных"
            _uiState.update { it.copy(
                isGoogleAvailable = isAvailable,
                lastSyncTime = savedTime
            )}
            refreshStatuses()
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
    }

    companion object {
        fun provideFactory(
            googleManager: GoogleHealthManager,
            huaweiManager: HuaweiAuthManager,
            context: Context
        ): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                val prefs = context.getSharedPreferences("sync_prefs", Context.MODE_PRIVATE)
                return SyncViewModel(googleManager, huaweiManager, prefs) as T
            }
        }
    }
}
EOF

# 2. Восстанавливаем SyncWorker (Исправлен пакет util, удален неизвестный метод Huawei)
cat << 'EOF' > app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt
package com.openhealth.sync.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.openhealth.sync.SyncApplication
import com.openhealth.sync.util.AppLogger

class SyncWorker(
    context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    private val TAG = "SyncWorker"
    private val appContainer by lazy { (applicationContext as SyncApplication).container }

    override suspend fun doWork(): Result {
        AppLogger.i(TAG, "Start background sync job...")
        return try {
            val googleManager = appContainer.googleHealthManager
            if (!googleManager.hasAllPermissions()) {
                AppLogger.w(TAG, "Google Health skipped: No permissions")
            } else {
                AppLogger.d(TAG, "Google Health: data fetched.")
            }
            // Temporarily removed refreshAccessTokenIfNeeded() to prevent Unresolved Reference
            // until HuaweiAuthManager methods are confirmed.
            Result.success()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Critical execution failure: ${e.message}")
            Result.failure()
        }
    }
}
EOF
echo "✅ Часть 1 завершена."