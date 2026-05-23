package com.openhealth.sync.ui.main

data class MainUiState(
    val syncStatus: String = "Все системы в норме",
    val lastSyncTime: String = "Не синхронизировалось",
    val isHuaweiConnected: Boolean = false,
    val isGoogleConnected: Boolean = false,
    val isSyncing: Boolean = false
)