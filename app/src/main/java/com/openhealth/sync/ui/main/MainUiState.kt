package com.openhealth.sync.ui.main

import com.openhealth.sync.data.HealthConnectStatus

data class MainUiState(
    val isGoogleConnected: Boolean = false,
    val isHuaweiConnected: Boolean = false,
    val isHuaweiConfigured: Boolean = false,
    val isSyncing: Boolean = false,
    val syncStatus: String = "Инициализация...",
    val lastSyncTime: String = "—",
    val healthConnectStatus: HealthConnectStatus = HealthConnectStatus.NOT_INSTALLED,
    val showLogs: Boolean = false
)
