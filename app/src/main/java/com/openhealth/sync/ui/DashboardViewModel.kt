package com.openhealth.sync.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.config.DashboardWidget
import com.openhealth.sync.config.WidgetVisibilityPrefs
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.GoogleDashboardSnapshot
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.MetricBar
import com.openhealth.sync.data.WorkoutTypeSummary
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/** Selectable History range options, in days. Order matters for the chip row UI. */
val HISTORY_RANGE_OPTIONS = listOf(7, 14, 30, 60, 90, 180, 365)

data class DashboardUiState(
    val isLoading: Boolean = true,
    val hasPermissions: Boolean = false,
    val stepsToday: Long = 0L,
    val stepsGoal: Long = 10_000L,
    val distanceMeters: Double = 0.0,
    val caloriesKcal: Double = 0.0,
    val workoutMinutesToday: Long = 0L,
    val activeHoursToday: Int = 0,
    val stepsBars: List<MetricBar> = emptyList(),
    val sleepHours: Double = 0.0,
    val sleepQualityScore: Int? = null,
    val heartRateBpm: Long? = null,
    val heartRateTodayBars: List<MetricBar> = emptyList(),
    val stressScore: Int? = null,
    val spo2Percent: Double? = null,
    val sleepBars: List<MetricBar> = emptyList(),
    val heartRateBars: List<MetricBar> = emptyList(),
    val recentWorkouts: List<ActivitySessionData> = emptyList(),
    val selectedHistoryRangeDays: Int = 7,
    val workoutSummaries: List<WorkoutTypeSummary> = emptyList(),
    val visibleWidgets: Map<DashboardWidget, Boolean> = DashboardWidget.entries.associateWith { true }
) {
    val stepsProgress: Float get() = (stepsToday.toFloat() / stepsGoal.toFloat()).coerceIn(0f, 1f)

    fun isWidgetVisible(widget: DashboardWidget): Boolean = visibleWidgets[widget] ?: true
}

class DashboardViewModel(
    private val googleManager: GoogleHealthManager,
    private val widgetVisibilityPrefs: WidgetVisibilityPrefs
) : ViewModel() {

    private val _state = MutableStateFlow(
        DashboardUiState(visibleWidgets = widgetVisibilityPrefs.snapshot())
    )
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    private var loadJob: Job? = null
    private var loadGeneration: Long = 0L

    init { load() }

    fun refresh() { load() }

    /** Called when the person taps a different range chip (7/14/30/60/90/180/365) on History. */
    fun onHistoryRangeSelected(days: Int) {
        if (days == _state.value.selectedHistoryRangeDays) return
        _state.update { it.copy(selectedHistoryRangeDays = days) }
        load()
    }

    /** Called from the Settings widget-visibility toggles. Persists immediately and
     *  updates the in-memory state so Summary/History reflect the change without a
     *  full reload (no Health Connect calls needed — this is purely a display
     *  preference, not new data). */
    fun setWidgetVisible(widget: DashboardWidget, visible: Boolean) {
        widgetVisibilityPrefs.setVisible(widget, visible)
        _state.update { it.copy(visibleWidgets = it.visibleWidgets + (widget to visible)) }
    }

    fun load() {
        val generation = ++loadGeneration
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }

            val hasPerms = googleManager.hasAllPermissions()
            if (generation != loadGeneration) return@launch

            if (!hasPerms) {
                _state.update { it.copy(isLoading = false, hasPermissions = false) }
                return@launch
            }

            val previous = _state.value
            val rangeDays = previous.selectedHistoryRangeDays
            val snapshot = googleManager.readDashboardSnapshot(rangeDays)
            if (generation != loadGeneration) return@launch

            _state.update { current ->
                if (snapshot == null) {
                    current.copy(isLoading = false, hasPermissions = true)
                } else {
                    current.withSnapshot(snapshot)
                }
            }
        }
    }

    private fun DashboardUiState.withSnapshot(snapshot: GoogleDashboardSnapshot): DashboardUiState =
        copy(
            isLoading       = false,
            hasPermissions  = true,
            stepsToday      = snapshot.stepsToday,
            distanceMeters  = snapshot.distanceMeters,
            caloriesKcal    = snapshot.caloriesKcal,
            workoutMinutesToday = snapshot.workoutMinutesToday,
            activeHoursToday = snapshot.activeHoursToday,
            sleepHours      = snapshot.sleepHours,
            sleepQualityScore = snapshot.sleepQualityScore,
            heartRateBpm    = snapshot.heartRateBpm,
            heartRateTodayBars = snapshot.heartRateTodayBars.ifEmpty { heartRateTodayBars },
            stressScore     = snapshot.stressScore,
            spo2Percent     = snapshot.spo2Percent,
            sleepBars       = snapshot.sleepBars.ifEmpty { sleepBars },
            heartRateBars   = snapshot.heartRateBars.ifEmpty { heartRateBars },
            stepsBars       = snapshot.stepsBars.ifEmpty { stepsBars },
            recentWorkouts  = snapshot.recentWorkouts.ifEmpty { recentWorkouts },
            workoutSummaries = snapshot.workoutSummaries.ifEmpty { workoutSummaries }
        )

    companion object {
        fun provideFactory(
            googleManager: GoogleHealthManager,
            widgetVisibilityPrefs: WidgetVisibilityPrefs
        ): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    DashboardViewModel(googleManager, widgetVisibilityPrefs) as T
            }
    }
}
