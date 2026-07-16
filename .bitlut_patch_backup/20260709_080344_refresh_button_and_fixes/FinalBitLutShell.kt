package com.openhealth.sync
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.navigationBarsPadding

import android.content.Context
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.health.connect.client.PermissionController
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.WorkoutTypeSummary
import com.openhealth.sync.data.MetricBar
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison
import com.openhealth.sync.config.DashboardWidget
import com.openhealth.sync.config.GoalPrefs
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.DashboardUiState
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.HISTORY_RANGE_OPTIONS
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.util.AppLogger
import java.util.Locale
import java.util.concurrent.TimeUnit
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.ui.res.stringResource
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Today
import androidx.compose.material.icons.rounded.TrendingUp
import androidx.compose.material.icons.rounded.UploadFile
import androidx.compose.material.icons.rounded.Cloud
import androidx.compose.material.icons.rounded.Watch
import androidx.compose.material.icons.rounded.CloudSync
import androidx.compose.material.icons.rounded.DirectionsRun
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.LocalFireDepartment
import androidx.compose.material3.Icon
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow
import com.openhealth.sync.ui.ImportScreen
import com.openhealth.sync.ui.ImportViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.Spring
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.lerp
import androidx.compose.foundation.Canvas
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.geometry.Offset

internal enum class MainTab(val key: String, val icon: ImageVector) {
    Today("tab_today", Icons.Rounded.Today),
    Settings("tab_settings", Icons.Rounded.Settings)
}

@Composable
fun FinalBitLutShell(
    dashboardStateProvider: @Composable () -> DashboardUiState,
    syncStateProvider: @Composable () -> SyncUiState,
    onRefresh: () -> Unit,
    onRequestGoogle: () -> Unit,
    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit,
    onImportArchive: () -> Unit = {},
    onHistoryRangeSelected: (Int) -> Unit = {},
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit = { _, _ -> },
    onStepsGoalChanged: (Long) -> Unit = {},
    onDistanceGoalChanged: (Double) -> Unit = {},
    onActiveMinutesGoalChanged: (Int) -> Unit = {},
    onCaloriesGoalChanged: (Double) -> Unit = {},
    hasSeenPermissionsOnboarding: Boolean = true,
    onPermissionsOnboardingSeen: () -> Unit = {},
    importViewModel: ImportViewModel) {
    var selected by rememberSaveable { mutableStateOf(MainTab.Today) }
    var showArchiveImport by rememberSaveable { mutableStateOf(false) }
    var showPermissionsOnboarding by rememberSaveable { mutableStateOf(false) }
    var showLogViewer by rememberSaveable { mutableStateOf(false) }
    val dashboardState = dashboardStateProvider()
    val syncState = syncStateProvider()
    val isDark = androidx.compose.foundation.isSystemInDarkTheme()
    val palette = remember(isDark) { if (isDark) BitPalette.dark() else BitPalette.light() }

    // Sprint 7: the first time someone would trigger the real Health Connect
    // permission request, show a plain-language rationale screen instead --
    // the system's own permission dialog is terse ("Allow BitLut to access
    // Steps?") and gives no context for why. This wraps every onRequestGoogle
    // call site (Summary lock screen, History lock screen, Settings) without
    // changing any of them individually.
    val wrappedOnRequestGoogle: () -> Unit = {
        if (!hasSeenPermissionsOnboarding) {
            showPermissionsOnboarding = true
        } else {
            onRequestGoogle()
        }
    }

    Scaffold(
        containerColor = palette.systemBackground,
        bottomBar = {
            Glass20BottomNavigation(
                selected = selected,
                palette = palette,
                onSelected = { selected = it },
                onSecretLogViewerTriggered = { showLogViewer = true }
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(palette.backgroundBrush)
                .padding(padding)
        ) {
            
            if (showArchiveImport) {
                ImportScreen(
                    viewModel = importViewModel,
                    onBack = { showArchiveImport = false; onRefresh() }
                )
            } else when (selected) {
                MainTab.Today -> SummaryScreen(palette, dashboardState, onRefresh, wrappedOnRequestGoogle)
                MainTab.Settings -> SettingsScreen(palette, syncState, dashboardState, onRefresh, wrappedOnRequestGoogle, onRequestHuawei, onSyncNow,
                    onImportArchive = { showArchiveImport = true },
                    onWidgetVisibilityChanged = onWidgetVisibilityChanged,
                    onStepsGoalChanged = onStepsGoalChanged,
                    onDistanceGoalChanged = onDistanceGoalChanged,
                    onActiveMinutesGoalChanged = onActiveMinutesGoalChanged,
                    onCaloriesGoalChanged = onCaloriesGoalChanged)
            }
        }
    }

    if (showPermissionsOnboarding) {
        PermissionsOnboardingScreen(
            palette = palette,
            onContinue = {
                showPermissionsOnboarding = false
                onPermissionsOnboardingSeen()
                onRequestGoogle()
            }
        )
    }

    if (showLogViewer) {
        LogViewerScreen(
            palette = palette,
            onClose = { showLogViewer = false }
        )
    }
}

/**
 * One-time permissions rationale screen (v1.9.12, sprint 7), shown as a
 * full-screen overlay the first time "Connect Google Health" would be
 * tapped -- before the system's own Health Connect permission dialog
 * appears. Explains in plain language what BitLut actually reads/writes
 * (activity-only: steps, distance, calories, floors, workouts) and why,
 * since the system dialog itself only lists raw permission names with no
 * context. Shown exactly once per install; OnboardingPrefs tracks that.
 */
@Composable
private fun LogViewerScreen(palette: BitPalette, onClose: () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val clipboardManager = androidx.compose.ui.platform.LocalClipboardManager.current
    val logs by com.openhealth.sync.util.AppLogger.logs.collectAsStateWithLifecycle()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Diagnostic log",
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 22.sp
                )
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    PrimaryButton(
                        text = "Copy",
                        accent = HealthAccent.mind,
                        modifier = Modifier,
                        onClick = {
                            val dump = com.openhealth.sync.util.AppLogger.exportFullDump(context)
                            clipboardManager.setText(androidx.compose.ui.text.AnnotatedString(dump))
                        }
                    )
                    PrimaryButton(
                        text = "Close",
                        accent = HealthAccent.activity,
                        modifier = Modifier,
                        onClick = onClose
                    )
                }
            }

            androidx.compose.foundation.lazy.LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                if (logs.isEmpty()) {
                    item {
                        Text(
                            text = "No log entries yet.",
                            color = palette.secondaryText,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 13.sp
                        )
                    }
                }
                items(logs) { entry ->
                    Text(
                        text = entry,
                        color = palette.text,
                        fontWeight = FontWeight.Medium,
                        fontSize = 11.sp,
                        fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
                    )
                }
            }
        }
    }
}

@Composable
private fun PermissionsOnboardingScreen(palette: BitPalette, onContinue: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp, vertical = 32.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Icon(
                    Icons.Rounded.Cloud,
                    contentDescription = null,
                    tint = HealthAccent.mind,
                    modifier = Modifier.size(40.dp)
                )
                Spacer(Modifier.height(20.dp))
                Text(
                    text = stringResource(R.string.onboarding_title),
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 26.sp
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    text = stringResource(R.string.onboarding_body),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 15.sp,
                    lineHeight = 21.sp
                )
                Spacer(Modifier.height(24.dp))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.TrendingUp, text = stringResource(R.string.onboarding_scope_steps))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.TrendingUp, text = stringResource(R.string.onboarding_scope_distance))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.TrendingUp, text = stringResource(R.string.onboarding_scope_workouts))
                Spacer(Modifier.height(16.dp))
                Text(
                    text = stringResource(R.string.onboarding_privacy_note),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                )
            }

            PrimaryButton(
                text = stringResource(R.string.onboarding_continue_button),
                accent = HealthAccent.mind,
                onClick = onContinue
            )
        }
    }
}

@Composable
private fun OnboardingScopeRow(palette: BitPalette, icon: ImageVector, text: String) {
    Row(
        modifier = Modifier.padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = HealthAccent.activity, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(10.dp))
        Text(text, color = palette.text, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
    }
}

@Composable
private fun SummaryScreen(
    palette: BitPalette,
    state: DashboardUiState,
    onRefresh: () -> Unit,
    onRequestGoogle: () -> Unit
) {
    // Sprint (2026-07-08): fixed, non-scrolling layout with exactly the 5
    // widgets that map to our current Huawei Health Kit scope: steps today,
    // workout time today, personal records, streak, and the last imported
    // workout. The calories/workout-minutes/active-hours mini-grid and the
    // week-over-week comparison card moved off this screen so it fits one
    // viewport without scrolling.
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        MinimalHeader(
            palette = palette,
            title = stringResource(R.string.summary_short_title),
            subtitle = formatUpdatedAgo(state.lastUpdatedAtMs, state.isFromCache)
        )

        if (state.showConnectLockScreen) {
            MinimalMetricCard(
                palette = palette,
                title = stringResource(R.string.connect_google_title),
                value = stringResource(R.string.no_data_short),
                unit = stringResource(R.string.connect_google_button),
                accent = HealthAccent.mind,
                icon = Icons.Rounded.Cloud,
                onClick = onRequestGoogle
            )
        } else if (state.isLoading && state.stepsToday == 0L && state.recentWorkouts.isEmpty()) {
            // First-ever launch on this device, with no cached snapshot yet and no
            // confirmed permission result either way. Show a neutral loading state
            // instead of either real (zero) numbers or the "Connect Google Health"
            // lock screen, which would be misleading this early.
            DashboardLoadingCard(palette = palette)
        } else {
            MinimalMetricCard(
                palette = palette,
                title = stringResource(R.string.steps_today),
                value = formatNumber(state.stepsToday),
                unit = "${stringResource(R.string.steps_unit)} · ${stringResource(R.string.distance_today_value, formatOneDecimal(state.distanceMeters / 1000.0))} · ${stringResource(R.string.dashboard_pct_goal, (state.stepsProgress * 100).toInt())}",
                accent = HealthAccent.activity,
                progress = state.stepsProgress
            )

            MiniMetricWidget(
                palette = palette,
                title = stringResource(R.string.workout_minutes_title),
                value = "${state.workoutMinutesToday}",
                unit = stringResource(R.string.minutes_short),
                accent = HealthAccent.activity,
                modifier = Modifier.fillMaxWidth()
            )

            if (state.bestStepsDay != null || state.bestDistanceDay != null) {
                PersonalRecordsCard(
                    palette = palette,
                    bestStepsDay = state.bestStepsDay,
                    bestDistanceDay = state.bestDistanceDay,
                    isStepsRecordToday = state.isStepsRecordToday
                )
            }
            if (state.streak.currentStreakDays > 0 || state.streak.longestStreakDays > 0) {
                StreakCard(palette = palette, streak = state.streak, stepsGoal = state.stepsGoal)
            }
            state.recentWorkouts.firstOrNull()?.let { lastWorkout ->
                LastWorkoutCard(palette = palette, session = lastWorkout)
            }
        }
    }
}

@Composable
private fun HistoryScreen(
    palette: BitPalette,
    state: DashboardUiState,
    onRequestGoogle: () -> Unit,
    onRangeSelected: (Int) -> Unit
) {
    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            MinimalHeader(
                palette = palette,
                title = stringResource(R.string.history_short_title)
            )
        }

        if (!state.showConnectLockScreen && state.hasPermissions) {
            item {
                HistoryRangeChips(
                    palette = palette,
                    selectedDays = state.selectedHistoryRangeDays,
                    onRangeSelected = onRangeSelected
                )
            }
        }

        if (state.showConnectLockScreen) {
            item {
                MinimalMetricCard(
                    palette = palette,
                    title = stringResource(R.string.connect_google_title),
                    value = stringResource(R.string.no_data_short),
                    unit = stringResource(R.string.connect_google_button),
                    accent = HealthAccent.mind,
                    icon = Icons.Rounded.Cloud,
                    onClick = onRequestGoogle
                )
            }
        } else if (state.isLoading && state.stepsBars.isEmpty()) {
            item { DashboardLoadingCard(palette = palette) }
        } else {
            val rangeDays = state.selectedHistoryRangeDays
            val stepsTotal = state.stepsBars.sumOf { it.value }

            if (state.isWidgetVisible(DashboardWidget.STEPS)) {
                item {
                    MetricBarChartCard(
                        palette = palette,
                        title = stringResource(R.string.steps_label_days, rangeDays),
                        periodValueLabel = stringResource(R.string.period_total_steps, formatNumber(stepsTotal.toLong())),
                        bars = state.stepsBars,
                        accent = HealthAccent.activity,
                        valueFormatter = { formatNumber(it.toLong()) }
                    )
                }
            }

            if (state.isWidgetVisible(DashboardWidget.WORKOUTS) && state.workoutSummaries.isNotEmpty()) {
                item {
                    Text(
                        text = stringResource(R.string.workouts_section_title),
                        color = palette.text,
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 18.sp,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
                items(state.workoutSummaries) { summary ->
                    WorkoutTypeCard(palette = palette, summary = summary)
                }
            }
        }
    }
}

/**
 * Scrollable row of range chips (7/14/30/60/90/180/365 days) for the History screen,
 * placed on its own row below the screen title rather than sharing the title's row —
 * this avoids the kind of overflow/wrap risk that the Settings buttons had before
 * they were switched to FlowRow (a 7-chip row needs its own horizontal space, and
 * fighting the title for space on one line would risk the title getting clipped on
 * narrower screens or longer locale strings).
 */
@Composable
private fun HistoryRangeChips(
    palette: BitPalette,
    selectedDays: Int,
    onRangeSelected: (Int) -> Unit
) {
    LazyRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp, alignment = Alignment.End)
    ) {
        items(HISTORY_RANGE_OPTIONS) { days ->
            val selected = days == selectedDays
            val interactionSource = remember { MutableInteractionSource() }
            Box(
                modifier = Modifier
                    .pressScale(interactionSource)
                    .clip(RoundedCornerShape(99.dp))
                    .background(if (selected) HealthAccent.activity else palette.card)
                    .border(1.dp, if (selected) Color.Transparent else palette.stroke, RoundedCornerShape(99.dp))
                    .clickable(
                        interactionSource = interactionSource,
                        indication = null
                    ) { onRangeSelected(days) }
                    .padding(horizontal = 14.dp, vertical = 8.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = stringResource(R.string.history_range_days_short, days),
                    color = if (selected) Color.White else palette.secondaryText,
                    fontWeight = FontWeight.Black,
                    fontSize = 13.sp,
                    maxLines = 1
                )
            }
        }
    }
}

/**
 * Workout-type card for History: shown once per exercise type that has at least one
 * session in the currently selected range (no card for types with zero sessions).
 * Shows the localized exercise name (already handled by exerciseTypeName in
 * GoogleHealthManager — e.g. "Бег" for running), session count, and total duration.
 */
@Composable
private fun WorkoutTypeCard(
    palette: BitPalette,
    summary: WorkoutTypeSummary
) {
    SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    text = summary.displayName,
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 16.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = stringResource(R.string.workout_sessions_count, summary.sessionCount),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp
                )
            }
            Text(
                text = stringResource(R.string.workout_total_minutes, summary.totalDurationMinutes),
                color = HealthAccent.activity,
                fontWeight = FontWeight.Black,
                fontSize = 15.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

/**
 * Last imported workout (sprint 2026-07-08). state.recentWorkouts is already
 * sorted most-recent-first by GoogleHealthManager.readRecentWorkouts, so the
 * first entry is exactly "the last imported workout".
 */
@Composable
private fun LastWorkoutCard(palette: BitPalette, session: ActivitySessionData) {
    val durationMinutes = ((session.endTimeMs - session.startTimeMs) / 60_000L).coerceAtLeast(0L)
    SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Rounded.DirectionsRun, contentDescription = null, tint = HealthAccent.activity, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    text = session.title,
                    color = palette.text,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                formatUpdatedAgo(session.startTimeMs, isFromCache = false)?.let { agoText ->
                    Text(
                        text = agoText,
                        color = palette.secondaryText,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 12.sp
                    )
                }
            }
            Text(
                text = stringResource(R.string.workout_total_minutes, durationMinutes),
                color = HealthAccent.activity,
                fontWeight = FontWeight.Black,
                fontSize = 14.sp,
                maxLines = 1
            )
        }
    }
}

@Composable
private fun DashboardWidgetGrid(
    palette: BitPalette,
    state: DashboardUiState
) {
    val tiles = listOfNotNull(
        if (state.isWidgetVisible(DashboardWidget.CALORIES))
            Triple(stringResource(R.string.calories_active_title), "${state.caloriesKcal.toLong()}", stringResource(R.string.kcal_unit)) to HealthAccent.activity else null,
        if (state.isWidgetVisible(DashboardWidget.WORKOUT_MINUTES))
            Triple(stringResource(R.string.workout_minutes_title), "${state.workoutMinutesToday}", stringResource(R.string.minutes_short)) to HealthAccent.activity else null,
        if (state.isWidgetVisible(DashboardWidget.ACTIVE_HOURS))
            Triple(stringResource(R.string.active_hours_title), "${state.activeHoursToday}", stringResource(R.string.hours_short)) to HealthAccent.mind else null
    )

    if (tiles.isEmpty()) return

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        tiles.chunked(2).forEach { row ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                row.forEach { item ->
                    val data = item.first
                    MiniMetricWidget(
                        palette = palette,
                        title = data.first,
                        value = data.second,
                        unit = data.third,
                        accent = item.second,
                        modifier = Modifier.weight(1f)
                    )
                }
                if (row.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun MiniMetricWidget(
    palette: BitPalette,
    title: String,
    value: String,
    unit: String,
    accent: Color,
    modifier: Modifier = Modifier
) {
    SoftCard(palette = palette, modifier = modifier, accent = accent, hero = false, tintWithAccent = true) {
        Text(title, color = palette.secondaryText, fontWeight = FontWeight.Bold, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Spacer(Modifier.height(6.dp))
        Row(verticalAlignment = Alignment.Bottom) {
            Text(value, color = palette.text, fontWeight = FontWeight.Black, fontSize = 24.sp, maxLines = 1)
            Spacer(Modifier.width(4.dp))
            Text(unit, color = accent, fontWeight = FontWeight.Black, fontSize = 12.sp, modifier = Modifier.padding(bottom = 3.dp))
        }
    }
}

@Composable
private fun MiniSparkline(
    bars: List<MetricBar>,
    accent: Color,
    modifier: Modifier = Modifier
) {
    Canvas(modifier = modifier) {
        val values = bars.map { it.value }.filter { it > 0.0 }
        if (values.size < 2) return@Canvas
        val min = values.minOrNull() ?: 0.0
        val max = values.maxOrNull() ?: 1.0
        val range = (max - min).takeIf { it > 0.0 } ?: 1.0
        val step = size.width / (values.size - 1).coerceAtLeast(1)
        var last: Offset? = null
        values.forEachIndexed { index, value ->
            val x = step * index
            val y = size.height - (((value - min) / range).toFloat() * size.height)
            val point = Offset(x, y.coerceIn(0f, size.height))
            last?.let { drawLine(accent, it, point, strokeWidth = 4.dp.toPx(), cap = StrokeCap.Round) }
            last = point
        }
    }
}

/**
 * Week-over-week comparison card (v1.9.12, sprint 4). Shows steps/distance/
 * calories change vs the previous 7 days as a signed percentage, or "first
 * tracked week" copy when there's no previous-week baseline to compare
 * against (WeekComparison.*PercentChange() returns null in that case).
 */
@Composable
private fun WeeklyComparisonCard(palette: BitPalette, comparison: WeekComparison) {
    SoftCard(palette = palette, accent = HealthAccent.mind, tintWithAccent = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.TrendingUp, contentDescription = null, tint = HealthAccent.mind, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(
                text = stringResource(R.string.insights_week_comparison_title),
                color = palette.text,
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp
            )
        }
        Spacer(Modifier.height(12.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            WeekChangeStat(
                modifier = Modifier.weight(1f),
                palette = palette,
                label = stringResource(R.string.steps_today),
                percentChange = comparison.stepsPercentChange()
            )
            WeekChangeStat(
                modifier = Modifier.weight(1f),
                palette = palette,
                label = stringResource(R.string.distance_short_title),
                percentChange = comparison.distancePercentChange()
            )
            WeekChangeStat(
                modifier = Modifier.weight(1f),
                palette = palette,
                label = stringResource(R.string.calories_active_title),
                percentChange = comparison.caloriesPercentChange()
            )
        }
    }
}

@Composable
private fun WeekChangeStat(
    palette: BitPalette,
    label: String,
    percentChange: Int?,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier) {
        Text(label, color = palette.secondaryText, fontWeight = FontWeight.SemiBold, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Spacer(Modifier.height(4.dp))
        if (percentChange == null) {
            Text(
                stringResource(R.string.insights_first_week),
                color = palette.secondaryText,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp
            )
        } else {
            val positive = percentChange >= 0
            val displayColor = if (positive) HealthAccent.mind else palette.secondaryText
            Text(
                text = "${if (positive) "+" else ""}$percentChange%",
                color = displayColor,
                fontWeight = FontWeight.Black,
                fontSize = 18.sp
            )
        }
    }
}

/**
 * All-time personal records card (v1.9.12, sprint 4). Only renders the
 * metrics that actually have a record yet (a brand-new install has neither
 * until the first full day of tracked data goes by, per
 * AchievementsStore.recordDailyTotals). Shows a "new record today" badge
 * when today's live number has already met or beaten the stored best, ahead
 * of the next sync actually persisting it.
 */
@Composable
private fun PersonalRecordsCard(
    palette: BitPalette,
    bestStepsDay: PersonalRecord?,
    bestDistanceDay: PersonalRecord?,
    isStepsRecordToday: Boolean
) {
    SoftCard(palette = palette, accent = HealthAccent.activity, tintWithAccent = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.EmojiEvents, contentDescription = null, tint = HealthAccent.activity, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(
                text = stringResource(R.string.insights_personal_records_title),
                color = palette.text,
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp
            )
            if (isStepsRecordToday) {
                Spacer(Modifier.width(8.dp))
                Box(
                    modifier = Modifier
                        .background(HealthAccent.activity.copy(alpha = 0.18f), shape = RoundedCornerShape(20.dp))
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        stringResource(R.string.insights_new_record_badge),
                        color = HealthAccent.activity,
                        fontWeight = FontWeight.Black,
                        fontSize = 10.sp
                    )
                }
            }
        }
        Spacer(Modifier.height(12.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            if (bestStepsDay != null) {
                RecordStat(
                    modifier = Modifier.weight(1f),
                    palette = palette,
                    label = stringResource(R.string.steps_today),
                    value = formatNumber(bestStepsDay.value.toLong()),
                    date = bestStepsDay.date
                )
            }
            if (bestDistanceDay != null) {
                RecordStat(
                    modifier = Modifier.weight(1f),
                    palette = palette,
                    label = stringResource(R.string.distance_short_title),
                    value = stringResource(R.string.distance_today_value, formatOneDecimal(bestDistanceDay.value / 1000.0)),
                    date = bestDistanceDay.date
                )
            }
        }
    }
}

@Composable
private fun RecordStat(
    palette: BitPalette,
    label: String,
    value: String,
    date: java.time.LocalDate,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier) {
        Text(label, color = palette.secondaryText, fontWeight = FontWeight.SemiBold, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Spacer(Modifier.height(4.dp))
        Text(value, color = palette.text, fontWeight = FontWeight.Black, fontSize = 18.sp)
        Spacer(Modifier.height(2.dp))
        Text(formatRecordDate(date), color = palette.secondaryText, fontWeight = FontWeight.SemiBold, fontSize = 10.sp)
    }
}

/**
 * Streak card (v1.9.12, sprint 4). Shows the current consecutive-day streak
 * of hitting the steps goal, plus the longest streak ever if it differs from
 * the current one (avoids showing a redundant "current: 5, longest: 5").
 */
@Composable
private fun StreakCard(palette: BitPalette, streak: StreakState, stepsGoal: Long) {
    SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.LocalFireDepartment, contentDescription = null, tint = HealthAccent.activity, modifier = Modifier.size(22.dp))
            Spacer(Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = pluralDaysStreak(streak.currentStreakDays),
                    color = palette.text,
                    fontWeight = FontWeight.Black,
                    fontSize = 20.sp
                )
                Text(
                    text = stringResource(R.string.insights_streak_subtitle, formatNumber(stepsGoal)),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 12.sp
                )
            }
            if (streak.longestStreakDays > streak.currentStreakDays) {
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "${streak.longestStreakDays}",
                        color = palette.secondaryText,
                        fontWeight = FontWeight.Black,
                        fontSize = 16.sp
                    )
                    Text(
                        text = stringResource(R.string.insights_streak_best),
                        color = palette.secondaryText,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 10.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun pluralDaysStreak(days: Int): String {
    // Russian day-count pluralization has three forms (1 день / 2-4 дня /
    // 5+ дней) that a single %d string template cannot express correctly.
    // English (and the fallback for any other locale) only needs singular
    // vs plural. This keeps the grammar correct in both shipped locales
    // without pulling in Android <plurals> resource complexity for a single
    // string.
    val isRussian = java.util.Locale.getDefault().language == "ru"
    if (!isRussian) {
        return if (days == 1) stringResource(R.string.insights_streak_days_one, days)
        else stringResource(R.string.insights_streak_days_other, days)
    }

    val mod100 = days % 100
    val mod10 = days % 10
    return when {
        mod100 in 11..14 -> stringResource(R.string.insights_streak_days_ru_many, days)
        mod10 == 1 -> stringResource(R.string.insights_streak_days_ru_one, days)
        mod10 in 2..4 -> stringResource(R.string.insights_streak_days_ru_few, days)
        else -> stringResource(R.string.insights_streak_days_ru_many, days)
    }
}

private fun formatRecordDate(date: java.time.LocalDate): String {
    val formatter = java.time.format.DateTimeFormatter.ofPattern("d MMM", java.util.Locale.getDefault())
    return date.format(formatter)
}

@Composable
private fun SettingsScreen(
    palette: BitPalette,
    syncState: SyncUiState,
    dashboardState: DashboardUiState,
    onRefresh: () -> Unit,
    onRequestGoogle: () -> Unit,
    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit,
    onImportArchive: () -> Unit,
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit,
    onStepsGoalChanged: (Long) -> Unit,
    onDistanceGoalChanged: (Double) -> Unit,
    onActiveMinutesGoalChanged: (Int) -> Unit,
    onCaloriesGoalChanged: (Double) -> Unit
) {
    // Sprint (2026-07-08): Daily goals moved to the top (right under the
    // header), calories dropped from it. The three connection cards below
    // lost their explanatory body text and status line (title + icon only
    // now) and their two actions are a single compact row instead of a
    // wrapping FlowRow. The widget-visibility toggle section was removed
    // entirely -- Summary's widget set is fixed now, not user-configurable.
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        MinimalHeader(
            palette = palette,
            title = stringResource(R.string.tab_settings)
        )

        Text(
            text = stringResource(R.string.goals_section_title),
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 18.sp
        )
        SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {
            GoalStepperRow(
                palette = palette,
                accent = HealthAccent.activity,
                label = stringResource(R.string.goal_steps_label),
                valueText = "${formatNumber(dashboardState.stepsGoal)} ${stringResource(R.string.steps_unit)}",
                onDecrease = { onStepsGoalChanged((dashboardState.stepsGoal - STEPS_GOAL_STEP).coerceAtLeast(GoalPrefs.STEPS_GOAL_RANGE.first)) },
                onIncrease = { onStepsGoalChanged((dashboardState.stepsGoal + STEPS_GOAL_STEP).coerceAtMost(GoalPrefs.STEPS_GOAL_RANGE.last)) }
            )
            GoalStepperRow(
                palette = palette,
                accent = HealthAccent.mind,
                label = stringResource(R.string.goal_distance_label),
                valueText = stringResource(R.string.distance_today_value, formatOneDecimal(dashboardState.distanceGoalMeters / 1000.0)),
                onDecrease = { onDistanceGoalChanged((dashboardState.distanceGoalMeters - DISTANCE_GOAL_STEP_METERS).coerceAtLeast(GoalPrefs.DISTANCE_GOAL_RANGE_METERS.start)) },
                onIncrease = { onDistanceGoalChanged((dashboardState.distanceGoalMeters + DISTANCE_GOAL_STEP_METERS).coerceAtMost(GoalPrefs.DISTANCE_GOAL_RANGE_METERS.endInclusive)) }
            )
            GoalStepperRow(
                palette = palette,
                accent = HealthAccent.activity,
                label = stringResource(R.string.goal_active_minutes_label),
                valueText = "${dashboardState.activeMinutesGoal} ${stringResource(R.string.minutes_short)}",
                onDecrease = { onActiveMinutesGoalChanged((dashboardState.activeMinutesGoal - ACTIVE_MINUTES_GOAL_STEP).coerceAtLeast(GoalPrefs.ACTIVE_MINUTES_GOAL_RANGE.first)) },
                onIncrease = { onActiveMinutesGoalChanged((dashboardState.activeMinutesGoal + ACTIVE_MINUTES_GOAL_STEP).coerceAtMost(GoalPrefs.ACTIVE_MINUTES_GOAL_RANGE.last)) },
                isLast = true
            )
        }

        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.google_health_connect),
            accent = HealthAccent.mind,
            icon = Icons.Rounded.Cloud,
            primaryAction = stringResource(R.string.connect_google_button),
            onPrimaryAction = onRequestGoogle,
            secondaryAction = stringResource(R.string.refresh_status),
            onSecondaryAction = onSyncNow
        )

        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.huawei_health_title),
            accent = HealthAccent.activity,
            icon = Icons.Rounded.Watch,
            primaryAction = stringResource(R.string.connect_huawei_button),
            onPrimaryAction = onRequestHuawei,
            secondaryAction = stringResource(R.string.refresh_status),
            onSecondaryAction = onRefresh
        )

        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.manual_sync_title),
            accent = HealthAccent.sleep,
            icon = Icons.Rounded.CloudSync,
            primaryAction = stringResource(R.string.sync_now),
            onPrimaryAction = onSyncNow,
            secondaryAction = stringResource(R.string.import_archive_title),
            onSecondaryAction = onImportArchive
        )
    }
}

/** Single toggle row inside the Widgets settings card: label + Switch. [isLast]
 *  suppresses the bottom spacer so the card doesn't end with extra trailing gap. */
@Composable
private fun WidgetVisibilityRow(
    palette: BitPalette,
    label: String,
    accent: Color,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    isLast: Boolean = false
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            color = palette.text,
            fontWeight = FontWeight.SemiBold,
            fontSize = 14.sp
        )
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Color.White,
                checkedTrackColor = accent,
                uncheckedThumbColor = Color.White,
                uncheckedTrackColor = palette.stroke
            )
        )
    }
    if (!isLast) {
        Spacer(Modifier.height(8.dp))
    }
}

// ── Sprint 7: goal step sizes for the Settings steppers ──────────────────
private const val STEPS_GOAL_STEP = 500L
private const val DISTANCE_GOAL_STEP_METERS = 500.0
private const val ACTIVE_MINUTES_GOAL_STEP = 5
private const val CALORIES_GOAL_STEP = 50.0

/**
 * A single goal row in Settings: label, current value, and -/+ stepper
 * buttons (v1.9.12, sprint 7). Deliberately a stepper rather than a free-text
 * field: it makes an invalid/out-of-range value structurally impossible
 * (every tap is pre-clamped by the caller against GoalPrefs' *_RANGE bounds),
 * which is both simpler to implement correctly and more comfortable to use
 * one-handed than opening a keyboard for a single number.
 */
@Composable
private fun GoalStepperRow(
    palette: BitPalette,
    accent: Color,
    label: String,
    valueText: String,
    onDecrease: () -> Unit,
    onIncrease: () -> Unit,
    isLast: Boolean = false
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(label, color = palette.text, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            Spacer(Modifier.height(2.dp))
            Text(valueText, color = palette.secondaryText, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        }
        Spacer(Modifier.width(12.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            GoalStepperButton(palette = palette, accent = accent, symbol = "–", onClick = onDecrease)
            Spacer(Modifier.width(8.dp))
            GoalStepperButton(palette = palette, accent = accent, symbol = "+", onClick = onIncrease)
        }
    }
    if (!isLast) {
        Spacer(Modifier.height(14.dp))
    }
}

@Composable
private fun GoalStepperButton(palette: BitPalette, accent: Color, symbol: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(34.dp)
            .background(accent.copy(alpha = 0.16f), shape = RoundedCornerShape(12.dp))
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Text(symbol, color = accent, fontWeight = FontWeight.Black, fontSize = 18.sp)
    }
}

/**
 * Generic reference target for the Sleep progress ring on Summary, in hours.
 * Unlike [DashboardUiState.stepsGoal], this is NOT a personalized or
 * user-configurable value — it's the commonly cited adult sleep guideline,
 * used only to give the ring a sense of "how close to a typical night" the
 * person is. If/when per-user sleep goals are added, replace this constant.
 */
internal object HealthAccent {
    val activity = Color(0xFFFF6B5A)
    val sleep = Color(0xFF9E6FC3)
    val heart = Color(0xFFFF453A)
    val mind = Color(0xFF5FE0C6)
    val cardLight = Color.White
    val cardDark = Color(0xCC1C1C1E)
    val systemLight = Color(0xFFF2F2F7)
}

/**
 * iOS/Apple-Health-style tactile press feedback: scales a tappable surface down
 * slightly while pressed, using spring physics rather than a linear tween so the
 * release has a small natural bounce.
 *
 * Pass the SAME [interactionSource] you give to your own `Modifier.clickable(...)`
 * — this modifier only observes press state, it never intercepts the tap itself,
 * so the real onClick still fires exactly as before.
 */
@Composable
internal fun Modifier.pressScale(interactionSource: MutableInteractionSource): Modifier {
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.97f else 1f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "pressScale"
    )
    return this.scale(scale)
}

@Composable
private fun PrimaryButton(
    text: String,
    accent: Color,
    enabled: Boolean = true,
    compact: Boolean = false,
    modifier: Modifier = Modifier.fillMaxWidth(),
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier,
        shape = RoundedCornerShape(if (compact) 16.dp else 22.dp),
        colors = ButtonDefaults.buttonColors(containerColor = accent, contentColor = Color.White),
        contentPadding = if (compact) PaddingValues(horizontal = 12.dp, vertical = 6.dp) else ButtonDefaults.ContentPadding
    ) { Text(text, fontWeight = FontWeight.ExtraBold, fontSize = if (compact) 12.sp else 14.sp, maxLines = 1, overflow = TextOverflow.Ellipsis) }
}

@Composable
private fun MinimalTopBar(
    palette: BitPalette,
    title: String,
    action: String,
    onAction: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 30.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f)
        )
        PrimaryButton(
            text = action,
            accent = HealthAccent.activity,
            modifier = Modifier.wrapContentWidth(),
            onClick = onAction
        )
    }
}

@Composable
private fun MinimalHeader(
    palette: BitPalette,
    title: String,
    subtitle: String? = null
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = title,
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 30.sp,
            modifier = Modifier.fillMaxWidth()
        )
        if (subtitle != null) {
            Spacer(Modifier.height(4.dp))
            Text(
                text = subtitle,
                color = palette.secondaryText,
                fontWeight = FontWeight.SemiBold,
                fontSize = 13.sp,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

@Composable
private fun MinimalMetricCard(
    palette: BitPalette,
    title: String,
    value: String,
    unit: String,
    accent: Color,
    progress: Float? = null,
    icon: ImageVector? = null,
    onClick: (() -> Unit)? = null
) {
    val interactionSource = remember { MutableInteractionSource() }
    val cardModifier = if (onClick != null) {
        Modifier
            .fillMaxWidth()
            .pressScale(interactionSource)
            .clickable(interactionSource = interactionSource, indication = null, onClick = onClick)
    } else {
        Modifier.fillMaxWidth()
    }
    SoftCard(palette = palette, modifier = cardModifier, accent = accent, hero = false, tintWithAccent = true) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 96.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    text = title.uppercase(Locale.getDefault()),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp
                )
                Spacer(Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(
                        text = value,
                        color = palette.text,
                        fontWeight = FontWeight.Black,
                        fontSize = 56.sp,
                        lineHeight = 56.sp,
                        letterSpacing = (-1.5).sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false)
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = unit,
                        color = accent,
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 13.sp,
                        modifier = Modifier.padding(bottom = 6.dp)
                    )
                }
            }
            if (progress != null) {
                ProgressRingChip(progress = progress, accent = accent, size = 52.dp)
            } else {
                Box(
                    modifier = Modifier
                        .size(52.dp)
                        .clip(RoundedCornerShape(26.dp))
                        .background(accent.copy(alpha = 0.16f)),
                    contentAlignment = Alignment.Center
                ) {
                    if (icon != null) {
                        Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(24.dp))
                    } else {
                        Text("●", color = accent, fontSize = 17.sp, fontWeight = FontWeight.Black)
                    }
                }
            }
        }
        if (onClick != null) {
            Spacer(Modifier.height(10.dp))
            PrimaryButton(text = unit, accent = accent, onClick = onClick)
        }
    }
}

/**
 * Neutral loading placeholder shown only on a brand-new install (no cached
 * snapshot yet) while the very first Health Connect read is still in flight.
 * Distinct from the "Connect Google Health" lock screen on purpose: we don't
 * yet know whether permissions are granted or not, so showing the lock
 * screen here would be actively misleading on every cold start.
 */
@Composable
private fun DashboardLoadingCard(palette: BitPalette) {
    SoftCard(palette = palette, accent = HealthAccent.mind, hero = false, tintWithAccent = true) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 96.dp),
            horizontalArrangement = Arrangement.Start,
            verticalAlignment = Alignment.CenterVertically
        ) {
            CircularProgressIndicator(
                color = HealthAccent.mind,
                strokeWidth = 3.dp,
                modifier = Modifier.size(28.dp)
            )
            Spacer(Modifier.width(14.dp))
            Text(
                text = stringResource(R.string.status_syncing),
                color = palette.secondaryText,
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp
            )
        }
    }
}

/**
 * Square tile for the 2x2 Summary grid (Heart/Sleep sit side by side under the
 * full-width Steps hero card). Follows the "traffic light" rule: exactly three
 * elements on the tile — a filled icon chip, one large value, one small label.
 * No secondary text, no extra rows — the number does the talking.
 */
@Composable
private fun MinimalSquareTile(
    palette: BitPalette,
    icon: String,
    label: String,
    value: String,
    accent: Color,
    modifier: Modifier = Modifier.fillMaxWidth(),
    progress: Float? = null,
    onClick: (() -> Unit)? = null
) {
    val interactionSource = remember { MutableInteractionSource() }
    val tileModifier = if (onClick != null) {
        modifier
            .pressScale(interactionSource)
            .clickable(interactionSource = interactionSource, indication = null, onClick = onClick)
    } else {
        modifier
    }
    SoftCard(palette = palette, modifier = tileModifier, accent = accent, hero = false, tintWithAccent = true) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 132.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            if (progress != null) {
                ProgressRingChip(progress = progress, accent = accent, size = 40.dp, centerText = icon)
            } else {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(RoundedCornerShape(20.dp))
                        .background(accent.copy(alpha = 0.16f)),
                    contentAlignment = Alignment.Center
                ) {
                    Text(icon, color = accent, fontSize = 17.sp, fontWeight = FontWeight.Black)
                }
            }
            Column {
                Text(
                    text = value,
                    color = palette.text,
                    fontWeight = FontWeight.Black,
                    fontSize = 38.sp,
                    lineHeight = 40.sp,
                    letterSpacing = (-1.5).sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = label.uppercase(Locale.getDefault()),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Black,
                    fontSize = 11.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

/**
 * Compact progress ring used as the icon-chip replacement on Summary tiles that
 * have a real goal to show (Steps vs daily goal, Sleep vs the 8h reference).
 * [progress] is expected pre-clamped to 0f..1f by the caller (see [coerceProgress]).
 */
@Composable
/**
 * Redesigned (v1.9.11) to carry more visual weight against the 56sp hero
 * number it sits beside on the steps card: a thicker stroke, a soft glow
 * behind the ring (instead of just the bare arc), and the actual percentage
 * by default instead of a plain "•" -- matching the convention set by
 * Apple Health / Oura rings, where the ring itself communicates real
 * progress information rather than functioning as pure decoration.
 */
private fun ProgressRingChip(
    progress: Float,
    accent: Color,
    size: androidx.compose.ui.unit.Dp,
    centerText: String? = null
) {
    val resolvedCenterText = centerText ?: "${(progress.coerceIn(0f, 1f) * 100).toInt()}%"
    val glowColors = remember(accent) { listOf(accent.copy(alpha = 0.30f), Color.Transparent) }

    Box(modifier = Modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.matchParentSize()) {
            drawCircle(
                brush = Brush.radialGradient(colors = glowColors, radius = this.size.maxDimension * 0.62f),
                radius = this.size.maxDimension * 0.55f
            )
            val stroke = Stroke(width = 4.5.dp.toPx(), cap = StrokeCap.Round)
            drawArc(
                color = accent.copy(alpha = 0.20f),
                startAngle = -90f,
                sweepAngle = 360f,
                useCenter = false,
                style = stroke
            )
            drawArc(
                color = accent,
                startAngle = -90f,
                sweepAngle = 360f * progress,
                useCenter = false,
                style = stroke
            )
        }
        Text(
            resolvedCenterText,
            color = accent,
            fontSize = if (resolvedCenterText.length > 2) 11.sp else 13.sp,
            fontWeight = FontWeight.Black,
            maxLines = 1
        )
    }
}

/** Clamps any progress ratio into the 0f..1f range a ring can safely draw, and
 *  guards against division by zero when [goal] is zero or negative. */
private fun coerceProgress(value: Double, goal: Double): Float =
    if (goal <= 0.0) 0f else (value / goal).toFloat().coerceIn(0f, 1f)

/**
 * Combined count + trend widget for History: shows the period-aggregate value at
 * the top (e.g. total steps across the selected range) and a proportional-height
 * bar chart below it, one bar per MetricBar from computeMetricBarRanges, each
 * labeled with its value and a short date label. This replaces the earlier design
 * of two separate cards (an average-value card plus a standalone sparkline card)
 * with a single merged widget, per the latest design direction.
 *
 * Bar label granularity follows the bar's own date span: a single-day bar shows
 * the day-of-month, a multi-day bar shows a week-style short range, and the
 * 180/365-day cases (whose bars are real calendar months) show the month
 * abbreviation in the current locale.
 *
 * Safe by construction: an empty bar list (e.g. permission edge case) renders
 * nothing rather than dividing by zero; an all-zero bar list renders all bars at
 * minimum height rather than NaN-height bars.
 */
/** Short numeric label above a bar (e.g. "1.2k" for 1200 steps, "72" for bpm). */
internal fun formatBarValueShort(value: Double): String = when {
    value <= 0.0 -> "0"
    value >= 1000.0 -> String.format(Locale.getDefault(), "%.1fk", value / 1000.0)
    value == value.toLong().toDouble() -> value.toLong().toString()
    else -> String.format(Locale.getDefault(), "%.1f", value)
}

/** Short date label under a bar: day-of-month for single-day bars, month
 *  abbreviation for real calendar-month bars (180/365-day ranges), otherwise a
 *  compact day-range for the multi-day week-style buckets. */
internal fun barDateLabel(bar: MetricBar): String {
    val isWholeMonth = bar.startDate.dayOfMonth == 1 &&
        bar.endDate == bar.startDate.plusMonths(1).minusDays(1)
    return when {
        isWholeMonth -> bar.startDate.month.getDisplayName(java.time.format.TextStyle.SHORT, Locale.getDefault())
        bar.startDate == bar.endDate -> bar.startDate.dayOfMonth.toString()
        else -> "${bar.startDate.dayOfMonth}–${bar.endDate.dayOfMonth}"
    }
}

private fun List<Double>.safeAverage(): Double =
    if (isEmpty()) 0.0 else average()

private fun formatOneDecimal(value: Double): String =
    String.format(Locale.getDefault(), "%.1f", value)

@Composable
private fun SettingsConnectionCard(
    palette: BitPalette,
    title: String,
    accent: Color,
    icon: ImageVector,
    primaryAction: String,
    onPrimaryAction: () -> Unit,
    secondaryAction: String? = null,
    onSecondaryAction: (() -> Unit)? = null
) {
    // Sprint (2026-07-08): dropped the body/status text entirely (title +
    // icon only per request) and replaced the wrapping FlowRow with a plain
    // Row so the two actions are always on one line, each taking half the
    // width, instead of sometimes wrapping to a second line.
    SoftCard(palette = palette, accent = accent, hero = false, tintWithAccent = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(accent.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(16.dp))
            }
            Spacer(Modifier.width(10.dp))
            Text(
                text = title,
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 15.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
        }
        Spacer(Modifier.height(10.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            PrimaryButton(
                text = primaryAction,
                accent = accent,
                compact = true,
                modifier = Modifier.weight(1f),
                onClick = onPrimaryAction
            )
            if (secondaryAction != null && onSecondaryAction != null) {
                PrimaryButton(
                    text = secondaryAction,
                    accent = accent,
                    compact = true,
                    modifier = Modifier.weight(1f),
                    onClick = onSecondaryAction
                )
            }
        }
    }
}

internal data class BitPalette(
    val dark: Boolean,
    val systemBackground: Color,
    val card: Color,
    val text: Color,
    val secondaryText: Color,
    val stroke: Color,
    val activity: Color,
    val sleep: Color,
    val mind: Color,
    val heart: Color,
    val backgroundBrush: Brush
) {
    companion object {
        // light() intentionally uses its own, slightly more saturated accent
        // values rather than HealthAccent's dark-mode hexes verbatim: the same
        // glow-tinted accent that reads as rich against a near-black card
        // washes out and looks chalky against white, so a small amount of
        // per-theme accent tuning is correct design, not drift -- unlike the
        // old dark() values below, which differed from HealthAccent by a few
        // hex units for no reason and would have drifted further over time.
        fun light(): BitPalette = BitPalette(
            dark = false,
            systemBackground = Color(0xFFF6F4F1),
            card = Color.White,
            text = Color(0xFF111318),
            secondaryText = Color(0xFF6E6E73),
            stroke = Color(0x1A111318),
            activity = Color(0xFFFF6B5F),
            sleep = Color(0xFF7B61FF),
            mind = Color(0xFF46C7B7),
            heart = Color(0xFFE53935),
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFFF6F4F1), Color(0xFFFFFFFF)))
        )
        // dark() now matches HealthAccent exactly (single source of truth):
        // previously activity was FF6B5F here vs FF6B5A in HealthAccent, and
        // sleep had three different values across the file (FF6B5A's sibling
        // mismatch, 9E6FC3 here, 7B61FF in light(), 6D5DF6 in the old
        // HealthAccent) -- imperceptible individually, but exactly the kind
        // of token drift that compounds into visible inconsistency over time.
        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = Color(0xFF0C0C0E),
            card = Color(0xCC1C1C1E),
            text = Color(0xFFF8F8F8),
            secondaryText = Color(0xFF8E8E93),
            stroke = Color(0x22FFFFFF),
            activity = HealthAccent.activity,
            sleep = HealthAccent.sleep,
            mind = HealthAccent.mind,
            heart = HealthAccent.heart,
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFF0C0C0E), Color(0xFF1C1C1E)))
        )
    }
}

/*
 * UI sprint note:
 * Runtime copy must remain cleanly localized: Russian for ru devices, English fallback for all others.
 * New UI strings should be added to res/values and res/values-ru first.
 */

private fun formatNumber(value: Long): String = String.format(Locale.getDefault(), "%,d", value).replace(',', ' ')

/**
 * Builds the "Обновлено только что / N мин назад / N ч назад" subtitle shown
 * under the Summary title (v1.9.11). [lastUpdatedAtMs] of 0 means no
 * successful read has ever completed in this install (genuinely brand new),
 * in which case this returns null and no subtitle is shown at all.
 *
 * This exists to directly answer the original complaint that prompted this
 * whole persistence effort: "data doesn't seem to be saved, every launch
 * looks like a blank slate". Showing concretely how fresh the on-screen
 * numbers are turns that uncertainty into visible, verifiable trust -- the
 * same pattern Apple Health/Oura/Whoop use for exactly this reason.
 */
@Composable
private fun formatUpdatedAgo(lastUpdatedAtMs: Long, isFromCache: Boolean): String? {
    if (lastUpdatedAtMs <= 0L) return null

    val ageMs = (System.currentTimeMillis() - lastUpdatedAtMs).coerceAtLeast(0L)
    val ageMinutes = ageMs / 60_000L
    val ageHours = ageMinutes / 60L

    val whenText = when {
        ageMinutes < 1L -> stringResource(R.string.updated_just_now)
        ageMinutes < 60L -> stringResource(R.string.updated_minutes_ago, ageMinutes.toInt())
        ageHours < 24L -> stringResource(R.string.updated_hours_ago, ageHours.toInt())
        else -> stringResource(R.string.updated_days_ago, (ageHours / 24L).toInt())
    }

    return if (isFromCache) "$whenText · ${stringResource(R.string.updated_cached_suffix)}" else whenText
}
