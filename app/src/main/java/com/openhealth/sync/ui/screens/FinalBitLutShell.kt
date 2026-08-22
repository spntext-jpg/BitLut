package com.openhealth.sync
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.statusBarsPadding

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
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.HuaweiAuthFailureReason
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison
import com.openhealth.sync.config.DashboardWidget
import com.openhealth.sync.config.HealthDataSource
import com.openhealth.sync.ui.DashboardUiState
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustMotion
import com.openhealth.sync.ui.theme.AugustRadius
import com.openhealth.sync.util.AppLogger
import java.util.Locale
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.ui.res.stringResource
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Today
import androidx.compose.material.icons.rounded.TrendingUp
import androidx.compose.material.icons.rounded.Cloud
import androidx.compose.material.icons.rounded.Watch
import androidx.compose.material.icons.rounded.CloudSync
import androidx.compose.material.icons.rounded.DirectionsRun
import androidx.compose.material.icons.rounded.DirectionsWalk
import androidx.compose.material.icons.rounded.DirectionsBike
import androidx.compose.material.icons.rounded.Pool
import androidx.compose.material.icons.rounded.FitnessCenter
import androidx.compose.material.icons.rounded.SelfImprovement
import androidx.compose.material.icons.rounded.Hiking
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.LocalFireDepartment
import androidx.compose.material.icons.rounded.Schedule
import androidx.compose.material.icons.rounded.Edit
import androidx.compose.material.icons.rounded.KeyboardArrowUp
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.style.TextAlign
import com.openhealth.sync.ui.ImportScreen
import com.openhealth.sync.ui.ImportViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.compose.foundation.BorderStroke
import androidx.compose.animation.core.tween
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.ui.draw.scale
import androidx.compose.foundation.Canvas
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.StrokeCap
import androidx.health.connect.client.records.ExerciseSessionRecord

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
    onExportCsv: () -> Unit = {},
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit = { _, _ -> },
    onDataSourceSelected: (HealthDataSource) -> Unit = {},
    onStepsGoalChanged: (Long) -> Unit = {},
    onActiveMinutesGoalChanged: (Int) -> Unit = {},
    onCaloriesGoalChanged: (Double) -> Unit = {},
    hasSeenPermissionsOnboarding: Boolean = true,
    onPermissionsOnboardingSeen: () -> Unit = {},
    importViewModel: ImportViewModel) {
    var selected by rememberSaveable { mutableStateOf(MainTab.Today) }
    var showArchiveImport by rememberSaveable { mutableStateOf(false) }
    var showCardLayoutEditor by rememberSaveable { mutableStateOf(false) }
    var cardLayoutVersion by rememberSaveable { mutableStateOf(0) }
    var showPermissionsOnboarding by rememberSaveable { mutableStateOf(false) }
    var showLogViewer by rememberSaveable { mutableStateOf(false) }
    val dashboardState = dashboardStateProvider()
    val syncState = syncStateProvider()
    // August v3 uses a stable light Canvas + White Surface architecture.
    // Dark styling belongs only to explicit semantic anchors (hero/nav), not
    // to every card when the OS happens to be in dark mode.
    val palette = remember { BitPalette.light() }

    // Sprint 7: the first time someone would trigger the real Health Connect
    // permission request, show a plain-language rationale screen instead --
    // the system's own permission dialog is terse ("Allow BitLut to access
    // Steps?") and gives no context for why. This wraps every onRequestGoogle
    // call site (Summary lock screen, Settings) without changing any of
    // them individually.
    val wrappedOnRequestGoogle: () -> Unit = {
        if (!hasSeenPermissionsOnboarding) {
            showPermissionsOnboarding = true
        } else {
            onRequestGoogle()
        }
    }

    // August v3 keeps navigation as a stable Navy anchor. Scaffold owns
    // content insets normally; no blur-source or measured-clearance plumbing.

    Scaffold(
        containerColor = palette.systemBackground,
        bottomBar = {
            AugustBottomNav(
                selected = selected,
                onSelected = { selected = it },
                onSecretLogViewerTriggered = { showLogViewer = true },
                onRefreshClick = onSyncNow
            )
        }
    ) { padding ->
        // Standard Scaffold padding keeps content clear of the fixed bottom navigation.
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
            } else if (showCardLayoutEditor) {
                CardLayoutEditorScreen(
                    palette = palette,
                    onBack = {
                        showCardLayoutEditor = false
                        cardLayoutVersion++
                    }
                )
            } else when (selected) {
                MainTab.Today -> SummaryScreen(
                    palette, dashboardState, syncState.selectedDataSource, onRefresh, wrappedOnRequestGoogle,
                    onEditLayout = { showCardLayoutEditor = true },
                    cardLayoutVersion = cardLayoutVersion
                )
                MainTab.Settings -> SettingsScreen(palette, syncState, onRefresh, wrappedOnRequestGoogle, onRequestHuawei, onSyncNow,
                    onImportArchive = { showArchiveImport = true },
                    onExportCsv = onExportCsv,
                    onWidgetVisibilityChanged = onWidgetVisibilityChanged,
                    onDataSourceSelected = onDataSourceSelected,
                    stepsGoal = dashboardState.stepsGoal,
                    activeMinutesGoal = dashboardState.activeMinutesGoal,
                    caloriesGoalKcal = dashboardState.caloriesGoalKcal,
                    onStepsGoalChanged = onStepsGoalChanged,
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

    // Sprint (2026-07-16): same fix as PermissionsOnboardingScreen just
    // above -- this screen also renders outside the Scaffold, so its Copy/
    // Close buttons started rendering half under the status bar the moment
    // enableEdgeToEdge() shipped (confirmed from a real device: "кнопка
    // слезла вверх, наполовину закрыта").
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
            .statusBarsPadding()
            .navigationBarsPadding()
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
                        modifier = Modifier,
                        onClick = {
                            val dump = com.openhealth.sync.util.AppLogger.exportFullDump(context)
                            clipboardManager.setText(androidx.compose.ui.text.AnnotatedString(dump))
                        }
                    )
                    PrimaryButton(
                        text = "Close",
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
    // Sprint (2026-07-16): this screen renders outside the main Scaffold
    // (see FinalBitLutShell's root -- it's a sibling shown after the
    // Scaffold closes, not routed through its content padding), so it never
    // got the Scaffold's automatic safeDrawing inset padding that
    // ImportScreen/SummaryScreen/SettingsScreen get for free. That was
    // invisible before enableEdgeToEdge() (the OS reserved status/nav bar
    // space outside the app's content entirely), but became a real bug the
    // moment edge-to-edge was enabled: this screen's own content now draws
    // under the status bar with nothing pushing it down. Fixed here rather
    // than by routing this screen through the Scaffold, to keep this a
    // one-line fix instead of a structural change.
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
            .statusBarsPadding()
            .navigationBarsPadding()
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

/**
 * Trust screen (sprint 2026-07-14): a plain-language, complete list of the
 * exact 5 Huawei Health Kit scopes BitLut requests -- not a marketing
 * summary, the actual list, matching requestedScopeNames() in
 * HuaweiHealthManager verbatim in substance (5 items, same order). Answers
 * the single most common complaint pattern seen in reviews of similar sync
 * apps: "I don't understand what's being synced where." No dismiss-and-never
 * shown-again state -- this is meant to be checked back in on, so it's
 * reachable any time from Settings rather than a one-time onboarding step.
 */
@Composable
private fun DataScopesScreen(palette: BitPalette, onClose: () -> Unit) {
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
                    text = stringResource(R.string.data_scopes_title),
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 26.sp
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    text = stringResource(R.string.data_scopes_body),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 15.sp,
                    lineHeight = 21.sp
                )
                Spacer(Modifier.height(24.dp))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.DirectionsRun, text = stringResource(R.string.data_scopes_step))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.TrendingUp, text = stringResource(R.string.data_scopes_distance))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.Watch, text = stringResource(R.string.data_scopes_activity))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.LocalFireDepartment, text = stringResource(R.string.data_scopes_activity_record))
                OnboardingScopeRow(palette = palette, icon = Icons.Rounded.Schedule, text = stringResource(R.string.data_scopes_history_week))
                Spacer(Modifier.height(16.dp))
                Text(
                    text = stringResource(R.string.data_scopes_destination),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                )
            }

            PrimaryButton(
                text = stringResource(R.string.data_scopes_close),
                onClick = onClose
            )
        }
    }
}

@Composable
private fun SummaryScreen(
    palette: BitPalette,
    state: DashboardUiState,
    dataSource: HealthDataSource,
    onRefresh: () -> Unit,
    onRequestGoogle: () -> Unit,
    onEditLayout: () -> Unit,
    cardLayoutVersion: Int
) {
    val context = LocalContext.current
    val orderedCards = remember(cardLayoutVersion) {
        com.openhealth.sync.config.DashboardCardLayoutPrefs(context).orderedVisibleCards()
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 14.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            MinimalHeader(
                palette = palette,
                title = stringResource(R.string.summary_short_title),
                trailing = formatDashboardSourceStatus(
                    source = dataSource,
                    lastUpdatedAtMs = state.lastUpdatedAtMs,
                    isFromCache = state.isFromCache
                ),
                onEditClick = onEditLayout
            )
        }

        when {
            state.showConnectLockScreen -> item {
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

            state.isLoading && state.stepsToday == 0L && state.recentWorkouts.isEmpty() -> item {
                DashboardLoadingCard(palette = palette)
            }

            else -> {
                item {
                    MinimalMetricCard(
                        palette = palette,
                        title = stringResource(R.string.steps_today),
                        value = formatNumber(state.stepsToday),
                        unit = "${stringResource(R.string.steps_unit)} · ${stringResource(R.string.distance_today_value, formatOneDecimal(state.distanceMeters / 1000.0))}",
                        accent = AugustColor.Lime,
                        progress = state.stepsProgress,
                        progressText = stepsGoalProgressText(state.stepsToday, state.stepsGoal),
                        hero = true,
                        pressLift = true
                    )
                }

                orderedCards.forEach { cardType ->
                    item {
                        DashboardOrderedCard(palette = palette, state = state, cardType = cardType)
                    }
                }
            }
        }
    }
}

/** Dispatches to the right card composable for a DashboardCardType -- the reorderable set edited from the pencil icon. */
@Composable
private fun DashboardOrderedCard(palette: BitPalette, state: DashboardUiState, cardType: com.openhealth.sync.config.DashboardCardType) {
    when (cardType) {
        com.openhealth.sync.config.DashboardCardType.WORKOUT_LATEST ->
            WorkoutRecencyCard(
                palette = palette,
                label = stringResource(R.string.dashboard_latest_workout),
                emptyText = stringResource(R.string.dashboard_workout_empty_latest),
                position = 1,
                session = state.recentWorkouts.getOrNull(0),
                accent = HealthAccent.mind
            )

        com.openhealth.sync.config.DashboardCardType.WORKOUT_PREVIOUS ->
            WorkoutRecencyCard(
                palette = palette,
                label = stringResource(R.string.dashboard_previous_workout),
                emptyText = stringResource(R.string.dashboard_workout_empty_previous),
                position = 2,
                session = state.recentWorkouts.getOrNull(1),
                accent = HealthAccent.violet
            )

        com.openhealth.sync.config.DashboardCardType.LAST_7_DAYS ->
            LastSevenDaysCard(palette = palette, state = state)

        com.openhealth.sync.config.DashboardCardType.PERSONAL_RECORDS ->
            PersonalRecordsCard(
                palette = palette,
                bestStepsDay = state.bestStepsDay,
                bestDistanceDay = state.bestDistanceDay,
                bestCaloriesDay = state.bestCaloriesDay,
                bestElevationDay = state.bestElevationDay,
                bestWorkoutDuration = state.bestWorkoutDuration,
                isStepsRecordToday = state.isStepsRecordToday
            )

        com.openhealth.sync.config.DashboardCardType.STREAK ->
            StreakCard(palette = palette, streak = state.streak, stepsGoal = state.stepsGoal)
    }
}

/**
 * Full-screen editor reached from the pencil icon on the Today screen.
 * Reorders with up/down buttons rather than drag-and-drop -- Compose has no
 * built-in drag-reorder, and pulling in a third-party library for it is
 * exactly the kind of new-dependency risk worth avoiding for a first pass.
 * Every change (reorder or visibility toggle) is persisted immediately, the
 * same "no explicit save button" pattern already used everywhere else in
 * Settings (goals, workout filter).
 */
@Composable
private fun CardLayoutEditorScreen(palette: BitPalette, onBack: () -> Unit) {
    val context = LocalContext.current
    val prefs = remember { com.openhealth.sync.config.DashboardCardLayoutPrefs(context) }
    var cards by remember { mutableStateOf(prefs.allCardsForEditor()) }
    var hidden by remember { mutableStateOf(prefs.hiddenKeys()) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
            .padding(horizontal = 20.dp, vertical = 14.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .clickable(onClick = onBack),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = null, tint = palette.text)
            }
            Spacer(Modifier.width(10.dp))
            Text(
                text = stringResource(R.string.dashboard_edit_layout_title),
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 22.sp
            )
        }
        Spacer(Modifier.height(6.dp))
        Text(
            text = stringResource(R.string.dashboard_edit_layout_body),
            color = palette.secondaryText,
            fontWeight = FontWeight.Medium,
            fontSize = 13.sp,
            lineHeight = 18.sp
        )
        Spacer(Modifier.height(16.dp))
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(bottom = 8.dp)
        ) {
            itemsIndexed(cards, key = { _, item -> item.key }) { index, cardType ->
                CardLayoutRow(
                    palette = palette,
                    label = dashboardCardLabel(cardType),
                    visible = cardType.key !in hidden,
                    canMoveUp = index > 0,
                    canMoveDown = index < cards.lastIndex,
                    onToggleVisible = { checked ->
                        hidden = if (checked) hidden - cardType.key else hidden + cardType.key
                        prefs.setHidden(cardType, !checked)
                    },
                    onMoveUp = {
                        cards = cards.toMutableList().apply { add(index - 1, removeAt(index)) }
                        prefs.setOrder(cards)
                    },
                    onMoveDown = {
                        cards = cards.toMutableList().apply { add(index + 1, removeAt(index)) }
                        prefs.setOrder(cards)
                    }
                )
            }
        }
    }
}

@Composable
private fun CardLayoutRow(
    palette: BitPalette,
    label: String,
    visible: Boolean,
    canMoveUp: Boolean,
    canMoveDown: Boolean,
    onToggleVisible: (Boolean) -> Unit,
    onMoveUp: () -> Unit,
    onMoveDown: () -> Unit
) {
    SoftCard(palette = palette, accent = HealthAccent.activity) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Text(
                text = label,
                color = palette.text,
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .then(if (canMoveUp) Modifier.clickable(onClick = onMoveUp) else Modifier)
                    .alpha(if (canMoveUp) 1f else 0.3f),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Rounded.KeyboardArrowUp, contentDescription = null, tint = palette.secondaryText, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(4.dp))
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .then(if (canMoveDown) Modifier.clickable(onClick = onMoveDown) else Modifier)
                    .alpha(if (canMoveDown) 1f else 0.3f),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Rounded.KeyboardArrowDown, contentDescription = null, tint = palette.secondaryText, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(10.dp))
            Switch(
                checked = visible,
                onCheckedChange = onToggleVisible,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.White,
                    checkedTrackColor = HealthAccent.activity,
                    uncheckedThumbColor = Color.White,
                    uncheckedTrackColor = palette.stroke
                )
            )
        }
    }
}

@Composable
private fun dashboardCardLabel(type: com.openhealth.sync.config.DashboardCardType): String = when (type) {
    com.openhealth.sync.config.DashboardCardType.WORKOUT_LATEST -> stringResource(R.string.dashboard_latest_workout)
    com.openhealth.sync.config.DashboardCardType.WORKOUT_PREVIOUS -> stringResource(R.string.dashboard_previous_workout)
    com.openhealth.sync.config.DashboardCardType.LAST_7_DAYS -> stringResource(R.string.dashboard_last_7_days_title)
    com.openhealth.sync.config.DashboardCardType.PERSONAL_RECORDS -> stringResource(R.string.insights_personal_records_title)
    com.openhealth.sync.config.DashboardCardType.STREAK -> stringResource(R.string.dashboard_card_streak_label)
}

@Composable
private fun LastSevenDaysCard(palette: BitPalette, state: DashboardUiState) {
    SoftCard(palette = palette, accent = HealthAccent.mind, tintWithAccent = true, pressLift = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.Schedule, contentDescription = null, tint = HealthAccent.mind, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(8.dp))
            Text(
                text = stringResource(R.string.dashboard_last_7_days_title),
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 16.sp
            )
        }
        Spacer(Modifier.height(14.dp))
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SevenDayStat(
                modifier = Modifier.weight(1f),
                palette = palette,
                label = stringResource(R.string.dashboard_average_steps),
                value = formatNumber(state.averageSteps7d),
                detail = stringResource(R.string.steps_unit),
                accent = HealthAccent.mind
            )
            SevenDayStat(
                modifier = Modifier.weight(1f),
                palette = palette,
                label = stringResource(R.string.dashboard_best_day),
                value = state.bestStepsDay7d?.let { formatNumber(it.value.toLong()) } ?: stringResource(R.string.no_data_short),
                detail = state.bestStepsDay7d?.let { formatRecordDate(it.date) } ?: "",
                accent = HealthAccent.activity
            )
            val change = state.stepsChangeVsPrevious7d
            SevenDayStat(
                modifier = Modifier.weight(1f),
                palette = palette,
                label = stringResource(R.string.dashboard_vs_previous_7_days),
                value = change?.let { "${if (it >= 0) "+" else ""}$it%" } ?: stringResource(R.string.no_data_short),
                detail = if (change == null) stringResource(R.string.dashboard_no_baseline) else "",
                accent = if ((change ?: 0) >= 0) HealthAccent.mind else palette.secondaryText
            )
        }
    }
}

@Composable
private fun SevenDayStat(
    palette: BitPalette,
    label: String,
    value: String,
    detail: String,
    accent: Color,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier) {
        Text(label, color = palette.secondaryText, fontWeight = FontWeight.SemiBold, fontSize = 10.sp, maxLines = 2, lineHeight = 13.sp)
        Spacer(Modifier.height(5.dp))
        Text(value, color = accent, fontWeight = FontWeight.Black, fontSize = 18.sp, maxLines = 1)
        if (detail.isNotBlank()) {
            Spacer(Modifier.height(2.dp))
            Text(detail, color = palette.secondaryText, fontWeight = FontWeight.SemiBold, fontSize = 9.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}


/**
 * Maps a Health Connect exercise type to a representative icon so workout
 * cards visually distinguish running from cycling, swimming, etc., instead
 * of showing the same running icon for every session type. Only covers the
 * exercise types common enough in Huawei Health exports to be worth a
 * dedicated icon; anything else (including a null/unknown type, e.g. no
 * recent workout yet) falls back to the generic running icon that was
 * already the card's default before per-type icons existed.
 */
private fun workoutIcon(exerciseType: Int?): ImageVector = when (exerciseType) {
    ExerciseSessionRecord.EXERCISE_TYPE_WALKING -> Icons.Rounded.DirectionsWalk
    ExerciseSessionRecord.EXERCISE_TYPE_BIKING -> Icons.Rounded.DirectionsBike
    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER,
    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL -> Icons.Rounded.Pool
    ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING,
    ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING -> Icons.Rounded.FitnessCenter
    ExerciseSessionRecord.EXERCISE_TYPE_YOGA,
    ExerciseSessionRecord.EXERCISE_TYPE_PILATES -> Icons.Rounded.SelfImprovement
    ExerciseSessionRecord.EXERCISE_TYPE_HIKING -> Icons.Rounded.Hiking
    else -> Icons.Rounded.DirectionsRun
}

/**
 * Four deliberately type-aware metrics per workout. Values are either read
 * from already-imported Health Connect streams or derived from real distance +
 * duration; unavailable values render as an em dash instead of being invented.
 */
private data class WorkoutMetricDisplay(val label: String, val value: String)

@Composable
private fun workoutMetricDisplays(session: ActivitySessionData, durationMinutes: Long): List<WorkoutMetricDisplay> {
    val noData = stringResource(R.string.no_data_short)
    val distanceMeters = session.distanceMeters?.takeIf { it > 0.0 }
    val distanceKm = distanceMeters?.div(1000.0)
    val calories = session.activeCaloriesKcal?.takeIf { it > 0.0 }
    val elevation = session.elevationMeters?.takeIf { it > 0.0 }
    val steps = session.steps?.takeIf { it > 0L }
    val durationHours = (session.endTimeMs - session.startTimeMs).toDouble() / 3_600_000.0
    val averageSpeedKmh = if (distanceKm != null && durationHours > 0.0 && distanceMeters >= MIN_DISTANCE_METERS_FOR_SPEED) {
        distanceKm / durationHours
    } else null
    val paceMinutesPerKm = if (distanceKm != null && distanceMeters >= MIN_DISTANCE_METERS_FOR_PACE && durationMinutes > 0L) {
        durationMinutes.toDouble() / distanceKm
    } else null
    val swimPaceMinutesPer100m = if (distanceMeters != null && distanceMeters >= MIN_DISTANCE_METERS_FOR_SWIM_PACE && durationMinutes > 0L) {
        durationMinutes.toDouble() / (distanceMeters / 100.0)
    } else null

    @Composable
    fun duration() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_duration_label),
        stringResource(R.string.workout_duration_value, durationMinutes)
    )
    @Composable
    fun distance() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_distance_label),
        distanceKm?.let { stringResource(R.string.distance_today_value, formatOneDecimal(it)) } ?: noData
    )
    @Composable
    fun caloriesMetric() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_calories_label),
        calories?.let { stringResource(R.string.workout_calories_value, it.toLong()) } ?: noData
    )
    @Composable
    fun elevationMetric() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_elevation_label),
        elevation?.let { stringResource(R.string.workout_elevation_value, it.toLong()) } ?: noData
    )
    @Composable
    fun stepsMetric() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_steps_label),
        steps?.let(::formatNumber) ?: noData
    )
    @Composable
    fun started() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_started_label),
        formatWorkoutDateTime(session.startTimeMs)
    )
    @Composable
    fun ended() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_ended_label),
        formatWorkoutClockTime(session.endTimeMs)
    )
    @Composable
    fun pace() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_pace_label),
        paceMinutesPerKm?.let { stringResource(R.string.workout_pace_value, formatPace(it)) } ?: noData
    )
    @Composable
    fun speed() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_speed_label),
        averageSpeedKmh?.let { stringResource(R.string.workout_speed_value, formatOneDecimal(it)) } ?: noData
    )
    @Composable
    fun swimPace() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_swim_pace_label),
        swimPaceMinutesPer100m?.let { stringResource(R.string.workout_swim_pace_value, formatPace(it)) } ?: noData
    )

    fun prefer(primary: WorkoutMetricDisplay, fallback: WorkoutMetricDisplay): WorkoutMetricDisplay =
        if (primary.value != noData) primary else fallback

    return when (session.exerciseType) {
        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING,
        ExerciseSessionRecord.EXERCISE_TYPE_WALKING -> listOf(
            duration(),
            prefer(distance(), stepsMetric()),
            prefer(pace(), started()),
            prefer(caloriesMetric(), ended())
        )

        ExerciseSessionRecord.EXERCISE_TYPE_BIKING -> listOf(
            duration(),
            prefer(distance(), started()),
            prefer(speed(), ended()),
            prefer(elevationMetric(), stepsMetric())
        )

        ExerciseSessionRecord.EXERCISE_TYPE_HIKING -> listOf(
            duration(),
            prefer(distance(), stepsMetric()),
            prefer(elevationMetric(), started()),
            prefer(caloriesMetric(), ended())
        )

        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER,
        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL -> listOf(
            duration(),
            prefer(distance(), started()),
            prefer(swimPace(), ended()),
            prefer(caloriesMetric(), started())
        )

        ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING,
        ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING ->
            listOf(duration(), prefer(caloriesMetric(), stepsMetric()), started(), ended())

        ExerciseSessionRecord.EXERCISE_TYPE_YOGA,
        ExerciseSessionRecord.EXERCISE_TYPE_PILATES ->
            listOf(duration(), started(), ended(), prefer(caloriesMetric(), stepsMetric()))

        else -> listOf(
            duration(),
            prefer(distance(), stepsMetric()),
            started(),
            prefer(caloriesMetric(), ended())
        )
    }
}

@Composable
private fun WorkoutRecencyCard(
    palette: BitPalette,
    label: String,
    emptyText: String,
    position: Int,
    session: ActivitySessionData?,
    accent: Color
) {
    val durationMinutes = session?.let {
        ((it.endTimeMs - it.startTimeMs) / 60_000L).coerceAtLeast(0L)
    }

    SoftCard(
        palette = palette,
        accent = accent,
        hero = false,
        tintWithAccent = true,
        pressLift = true
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.Top
        ) {
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(RoundedCornerShape(18.dp))
                    .background(accent.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    workoutIcon(session?.exerciseType),
                    contentDescription = null,
                    tint = accent,
                    modifier = Modifier.size(24.dp)
                )
            }
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = label.uppercase(Locale.getDefault()),
                        color = palette.secondaryText,
                        fontWeight = FontWeight.Black,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(99.dp))
                            .background(accent.copy(alpha = 0.14f))
                            .padding(horizontal = 8.dp, vertical = 3.dp)
                    ) {
                        Text(text = "#$position", color = accent, fontWeight = FontWeight.Black, fontSize = 10.sp)
                    }
                }
                Spacer(Modifier.height(7.dp))
                Text(
                    text = session?.let { cleanWorkoutCardTitle(it.title) } ?: stringResource(R.string.no_workouts),
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 17.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (session != null) {
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = formatWorkoutDateTime(session.startTimeMs),
                        color = palette.secondaryText,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 11.sp,
                        maxLines = 1
                    )
                }
                Spacer(Modifier.height(12.dp))
                if (session != null && durationMinutes != null) {
                    WorkoutStatsGrid(
                        palette = palette,
                        accent = accent,
                        metrics = workoutMetricDisplays(session, durationMinutes)
                    )
                } else {
                    Text(
                        text = emptyText,
                        color = palette.secondaryText,
                        fontWeight = FontWeight.Medium,
                        fontSize = 12.sp,
                        lineHeight = 17.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun WorkoutStatsGrid(
    palette: BitPalette,
    accent: Color,
    metrics: List<WorkoutMetricDisplay>
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        metrics.take(4).chunked(2).forEach { rowMetrics ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                rowMetrics.forEach { metric ->
                    WorkoutStat(
                        modifier = Modifier.weight(1f),
                        palette = palette,
                        valueColor = palette.text,
                        label = metric.label,
                        value = metric.value
                    )
                }
                if (rowMetrics.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun WorkoutStat(
    modifier: Modifier = Modifier,
    palette: BitPalette,
    valueColor: Color,
    label: String,
    value: String
) {
    Column(modifier = modifier) {
        Text(
            text = label.uppercase(Locale.getDefault()),
            color = palette.secondaryText,
            fontWeight = FontWeight.Black,
            fontSize = 9.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
        Spacer(Modifier.height(3.dp))
        Text(
            text = value,
            color = valueColor,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 14.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}

/** Pace shown as M:SS per unit distance. */
private fun formatPace(minutesPerUnit: Double): String {
    val totalSeconds = (minutesPerUnit * 60.0).toInt().coerceAtLeast(0)
    val minutes = totalSeconds / 60
    val seconds = totalSeconds % 60
    return "$minutes:${seconds.toString().padStart(2, '0')}"
}

private const val MIN_DISTANCE_METERS_FOR_PACE = 500.0
private const val MIN_DISTANCE_METERS_FOR_SPEED = 500.0
private const val MIN_DISTANCE_METERS_FOR_SWIM_PACE = 100.0

private fun formatWorkoutClockTime(epochMs: Long): String =
    java.time.Instant.ofEpochMilli(epochMs)
        .atZone(java.time.ZoneId.systemDefault())
        .format(java.time.format.DateTimeFormatter.ofPattern("HH:mm", Locale.getDefault()))

private fun formatWorkoutDateTime(epochMs: Long): String =
    java.time.Instant.ofEpochMilli(epochMs)
        .atZone(java.time.ZoneId.systemDefault())
        .format(
            java.time.format.DateTimeFormatter.ofPattern(
                "d MMM · HH:mm",
                Locale.getDefault()
            )
        )

private val workoutCadenceLabel = Regex(
    pattern = "(?i)(макс(?:имальный)?\\.?\\s*каденс|max(?:imum)?\\.?\\s*cadence)"
)

private fun cleanWorkoutCardTitle(raw: String): String {
    val normalized = raw.replace('\r', '\n').trim()
    val match = workoutCadenceLabel.find(normalized)
    val cleaned = if (match != null) normalized.substring(0, match.range.first) else normalized
    return cleaned
        .trim(' ', '\n', '\t', '·', '•', '|', ';', ':', '-')
        .ifBlank {
            normalized.lineSequence()
                .map { it.trim() }
                .firstOrNull { it.isNotBlank() && !workoutCadenceLabel.containsMatchIn(it) }
                ?: normalized
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
            if (positive) {
                // August design system integration, phase 2 (see
                // AugustTokens.kt): this is the app's first real "growth"
                // moment -- a week-over-week improvement -- and the doc's
                // own named pattern for exactly this ("Growth: Lime with
                // Navy text. Never use Lime text on white", section 3.1) is
                // a small dark-backed badge, not bare colored text on the
                // ambient card. A bare Lime number on this app's white/light
                // cards measures at 1.14:1 contrast (computed) -- unreadable
                // -- which is why [mind]/HealthAccent still aliases to
                // Accent Dark rather than Lime (see HealthAccent's doc
                // comment): Lime needs its own dark backing per call site,
                // not a global color swap. Navy is used as a fixed badge
                // color in both light and dark theme, matching the doc's
                // literal "Lime with Navy text" pairing rather than
                // following the surrounding card's theme.
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(AugustRadius.Pill))
                        .background(AugustColor.Navy)
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = "+$percentChange%",
                        color = AugustColor.GrowthLime,
                        fontWeight = FontWeight.Black,
                        fontSize = 14.sp
                    )
                }
            } else {
                Text(
                    text = "$percentChange%",
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Black,
                    fontSize = 18.sp
                )
            }
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
private data class PersonalRecordDisplay(
    val label: String,
    val value: String,
    val record: PersonalRecord
)

@Composable
private fun PersonalRecordsCard(
    palette: BitPalette,
    bestStepsDay: PersonalRecord?,
    bestDistanceDay: PersonalRecord?,
    bestCaloriesDay: PersonalRecord?,
    bestElevationDay: PersonalRecord?,
    bestWorkoutDuration: PersonalRecord?,
    isStepsRecordToday: Boolean
) {
    val records = listOfNotNull(
        bestStepsDay?.let {
            PersonalRecordDisplay(
                label = stringResource(R.string.record_steps_per_day),
                value = formatNumber(it.value.toLong()),
                record = it
            )
        },
        bestDistanceDay?.let {
            PersonalRecordDisplay(
                label = stringResource(R.string.distance_short_title),
                value = stringResource(R.string.distance_today_value, formatOneDecimal(it.value / 1000.0)),
                record = it
            )
        },
        bestCaloriesDay?.let {
            PersonalRecordDisplay(
                label = stringResource(R.string.dashboard_record_calories),
                value = "${it.value.toLong()} ${stringResource(R.string.kcal_unit)}",
                record = it
            )
        },
        bestElevationDay?.let {
            PersonalRecordDisplay(
                label = stringResource(R.string.dashboard_record_elevation),
                value = stringResource(R.string.dashboard_elevation_value, formatOneDecimal(it.value)),
                record = it
            )
        },
        bestWorkoutDuration?.let {
            PersonalRecordDisplay(
                label = stringResource(R.string.dashboard_record_workout),
                value = stringResource(R.string.dashboard_workout_minutes_value, it.value.toLong()),
                record = it
            )
        }
    )

    SoftCard(
        palette = palette,
        accent = HealthAccent.activity,
        tintWithAccent = true,
        pressLift = true
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(HealthAccent.activity.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Rounded.EmojiEvents, contentDescription = null, tint = HealthAccent.activity, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.width(10.dp))
            Text(
                text = stringResource(R.string.insights_personal_records_title),
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 16.sp,
                modifier = Modifier.weight(1f)
            )
            if (isStepsRecordToday) {
                Box(
                    modifier = Modifier
                        .background(HealthAccent.activity.copy(alpha = 0.18f), shape = RoundedCornerShape(20.dp))
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(stringResource(R.string.insights_new_record_badge), color = HealthAccent.activity, fontWeight = FontWeight.Black, fontSize = 10.sp)
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        if (records.isEmpty()) {
            Text(
                text = stringResource(R.string.dashboard_records_empty),
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )
        } else {
            records.forEachIndexed { index, item ->
                if (index > 0) Spacer(Modifier.height(10.dp))
                PersonalRecordRow(palette = palette, item = item)
            }
        }
    }
}

@Composable
private fun PersonalRecordRow(palette: BitPalette, item: PersonalRecordDisplay) {
    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(
            text = item.label,
            color = palette.secondaryText,
            fontWeight = FontWeight.SemiBold,
            fontSize = 12.sp,
            modifier = Modifier.weight(1f)
        )
        Column(horizontalAlignment = Alignment.End) {
            Text(item.value, color = palette.text, fontWeight = FontWeight.Black, fontSize = 15.sp)
            Text(formatRecordDate(item.record.date), color = palette.secondaryText, fontWeight = FontWeight.SemiBold, fontSize = 10.sp)
        }
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
    onRefresh: () -> Unit,
    onRequestGoogle: () -> Unit,
    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit,
    onImportArchive: () -> Unit,
    onExportCsv: () -> Unit,
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit,
    onDataSourceSelected: (HealthDataSource) -> Unit,
    stepsGoal: Long,
    activeMinutesGoal: Int,
    caloriesGoalKcal: Double,
    onStepsGoalChanged: (Long) -> Unit,
    onActiveMinutesGoalChanged: (Int) -> Unit,
    onCaloriesGoalChanged: (Double) -> Unit
) {
    var showDataScopes by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf(false) }

    // Settings intentionally contains only source selection,
    // permissions/connections, import/export, and trust information. Daily
    // goals were removed because they are outside BitLut's transfer mission.
    Box(modifier = Modifier.fillMaxSize()) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        MinimalHeader(
            palette = palette,
            title = stringResource(R.string.tab_settings)
        )

        Text(
            text = stringResource(R.string.data_source_section_title),
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 18.sp
        )
        SoftCard(palette = palette, accent = HealthAccent.violet, hero = false, tintWithAccent = true) {
            Text(
                text = stringResource(R.string.data_source_section_body),
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )
            Spacer(Modifier.height(10.dp))
            DataSourceToggleRow(
                palette = palette,
                title = stringResource(R.string.data_source_huawei_title),
                subtitle = stringResource(R.string.data_source_huawei_body),
                accent = HealthAccent.activity,
                selected = syncState.selectedDataSource == HealthDataSource.HUAWEI_HEALTH,
                onSelect = { onDataSourceSelected(HealthDataSource.HUAWEI_HEALTH) }
            )
            DataSourceToggleRow(
                palette = palette,
                title = stringResource(R.string.data_source_google_fit_title),
                subtitle = stringResource(R.string.data_source_google_fit_body),
                accent = HealthAccent.mind,
                selected = syncState.selectedDataSource == HealthDataSource.GOOGLE_FIT,
                onSelect = { onDataSourceSelected(HealthDataSource.GOOGLE_FIT) },
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

        // Sprint (2026-07-14, generalized 2026-07-18): a calm, specific
        // explanation instead of a silent no-op degrade or a generic toast.
        // Previously only shown for the 50005/pending-approval case; now
        // covers all known Huawei Health Kit failure reasons (see
        // HuaweiAuthFailureReason), since an AppGallery review rejection
        // showed that a reviewer or user hitting ANY of the other 4 cases
        // (cert mismatch, invalid config, privacy not accepted, unknown)
        // previously saw nothing here at all -- just the same generic toast
        // regardless of cause.
        val huaweiFailureReason = syncState.lastHuaweiAuthFailureReason
        if (!syncState.isHuaweiAuthorized && huaweiFailureReason != null) {
            HuaweiAuthIssueCard(palette = palette, reason = huaweiFailureReason, onRetryConnect = onRequestHuawei)
        }

        SettingsConnectionCard(
            palette = palette,
            title = stringResource(R.string.manual_sync_title),
            accent = HealthAccent.violet,
            icon = Icons.Rounded.CloudSync,
            primaryAction = stringResource(R.string.sync_now),
            onPrimaryAction = onSyncNow,
            secondaryAction = stringResource(R.string.import_archive_title),
            onSecondaryAction = onImportArchive
        )

        Text(
            text = stringResource(R.string.dashboard_goals_section_title),
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 18.sp
        )
        SoftCard(palette = palette, accent = HealthAccent.activity, tintWithAccent = true) {
            Text(
                text = stringResource(R.string.goals_section_body),
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )
            Spacer(Modifier.height(14.dp))
            GoalStepperRow(
                palette = palette,
                accent = HealthAccent.activity,
                label = stringResource(R.string.dashboard_rings_steps),
                valueText = formatNumber(stepsGoal),
                onDecrease = {
                    onStepsGoalChanged((stepsGoal - STEPS_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.STEPS_GOAL_RANGE))
                },
                onIncrease = {
                    onStepsGoalChanged((stepsGoal + STEPS_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.STEPS_GOAL_RANGE))
                }
            )
            Spacer(Modifier.height(12.dp))
            GoalStepperRow(
                palette = palette,
                accent = HealthAccent.mind,
                label = stringResource(R.string.dashboard_rings_active_minutes),
                valueText = "$activeMinutesGoal ${stringResource(R.string.minutes_short)}",
                onDecrease = {
                    onActiveMinutesGoalChanged((activeMinutesGoal - ACTIVE_MINUTES_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.ACTIVE_MINUTES_GOAL_RANGE))
                },
                onIncrease = {
                    onActiveMinutesGoalChanged((activeMinutesGoal + ACTIVE_MINUTES_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.ACTIVE_MINUTES_GOAL_RANGE))
                }
            )
            Spacer(Modifier.height(12.dp))
            GoalStepperRow(
                palette = palette,
                accent = HealthAccent.violet,
                label = stringResource(R.string.dashboard_rings_calories),
                valueText = "${caloriesGoalKcal.toInt()} ${stringResource(R.string.kcal_unit)}",
                onDecrease = {
                    onCaloriesGoalChanged((caloriesGoalKcal - CALORIES_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.CALORIES_GOAL_RANGE))
                },
                onIncrease = {
                    onCaloriesGoalChanged((caloriesGoalKcal + CALORIES_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.CALORIES_GOAL_RANGE))
                }
            )
        }

        Text(
            text = stringResource(R.string.workout_filter_section_title),
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 18.sp
        )
        SoftCard(palette = palette, accent = HealthAccent.activity, tintWithAccent = true) {
            val context = LocalContext.current
            val workoutFilterPrefs = remember { com.openhealth.sync.config.WorkoutFilterPrefs(context) }
            var minDurationMinutes by remember { mutableStateOf(workoutFilterPrefs.minDurationMinutes()) }
            var excludedTypes by remember { mutableStateOf(workoutFilterPrefs.excludedExerciseTypes()) }

            Text(
                text = stringResource(R.string.workout_filter_section_body),
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )
            Spacer(Modifier.height(14.dp))
            Text(
                text = stringResource(R.string.workout_filter_min_duration_label),
                color = palette.text,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp
            )
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                com.openhealth.sync.config.WorkoutFilterPrefs.MIN_DURATION_PRESETS_MINUTES.forEach { minutes ->
                    val selected = minDurationMinutes == minutes
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(99.dp))
                            .background(if (selected) HealthAccent.activity else palette.stroke.copy(alpha = 0.3f))
                            .clickable {
                                minDurationMinutes = minutes
                                workoutFilterPrefs.setMinDurationMinutes(minutes)
                            }
                            .padding(horizontal = 12.dp, vertical = 7.dp)
                    ) {
                        Text(
                            text = if (minutes == 0) {
                                stringResource(R.string.workout_filter_min_duration_off)
                            } else {
                                stringResource(R.string.workout_filter_min_duration_value, minutes)
                            },
                            color = if (selected) Color.White else palette.text,
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp
                        )
                    }
                }
            }
            Spacer(Modifier.height(16.dp))
            val categories = listOf(
                stringResource(R.string.workout_filter_type_walking) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_WALKING),
                stringResource(R.string.workout_filter_type_running) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_RUNNING),
                stringResource(R.string.workout_filter_type_biking) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_BIKING),
                stringResource(R.string.workout_filter_type_swimming) to listOf(
                    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL,
                    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER
                ),
                stringResource(R.string.workout_filter_type_strength) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING),
                stringResource(R.string.workout_filter_type_hiking) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_HIKING)
            )
            categories.forEachIndexed { index, (label, exerciseTypes) ->
                WidgetVisibilityRow(
                    palette = palette,
                    label = label,
                    accent = HealthAccent.activity,
                    checked = exerciseTypes.none { it in excludedTypes },
                    onCheckedChange = { checked ->
                        val updated = if (checked) {
                            excludedTypes - exerciseTypes.toSet()
                        } else {
                            excludedTypes + exerciseTypes.toSet()
                        }
                        excludedTypes = updated
                        workoutFilterPrefs.setExcludedExerciseTypes(updated)
                    },
                    isLast = index == categories.lastIndex
                )
            }
        }

        Text(
            text = stringResource(R.string.data_scopes_link),
            color = palette.secondaryText,
            fontWeight = FontWeight.SemiBold,
            fontSize = 13.sp,
            textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline,
            modifier = Modifier
                .padding(top = 4.dp)
                .clickable { showDataScopes = true }
        )

        Text(
            text = stringResource(R.string.export_csv_link),
            color = palette.secondaryText,
            fontWeight = FontWeight.SemiBold,
            fontSize = 13.sp,
            textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline,
            modifier = Modifier
                .padding(top = 2.dp, bottom = 8.dp)
                .clickable { onExportCsv() }
        )
    }

    if (showDataScopes) {
        DataScopesScreen(palette = palette, onClose = { showDataScopes = false })
    }
    }
}

/**
 * Explains *why* the last Huawei Health Kit authorization attempt failed,
 * in plain language specific to the actual cause (sprint 2026-07-18,
 * generalized from a 50005-only card after an AppGallery review rejection
 * showed the other 4 cases had no explanation at all -- just a generic
 * toast). [onRetryConnect] re-triggers the real Huawei OAuth flow -- shown
 * only for the two reasons where a fresh attempt can plausibly succeed:
 * SCOPE_PENDING_APPROVAL (Huawei's own approval notification arrives
 * outside the app entirely, e.g. by email -- the app has no way to detect
 * that on its own, so a manual retry is the only way to pick it up) and
 * PRIVACY_NOT_ACCEPTED (resolved by accepting terms in Huawei Health, then
 * retrying here). CERTIFICATE_MISMATCH and INVALID_CONFIGURATION need an
 * AppGallery Connect-side fix first -- retrying before that's done would
 * just fail the same way again, so no retry button is shown for those.
 */
@Composable
private fun HuaweiAuthIssueCard(palette: BitPalette, reason: HuaweiAuthFailureReason, onRetryConnect: () -> Unit) {
    val title: String
    val body: String
    val showRetry: Boolean
    when (reason) {
        HuaweiAuthFailureReason.SCOPE_PENDING_APPROVAL -> {
            title = stringResource(R.string.huawei_pending_approval_title)
            body = stringResource(R.string.huawei_pending_approval_body)
            showRetry = true
        }
        HuaweiAuthFailureReason.PRIVACY_NOT_ACCEPTED -> {
            title = stringResource(R.string.huawei_reason_privacy_not_accepted_title)
            body = stringResource(R.string.huawei_reason_privacy_not_accepted_body)
            showRetry = true
        }
        HuaweiAuthFailureReason.CERTIFICATE_MISMATCH -> {
            title = stringResource(R.string.huawei_reason_cert_mismatch_title)
            body = stringResource(R.string.huawei_reason_cert_mismatch_body)
            showRetry = false
        }
        HuaweiAuthFailureReason.INVALID_CONFIGURATION -> {
            title = stringResource(R.string.huawei_reason_invalid_config_title)
            body = stringResource(R.string.huawei_reason_invalid_config_body)
            showRetry = false
        }
        HuaweiAuthFailureReason.UNKNOWN -> {
            title = stringResource(R.string.huawei_reason_unknown_title)
            body = stringResource(R.string.huawei_reason_unknown_body)
            showRetry = false
        }
    }

    SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {
        Row(verticalAlignment = Alignment.Top) {
            Icon(
                Icons.Rounded.Schedule,
                contentDescription = null,
                tint = HealthAccent.activity,
                modifier = Modifier.size(20.dp)
            )
            Spacer(Modifier.width(10.dp))
            Column {
                Text(
                    text = title,
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 15.sp
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = body,
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )
                if (showRetry) {
                    Spacer(Modifier.height(10.dp))
                    val interactionSource = remember { MutableInteractionSource() }
                    Box(
                        modifier = Modifier
                            .pressScale(interactionSource)
                            .clip(RoundedCornerShape(AugustRadius.Button))
                            .background(AugustColor.Lime)
                            .clickable(interactionSource = interactionSource, indication = null) { onRetryConnect() }
                            .padding(horizontal = 16.dp, vertical = 9.dp)
                    ) {
                        Text(
                            text = stringResource(R.string.huawei_retry_connect),
                            color = AugustColor.LimeInk,
                            fontWeight = FontWeight.Black,
                            fontSize = 13.sp
                        )
                    }
                }
            }
        }
    }
}

/** One row in the exclusive source selector. A selected switch cannot
 *  be turned off by itself, which guarantees there is never a zero-source
 *  state; enabling the other row atomically deselects this one. */
@Composable
private fun DataSourceToggleRow(
    palette: BitPalette,
    title: String,
    subtitle: String,
    accent: Color,
    selected: Boolean,
    onSelect: () -> Unit,
    isLast: Boolean = false
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f).padding(end = 12.dp)) {
            Text(
                text = title,
                color = palette.text,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp
            )
            Text(
                text = subtitle,
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 12.sp,
                lineHeight = 16.sp
            )
        }
        Switch(
            checked = selected,
            onCheckedChange = { checked ->
                // Ignore an attempt to switch off the currently-selected row;
                // selecting the other row is the only valid transition.
                if (checked || !selected) onSelect()
            },
            colors = SwitchDefaults.colors(
                checkedThumbColor = AugustColor.Surface,
                checkedTrackColor = AugustColor.Purple,
                uncheckedThumbColor = Color.White,
                uncheckedTrackColor = palette.stroke
            )
        )
    }
    if (!isLast) Spacer(Modifier.height(10.dp))
}

/** Step sizes for the +/- goal editor in Settings. Values stay within GoalPrefs' own ranges via coerceIn at the call site. */
private const val STEPS_GOAL_STEP = 500L
private const val ACTIVE_MINUTES_GOAL_STEP = 5
private const val CALORIES_GOAL_STEP = 50.0

/** Label + a compact -/value/+ stepper, used by the three goal rows in Settings. */
@Composable
private fun GoalStepperRow(
    palette: BitPalette,
    accent: Color,
    label: String,
    valueText: String,
    onDecrease: () -> Unit,
    onIncrease: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, color = palette.text, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        Row(verticalAlignment = Alignment.CenterVertically) {
            GoalStepperButton(accent = accent, symbol = "–", onClick = onDecrease)
            Text(
                text = valueText,
                color = palette.text,
                fontWeight = FontWeight.Black,
                fontSize = 14.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .padding(horizontal = 10.dp)
                    .widthIn(min = 64.dp)
            )
            GoalStepperButton(accent = accent, symbol = "+", onClick = onIncrease)
        }
    }
}

@Composable
private fun GoalStepperButton(accent: Color, symbol: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(30.dp)
            .clip(RoundedCornerShape(AugustRadius.Compact))
            .background(accent.copy(alpha = 0.16f))
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Text(symbol, color = accent, fontWeight = FontWeight.Black, fontSize = 16.sp)
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
                checkedThumbColor = AugustColor.Surface,
                checkedTrackColor = AugustColor.Purple,
                uncheckedThumbColor = Color.White,
                uncheckedTrackColor = palette.stroke
            )
        )
    }
    if (!isLast) {
        Spacer(Modifier.height(8.dp))
    }
}

/**
 * Existing metric/decorative accents mapped onto August v3 Purple.
 *
 * These aliases intentionally remain for incremental migration of the large
 * dashboard file. Primary actions do not consume this object; they are always
 * Lime + Ink through PrimaryButton.
 */
internal object HealthAccent {
    // Legacy names retained for source compatibility only. Metric/card
    // decoration is neutral InkSoft in August v3; Purple is reserved for
    // focus, links and explicit secondary interaction states.
    val activity = AugustColor.InkSoft
    val violet = AugustColor.InkSoft
    val mind = AugustColor.InkSoft
}

/**
 * Tactile press feedback: scales a tappable surface down slightly while
 * pressed.
 *
 * August design system integration, phase 3 (see AugustTokens.kt): was a
 * bouncy spring (small overshoot on release) -- section 7 is explicit that
 * motion "confirms" a state change and rules out bounce/elastic overshoot
 * everywhere, not just on cards (which phase 2 already fixed). This keeps
 * the scale-on-press technique itself, which the doc doesn't rule out, just
 * on its standard tween + easing instead of a spring.
 *
 * Pass the SAME [interactionSource] you give to your own `Modifier.clickable(...)`
 * — this modifier only observes press state, it never intercepts the tap itself,
 * so the real onClick still fires exactly as before.
 */
@Composable
internal fun Modifier.pressScale(interactionSource: MutableInteractionSource): Modifier {
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.98f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "pressScale"
    )
    return this.scale(scale)
}

@Composable
private fun PrimaryButton(
    text: String,
    enabled: Boolean = true,
    compact: Boolean = false,
    modifier: Modifier = Modifier.fillMaxWidth(),
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val focused by interactionSource.collectIsFocusedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.98f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "primaryButtonScale"
    )
    val minHeight = if (compact) 44.dp else 48.dp
    val shape = RoundedCornerShape(AugustRadius.Button)

    Button(
        onClick = onClick,
        enabled = enabled,
        interactionSource = interactionSource,
        modifier = modifier
            .heightIn(min = minHeight)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .then(
                if (enabled) {
                    Modifier.shadow(
                        elevation = AugustElevation.ButtonShadowElevation,
                        shape = shape,
                        ambientColor = AugustElevation.ButtonShadowColor.copy(
                            alpha = AugustElevation.ButtonShadowAlpha
                        ),
                        spotColor = AugustElevation.ButtonShadowColor.copy(
                            alpha = AugustElevation.ButtonShadowAlpha
                        )
                    )
                } else {
                    Modifier
                }
            ),
        shape = shape,
        colors = ButtonDefaults.buttonColors(
            containerColor = AugustColor.Lime,
            contentColor = AugustColor.LimeInk,
            disabledContainerColor = AugustColor.Soft,
            disabledContentColor = AugustColor.Muted
        ),
        border = if (focused) BorderStroke(2.dp, AugustColor.Purple) else null,
        elevation = ButtonDefaults.buttonElevation(
            defaultElevation = 0.dp,
            pressedElevation = 0.dp,
            disabledElevation = 0.dp
        ),
        contentPadding = if (compact) {
            PaddingValues(horizontal = 12.dp, vertical = 8.dp)
        } else {
            ButtonDefaults.ContentPadding
        }
    ) {
        Text(
            text = text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = if (compact) 12.sp else 14.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}

/** August v3 neutral secondary action with Purple focus. */
@Composable
private fun SecondaryButton(
    text: String,
    palette: BitPalette,
    enabled: Boolean = true,
    compact: Boolean = false,
    modifier: Modifier = Modifier.fillMaxWidth(),
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val focused by interactionSource.collectIsFocusedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.98f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "secondaryButtonScale"
    )
    val minHeight = 44.dp
    val shape = RoundedCornerShape(AugustRadius.Button)

    Button(
        onClick = onClick,
        enabled = enabled,
        interactionSource = interactionSource,
        modifier = modifier
            .heightIn(min = minHeight)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            },
        shape = shape,
        colors = ButtonDefaults.buttonColors(
            containerColor = if (palette.dark) AugustColor.NavySoft else AugustColor.Soft,
            contentColor = if (palette.dark) AugustColor.Surface else AugustColor.Ink,
            disabledContainerColor = if (palette.dark) {
                AugustColor.NavySoft.copy(alpha = 0.55f)
            } else {
                AugustColor.Soft.copy(alpha = 0.65f)
            },
            disabledContentColor = if (palette.dark) {
                AugustColor.DarkSecondaryText.copy(alpha = 0.70f)
            } else {
                AugustColor.Muted.copy(alpha = 0.75f)
            }
        ),
        border = BorderStroke(
            width = if (focused) 2.dp else 1.dp,
            color = if (focused) AugustColor.Purple else palette.stroke
        ),
        elevation = ButtonDefaults.buttonElevation(
            defaultElevation = 0.dp,
            pressedElevation = 0.dp,
            disabledElevation = 0.dp
        ),
        contentPadding = if (compact) {
            PaddingValues(horizontal = 12.dp, vertical = 8.dp)
        } else {
            ButtonDefaults.ContentPadding
        }
    ) {
        Text(
            text = text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = if (compact) 12.sp else 14.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
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
            modifier = Modifier.wrapContentWidth(),
            onClick = onAction
        )
    }
}

@Composable
private fun MinimalHeader(
    palette: BitPalette,
    title: String,
    subtitle: String? = null,
    trailing: String? = null,
    onEditClick: (() -> Unit)? = null
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = title,
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 30.sp,
                maxLines = 1,
                modifier = Modifier.weight(1f)
            )
            if (trailing != null) {
                Spacer(Modifier.width(10.dp))
                Text(
                    text = trailing,
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Bold,
                    fontSize = 11.sp,
                    maxLines = 1
                )
            }
            if (onEditClick != null) {
                Spacer(Modifier.width(10.dp))
                Box(
                    modifier = Modifier
                        .size(30.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .clickable(onClick = onEditClick),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Rounded.Edit,
                        contentDescription = stringResource(R.string.dashboard_edit_layout),
                        tint = palette.secondaryText,
                        modifier = Modifier.size(19.dp)
                    )
                }
            }
        }
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
private fun formatDashboardSourceStatus(
    source: HealthDataSource,
    lastUpdatedAtMs: Long,
    isFromCache: Boolean
): String {
    val sourceName = when (source) {
        HealthDataSource.HUAWEI_HEALTH -> stringResource(R.string.data_source_huawei_title)
        HealthDataSource.GOOGLE_FIT -> stringResource(R.string.data_source_google_fit_title)
    }
    val whenText = formatUpdatedAgo(lastUpdatedAtMs, isFromCache)
        ?: stringResource(R.string.no_data_short)
    return "$sourceName · $whenText"
}

/** Progress-to-goal text shown inside the Steps card. Null when no real goal is set (defensive; GoalPrefs always returns a positive default in practice). */
@Composable
private fun stepsGoalProgressText(stepsToday: Long, stepsGoal: Long): String? {
    if (stepsGoal <= 0) return null
    val remaining = stepsGoal - stepsToday
    return if (remaining <= 0) {
        stringResource(R.string.steps_goal_reached)
    } else {
        stringResource(R.string.steps_goal_remaining, formatNumber(remaining))
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
    progressText: String? = null,
    icon: ImageVector? = null,
    hero: Boolean = false,
    pressLift: Boolean = false,
    onClick: (() -> Unit)? = null
) {
    val interactionSource = remember { MutableInteractionSource() }
    val resolvedAccent = if (hero) AugustColor.Lime else accent
    val titleColor = if (hero) AugustColor.DarkSecondaryText else palette.secondaryText
    val valueColor = if (hero) AugustColor.Surface else palette.text
    val supportingColor = if (hero) AugustColor.DarkSecondaryText else palette.secondaryText
    val cardModifier = if (onClick != null) {
        Modifier
            .fillMaxWidth()
            .pressScale(interactionSource)
            .clickable(interactionSource = interactionSource, indication = null, onClick = onClick)
    } else {
        Modifier.fillMaxWidth()
    }
    SoftCard(
        palette = palette,
        modifier = cardModifier,
        accent = resolvedAccent,
        hero = hero,
        tintWithAccent = true,
        pressLift = pressLift
    ) {
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
                    color = titleColor,
                    fontWeight = FontWeight.Black,
                    fontSize = 12.sp
                )
                Spacer(Modifier.height(4.dp))
                // Sprint (2026-07-09): fixed 56.sp overflowed once steps
                // crossed 10,000 (e.g. "12 345" is wider than "9 999").
                // Step the font size down for longer formatted values
                // instead of letting it clip/ellipsize.
                val valueFontSize = when {
                    value.length > 7 -> 36.sp
                    value.length > 5 -> 44.sp
                    else -> 56.sp
                }
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(
                        text = value,
                        color = valueColor,
                        fontWeight = FontWeight.Black,
                        fontSize = valueFontSize,
                        lineHeight = valueFontSize,
                        letterSpacing = (-1.5).sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false)
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = unit,
                        color = resolvedAccent,
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 13.sp,
                        modifier = Modifier.padding(bottom = 6.dp)
                    )
                }
            }
            if (progress != null) {
                ProgressRingChip(progress = progress, accent = resolvedAccent, size = 52.dp)
            } else if (icon != null) {
                Box(
                    modifier = Modifier
                        .size(52.dp)
                        .clip(RoundedCornerShape(26.dp))
                        .background(resolvedAccent.copy(alpha = if (hero) 1f else 0.16f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(icon, contentDescription = null, tint = if (hero) AugustColor.LimeInk else resolvedAccent, modifier = Modifier.size(24.dp))
                }
            }
        }
        if (progressText != null) {
            Spacer(Modifier.height(8.dp))
            Text(
                text = progressText,
                color = supportingColor,
                fontWeight = FontWeight.SemiBold,
                fontSize = 12.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
        if (onClick != null) {
            Spacer(Modifier.height(10.dp))
            PrimaryButton(text = unit, onClick = onClick)
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
 * Square tile for the 2x2 Summary grid (calories/workout-minutes/active-hours
 * sit side by side under the full-width Steps hero card). Follows the
 * "traffic light" rule: exactly three elements on the tile — a filled icon
 * chip, one large value, one small label. No secondary text, no extra rows —
 * the number does the talking.
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
 * have a real goal to show (currently just Steps vs the daily goal).
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
    val glowColors = remember(accent) { listOf(accent.copy(alpha = 0.14f), Color.Transparent) }

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
                compact = true,
                modifier = Modifier.weight(1f),
                onClick = onPrimaryAction
            )
            if (secondaryAction != null && onSecondaryAction != null) {
                SecondaryButton(
                    text = secondaryAction,
                    palette = palette,
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
    val mind: Color,
    val backgroundBrush: Brush
) {
    companion object {
        // August design system integration, phase 1 (see AugustTokens.kt).
        // light() previously used its own hand-tuned accent hexes rather than
        // HealthAccent's verbatim, because the old warm-orange/teal accents
        // read as "chalky" against white without per-theme tuning. August's
        // Accent/Accent Dark tokens don't have that problem -- the doc's own
        // contrast numbers (4.64:1 / 6.74:1) are already computed against a
        // white surface -- so light() now reuses HealthAccent directly too,
        // same as dark() already did.
        fun light(): BitPalette = BitPalette(
            dark = false,
            systemBackground = AugustColor.Canvas,
            card = AugustColor.Surface,
            text = AugustColor.Ink,
            secondaryText = AugustColor.Muted,
            stroke = AugustColor.BorderLight,
            activity = HealthAccent.activity,
            mind = HealthAccent.mind,
            backgroundBrush = Brush.verticalGradient(listOf(AugustColor.Canvas, AugustColor.Canvas))
        )
        // dark() reuses HealthAccent directly (single source of truth) rather
        // than redeclaring near-duplicate hex values that could drift apart.
        // systemBackground/card/text/secondaryText/stroke follow August's own
        // dark-surface rule (section 3.1: "Navy or Dark Panel with white
        // primary text and #BEC3D4 secondary text") -- see AugustColor's
        // DarkPanel/AccentLight doc comments for how those specific values
        // were derived and contrast-checked, since the source doc describes
        // Navy as a component-level anchor, not a full app dark theme.
        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = AugustColor.Navy,
            card = AugustColor.DarkPanel,
            text = Color.White,
            secondaryText = AugustColor.DarkSecondaryText,
            stroke = AugustColor.BorderDark,
            activity = HealthAccent.activity,
            mind = HealthAccent.mind,
            backgroundBrush = Brush.verticalGradient(listOf(AugustColor.Navy, AugustColor.DarkPanel))
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
