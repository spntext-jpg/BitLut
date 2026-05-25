package com.openhealth.sync.ui
import androidx.lifecycle.*
import com.openhealth.sync.data.*
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class SyncViewModel(
    private val googleManager: GoogleHealthManager,
    private val huaweiManager: HuaweiAuthManager
) : ViewModel() {
    private val _uiState = MutableStateFlow(SyncUiState())
    val uiState = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            val isAvailable = googleManager.getStatus() == HealthConnectStatus.AVAILABLE
            _uiState.update { it.copy(isGoogleAvailable = isAvailable) }
        }
    }
}
data class SyncUiState(val isGoogleAvailable: Boolean = false)
