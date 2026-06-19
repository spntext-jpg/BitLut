package com.openhealth.sync

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
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
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
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.DashboardUiState
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.util.AppLogger
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.TimeUnit
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.Canvas
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.geometry.Offset
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxHeight

private const val UNIQUE_SYNC_NOW = "bitlut_sync_now"
private const val UNIQUE_PERIODIC_SYNC = "bitlut_periodic_sync"

class MainActivity : ComponentActivity() {
    private val syncViewModel: SyncViewModel by viewModels {
        val app = application as SyncApplication
        SyncViewModel.provideFactory(app.container.googleHealthManager, app.container.huaweiHealthManager, this)
    }

    private val dashboardViewModel: DashboardViewModel by viewModels {
        val app = application as SyncApplication
        DashboardViewModel.provideFactory(app.container.googleHealthManager)
    }

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")
        syncViewModel.refreshStatuses()
        dashboardViewModel.refresh()
        if (!granted.containsAll(syncViewModel.googleManager.permissions)) {
            Toast.makeText(this, BText.t("toast_hc_permissions"), Toast.LENGTH_LONG).show()
        }
    }

    private val huaweiAuthorizationLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val success = syncViewModel.huaweiHealthManager.handleAuthorizationResult(result.resultCode, result.data)
        syncViewModel.onHuaweiAuthorizationResult(success)
        syncViewModel.refreshStatuses()
        Toast.makeText(
            this,
            if (success) BText.t("toast_huawei_connected") else BText.t("toast_huawei_pending"),
            Toast.LENGTH_LONG
        ).show()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupPeriodicSync()
        setContent {
            BitLutExpressiveTheme {
                FinalBitLutShell(
                    dashboardStateProvider = { dashboardViewModel.state.collectAsState().value },
                    syncStateProvider = { syncViewModel.uiState.collectAsState().value },
                    onRefresh = {
                        syncViewModel.refreshStatuses()
                        dashboardViewModel.refresh()
                    },
                    onRequestGoogle = { googlePermissionLauncher.launch(syncViewModel.googleManager.permissions) },
                    onRequestHuawei = { startHuaweiAuthorization() },
                    onSyncNow = { triggerImmediateSync() }
                )
            }
        }
    }

    private fun startHuaweiAuthorization() {
        try {
            if (!HmsCoreHelper.isInstalled(this)) {
                Toast.makeText(this, HmsCoreHelper.missingMessage, Toast.LENGTH_LONG).show()
                return
            }
            if (!HmsCoreHelper.isHuaweiHealthInstalled(this)) {
                Toast.makeText(this, BText.t("toast_huawei_health_missing"), Toast.LENGTH_LONG).show()
                return
            }
            huaweiAuthorizationLauncher.launch(syncViewModel.huaweiHealthManager.getAuthorizationIntent())
        } catch (e: Exception) {
            AppLogger.e("MainActivity", "Huawei authorization start failed: ${e.message}", e)
            Toast.makeText(this, BText.t("toast_huawei_start_failed"), Toast.LENGTH_LONG).show()
        }
    }

    private fun triggerImmediateSync() {
        syncViewModel.markSyncStarted()
        val request = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        val wm = WorkManager.getInstance(this)
        wm.enqueueUniqueWork(UNIQUE_SYNC_NOW, ExistingWorkPolicy.REPLACE, request)
        wm.getWorkInfoByIdLiveData(request.id).observe(this) { info ->
            when (info?.state) {
                WorkInfo.State.SUCCEEDED -> {
                    syncViewModel.markSyncCompleted(true)
                    dashboardViewModel.refresh()
                }
                WorkInfo.State.FAILED, WorkInfo.State.CANCELLED -> syncViewModel.markSyncCompleted(false)
                else -> Unit
            }
        }
    }

    private fun setupPeriodicSync() {
        val request = PeriodicWorkRequestBuilder<SyncWorker>(6, TimeUnit.HOURS)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            UNIQUE_PERIODIC_SYNC,
            ExistingPeriodicWorkPolicy.UPDATE,
            request
        )
    }
}

private enum class MainTab(val key: String, val icon: String) {
    Summary("tab_summary", "◌"),
    History("tab_history", "⌁"),
    Settings("tab_settings", "⚙")
}

@Composable
private fun FinalBitLutShell(
    dashboardStateProvider: @Composable () -> DashboardUiState,
    syncStateProvider: @Composable () -> SyncUiState,
    onRefresh: () -> Unit,
    onRequestGoogle: () -> Unit,
    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit
) {
    var selected by rememberSaveable { mutableStateOf(MainTab.Summary) }
    val dashboardState = dashboardStateProvider()
    val syncState = syncStateProvider()
    val isDark = androidx.compose.foundation.isSystemInDarkTheme()
    val palette = remember(isDark) { if (isDark) BitPalette.dark() else BitPalette.light() }

    Scaffold(
        containerColor = palette.systemBackground,
        bottomBar = {
            NavigationBar(containerColor = palette.card.copy(alpha = if (isDark) 0.72f else 0.96f)) {
                MainTab.values().forEach { tab ->
                    NavigationBarItem(
                        selected = selected == tab,
                        onClick = { selected = tab },
                        icon = { Text(tab.icon, fontSize = 20.sp) },
                        label = { Text(BText.t(tab.key), fontWeight = FontWeight.SemiBold) }
                    )
                }
            }
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(palette.backgroundBrush)
                .padding(padding)
        ) {
            when (selected) {
                MainTab.Summary -> SummaryScreen(palette, dashboardState, onRefresh, onRequestGoogle)
                MainTab.History -> HistoryScreen(palette, dashboardState, onRequestGoogle)
                MainTab.Settings -> SettingsScreen(palette, syncState, onRefresh, onRequestGoogle, onRequestHuawei, onSyncNow)
            }
        }
    }
}

@Composable
private fun SummaryScreen(
    palette: BitPalette,
    state: DashboardUiState,
    onRefresh: () -> Unit,
    onRequestGoogle: () -> Unit
) {
    if (!state.hasPermissions) {
        EmptyPermissionCard(
            palette = palette,
            title = FinalUiText.t("connect_google_title"),
            body = FinalUiText.t("connect_google_summary_body"),
            button = FinalUiText.t("connect_google_button"),
            onClick = onRequestGoogle
        )
        return
    }

    val goal = 10_000L
    val steps = state.stepsToday
    val sleep = 0.0 ?: 0.0
    val heart = null ?: 0L
    val stepProgress = safeProgress(steps.toDouble(), goal.toDouble())
    val sleepProgress = safeProgress(sleep, 8.0)
    val heartProgress = if (heart > 0) safeProgress(heart.toDouble(), 120.0) else 0f

    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        item {
            FinalHealthHero(
                title = FinalUiText.t("summary_title"),
                subtitle = FinalUiText.t("summary_subtitle"),
                value = formatNumber(steps),
                unit = FinalUiText.t("steps_unit"),
                progress = stepProgress,
                accent = HealthAccent.activity,
                secondary = HealthAccent.sleep,
                tertiary = HealthAccent.heart,
                onRefresh = onRefresh
            )
        }
        item {
            FinalRingRow(
                stepProgress = stepProgress,
                sleepProgress = sleepProgress,
                heartProgress = heartProgress,
                steps = formatNumber(steps),
                sleep = if (sleep > 0.0) String.format(Locale.getDefault(), "%.1f h", sleep) else FinalUiText.t("no_data_short"),
                heart = if (heart > 0) "$heart bpm" else FinalUiText.t("no_data_short")
            )
        }
        item {
            SectionTitle(palette, FinalUiText.t("today_metrics"))
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(14.dp), modifier = Modifier.fillMaxWidth()) {
                FinalMetricTile(
                    modifier = Modifier.weight(1f),
                    icon = "👣",
                    label = FinalUiText.t("steps_today"),
                    value = formatNumber(steps),
                    detail = FinalUiText.t("goal_template").replace("%s", formatNumber(goal)),
                    accent = HealthAccent.activity
                )
                FinalMetricTile(
                    modifier = Modifier.weight(1f),
                    icon = "😴",
                    label = FinalUiText.t("sleep_last_night"),
                    value = if (sleep > 0.0) String.format(Locale.getDefault(), "%.1f", sleep) else "—",
                    detail = FinalUiText.t("hours_unit"),
                    accent = HealthAccent.sleep
                )
            }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(14.dp), modifier = Modifier.fillMaxWidth()) {
                FinalMetricTile(
                    modifier = Modifier.weight(1f),
                    icon = "♥",
                    label = FinalUiText.t("heart_today"),
                    value = if (heart > 0) heart.toString() else "—",
                    detail = FinalUiText.t("bpm_unit"),
                    accent = HealthAccent.heart
                )
                FinalMetricTile(
                    modifier = Modifier.weight(1f),
                    icon = "🏃",
                    label = FinalUiText.t("workouts"),
                    value = state.recentWorkouts.size.toString(),
                    detail = FinalUiText.t("recent_sessions"),
                    accent = HealthAccent.mind
                )
            }
        }
    }
}

@Composable
private fun SummaryRefreshButton(accent: Color, onRefresh: () -> Unit) {
    PrimaryButton(text = FinalUiText.t("refresh_short"), accent = accent, onClick = onRefresh)
}

@Composable
private fun HistoryScreen(
    palette: BitPalette,
    state: DashboardUiState,
    onRequestGoogle: () -> Unit
) {
    if (!state.hasPermissions) {
        EmptyPermissionCard(
            palette = palette,
            title = FinalUiText.t("connect_google_title"),
            body = FinalUiText.t("connect_google_history_body"),
            button = FinalUiText.t("connect_google_button"),
            onClick = onRequestGoogle
        )
        return
    }

    val stepValues = state.weeklySteps.map { it.steps.toDouble() }
    val sleepValues = state.weeklySleep.map { it.value ?: 0.0 }
    val heartValues = state.weeklyHeartRate.map { it.value?.toDouble() ?: 0.0 }

    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        item {
            ScreenHero(
                palette = palette,
                title = FinalUiText.t("history_title"),
                subtitle = FinalUiText.t("history_subtitle"),
                action = null,
                onAction = {}
            )
        }
        item {
            FinalTrendCard(
                title = FinalUiText.t("steps_7d"),
                value = formatNumber(stepValues.sumOf { it.toLong() }),
                subtitle = FinalUiText.t("total_7d"),
                values = stepValues,
                accent = HealthAccent.activity
            )
        }
        item {
            FinalTrendCard(
                title = FinalUiText.t("sleep_7d"),
                value = if (sleepValues.any { it > 0.0 }) String.format(Locale.getDefault(), "%.1f h", sleepValues.filter { it > 0.0 }.average()) else "—",
                subtitle = FinalUiText.t("avg_7d"),
                values = sleepValues,
                accent = HealthAccent.sleep
            )
        }
        item {
            FinalTrendCard(
                title = FinalUiText.t("heart_7d"),
                value = if (heartValues.any { it > 0.0 }) heartValues.filter { it > 0.0 }.average().toLong().toString() else "—",
                subtitle = FinalUiText.t("avg_bpm_7d"),
                values = heartValues,
                accent = HealthAccent.heart
            )
        }
    }
}

@Composable
private fun SettingsScreen(
    palette: BitPalette,
    state: SyncUiState,
    onRefresh: () -> Unit,
    onRequestGoogle: () -> Unit,
    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit
) {
    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        item {
            ScreenHero(
                palette = palette,
                title = FinalUiText.t("settings_title"),
                subtitle = FinalUiText.t("settings_subtitle"),
                action = FinalUiText.t("refresh_status"),
                onAction = onRefresh
            )
        }
        item {
            FinalConnectionCockpit(
                title = "Google Health Connect",
                status = if (state.hasGooglePermissions) FinalUiText.t("connected") else FinalUiText.t("not_connected"),
                body = FinalUiText.t("google_connection_body"),
                button = FinalUiText.t("connect_google_button"),
                accent = HealthAccent.mind,
                positive = state.hasGooglePermissions,
                onClick = onRequestGoogle
            )
        }
        item {
            FinalConnectionCockpit(
                title = "Huawei Health",
                status = if (state.isHuaweiAuthorized) FinalUiText.t("connected") else FinalUiText.t("not_connected"),
                body = FinalUiText.t("huawei_connection_body"),
                button = FinalUiText.t("connect_huawei_button"),
                accent = HealthAccent.activity,
                positive = state.isHuaweiAuthorized,
                onClick = onRequestHuawei
            )
        }
        item {
            FinalSyncCockpit(
                title = FinalUiText.t("manual_sync"),
                status = syncStatusText(state),
                lastSync = formatLastSync(0L),
                enabled = state.hasGooglePermissions && state.isHuaweiAuthorized,
                onSyncNow = onSyncNow
            )
        }
        item {
            FinalHealthKitStatusCard(
                title = FinalUiText.t("health_kit_status"),
                status = if (state.isHuaweiAuthorized) FinalUiText.t("health_kit_ready") else FinalUiText.t("health_kit_waiting"),
                detail = FinalUiText.t("health_kit_detail")
            )
        }
    }
}

private object HealthAccent {
    val activity = Color(0xFFFF6B5A)
    val sleep = Color(0xFF6D5DF6)
    val heart = Color(0xFFE53935)
    val mind = Color(0xFF64D2C8)
    val cardLight = Color.White
    val cardDark = Color(0xCC1C1C1E)
    val systemLight = Color(0xFFF2F2F7)
}

@Composable
private fun FinalHealthHero(
    title: String,
    subtitle: String,
    value: String,
    unit: String,
    progress: Float,
    accent: Color,
    secondary: Color,
    tertiary: Color,
    onRefresh: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(34.dp))
            .background(
                Brush.linearGradient(
                    listOf(Color.White, Color(0xFFFFF8F3), Color(0xFFF7F2FF))
                )
            )
            .border(1.dp, Color.White.copy(alpha = 0.78f), RoundedCornerShape(34.dp))
            .padding(24.dp)
    ) {
        Canvas(modifier = Modifier.matchParentSize()) {
            drawCircle(accent.copy(alpha = 0.16f), radius = size.minDimension * 0.42f, center = Offset(size.width * 0.86f, size.height * 0.20f))
            drawCircle(secondary.copy(alpha = 0.14f), radius = size.minDimension * 0.32f, center = Offset(size.width * 0.72f, size.height * 0.88f))
            drawCircle(tertiary.copy(alpha = 0.10f), radius = size.minDimension * 0.22f, center = Offset(size.width * 0.12f, size.height * 0.15f))
        }
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(title, fontSize = 34.sp, fontWeight = FontWeight.Black, color = Color(0xFF141414), lineHeight = 36.sp)
                    Spacer(Modifier.height(6.dp))
                    Text(subtitle, fontSize = 15.sp, fontWeight = FontWeight.Medium, color = Color(0xFF6B7280), lineHeight = 21.sp)
                }
                PrimaryButton(FinalUiText.t("refresh_status"), accent = accent, onClick = onRefresh)
            }
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.Bottom) {
                Text(value, fontSize = 68.sp, fontWeight = FontWeight.Black, color = Color(0xFF0B0B0C), letterSpacing = (-2).sp)
                Spacer(Modifier.width(8.dp))
                Text(unit, fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6B7280), modifier = Modifier.padding(bottom = 12.dp))
            }
            Box(Modifier.fillMaxWidth().height(13.dp).clip(RoundedCornerShape(99.dp)).background(Color(0xFFE9ECF3))) {
                Box(Modifier.fillMaxWidth(progress).fillMaxHeight().clip(RoundedCornerShape(99.dp)).background(Brush.horizontalGradient(listOf(accent, Color(0xFFFFB37A)))))
            }
        }
    }
}

@Composable
private fun FinalRingRow(stepProgress: Float, sleepProgress: Float, heartProgress: Float, steps: String, sleep: String, heart: String) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp), modifier = Modifier.fillMaxWidth()) {
        FinalActivityRing(Modifier.weight(1f), "👣", FinalUiText.t("steps_today"), steps, stepProgress, HealthAccent.activity)
        FinalActivityRing(Modifier.weight(1f), "😴", FinalUiText.t("sleep_last_night"), sleep, sleepProgress, HealthAccent.sleep)
        FinalActivityRing(Modifier.weight(1f), "♥", FinalUiText.t("heart_today"), heart, heartProgress, HealthAccent.heart)
    }
}

@Composable
private fun FinalActivityRing(modifier: Modifier, icon: String, label: String, value: String, progress: Float, accent: Color) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(32.dp))
            .background(Color.White)
            .border(1.dp, Color(0x11FFFFFF), RoundedCornerShape(32.dp))
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.size(76.dp)) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val stroke = Stroke(width = 11.dp.toPx(), cap = StrokeCap.Round)
                drawArc(Color(0xFFE9ECF3), -90f, 360f, false, style = stroke)
                drawArc(accent, -90f, 360f * progress.coerceIn(0f, 1f), false, style = stroke)
            }
            Text(icon, fontSize = 24.sp)
        }
        Text(value, fontSize = 18.sp, fontWeight = FontWeight.Black, color = Color(0xFF111827), maxLines = 1)
        Text(label, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFF8E8E93), maxLines = 1)
    }
}

@Composable
private fun FinalMetricTile(modifier: Modifier, icon: String, label: String, value: String, detail: String, accent: Color) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(32.dp))
            .background(Color.White)
            .padding(18.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            GlowBubble(accent, icon)
            Text(label, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color(0xFF8E8E93))
            Text(value, fontSize = 32.sp, fontWeight = FontWeight.Black, color = Color(0xFF111827), letterSpacing = (-1).sp)
            Text(detail, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF6B7280))
        }
    }
}

@Composable
private fun FinalTrendCard(title: String, value: String, subtitle: String, values: List<Double>, accent: Color) {
    val clean = values.ifEmpty { listOf(0.0) }
    val trend = clean.lastOrNull().orZero() - clean.firstOrNull().orZero()
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(32.dp))
            .background(Color.White)
            .padding(20.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Column {
                    Text(title, fontSize = 17.sp, fontWeight = FontWeight.Black, color = Color(0xFF111827))
                    Text(subtitle, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF8E8E93))
                }
                FinalTrendPill(trend, accent)
            }
            Text(value, fontSize = 42.sp, fontWeight = FontWeight.Black, color = Color(0xFF111827), letterSpacing = (-1.5).sp)
            FinalSparkline(values = clean, accent = accent, modifier = Modifier.fillMaxWidth().height(92.dp))
        }
    }
}

@Composable
private fun FinalSparkline(values: List<Double>, accent: Color, modifier: Modifier) {
    Canvas(modifier = modifier) {
        val max = values.maxOrNull()?.takeIf { it > 0.0 } ?: 1.0
        val min = values.minOrNull() ?: 0.0
        val range = (max - min).takeIf { it > 0.0 } ?: 1.0
        val step = if (values.size > 1) size.width / (values.size - 1) else size.width
        var previous: Offset? = null
        values.forEachIndexed { index, v ->
            val x = index * step
            val y = size.height - (((v - min) / range).toFloat() * size.height * 0.82f + size.height * 0.09f)
            val point = Offset(x, y)
            previous?.let { drawLine(accent.copy(alpha = 0.85f), it, point, strokeWidth = 5.dp.toPx(), cap = StrokeCap.Round) }
            drawCircle(accent.copy(alpha = 0.18f), radius = 9.dp.toPx(), center = point)
            drawCircle(accent, radius = 4.dp.toPx(), center = point)
            previous = point
        }
    }
}

@Composable
private fun FinalTrendPill(delta: Double, accent: Color) {
    val up = delta >= 0.0
    val arrow = if (up) "↗" else "↘"
    val text = if (delta == 0.0) "0" else String.format(Locale.getDefault(), "%.0f", kotlin.math.abs(delta))
    Box(Modifier.clip(RoundedCornerShape(99.dp)).background(accent.copy(alpha = 0.14f)).padding(horizontal = 12.dp, vertical = 8.dp)) {
        Text("$arrow $text", fontSize = 13.sp, fontWeight = FontWeight.Black, color = accent)
    }
}

@Composable
private fun FinalConnectionCockpit(title: String, status: String, body: String, button: String, accent: Color, positive: Boolean, onClick: () -> Unit) {
    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(32.dp)).background(Color.White).padding(20.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(title, fontSize = 20.sp, fontWeight = FontWeight.Black, color = Color(0xFF111827))
                    Text(body, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = Color(0xFF6B7280), lineHeight = 20.sp)
                }
                Box(Modifier.clip(RoundedCornerShape(99.dp)).background(if (positive) Color(0xFF34C759).copy(alpha = .15f) else Color(0xFFFF9500).copy(alpha = .15f)).padding(horizontal = 12.dp, vertical = 8.dp)) {
                    Text(status, fontSize = 12.sp, fontWeight = FontWeight.Black, color = if (positive) Color(0xFF15803D) else Color(0xFFB45309))
                }
            }
            PrimaryButton(button, accent = accent, onClick = onClick)
        }
    }
}

@Composable
private fun FinalSyncCockpit(title: String, status: String, lastSync: String, enabled: Boolean, onSyncNow: () -> Unit) {
    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(32.dp)).background(Color.White).padding(20.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text(title, fontSize = 20.sp, fontWeight = FontWeight.Black, color = Color(0xFF111827))
            Text(status, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF6B7280))
            Text(lastSync, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color(0xFF8E8E93))
            PrimaryButton(FinalUiText.t("sync_now"), accent = HealthAccent.activity, enabled = enabled, onClick = onSyncNow)
        }
    }
}

@Composable
private fun FinalHealthKitStatusCard(title: String, status: String, detail: String) {
    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(32.dp)).background(Brush.linearGradient(listOf(Color(0xFFFFFBF7), Color(0xFFF4F0FF)))).padding(20.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, fontSize = 20.sp, fontWeight = FontWeight.Black, color = Color(0xFF111827))
            Text(status, fontSize = 16.sp, fontWeight = FontWeight.Black, color = HealthAccent.activity)
            Text(detail, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = Color(0xFF6B7280), lineHeight = 20.sp)
        }
    }
}

private fun safeProgress(value: Double, target: Double): Float = if (target <= 0.0) 0f else (value / target).toFloat().coerceIn(0f, 1f)
private fun Double?.orZero(): Double = this ?: 0.0
@Composable
private fun formatLastSync(ms: Long): String = if (ms <= 0L) FinalUiText.t("last_sync_never") else FinalUiText.t("last_sync_template").replace("%s", formatDateTime(ms))

private object FinalUiText {
    private val ru = mapOf(
        "summary_title" to "Сводка",
        "summary_subtitle" to "Ключевые показатели здоровья: шаги, сон, пульс и тренировки.",
        "history_title" to "История",
        "history_subtitle" to "Динамика за последние 7 дней: тренды, графики и изменения.",
        "settings_title" to "Настройки",
        "settings_subtitle" to "Подключите Google Health Connect и Huawei Health, затем запустите синхронизацию.",
        "connect_google_title" to "Подключите Google Health",
        "connect_google_summary_body" to "Разрешите доступ к Health Connect, чтобы увидеть сводку здоровья.",
        "connect_google_history_body" to "Разрешите доступ к Health Connect, чтобы увидеть историю за 7 дней.",
        "connect_google_button" to "Подключить Google Health",
        "steps_unit" to "шагов",
        "no_data_short" to "—",
        "today_metrics" to "Сегодня",
        "steps_today" to "Шаги сегодня",
        "goal_template" to "цель %s",
        "sleep_last_night" to "Сон",
        "hours_unit" to "часов",
        "heart_today" to "Пульс",
        "bpm_unit" to "уд/мин",
        "workouts" to "Тренировки",
        "recent_sessions" to "последние сессии",
        "steps_7d" to "Шаги за 7 дней",
        "sleep_7d" to "Сон за 7 дней",
        "heart_7d" to "Пульс за 7 дней",
        "total_7d" to "суммарно",
        "avg_7d" to "среднее значение",
        "avg_bpm_7d" to "средний пульс",
        "refresh_status" to "Обновить",
        "connected" to "Подключено",
        "not_connected" to "Не подключено",
        "google_connection_body" to "Health Connect хранит данные на устройстве и даёт BitLut право читать и записывать поддерживаемые метрики.",
        "huawei_connection_body" to "Huawei Health Kit нужен для чтения данных Huawei Health перед экспортом в Health Connect.",
        "connect_huawei_button" to "Подключить Huawei Health",
        "manual_sync" to "Ручная синхронизация",
        "sync_now" to "Синхронизировать",
        "last_sync_never" to "Последняя синхронизация: ещё не выполнялась",
        "last_sync_template" to "Последняя синхронизация: %s",
        "health_kit_status" to "Статус Health Kit",
        "health_kit_ready" to "Готово к синхронизации",
        "health_kit_waiting" to "Ожидает авторизации или одобрения",
        "health_kit_detail" to "Если Huawei Health Kit ещё возвращает 50005, это означает ожидание серверного одобрения Huawei. Приложение не должно падать."
    )
    private val en = mapOf(
        "summary_title" to "Summary",
        "summary_subtitle" to "Key health metrics: steps, sleep, heart rate and workouts.",
        "history_title" to "History",
        "history_subtitle" to "Last 7 days: trends, charts and changes.",
        "settings_title" to "Settings",
        "settings_subtitle" to "Connect Google Health Connect and Huawei Health, then start sync.",
        "connect_google_title" to "Connect Google Health",
        "connect_google_summary_body" to "Allow Health Connect access to see your health summary.",
        "connect_google_history_body" to "Allow Health Connect access to see your 7-day history.",
        "connect_google_button" to "Connect Google Health",
        "steps_unit" to "steps",
        "no_data_short" to "—",
        "today_metrics" to "Today",
        "steps_today" to "Steps today",
        "goal_template" to "goal %s",
        "sleep_last_night" to "Sleep",
        "hours_unit" to "hours",
        "heart_today" to "Heart rate",
        "bpm_unit" to "bpm",
        "workouts" to "Workouts",
        "recent_sessions" to "recent sessions",
        "steps_7d" to "Steps over 7 days",
        "sleep_7d" to "Sleep over 7 days",
        "heart_7d" to "Heart rate over 7 days",
        "total_7d" to "total",
        "avg_7d" to "average",
        "avg_bpm_7d" to "average bpm",
        "refresh_status" to "Refresh",
        "connected" to "Connected",
        "not_connected" to "Not connected",
        "google_connection_body" to "Health Connect stores data on this device and allows BitLut to read and write supported metrics.",
        "huawei_connection_body" to "Huawei Health Kit is required to read Huawei Health data before export to Health Connect.",
        "connect_huawei_button" to "Connect Huawei Health",
        "manual_sync" to "Manual sync",
        "sync_now" to "Sync now",
        "last_sync_never" to "Last sync: never",
        "last_sync_template" to "Last sync: %s",
        "health_kit_status" to "Health Kit status",
        "health_kit_ready" to "Ready to sync",
        "health_kit_waiting" to "Waiting for authorization or approval",
        "health_kit_detail" to "If Huawei Health Kit still returns 50005, server-side Huawei approval is still pending. The app should not crash."
    )
    fun t(key: String): String = if (Locale.getDefault().language == "ru") ru[key] ?: key else en[key] ?: key
}

@Composable
private fun ScreenHero(palette: BitPalette, title: String, subtitle: String, action: String?, onAction: () -> Unit) {
    SoftCard(palette, accent = palette.activity, hero = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(title, color = palette.text, fontWeight = FontWeight.ExtraBold, fontSize = 34.sp, lineHeight = 36.sp)
                Spacer(Modifier.height(8.dp))
                Text(subtitle, color = palette.secondaryText, fontWeight = FontWeight.Medium, fontSize = 15.sp)
            }
            if (action != null) {
                PrimaryButton(text = action, accent = palette.activity, onClick = onAction)
            }
        }
    }
}

@Composable
private fun MetricCard(
    palette: BitPalette,
    modifier: Modifier,
    emoji: String,
    label: String,
    value: String,
    detail: String,
    accent: Color,
    large: Boolean = false
) {
    val scale by animateFloatAsState(if (large) 1.0f else 0.98f, label = "metricScale")
    SoftCard(palette, modifier = modifier.height(if (large) 178.dp else 160.dp), accent = accent) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            GlowBubble(accent, emoji)
            Spacer(Modifier.width(12.dp))
            Column {
                Text(label.uppercase(Locale.getDefault()), color = palette.secondaryText, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                Text(value, color = palette.text, fontWeight = FontWeight.Black, fontSize = if (large) 62.sp else 42.sp, lineHeight = if (large) 66.sp else 46.sp)
                Text(detail, color = accent, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            }
        }
    }
}

@Composable
private fun HistoryChartCard(palette: BitPalette, title: String, values: List<Pair<java.time.LocalDate, Double>>, accent: Color, emoji: String) {
    val max = values.maxOfOrNull { it.second }?.coerceAtLeast(1.0) ?: 1.0
    SoftCard(palette, accent = accent) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            GlowBubble(accent, emoji)
            Spacer(Modifier.width(10.dp))
            Text(title, color = palette.text, fontWeight = FontWeight.ExtraBold, fontSize = 20.sp)
        }
        Spacer(Modifier.height(18.dp))
        Row(
            modifier = Modifier.fillMaxWidth().height(150.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.Bottom
        ) {
            values.forEach { item ->
                val h = ((item.second / max) * 120.0).coerceIn(8.0, 120.0).dp
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.weight(1f)) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(h)
                            .shadow(16.dp, RoundedCornerShape(22.dp), ambientColor = accent.copy(alpha = 0.18f), spotColor = accent.copy(alpha = 0.18f))
                            .clip(RoundedCornerShape(22.dp))
                            .background(Brush.verticalGradient(listOf(accent.copy(alpha = 0.92f), accent.copy(alpha = 0.34f))))
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(item.first.format(DateTimeFormatter.ofPattern("dd.MM")), color = palette.secondaryText, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun ConnectionCard(palette: BitPalette, title: String, status: String, body: String, button: String, accent: Color, onClick: () -> Unit) {
    SoftCard(palette, accent = accent) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            GlowBubble(accent, "●")
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(title, color = palette.text, fontWeight = FontWeight.ExtraBold, fontSize = 21.sp)
                Text(status, color = accent, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            }
        }
        Spacer(Modifier.height(12.dp))
        Text(body, color = palette.secondaryText, fontWeight = FontWeight.Medium, fontSize = 14.sp)
        Spacer(Modifier.height(16.dp))
        PrimaryButton(button, accent, onClick = onClick)
    }
}

@Composable
private fun EmptyPermissionCard(palette: BitPalette, title: String, body: String, button: String, onClick: () -> Unit) {
    SoftCard(palette, accent = palette.mind, hero = true) {
        Text(title, color = palette.text, fontWeight = FontWeight.ExtraBold, fontSize = 24.sp)
        Spacer(Modifier.height(8.dp))
        Text(body, color = palette.secondaryText, fontWeight = FontWeight.Medium)
        Spacer(Modifier.height(18.dp))
        PrimaryButton(button, palette.mind, onClick = onClick)
    }
}

@Composable
private fun LoadingCard(palette: BitPalette) {
    SoftCard(palette) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            CircularProgressIndicator(color = palette.activity, strokeWidth = 3.dp)
            Spacer(Modifier.width(14.dp))
            Text(BText.t("loading"), color = palette.secondaryText, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun SoftCard(
    palette: BitPalette,
    modifier: Modifier = Modifier.fillMaxWidth(),
    accent: Color = palette.activity,
    hero: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = RoundedCornerShape(if (hero) 32.dp else 28.dp)
    val bg by animateColorAsState(palette.card, label = "cardBg")
    Column(
        modifier = modifier
            .shadow(28.dp, shape, ambientColor = Color.Black.copy(alpha = if (palette.dark) 0.28f else 0.055f), spotColor = accent.copy(alpha = if (palette.dark) 0.26f else 0.10f))
            .clip(shape)
            .background(bg)
            .border(1.dp, palette.stroke, shape)
            .padding(if (hero) 24.dp else 20.dp),
        content = content
    )
}

@Composable
private fun PrimaryButton(text: String, accent: Color, enabled: Boolean = true, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(22.dp),
        colors = ButtonDefaults.buttonColors(containerColor = accent, contentColor = Color.White)
    ) { Text(text, fontWeight = FontWeight.ExtraBold) }
}

@Composable
private fun GlowBubble(color: Color, text: String) {
    Box(
        modifier = Modifier
            .size(48.dp)
            .shadow(20.dp, RoundedCornerShape(18.dp), ambientColor = color.copy(alpha = 0.22f), spotColor = color.copy(alpha = 0.26f))
            .clip(RoundedCornerShape(18.dp))
            .background(color.copy(alpha = 0.18f)),
        contentAlignment = Alignment.Center
    ) { Text(text, color = color, fontWeight = FontWeight.Black, fontSize = 22.sp) }
}

@Composable
private fun SectionTitle(palette: BitPalette, text: String) {
    Text(text, color = palette.text, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp)
}

private data class BitPalette(
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
        fun light(): BitPalette = BitPalette(
            dark = false,
            systemBackground = Color(0xFFF2F2F7),
            card = Color.White,
            text = Color(0xFF111318),
            secondaryText = Color(0xFF6E6E73),
            stroke = Color(0x1A111318),
            activity = Color(0xFFFF6B5F),
            sleep = Color(0xFF7B61FF),
            mind = Color(0xFF46C7B7),
            heart = Color(0xFFE53935),
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFFF2F2F7), Color(0xFFFFFFFF)))
        )
        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = Color(0xFF0C0C0E),
            card = Color(0xCC1C1C1E),
            text = Color(0xFFF8F8F8),
            secondaryText = Color(0xFF8E8E93),
            stroke = Color(0x22FFFFFF),
            activity = Color(0xFFFF6B5F),
            sleep = Color(0xFF9E6FC3),
            mind = Color(0xFF5FE0C6),
            heart = Color(0xFFFF453A),
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFF0C0C0E), Color(0xFF1C1C1E)))
        )
    }
}


/*
 * UI sprint note:
 * Runtime copy must remain cleanly localized: Russian for ru devices, English fallback for all others.
 * New UI strings should be added to res/values and res/values-ru first. BText remains only as a
 * compatibility adapter for the current Compose shell and should not grow with new product copy.
 */

private object BText {
    private val ru = mapOf(
        "tab_summary" to "Сводка",
        "tab_history" to "История",
        "tab_settings" to "Настройки",
        "summary_title" to "Сводка здоровья",
        "summary_subtitle" to "Шаги, сон и пульс из Android Health Connect. Данные Huawei Health синхронизируются через настройки.",
        "history_title" to "История",
        "history_subtitle" to "Динамика ключевых показателей за последние 7 дней.",
        "settings_title" to "Настройки",
        "settings_subtitle" to "Подключите Google Health Connect и Huawei Health, затем запустите синхронизацию.",
        "refresh" to "Обновить",
        "check" to "Проверить",
        "steps" to "Шаги",
        "sleep" to "Сон",
        "heart" to "Пульс",
        "today" to "сегодня",
        "hours" to "часов",
        "bpm" to "уд/мин",
        "recent_workouts" to "Последние тренировки",
        "no_workouts" to "Тренировок пока нет.",
        "steps_7d" to "Шаги за 7 дней",
        "sleep_7d" to "Сон за 7 дней",
        "heart_7d" to "Пульс за 7 дней",
        "connect_google_title" to "Подключите Google Health Connect",
        "connect_google_body" to "BitLut нужны разрешения на чтение и запись, чтобы показывать данные и экспортировать импорт Huawei Health.",
        "connect_google" to "Подключить Google Health",
        "google_health_connect" to "Google Health Connect",
        "huawei_health" to "Huawei Health",
        "connected" to "Подключено",
        "not_connected" to "Не подключено",
        "google_settings_body" to "Разрешения Health Connect нужны для отображения сводки и записи импортированных данных.",
        "huawei_settings_body" to "Авторизация Huawei Health Kit нужна для чтения данных Huawei Health перед экспортом в Health Connect.",
        "connect_or_update" to "Подключить / обновить",
        "sync_title" to "Синхронизация",
        "sync_now" to "Синхронизировать",
        "syncing" to "Синхронизация...",
        "loading" to "Загружаем данные...",
        "status_idle" to "Готово к проверке подключений.",
        "status_syncing" to "Идёт синхронизация Huawei Health → Health Connect.",
        "status_success" to "Синхронизация выполнена. Последнее обновление: ",
        "status_error" to "Синхронизация не выполнена. Проверьте подключения и разрешения.",
        "toast_hc_permissions" to "Выданы не все разрешения Health Connect.",
        "toast_huawei_connected" to "Huawei Health подключён.",
        "toast_huawei_pending" to "Huawei Health Kit пока не подтвердил доступ. Проверьте статус согласования.",
        "toast_huawei_health_missing" to "Установите Huawei Health и войдите в аккаунт.",
        "toast_huawei_start_failed" to "Не удалось открыть авторизацию Huawei Health."
    )
    private val en = mapOf(
        "tab_summary" to "Summary",
        "tab_history" to "History",
        "tab_settings" to "Settings",
        "summary_title" to "Health Summary",
        "summary_subtitle" to "Steps, sleep and heart rate from Android Health Connect. Huawei Health sync is managed in Settings.",
        "history_title" to "History",
        "history_subtitle" to "Seven-day dynamics for key health metrics.",
        "settings_title" to "Settings",
        "settings_subtitle" to "Connect Google Health Connect and Huawei Health, then start sync.",
        "refresh" to "Refresh",
        "check" to "Check",
        "steps" to "Steps",
        "sleep" to "Sleep",
        "heart" to "Heart",
        "today" to "today",
        "hours" to "hours",
        "bpm" to "bpm",
        "recent_workouts" to "Recent workouts",
        "no_workouts" to "No workouts yet.",
        "steps_7d" to "Steps over 7 days",
        "sleep_7d" to "Sleep over 7 days",
        "heart_7d" to "Heart rate over 7 days",
        "connect_google_title" to "Connect Google Health Connect",
        "connect_google_body" to "BitLut needs read and write permissions to show data and export imported Huawei Health data.",
        "connect_google" to "Connect Google Health",
        "google_health_connect" to "Google Health Connect",
        "huawei_health" to "Huawei Health",
        "connected" to "Connected",
        "not_connected" to "Not connected",
        "google_settings_body" to "Health Connect permissions are required to display the summary and write imported data.",
        "huawei_settings_body" to "Huawei Health Kit authorization is required to read Huawei Health data before export to Health Connect.",
        "connect_or_update" to "Connect / update",
        "sync_title" to "Sync",
        "sync_now" to "Sync now",
        "syncing" to "Syncing...",
        "loading" to "Loading data...",
        "status_idle" to "Ready to check connections.",
        "status_syncing" to "Syncing Huawei Health → Health Connect.",
        "status_success" to "Sync completed. Last update: ",
        "status_error" to "Sync failed. Check connections and permissions.",
        "toast_hc_permissions" to "Not all Health Connect permissions were granted.",
        "toast_huawei_connected" to "Huawei Health connected.",
        "toast_huawei_pending" to "Huawei Health Kit has not confirmed access yet. Check approval status.",
        "toast_huawei_health_missing" to "Install Huawei Health and sign in.",
        "toast_huawei_start_failed" to "Could not open Huawei Health authorization."
    )
    fun t(key: String): String = if (Locale.getDefault().language == "ru") ru[key] ?: key else en[key] ?: key
}

private fun syncStatusText(state: SyncUiState): String = when (state.syncStatus) {
    "sync_status_syncing" -> BText.t("status_syncing")
    "sync_status_success" -> BText.t("status_success") + state.lastSyncTime
    "sync_status_error" -> BText.t("status_error")
    else -> BText.t("status_idle")
}

private fun formatNumber(value: Long): String = String.format(Locale.getDefault(), "%,d", value).replace(',', ' ')
private fun formatDateTime(ms: Long): String = java.text.SimpleDateFormat(
    if (Locale.getDefault().language == "ru") "dd.MM.yyyy HH:mm" else "MMM d, yyyy HH:mm",
    Locale.getDefault()
).format(java.util.Date(ms))
