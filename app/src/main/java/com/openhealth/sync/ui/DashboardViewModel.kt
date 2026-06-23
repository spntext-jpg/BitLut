package com.openhealth.sync.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.WorkoutTypeSummary
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate

data class WeeklyBar(val date: LocalDate, val steps: Long)
data class WeeklyMetric(val date: LocalDate, val value: Double?)

/** Selectable History range options, in days. Order matters for the chip row UI. */
val HISTORY_RANGE_OPTIONS = listOf(7, 14, 30, 60, 90, 180, 365)

data class DashboardUiState(
    val isLoading: Boolean = true,
    val hasPermissions: Boolean = false,
    val stepsToday: Long = 0L,
    val stepsGoal: Long = 10_000L,
    val distanceMeters: Double = 0.0,
    val caloriesKcal: Double = 0.0,
    val weeklySteps: List<WeeklyBar> = emptyList(),
    val sleepHours: Double = 0.0,
    val heartRateBpm: Long? = null,
    val weeklySleep: List<WeeklyMetric> = emptyList(),
    val weeklyHeartRate: List<WeeklyMetric> = emptyList(),
    val recentWorkouts: List<ActivitySessionData> = emptyList(),
    val selectedHistoryRangeDays: Int = 7,
    val workoutSummaries: List<WorkoutTypeSummary> = emptyList()
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

    /** Called when the person taps a different range chip (7/14/30/60/90/180/365) on History. */
    fun onHistoryRangeSelected(days: Int) {
        if (days == _state.value.selectedHistoryRangeDays) return
        _state.update { it.copy(selectedHistoryRangeDays = days) }
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            val hasPerms = googleManager.hasAllPermissions()
            if (!hasPerms) {
                _state.update { it.copy(isLoading = false, hasPermissions = false) }
                return@launch
            }
            val rangeDays = _state.value.selectedHistoryRangeDays
            val steps    = googleManager.readStepsToday()
            val distance = googleManager.readDistanceToday()
            val calories = googleManager.readCaloriesToday()
            val weekly   = googleManager.readDailySteps(rangeDays).map { (date, s) -> WeeklyBar(date, s) }
            val sleep    = googleManager.readSleepLastNight()
            val heart     = googleManager.readAverageHeartRateToday()
            val weeklySleep = googleManager.readDailySleep(rangeDays).map { (date, value) -> WeeklyMetric(date, value) }
            val weeklyHeart = googleManager.readDailyAverageHeartRate(rangeDays).map { (date, value) -> WeeklyMetric(date, value?.toDouble()) }
            val workouts = googleManager.readRecentWorkouts(5)
            val workoutSummaries = googleManager.readWorkoutSummariesByType(rangeDays)
            _state.update {
                it.copy(
                    isLoading       = false,
                    hasPermissions  = true,
                    stepsToday      = steps,
                    distanceMeters  = distance,
                    caloriesKcal    = calories,
                    sleepHours      = sleep,
                    heartRateBpm    = heart,
                    weeklySleep     = weeklySleep,
                    weeklyHeartRate = weeklyHeart,
                    weeklySteps     = weekly,
                    recentWorkouts  = workouts,
                    workoutSummaries = workoutSummaries
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
