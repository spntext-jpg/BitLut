from pathlib import Path
import re

ROOT = Path('.')
MAIN = ROOT / 'app/src/main/java/com/openhealth/sync/MainActivity.kt'
GOOGLE = ROOT / 'app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt'
DASH_VM = ROOT / 'app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt'
FLAGS = ROOT / 'app/src/main/java/com/openhealth/sync/config/FeatureFlags.kt'
MANIFEST = ROOT / 'app/src/main/AndroidManifest.xml'
BUILD = ROOT / 'app/build.gradle.kts'

for p in [MAIN, GOOGLE, DASH_VM, MANIFEST, BUILD]:
    if not p.exists():
        raise SystemExit(f'Missing required file: {p}')

# 1) Activate Huawei import feature flag safely.
FLAGS.parent.mkdir(parents=True, exist_ok=True)
FLAGS.write_text('''package com.openhealth.sync.config

/**
 * Runtime feature switches.
 * Huawei import is enabled because AppGallery approval is complete and Health Kit review is in progress.
 * The actual sync flow remains guarded by runtime permission/auth checks in Settings and SyncWorker.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = true
}
''')

# 2) Ensure manifest includes read permissions for sleep/heart and write permissions needed for Huawei -> Health Connect export.
manifest = MANIFEST.read_text()
needed_permissions = [
    'android.permission.ACTIVITY_RECOGNITION',
    'android.permission.INTERNET',
    'android.permission.health.READ_STEPS',
    'android.permission.health.WRITE_STEPS',
    'android.permission.health.READ_DISTANCE',
    'android.permission.health.WRITE_DISTANCE',
    'android.permission.health.READ_FLOORS_CLIMBED',
    'android.permission.health.WRITE_FLOORS_CLIMBED',
    'android.permission.health.READ_ELEVATION_GAINED',
    'android.permission.health.WRITE_ELEVATION_GAINED',
    'android.permission.health.READ_ACTIVE_CALORIES_BURNED',
    'android.permission.health.WRITE_ACTIVE_CALORIES_BURNED',
    'android.permission.health.READ_EXERCISE',
    'android.permission.health.WRITE_EXERCISE',
    'android.permission.health.READ_SLEEP',
    'android.permission.health.WRITE_SLEEP',
    'android.permission.health.READ_HEART_RATE',
]
for perm in needed_permissions:
    line = f'    <uses-permission android:name="{perm}" />'
    if perm not in manifest:
        manifest = manifest.replace('<manifest xmlns:android="http://schemas.android.com/apk/res/android">', '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n' + line)
MANIFEST.write_text(manifest)

# 3) Bump local fallback version for finalization if it still has old fallback values.
build = BUILD.read_text()
build = re.sub(r'\?:\s*"1\.\d+\.\d+"', '?: "1.6.0"', build, count=1)
build = re.sub(r'\?:\s*\d+\n\s*versionCode', '?: 26\n        versionCode', build, count=1)
BUILD.write_text(build)

# 4) Harden GoogleHealthManager with heart-rate read support and weekly history helpers.
g = GOOGLE.read_text()
if 'import androidx.health.connect.client.records.HeartRateRecord' not in g:
    g = g.replace('import androidx.health.connect.client.records.FloorsClimbedRecord\n', 'import androidx.health.connect.client.records.FloorsClimbedRecord\nimport androidx.health.connect.client.records.HeartRateRecord\n')

# Add heart rate read permission into the permission set.
if 'HealthPermission.getReadPermission(HeartRateRecord::class)' not in g:
    g = g.replace(
        'HealthPermission.getWritePermission(SleepSessionRecord::class),\n        HealthPermission.getReadPermission(SleepSessionRecord::class)',
        'HealthPermission.getWritePermission(SleepSessionRecord::class),\n        HealthPermission.getReadPermission(SleepSessionRecord::class),\n        HealthPermission.getReadPermission(HeartRateRecord::class)'
    )

helpers_marker = '    private fun offset(instant: Instant): ZoneOffset = zoneRules.getOffset(instant)\n}'
if 'suspend fun readAverageHeartRateToday()' not in g:
    helpers = r'''

    suspend fun readAverageHeartRateToday(): Long? {
        val c = healthConnectClient ?: return null
        return try {
            val start = LocalDate.now().atStartOfDay(ZoneId.systemDefault()).toInstant()
            val req = ReadRecordsRequest(
                recordType = HeartRateRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, Instant.now())
            )
            val samples = c.readRecords(req).records.flatMap { it.samples }
            if (samples.isEmpty()) null else samples.map { it.beatsPerMinute }.average().toLong()
        } catch (e: Exception) {
            AppLogger.e(TAG, "readAverageHeartRateToday failed: ${e.message}")
            null
        }
    }

    suspend fun readWeeklySleep(): List<Pair<LocalDate, Double>> {
        val c = healthConnectClient ?: return emptyList()
        return try {
            val today = LocalDate.now()
            val start = today.minusDays(6).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = today.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val req = ReadRecordsRequest(
                recordType = SleepSessionRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, end)
            )
            val records = c.readRecords(req).records
            (0..6).map { offsetDays ->
                val date = today.minusDays((6 - offsetDays).toLong())
                val dayStart = date.atStartOfDay(ZoneId.systemDefault()).toInstant()
                val dayEnd = date.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
                val hours = records
                    .filter { it.endTime > dayStart && it.startTime < dayEnd }
                    .sumOf { session ->
                        val clippedStart = maxOf(session.startTime, dayStart)
                        val clippedEnd = minOf(session.endTime, dayEnd)
                        (clippedEnd.toEpochMilli() - clippedStart.toEpochMilli()).coerceAtLeast(0L)
                    } / 3_600_000.0
                date to hours
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readWeeklySleep failed: ${e.message}")
            emptyList()
        }
    }

    suspend fun readWeeklyAverageHeartRate(): List<Pair<LocalDate, Long?>> {
        val c = healthConnectClient ?: return emptyList()
        return try {
            val today = LocalDate.now()
            val start = today.minusDays(6).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = Instant.now()
            val req = ReadRecordsRequest(
                recordType = HeartRateRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, end)
            )
            val records = c.readRecords(req).records
            (0..6).map { offsetDays ->
                val date = today.minusDays((6 - offsetDays).toLong())
                val dayStart = date.atStartOfDay(ZoneId.systemDefault()).toInstant()
                val dayEnd = date.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
                val samples = records.flatMap { it.samples }
                    .filter { it.time >= dayStart && it.time < dayEnd }
                val avg = if (samples.isEmpty()) null else samples.map { it.beatsPerMinute }.average().toLong()
                date to avg
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "readWeeklyAverageHeartRate failed: ${e.message}")
            emptyList()
        }
    }
'''
    g = g.replace(helpers_marker, helpers + '\n' + helpers_marker)
GOOGLE.write_text(g)

# 5) Expand dashboard state for heart and weekly history.
vm = DASH_VM.read_text()
if 'data class WeeklyMetric' not in vm:
    vm = vm.replace('data class WeeklyBar(val date: LocalDate, val steps: Long)\n', 'data class WeeklyBar(val date: LocalDate, val steps: Long)\ndata class WeeklyMetric(val date: LocalDate, val value: Double?)\n')
if 'val heartRateBpm' not in vm:
    vm = vm.replace('val sleepHours: Double = 0.0,\n    val recentWorkouts', 'val sleepHours: Double = 0.0,\n    val heartRateBpm: Long? = null,\n    val weeklySleep: List<WeeklyMetric> = emptyList(),\n    val weeklyHeartRate: List<WeeklyMetric> = emptyList(),\n    val recentWorkouts')
if 'val heart     = googleManager.readAverageHeartRateToday()' not in vm:
    vm = vm.replace('val sleep    = googleManager.readSleepLastNight()\n            val workouts', 'val sleep    = googleManager.readSleepLastNight()\n            val heart     = googleManager.readAverageHeartRateToday()\n            val weeklySleep = googleManager.readWeeklySleep().map { (date, value) -> WeeklyMetric(date, value) }\n            val weeklyHeart = googleManager.readWeeklyAverageHeartRate().map { (date, value) -> WeeklyMetric(date, value?.toDouble()) }\n            val workouts')
    vm = vm.replace('sleepHours      = sleep,\n                    weeklySteps', 'sleepHours      = sleep,\n                    heartRateBpm    = heart,\n                    weeklySleep     = weeklySleep,\n                    weeklyHeartRate = weeklyHeart,\n                    weeklySteps')
DASH_VM.write_text(vm)

# 6) Replace MainActivity with final 3-tab shell. Huawei auth/sync are active but guarded.
MAIN.write_text(r'''package com.openhealth.sync

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
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            ScreenHero(
                palette = palette,
                title = BText.t("summary_title"),
                subtitle = BText.t("summary_subtitle"),
                action = BText.t("refresh"),
                onAction = onRefresh
            )
        }
        if (state.isLoading) {
            item { LoadingCard(palette) }
        } else if (!state.hasPermissions) {
            item {
                EmptyPermissionCard(
                    palette = palette,
                    title = BText.t("connect_google_title"),
                    body = BText.t("connect_google_body"),
                    button = BText.t("connect_google"),
                    onClick = onRequestGoogle
                )
            }
        } else {
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp), modifier = Modifier.fillMaxWidth()) {
                    MetricCard(
                        palette = palette,
                        modifier = Modifier.weight(1f),
                        emoji = "↟",
                        label = BText.t("steps"),
                        value = formatNumber(state.stepsToday),
                        detail = BText.t("today"),
                        accent = palette.activity
                    )
                    MetricCard(
                        palette = palette,
                        modifier = Modifier.weight(1f),
                        emoji = "◡",
                        label = BText.t("sleep"),
                        value = if (state.sleepHours > 0.0) String.format(Locale.getDefault(), "%.1f", state.sleepHours) else "—",
                        detail = BText.t("hours"),
                        accent = palette.sleep
                    )
                }
            }
            item {
                MetricCard(
                    palette = palette,
                    modifier = Modifier.fillMaxWidth(),
                    emoji = "♥",
                    label = BText.t("heart"),
                    value = state.heartRateBpm?.toString() ?: "—",
                    detail = BText.t("bpm"),
                    accent = palette.heart,
                    large = true
                )
            }
            item { SectionTitle(palette, BText.t("recent_workouts")) }
            if (state.recentWorkouts.isEmpty()) {
                item { SoftCard(palette) { Text(BText.t("no_workouts"), color = palette.secondaryText, fontWeight = FontWeight.Medium) } }
            } else {
                items(state.recentWorkouts) { workout ->
                    SoftCard(palette) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            GlowBubble(palette.activity, "⌁")
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text(workout.title, color = palette.text, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                                Text(formatDateTime(workout.startTimeMs), color = palette.secondaryText, fontSize = 13.sp)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun HistoryScreen(
    palette: BitPalette,
    state: DashboardUiState,
    onRequestGoogle: () -> Unit
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item { ScreenHero(palette, BText.t("history_title"), BText.t("history_subtitle"), null, {}) }
        if (!state.hasPermissions && !state.isLoading) {
            item { EmptyPermissionCard(palette, BText.t("connect_google_title"), BText.t("connect_google_body"), BText.t("connect_google"), onRequestGoogle) }
        } else {
            item { HistoryChartCard(palette, BText.t("steps_7d"), state.weeklySteps.map { it.date to it.steps.toDouble() }, palette.activity, "↟") }
            item { HistoryChartCard(palette, BText.t("sleep_7d"), state.weeklySleep.map { it.date to (it.value ?: 0.0) }, palette.sleep, "◡") }
            item { HistoryChartCard(palette, BText.t("heart_7d"), state.weeklyHeartRate.map { it.date to (it.value ?: 0.0) }, palette.heart, "♥") }
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
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item { ScreenHero(palette, BText.t("settings_title"), BText.t("settings_subtitle"), BText.t("check"), onRefresh) }
        item {
            ConnectionCard(
                palette = palette,
                title = BText.t("google_health_connect"),
                status = if (state.hasGooglePermissions) BText.t("connected") else BText.t("not_connected"),
                body = BText.t("google_settings_body"),
                button = BText.t("connect_or_update"),
                accent = palette.mind,
                onClick = onRequestGoogle
            )
        }
        item {
            ConnectionCard(
                palette = palette,
                title = BText.t("huawei_health"),
                status = if (state.isHuaweiAuthorized) BText.t("connected") else BText.t("not_connected"),
                body = BText.t("huawei_settings_body"),
                button = BText.t("connect_or_update"),
                accent = palette.sleep,
                onClick = onRequestHuawei
            )
        }
        item {
            SoftCard(palette, accent = palette.activity) {
                Text(BText.t("sync_title"), color = palette.text, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp)
                Spacer(Modifier.height(6.dp))
                Text(syncStatusText(state), color = palette.secondaryText, fontWeight = FontWeight.Medium)
                Spacer(Modifier.height(16.dp))
                PrimaryButton(
                    text = if (state.isSyncing) BText.t("syncing") else BText.t("sync_now"),
                    accent = palette.activity,
                    enabled = !state.isSyncing,
                    onClick = onSyncNow
                )
            }
        }
    }
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
    content: @Composable Column.() -> Unit
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
''')

print('Final Health sync + 3-tab Material 3 Expressive UI patch applied.')
print('Run: ./gradlew :app:compileDebugKotlin --no-daemon && ./gradlew :app:assembleDebug --no-daemon')
