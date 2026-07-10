package com.openhealth.sync.ui
import com.openhealth.sync.data.HealthConnectManager

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.config.DashboardWidget
import com.openhealth.sync.config.GoalPrefs
import com.openhealth.sync.config.WidgetVisibilityPrefs
import com.openhealth.sync.data.AchievementsStore
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.DashboardSnapshotCache
import com.openhealth.sync.data.GoogleDashboardSnapshot
import com.openhealth.sync.data.MetricBar
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison
import com.openhealth.sync.data.WorkoutTypeSummary
import com.openhealth.sync.util.AppLogger
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.CancellationException
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
    /** Sourced from [GoalPrefs] (v1.9.12), configurable in Settings. Defaults
     *  to [GoalPrefs.DEFAULT_STEPS_GOAL], matching the value this field was
     *  hardcoded to before goals became configurable, so existing installs
     *  see no change until they explicitly set a custom goal. */
    val stepsGoal: Long = GoalPrefs.DEFAULT_STEPS_GOAL,
    val distanceGoalMeters: Double = GoalPrefs.DEFAULT_DISTANCE_GOAL_METERS,
    val activeMinutesGoal: Int = GoalPrefs.DEFAULT_ACTIVE_MINUTES_GOAL,
    val caloriesGoalKcal: Double = GoalPrefs.DEFAULT_CALORIES_GOAL,
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
    val visibleWidgets: Map<DashboardWidget, Boolean> = DashboardWidget.entries.associateWith { true },
    // ── Sprint 4: insights & trends (activity-only) ──────────────────────
    val weekComparison: WeekComparison? = null,
    val bestStepsDay: PersonalRecord? = null,
    val bestDistanceDay: PersonalRecord? = null,
    val streak: StreakState = StreakState(currentStreakDays = 0, longestStreakDays = 0, lastCountedDate = null)
) {
    val stepsProgress: Float get() = (stepsToday.toFloat() / stepsGoal.toFloat()).coerceIn(0f, 1f)
    val distanceProgress: Float get() = (distanceMeters / distanceGoalMeters).toFloat().coerceIn(0f, 1f)
    val activeMinutesProgress: Float get() = (workoutMinutesToday.toFloat() / activeMinutesGoal.toFloat()).coerceIn(0f, 1f)
    val caloriesProgress: Float get() = (caloriesKcal / caloriesGoalKcal).toFloat().coerceIn(0f, 1f)

    /** True only when we've actually checked permissions and confirmed they're
     *  missing -- never true purely because we're still loading. The UI should
     *  use this (not the raw absence of data) to decide whether to show the
     *  "Connect Google Health" lock screen. */
    val showConnectLockScreen: Boolean get() = permissionsChecked && !hasPermissions

    fun isWidgetVisible(widget: DashboardWidget): Boolean = visibleWidgets[widget] ?: true

    /** True if today's steps total is itself an all-time record in the making
     *  (i.e. already at or beyond the previously stored best). Used to show a
     *  small "new record" badge live, without waiting for the next sync to
     *  persist it via [AchievementsStore.recordDailyTotals]. */
    val isStepsRecordToday: Boolean get() = bestStepsDay != null && stepsToday >= bestStepsDay.value && stepsToday > 0L
}

class DashboardViewModel(
    private val googleManager: HealthConnectManager,
    private val widgetVisibilityPrefs: WidgetVisibilityPrefs,
    private val snapshotCache: DashboardSnapshotCache,
    private val goalPrefs: GoalPrefs,
    private val achievementsStore: AchievementsStore
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

    /** Called from the Settings goals editor (v1.9.12, sprint 7). Persists
     *  immediately and updates in-memory state so progress rings/percentages
     *  reflect the new goal right away, without a Health Connect round-trip. */
    fun setStepsGoal(value: Long) {
        goalPrefs.setStepsGoal(value)
        _state.update { it.copy(stepsGoal = value) }
    }

    fun setDistanceGoalMeters(value: Double) {
        goalPrefs.setDistanceGoalMeters(value)
        _state.update { it.copy(distanceGoalMeters = value) }
    }

    fun setActiveMinutesGoal(value: Int) {
        goalPrefs.setActiveMinutesGoal(value)
        _state.update { it.copy(activeMinutesGoal = value) }
    }

    fun setCaloriesGoalKcal(value: Double) {
        goalPrefs.setCaloriesGoalKcal(value)
        _state.update { it.copy(caloriesGoalKcal = value) }
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

        val goalsBase = readGoalsIntoState(DashboardUiState(visibleWidgets = widgetVisibilityPrefs.snapshot()))
        val base = readAchievementsIntoState(goalsBase)
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

    private fun readGoalsIntoState(state: DashboardUiState): DashboardUiState = state.copy(
        stepsGoal = goalPrefs.stepsGoal(),
        distanceGoalMeters = goalPrefs.distanceGoalMeters(),
        activeMinutesGoal = goalPrefs.activeMinutesGoal(),
        caloriesGoalKcal = goalPrefs.caloriesGoalKcal()
    )

    private fun readAchievementsIntoState(state: DashboardUiState): DashboardUiState = try {
        state.copy(
            bestStepsDay = achievementsStore.bestStepsDay(),
            bestDistanceDay = achievementsStore.bestDistanceMetersDay(),
            streak = achievementsStore.readStreak()
        )
    } catch (e: Exception) {
        AppLogger.e(TAG, "Failed to read achievements: ${e.message}", e)
        state
    }

    fun load() {
        val generation = ++loadGeneration
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            val hasPerms = try {
                googleManager.hasAllPermissions()
            } catch (e: CancellationException) {
                // Sprint (2026-07-10): load() cancels its own previous job
                // (loadJob?.cancel()) whenever it's called again before the
                // prior call finished -- now a routine, frequent occurrence
                // thanks to sync-on-resume, the refresh button, and
                // sync-completion callbacks all calling load() in quick
                // succession. Without this guard, that expected cancellation
                // was being caught by the generic Exception branch below,
                // logged as "Permission check threw" (log noise, seen on a
                // real device log right after a routine resume), and -- worse
                // -- forcing isLoading=false on a job that was only ever
                // superseded, not actually failed. CancellationException must
                // always propagate for structured concurrency to work
                // correctly; re-throwing it here is required, not optional.
                throw e
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
                    updateAchievementsFor(snapshot)
                    readAchievementsIntoState(
                        current.withSnapshot(snapshot).copy(
                            hasPermissions = true,
                            permissionsChecked = true,
                            isFromCache = false,
                            lastUpdatedAtMs = System.currentTimeMillis()
                        )
                    )
                }
            }

            // Sprint (2026-07-10): week-over-week comparison fed a card that
            // was removed from the Today screen in an earlier sprint, but
            // this call kept firing on every single load() anyway -- 2 more
            // wasted Health Connect calls (current + previous week
            // aggregates) contributing to the rate-limit cascade seen in a
            // real device log once sync-on-resume made load() run far more
            // often than before.
        }
    }

    /** Mirrors what SyncWorker does after a successful background sync, so
     *  manual refreshes (tapping "Обновить"/pull-to-refresh) also keep
     *  records/streaks current -- not just the periodic 30-minute sync. */
    private fun updateAchievementsFor(snapshot: GoogleDashboardSnapshot) {
        try {
            val today = LocalDate.now()
            achievementsStore.recordDailyTotals(
                date = today,
                stepsToday = snapshot.stepsToday,
                distanceMetersToday = snapshot.distanceMeters
            )
            val goalMet = _state.value.stepsGoal > 0 && snapshot.stepsToday >= _state.value.stepsGoal
            achievementsStore.updateStreak(today, goalMet)
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to update achievements from manual refresh: ${e.message}", e)
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
            snapshotCache: DashboardSnapshotCache,
            goalPrefs: GoalPrefs,
            achievementsStore: AchievementsStore
        ): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    DashboardViewModel(googleManager, widgetVisibilityPrefs, snapshotCache, goalPrefs, achievementsStore) as T
            }
    }
}
