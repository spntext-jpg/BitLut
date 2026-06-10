package com.openhealth.sync.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.GoogleHealthManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate

data class WeeklyBar(val date: LocalDate, val steps: Long)

data class DashboardUiState(
    val isLoading: Boolean = true,
    val hasPermissions: Boolean = false,
    val stepsToday: Long = 0L,
    val stepsGoal: Long = 10_000L,
    val distanceMeters: Double = 0.0,
    val caloriesKcal: Double = 0.0,
    val weeklySteps: List<WeeklyBar> = emptyList(),
    val recentWorkouts: List<ActivitySessionData> = emptyList()
) {
    val stepsProgress: Float get() = (stepsToday.toFloat() / stepsGoal.toFloat()).coerceIn(0f, 1f)
    val weeklyAvg: Long get() = if (weeklySteps.isEmpty()) 0L else weeklySteps.sumOf { it.steps } / weeklySteps.size
}

class DashboardViewModel(
    private val googleManager: GoogleHealthManager
) : ViewModel() {

    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init { load() }

    fun refresh() { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            val hasPerms = googleManager.hasAllPermissions()
            if (!hasPerms) {
                _state.update { it.copy(isLoading = false, hasPermissions = false) }
                return@launch
            }
            val steps    = googleManager.readStepsToday()
            val distance = googleManager.readDistanceToday()
            val calories = googleManager.readCaloriesToday()
            val weekly   = googleManager.readWeeklySteps().map { (date, s) -> WeeklyBar(date, s) }
            val workouts = googleManager.readRecentWorkouts(5)
            _state.update {
                it.copy(
                    isLoading       = false,
                    hasPermissions  = true,
                    stepsToday      = steps,
                    distanceMeters  = distance,
                    caloriesKcal    = calories,
                    weeklySteps     = weekly,
                    recentWorkouts  = workouts
                )
            }
        }
    }

    companion object {
        fun provideFactory(googleManager: GoogleHealthManager): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    DashboardViewModel(googleManager) as T
            }
    }
}
