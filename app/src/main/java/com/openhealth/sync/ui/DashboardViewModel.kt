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
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison
import com.openhealth.sync.util.AppLogger
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import com.openhealth.sync.data.AchievementSummary

private const val TAG = "DashboardViewModel"

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
    val recentWorkouts: List<ActivitySessionData> = emptyList(),
    val visibleWidgets: Map<DashboardWidget, Boolean> = DashboardWidget.entries.associateWith { true },
    // ── Sprint 4: insights & trends (activity-only) ──────────────────────
    val weekComparison: WeekComparison? = null,
    val bestStepsDay: PersonalRecord? = null,
    val bestDistanceDay: PersonalRecord? = null,
    val bestCaloriesDay: PersonalRecord? = null,
    val bestElevationDay: PersonalRecord? = null,
    val bestWorkoutDuration: PersonalRecord? = null,
    val achievementSummary: AchievementSummary = AchievementSummary(),
    val elevationMetersToday: Double = 0.0,
    val floorsToday: Double = 0.0,
    val elevationMeters7d: Double = 0.0,
    val floors7d: Double = 0.0,
    val averageSteps7d: Long = 0L,
    val bestStepsDay7d: PersonalRecord? = null,
    val stepsChangeVsPrevious7d: Int? = null,
    val streak: StreakState = StreakState(currentStreakDays = 0, longestStreakDays = 0, lastCountedDate = null)
) {
    val stepsProgress: Float get() = (stepsToday.toFloat() / stepsGoal.toFloat()).coerceIn(0f, 1f)
    val distanceProgress: Float get() = (distanceMeters / distanceGoalMeters).toFloat().coerceIn(0f, 1f)
    // activeMinutesProgress/caloriesProgress removed (2026-08): their only
    // consumer was the removed activity-rings card (see DashboardCardType's
    // doc comment in DashboardCardLayoutPrefs.kt for why). workoutMinutesToday
    // and caloriesKcal themselves are untouched -- still real, synced data,
    // just no longer paired with a goal-progress fraction nothing reads.

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
    private var lastLiveLoadStartedAtMs: Long = 0L

    init {
        // A warm cache is already the last successful SyncWorker snapshot.
        // Do not immediately duplicate that background read on every cold
        // launch; automatic sync will refresh the cache and notify this VM.
        val hasWarmCache = try { snapshotCache.load() != null } catch (_: Exception) { false }
        if (!hasWarmCache) load(force = true)
    }

    fun refresh(force: Boolean = false) { load(force) }

    /**
     * SyncWorker refreshes DashboardSnapshotCache before WorkManager reports
     * success. UI completion callbacks should consume that snapshot locally
     * instead of issuing another identical Health Connect read.
     */
    fun refreshFromCache() {
        val cached = try {
            snapshotCache.load()
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to read post-sync dashboard cache: ${e.message}", e)
            null
        } ?: return

        _state.update { current ->
            readAchievementsIntoState(
                current.withSnapshot(cached.snapshot).copy(
                    isLoading = false,
                    hasPermissions = true,
                    permissionsChecked = true,
                    isFromCache = false,
                    lastUpdatedAtMs = cached.dataChangedAtMs
                )
            )
        }
    }

    /** Rebuilds state from the newly selected source's own cache and achievement
     *  namespace before starting a live Health Connect read. This prevents even
     *  a single frame of Huawei totals/workouts being shown after switching to
     *  Google Fit, or vice versa. */
    fun onDataSourceChanged() {
        loadJob?.cancel()
        _state.value = buildInitialState()
        load(force = true)
    }

    /** Called from the Settings widget-visibility toggles. Persists immediately and
     *  updates the in-memory state so Summary reflects the change without a
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

        val cachedDate = Instant.ofEpochMilli(cached.savedAtMs).atZone(ZoneId.systemDefault()).toLocalDate()
        val isStaleAcrossMidnight = cachedDate.isBefore(LocalDate.now())

        val withCachedSnapshot = base.withSnapshot(cached.snapshot).copy(
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
            lastUpdatedAtMs = cached.dataChangedAtMs
        )

        if (!isStaleAcrossMidnight) return withCachedSnapshot

        // Sprint 2026-08-26: the cache was last written on a previous
        // calendar day (e.g. the app was closed overnight). Showing
        // yesterday's steps/distance/calories as if they were today's is
        // misleading -- a new day has genuinely started with zero activity
        // so far. recentWorkouts is left untouched: a workout from
        // yesterday is still real, valid history and belongs in the
        // "previous workout" card regardless of what day it is now. Only
        // the daily-total fields reset to their zero defaults, and only
        // until the next live sync (already scheduled via the periodic
        // worker, or triggered by load() right after this) replaces them
        // with real numbers for the new day.
        AppLogger.i(
            TAG,
            "Cached snapshot is from $cachedDate, before today (${LocalDate.now()}) -- " +
                "showing zeroed daily totals until the next sync completes"
        )
        return withCachedSnapshot.copy(
            stepsToday = 0L,
            distanceMeters = 0.0,
            caloriesKcal = 0.0,
            workoutMinutesToday = 0L,
            activeHoursToday = 0,
            elevationMetersToday = 0.0,
            floorsToday = 0.0
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
            bestCaloriesDay = achievementsStore.bestCaloriesDay(),
            bestElevationDay = achievementsStore.bestElevationMetersDay(),
            bestWorkoutDuration = achievementsStore.bestWorkoutDurationMinutes(),
            achievementSummary = achievementsStore.achievementSummary(),
            streak = achievementsStore.readStreak()
        )
    } catch (e: Exception) {
        AppLogger.e(TAG, "Failed to read achievements: ${e.message}", e)
        state
    }

    fun load(force: Boolean = false) {
        val now = System.currentTimeMillis()
        if (!force && loadJob?.isActive == true) {
            AppLogger.d(TAG, "Dashboard live refresh coalesced: read already in progress")
            return
        }
        if (!force && now - lastLiveLoadStartedAtMs < MIN_LIVE_REFRESH_INTERVAL_MS) {
            AppLogger.d(TAG, "Dashboard live refresh throttled")
            return
        }
        lastLiveLoadStartedAtMs = now
        val generation = ++loadGeneration
        if (force) loadJob?.cancel()
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

            val snapshot = googleManager.readDashboardSnapshot()
            if (generation != loadGeneration) return@launch

            _state.update { current ->
                if (snapshot == null) {
                    // Health Connect is reachable and permissions are granted, but this
                    // particular read failed transiently. Keep showing the last good
                    // data (cached or previously loaded) rather than blanking the UI.
                    current.copy(isLoading = false, hasPermissions = true, permissionsChecked = true)
                } else {
                    val dataChangedAtMs = snapshotCache.save(snapshot)
                    updateAchievementsFor(snapshot)
                    readAchievementsIntoState(
                        current.withSnapshot(snapshot).copy(
                            hasPermissions = true,
                            permissionsChecked = true,
                            isFromCache = false,
                            lastUpdatedAtMs = dataChangedAtMs
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
            if (snapshot.dailyActivity.isNotEmpty()) {
                achievementsStore.mergeDailyActivity(snapshot.dailyActivity)
            } else {
                achievementsStore.recordDailyTotals(
                    date = today,
                    stepsToday = snapshot.stepsToday,
                    distanceMetersToday = snapshot.distanceMeters,
                    caloriesKcalToday = snapshot.caloriesKcal
                )
            }
            val goalMet = _state.value.stepsGoal > 0 && snapshot.stepsToday >= _state.value.stepsGoal
            achievementsStore.updateStreak(today, goalMet)
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to update achievements from manual refresh: ${e.message}", e)
        }
    }

    private fun DashboardUiState.withSnapshot(snapshot: GoogleDashboardSnapshot): DashboardUiState {
        val today = LocalDate.now()
        val currentStart = today.minusDays(6)
        val previousStart = today.minusDays(13)
        val previousEnd = today.minusDays(7)
        val currentDays = snapshot.dailyActivity.filter { !it.date.isBefore(currentStart) && !it.date.isAfter(today) }
        val previousDays = snapshot.dailyActivity.filter { !it.date.isBefore(previousStart) && !it.date.isAfter(previousEnd) }
        val currentSteps = currentDays.sumOf { it.steps }
        val previousSteps = previousDays.sumOf { it.steps }
        val change = if (previousSteps > 0L) {
            (((currentSteps - previousSteps).toDouble() / previousSteps.toDouble()) * 100.0).toInt()
        } else {
            null
        }
        val bestCurrentDay = currentDays
            .filter { it.steps > 0L }
            .maxByOrNull { it.steps }
            ?.let { PersonalRecord(it.steps.toDouble(), it.date) }
        val todayActivity = snapshot.dailyActivity.firstOrNull { it.date == today }

        return copy(
            isLoading = false,
            hasPermissions = true,
            stepsToday = snapshot.stepsToday,
            distanceMeters = snapshot.distanceMeters,
            caloriesKcal = snapshot.caloriesKcal,
            workoutMinutesToday = snapshot.workoutMinutesToday,
            activeHoursToday = snapshot.activeHoursToday,
            recentWorkouts = snapshot.recentWorkouts,
            elevationMetersToday = todayActivity?.elevationMeters ?: 0.0,
            floorsToday = todayActivity?.floors ?: 0.0,
            elevationMeters7d = currentDays.sumOf { it.elevationMeters },
            floors7d = currentDays.sumOf { it.floors },
            averageSteps7d = currentSteps / 7L,
            bestStepsDay7d = bestCurrentDay,
            stepsChangeVsPrevious7d = change
        )
    }

    companion object {
        private const val MIN_LIVE_REFRESH_INTERVAL_MS = 5_000L

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
