package com.openhealth.sync.ui
import com.openhealth.sync.config.DataSourcePrefs
import com.openhealth.sync.config.HealthDataSource
import com.openhealth.sync.data.HuaweiHealthReader
import com.openhealth.sync.data.HuaweiAuthFailureReason
import com.openhealth.sync.data.HealthConnectManager

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.data.HealthConnectStatus
import kotlinx.coroutines.Job
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
    val lastHuaweiAuthFailureReason: HuaweiAuthFailureReason? = null,
    val selectedDataSource: HealthDataSource = HealthDataSource.HUAWEI_HEALTH,
    // 2026-08-31: isSyncing (below) is now the OR of these two independent
    // raw signals -- see its own doc comment for why a single flag wasn't
    // enough. Not private: SyncViewModel's markSyncStarted()/
    // markSyncCompleted()/setBackgroundSyncActive() need to set these via
    // copy(), and a private constructor property's generated copy()
    // parameter is only accessible from inside this class, not from
    // SyncViewModel even though it lives in the same file -- Kotlin scopes
    // member visibility to the class, not the file. Callers outside this
    // file should still read isSyncing, not these two fields directly.
    val isUiTriggeredSyncing: Boolean = false,
    val isBackgroundSyncActive: Boolean = false,
    val syncStatus: String = "sync_status_idle",
    val lastSyncTime: String = "sync_no_data"
) {
    /**
     * True while the "Syncing..." indicator should show. Previously this was
     * one flag, flipped only by SyncViewModel.markSyncStarted()/
     * markSyncCompleted(), which MainActivity calls only from its two
     * UI-triggered sync paths (manual refresh, auto-sync-on-launch). A real
     * device log showed that signal alone is not reliable: when the
     * periodic background SyncWorker happens to win the sync-run lease
     * race, the UI-triggered attempt gets deferred by SyncReliability's
     * lease check almost immediately, so its own started->completed pair
     * can collapse to well under a second -- too fast to ever render a
     * fade-in -- while the periodic worker actually doing the real,
     * multi-second sync has no path to this flag at all. isBackgroundSyncActive
     * (fed from a WorkManager tag observer in MainActivity, see
     * HuaweiConfig.SYNC_ACTIVITY_TAG) reflects "is any SyncWorker instance,
     * whichever one, actually RUNNING or ENQUEUED right now" regardless of
     * which path triggered it, so the indicator now shows for the sync that
     * is really doing the work.
     */
    val isSyncing: Boolean get() = isUiTriggeredSyncing || isBackgroundSyncActive
}

class SyncViewModel(
    val googleManager: HealthConnectManager,
    val huaweiHealthManager: HuaweiHealthReader,
    private val prefs: android.content.SharedPreferences,
    private val dataSourcePrefs: DataSourcePrefs
) : ViewModel() {

    private val _uiState = MutableStateFlow(SyncUiState())
    val uiState: StateFlow<SyncUiState> = _uiState.asStateFlow()

    private var statusJob: Job? = null
    private var lastStatusRefreshAtMs: Long = 0L

    init { refreshStatuses(force = true) }

    fun refreshStatuses(force: Boolean = false) {
        val now = System.currentTimeMillis()
        if (!force && statusJob?.isActive == true) return
        if (!force && now - lastStatusRefreshAtMs < STATUS_REFRESH_MIN_INTERVAL_MS) return
        lastStatusRefreshAtMs = now
        statusJob = viewModelScope.launch {
            val isAvailable = googleManager.getStatus() == HealthConnectStatus.AVAILABLE
            val hasPerms = googleManager.hasAllPermissions()
            val savedTime = prefs.getString("last_sync_time", "sync_no_data") ?: "sync_no_data"
            _uiState.update {
                it.copy(
                    isGoogleAvailable = isAvailable,
                    hasGooglePermissions = hasPerms,
                    needsPermissionRefresh = isAvailable && !hasPerms,
                    isHuaweiAuthorized = huaweiHealthManager.isAuthorized(),
                    lastHuaweiAuthFailureReason = huaweiHealthManager.lastAuthFailureReason(),
                    selectedDataSource = dataSourcePrefs.selected(),
                    lastSyncTime = savedTime
                )
            }
        }
    }

    fun onHuaweiAuthorizationResult(success: Boolean) {
        _uiState.update {
            it.copy(
                isHuaweiAuthorized = success,
                lastHuaweiAuthFailureReason = if (success) null else huaweiHealthManager.lastAuthFailureReason(),
                syncStatus = if (success) "sync_status_success" else "sync_status_error"
            )
        }
    }

    fun showImportScreen() { _uiState.update { it.copy(showImportScreen = true) } }
    fun hideImportScreen() { _uiState.update { it.copy(showImportScreen = false) } }

    fun setDataSource(source: HealthDataSource) {
        dataSourcePrefs.setSelected(source)
        _uiState.update { it.copy(selectedDataSource = source) }
    }

    fun markSyncStarted() {
        _uiState.update { it.copy(isUiTriggeredSyncing = true, syncStatus = "sync_status_syncing") }
    }

    fun markSyncCompleted(success: Boolean) {
        val statusMsg = if (success) "sync_status_success" else "sync_status_error"
        val time = if (success) SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()) else _uiState.value.lastSyncTime
        if (success) prefs.edit().putString("last_sync_time", time).apply()
        _uiState.update { it.copy(isUiTriggeredSyncing = false, syncStatus = statusMsg, lastSyncTime = time) }
        // Do not re-query Health Connect permissions here. A completed sync
        // already proved the provider path; repeating the permission snapshot
        // was one contributor to the quota storm.
    }

    /**
     * Fed by MainActivity's WorkManager tag observer (HuaweiConfig.
     * SYNC_ACTIVITY_TAG) -- see SyncUiState.isSyncing's doc comment for why
     * this exists alongside markSyncStarted()/markSyncCompleted(). Does not
     * touch syncStatus: that field carries a specific outcome message
     * (success/error) that only the UI-triggered path, which actually
     * observes a result, can meaningfully report.
     */
    fun setBackgroundSyncActive(active: Boolean) {
        _uiState.update { it.copy(isBackgroundSyncActive = active) }
    }

    companion object {
        private const val STATUS_REFRESH_MIN_INTERVAL_MS = 10_000L

        fun provideFactory(
            googleManager: HealthConnectManager,
            huaweiHealthManager: HuaweiHealthReader,
            context: Context,
            dataSourcePrefs: DataSourcePrefs
        ): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                val prefs = context.getSharedPreferences("sync_prefs", Context.MODE_PRIVATE)
                return SyncViewModel(googleManager, huaweiHealthManager, prefs, dataSourcePrefs) as T
            }
        }
    }
}
