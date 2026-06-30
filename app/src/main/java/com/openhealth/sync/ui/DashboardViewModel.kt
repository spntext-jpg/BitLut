package com.openhealth.sync.ui
import com.openhealth.sync.data.HealthConnectManager

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.config.DashboardWidget
import com.openhealth.sync.config.WidgetVisibilityPrefs
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.DashboardSnapshotCache
import com.openhealth.sync.data.GoogleDashboardSnapshot
import com.openhealth.sync.data.MetricBar
import com.openhealth.sync.data.WorkoutTypeSummary
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

private const val TAG = "DashboardViewModel"

/** Selectable History range options, in days. Order matters for the chip row UI. */
val HISTORY_RANGE_OPTIONS = listOf(7, 14, 30, 60, 90, 180, 365)

data class DashboardUiState(
    /** True only while the very first load of this process is still in flight and
     *  there is no cached snapshot to show meanwhile. Once any data (cached or
     *  live) has been shown once, subsequent reloads no longer flip this back to
     *  true -- they refresh in place so the UI never flashes back to a loading
     *  or locked state on every pull-to-refresh / periodic sync. */
    val isLoading: Boolean = true,
    val hasPermissions: Boolean = false,
    /** True once we've completed at least one permission check in this process.
     *  Used by the UI to tell "we don't know yet" (still loading) apart from
     *  "we checked and Google Health really isn't connected" (show lock screen). */
    val permissionsChecked: Boolean = false,
    val isFromCache: Boolean = false,
    val lastUpdatedAtMs: Long = 0L,
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

    /** True only when we've actually checked permissions and confirmed they're
     *  missing -- never true purely because we're still loading. The UI should
     *  use this (not the raw absence of data) to decide whether to show the
     *  "Connect Google Health" lock screen. */
    val showConnectLockScreen: Boolean get() = permissionsChecked && !hasPermissions

    fun isWidgetVisible(widget: DashboardWidget): Boolean = visibleWidgets[widget] ?: true
}

class DashboardViewModel(
    private val googleManager: HealthConnectManager,
    private val widgetVisibilityPrefs: WidgetVisibilityPrefs,
    private val snapshotCache: DashboardSnapshotCache
) : ViewModel() {

    private val _state = MutableStateFlow(buildInitialState())
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

    /** Builds the very first state synchronously from whatever is on disk, so the
     *  first composition already shows the last known real data instead of a
     *  loading spinner or a "Connect Google Health" lock screen. This never
     *  blocks: SharedPreferences reads here are fast and local. */
    private fun buildInitialState(): DashboardUiState {
        val cached = try {
            snapshotCache.load()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to read cached dashboard snapshot: ${e.message}", e)
            null
        }

        val base = DashboardUiState(visibleWidgets = widgetVisibilityPrefs.snapshot())
        if (cached == null) return base

        return base.withSnapshot(cached.snapshot).copy(
            isLoading = true,
            // We have cached data, but we haven't actually confirmed permissions
            // are still granted in this process yet -- that happens in load().
            // hasPermissions stays true here (optimistic, last-known-good) so the
            // UI renders real numbers immediately; permissionsChecked stays false
            // so showConnectLockScreen still correctly reports "unknown" rather
            // than a hard "true" or "false".
            hasPermissions = true,
            permissionsChecked = false,
            isFromCache = true,
            lastUpdatedAtMs = cached.savedAtMs
        )
    }

    fun load() {
        val generation = ++loadGeneration
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            val hasPerms = try {
                googleManager.hasAllPermissions()
            } catch (e: Exception) {
                AppLogger.e(TAG, "Permission check threw; keeping last known dashboard state: ${e.message}", e)
                // A transient failure here must not yank a working dashboard back
                // to the lock screen. Bail out and keep whatever is currently shown.
                _state.update { it.copy(isLoading = false) }
                return@launch
            }
            if (generation != loadGeneration) return@launch

            if (!hasPerms) {
                _state.update {
                    it.copy(
                        isLoading = false,
                        hasPermissions = false,
                        permissionsChecked = true
                    )
                }
                return@launch
            }

            val previous = _state.value
            val rangeDays = previous.selectedHistoryRangeDays
            val snapshot = googleManager.readDashboardSnapshot(rangeDays)
            if (generation != loadGeneration) return@launch

            _state.update { current ->
                if (snapshot == null) {
                    // Health Connect is reachable and permissions are granted, but this
                    // particular read failed transiently. Keep showing the last good
                    // data (cached or previously loaded) rather than blanking the UI.
                    current.copy(isLoading = false, hasPermissions = true, permissionsChecked = true)
                } else {
                    snapshotCache.save(snapshot)
                    current.withSnapshot(snapshot).copy(
                        hasPermissions = true,
                        permissionsChecked = true,
                        isFromCache = false,
                        lastUpdatedAtMs = System.currentTimeMillis()
                    )
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
            googleManager: HealthConnectManager,
            widgetVisibilityPrefs: WidgetVisibilityPrefs,
            snapshotCache: DashboardSnapshotCache
        ): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    DashboardViewModel(googleManager, widgetVisibilityPrefs, snapshotCache) as T
            }
    }
}
