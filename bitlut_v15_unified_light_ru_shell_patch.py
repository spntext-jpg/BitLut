#!/usr/bin/env python3
"""
BitLut v1.5 shell polish patch.

Goals:
- Keep the working DashboardScreen intact.
- Make Sync and Settings visually match the light premium dashboard style.
- Remove the separate Huawei tab and move Huawei import state into Sync.
- Fully localize the shell for Russian device locale while keeping English fallback.
- Keep Huawei import code preserved and locked behind FeatureFlags.HUAWEI_IMPORT_ENABLED.

Run from repository root:
  python3 bitlut_v15_unified_light_ru_shell_patch.py
  ./gradlew :app:compileDebugKotlin --no-daemon
  ./gradlew :app:assembleDebug --no-daemon
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom

ROOT = Path.cwd()
JAVA = ROOT / "app/src/main/java/com/openhealth/sync"
MAIN = JAVA / "MainActivity.kt"
L10N = JAVA / "util/L10n.kt"
FLAGS = JAVA / "config/FeatureFlags.kt"
DASH = JAVA / "ui/DashboardScreen.kt"
RES = ROOT / "app/src/main/res"

for path in [MAIN, L10N, FLAGS, DASH]:
    if not path.exists():
        print(f"ERROR: expected file not found: {path}", file=sys.stderr)
        sys.exit(1)

for path in [MAIN, L10N, FLAGS]:
    backup = path.with_suffix(path.suffix + ".v15-unified-shell.bak")
    if not backup.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

# Keep staged Huawei architecture explicit and AI-readable.
FLAGS.write_text('''package com.openhealth.sync.config

/**
 * Runtime switches for staged releases.
 *
 * v1.5 is a Google Health Connect dashboard-first AppGallery review build.
 * Huawei import is preserved in code and visible as a locked sync method,
 * but no Huawei runtime import flow is enabled before Health Kit approval.
 */
object FeatureFlags {
    const val HUAWEI_IMPORT_ENABLED: Boolean = false
    const val GOOGLE_HEALTH_DASHBOARD_ENABLED: Boolean = true
    const val RELEASE_TRACK: String = "v1.5-dashboard-first"
}
''', encoding="utf-8")

# Resource strings: keep English fallback and Russian locale files complete for the shell.
def load_strings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
        return {child.attrib.get("name"): child.text or "" for child in root if child.tag == "string" and child.attrib.get("name")}
    except ET.ParseError:
        backup = path.with_suffix(path.suffix + ".before_unified_shell.bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        return {}


def write_strings(path: Path, updates: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = load_strings(path)
    data.update(updates)
    root = ET.Element("resources")
    for key in sorted(data):
        item = ET.SubElement(root, "string", {"name": key})
        item.text = data[key]
    raw = ET.tostring(root, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="    ")
    pretty = "\n".join(line for line in pretty.splitlines() if line.strip()) + "\n"
    path.write_text(pretty, encoding="utf-8")

write_strings(RES / "values/strings.xml", {
    "nav_dashboard": "Dashboard",
    "nav_sync": "Sync",
    "nav_settings": "Settings",
    "sync_title": "Synchronization",
    "settings_title": "Settings",
})
write_strings(RES / "values-ru/strings.xml", {
    "nav_dashboard": "Главная",
    "nav_sync": "Синхронизация",
    "nav_settings": "Настройки",
    "sync_title": "Синхронизация",
    "settings_title": "Настройки",
})

# Runtime localization bridge for Compose shell text.
L10N.write_text('''package com.openhealth.sync.util

import java.text.NumberFormat
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Lightweight localization bridge for the current Compose shell.
 *
 * Russian device locale receives a fully localized interface and CIS-style date/time.
 * Other locales keep the English fallback. New large screens can later move to
 * Android string resources one by one without changing the product behavior.
 */
object L10n {
    val isRu: Boolean
        get() = Locale.getDefault().language.equals("ru", ignoreCase = true)

    private val ru = mapOf(
        "BitLut" to "BitLut",
        "Health Sync OS" to "ОС синхронизации здоровья",
        "Dashboard" to "Главная",
        "Sync" to "Синхронизация",
        "Settings" to "Настройки",
        "Dashboard-first release" to "Релиз с фокусом на панель данных",
        "Health overview" to "Обзор здоровья",
        "Sync methods" to "Методы синхронизации",
        "Privacy and release" to "Приватность и релиз",
        "Synchronization" to "Синхронизация",
        "Connect sources and manage available import methods." to "Подключите источники данных и управляйте доступными способами импорта.",
        "Google Health Connect" to "Google Health Connect",
        "Connected" to "Подключено",
        "Not connected" to "Не подключено",
        "Read-only access is active. BitLut can show steps, weekly progress and workouts." to "Доступ только на чтение активен. BitLut показывает шаги, прогресс за неделю и тренировки.",
        "Read-only access is required to show steps, weekly progress and workouts." to "Нужен доступ только на чтение, чтобы показать шаги, прогресс за неделю и тренировки.",
        "Refresh dashboard" to "Обновить главную",
        "Connect Google Health" to "Подключить Google Health",
        "Huawei Health import" to "Импорт из Huawei Health",
        "Locked until Huawei Health Kit approval" to "Заблокировано до согласования Huawei Health Kit",
        "The import pipeline is preserved in the app. It will be enabled here after Huawei approves Health Kit access." to "Модуль импорта сохранён в приложении. Он будет включён здесь после согласования доступа Huawei Health Kit.",
        "Approval pending" to "Ожидает согласования",
        "Manual sync" to "Ручная синхронизация",
        "Auto sync" to "Автосинхронизация",
        "Disabled for review build" to "Отключено в сборке для проверки",
        "Background Huawei sync is intentionally off until approval." to "Фоновая синхронизация Huawei намеренно отключена до согласования.",
        "Data policy" to "Политика данных",
        "Minimum permissions" to "Минимум разрешений",
        "Dashboard uses read-only Google Health data. Write permissions are reserved for the future import stage." to "Главная использует данные Google Health только на чтение. Разрешения на запись зарезервированы для будущего этапа импорта.",
        "Release settings" to "Настройки релиза",
        "Current build" to "Текущая сборка",
        "Huawei feature flag" to "Флаг функции Huawei",
        "Keep disabled until Huawei Health Kit approval and real-device QA." to "Оставить отключённым до согласования Huawei Health Kit и проверки на реальном устройстве.",
        "Protected" to "Защищено",
        "Private by design" to "Приватность по умолчанию",
        "Health data stays on the device and is requested only when the user grants access." to "Данные здоровья остаются на устройстве и запрашиваются только после разрешения пользователя.",
        "Open" to "Открыть",
        "Status" to "Статус",
        "Runtime" to "Режим",
        "Prepared" to "Подготовлено",
        "Locked" to "Заблокировано",
        "Enabled" to "Включено",
        "Disabled" to "Отключено",
        "Stable" to "Стабильно",
        "Pending" to "В ожидании",
        "Today" to "Сегодня",
        "Steps" to "Шаги",
        "Weekly steps" to "Шаги за неделю",
        "Workouts" to "Тренировки",
        "Imported workouts" to "Импортированные тренировки",
        "No workouts yet" to "Тренировок пока нет",
        "Connect Google Health Connect" to "Подключить Google Health Connect",
        "Refresh data" to "Обновить данные"
    )

    fun t(text: String): String = if (isRu) ru[text] ?: text else text

    fun number(value: Long): String = NumberFormat.getIntegerInstance(Locale.getDefault()).format(value)

    fun shortDate(date: LocalDate): String {
        val pattern = if (isRu) "dd.MM" else "MMM d"
        return date.format(DateTimeFormatter.ofPattern(pattern, Locale.getDefault()))
    }

    fun dateTime(epochMillis: Long): String {
        val pattern = if (isRu) "dd.MM.yyyy HH:mm" else "MMM d, yyyy HH:mm"
        return Instant.ofEpochMilli(epochMillis)
            .atZone(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern(pattern, Locale.getDefault()))
    }

    fun workoutTitle(rawTitle: String): String {
        if (!isRu) return rawTitle
        val title = rawTitle.lowercase(Locale.getDefault())
        return when {
            "run" in title || "running" in title -> "Бег"
            "walk" in title || "walking" in title -> "Ходьба"
            "cycl" in title || "bike" in title -> "Велосипед"
            "swim" in title -> "Плавание"
            "strength" in title || "weight" in title -> "Силовая тренировка"
            "yoga" in title -> "Йога"
            "hik" in title -> "Поход"
            "workout" in title || "exercise" in title -> "Тренировка"
            else -> rawTitle
        }
    }
}
''', encoding="utf-8")

# Detect current DashboardScreen contract.
dash_text = DASH.read_text(encoding="utf-8")
uses_new_contract = "onRequestPermissions" in dash_text and "onRefresh" in dash_text
if uses_new_contract:
    dashboard_call = """DashboardScreen(
                            viewModel = dashboardViewModel,
                            onRequestPermissions = onConnectGoogleHealth,
                            onRefresh = onRefreshDashboard
                        )"""
else:
    dashboard_call = """DashboardScreen(
                            viewModel = dashboardViewModel,
                            onSyncClick = onConnectGoogleHealth
                        )"""

MAIN.write_text('''package com.openhealth.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.CloudSync
import androidx.compose.material.icons.rounded.Dashboard
import androidx.compose.material.icons.rounded.FileUpload
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Security
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Shield
import androidx.compose.material.icons.rounded.VerifiedUser
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import com.openhealth.sync.config.FeatureFlags
import com.openhealth.sync.ui.DashboardScreen
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.ImportViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.util.AppLogger
import com.openhealth.sync.util.L10n

/**
 * Main product shell for BitLut v1.5.
 *
 * AI-readable architecture contract:
 * - Dashboard keeps the validated premium UI.
 * - Sync owns every connection/import method, including locked Huawei Health import.
 * - Settings owns release, privacy and feature-flag status.
 * - Huawei import code remains compiled, but runtime stays disabled until approval.
 */
class MainActivity : ComponentActivity() {{

    private val dashboardViewModel: DashboardViewModel by viewModels {{
        val app = application as SyncApplication
        DashboardViewModel.provideFactory(app.container.googleHealthManager)
    }}

    @Suppress("unused")
    private val importViewModel: ImportViewModel by viewModels {{
        val app = application as SyncApplication
        ImportViewModel.provideFactory(app.container.googleHealthManager, applicationContext)
    }}

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) {{ granted ->
        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")
        dashboardViewModel.refresh()
        val app = application as SyncApplication
        if (!granted.containsAll(app.container.googleHealthManager.permissions)) {{
            Toast.makeText(this, getString(R.string.toast_hc_no_permissions), Toast.LENGTH_LONG).show()
        }}
    }}

    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        setContent {{
            BitLutExpressiveTheme {{
                BitLutAppShell(
                    dashboardViewModel = dashboardViewModel,
                    onConnectGoogleHealth = {{ requestGooglePermissionsOrOpenProvider() }},
                    onRefreshDashboard = {{ dashboardViewModel.refresh() }}
                )
            }}
        }}
    }}

    override fun onResume() {{
        super.onResume()
        dashboardViewModel.refresh()
    }}

    private fun requestGooglePermissionsOrOpenProvider() {{
        when (HealthConnectClient.getSdkStatus(this)) {{
            HealthConnectClient.SDK_AVAILABLE -> {{
                Toast.makeText(this, getString(R.string.toast_hc_opening), Toast.LENGTH_SHORT).show()
                val app = application as SyncApplication
                googlePermissionLauncher.launch(app.container.googleHealthManager.permissions)
            }}
            else -> {{
                Toast.makeText(this, getString(R.string.toast_hc_required), Toast.LENGTH_LONG).show()
                openUriWithFallback(
                    primary = "market://details?id=com.google.android.apps.healthdata",
                    fallback = "https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata"
                )
            }}
        }}
    }}

    private fun openUriWithFallback(primary: String, fallback: String) {{
        runCatching {{ startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(primary))) }}
            .onFailure {{ startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(fallback))) }}
    }}
}}

private val Lime = Color(0xFFC1FF05)
private val Purple = Color(0xFF9E6FC3)
private val Orange = Color(0xFFFF7D32)
private val AirBlue = Color(0xFFC8E1FC)
private val Metal = Color(0xFFBAB8BA)
private val Ink = Color(0xFF172033)
private val InkSoft = Color(0xFF5B6472)
private val White = Color(0xFFFFFFFF)
private val Panel = Color(0xF7FFFFFF)
private val Line = Color(0xFFE7EAF0)

private enum class AppDestination(
    val label: String,
    val subtitle: String,
    val icon: ImageVector
) {{
    Dashboard("Dashboard", "Health overview", Icons.Rounded.Dashboard),
    Sync("Sync", "Sync methods", Icons.Rounded.CloudSync),
    Settings("Settings", "Privacy and release", Icons.Rounded.Settings)
}}

@Composable
private fun BitLutAppShell(
    dashboardViewModel: DashboardViewModel,
    onConnectGoogleHealth: () -> Unit,
    onRefreshDashboard: () -> Unit
) {{
    var destination by remember {{ mutableStateOf(AppDestination.Dashboard) }}

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(ShellBackground())
    ) {{
        val useSidebar = maxWidth >= 720.dp
        if (useSidebar) {{
            Row(modifier = Modifier.fillMaxSize().statusBarsPadding()) {{
                PremiumSidebar(
                    selected = destination,
                    onSelect = {{ destination = it }},
                    modifier = Modifier
                        .width(280.dp)
                        .fillMaxHeight()
                        .padding(16.dp)
                )
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .padding(top = 16.dp, end = 16.dp, bottom = 16.dp)
                ) {{
                    AppContent(
                        destination = destination,
                        dashboardViewModel = dashboardViewModel,
                        onConnectGoogleHealth = onConnectGoogleHealth,
                        onRefreshDashboard = onRefreshDashboard
                    )
                }}
            }}
        }} else {{
            Column(modifier = Modifier.fillMaxSize().statusBarsPadding()) {{
                Box(modifier = Modifier.weight(1f).fillMaxWidth()) {{
                    AppContent(
                        destination = destination,
                        dashboardViewModel = dashboardViewModel,
                        onConnectGoogleHealth = onConnectGoogleHealth,
                        onRefreshDashboard = onRefreshDashboard
                    )
                }}
                PremiumBottomNav(
                    selected = destination,
                    onSelect = {{ destination = it }},
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 12.dp, vertical = 10.dp)
                )
            }}
        }}
    }}
}}

@Composable
private fun AppContent(
    destination: AppDestination,
    dashboardViewModel: DashboardViewModel,
    onConnectGoogleHealth: () -> Unit,
    onRefreshDashboard: () -> Unit
) {{
    AnimatedContent(
        targetState = destination,
        transitionSpec = {{ fadeIn() togetherWith fadeOut() }},
        label = "appDestination"
    ) {{ current ->
        when (current) {{
            AppDestination.Dashboard -> {{
                {dashboard_call}
            }}
            AppDestination.Sync -> SyncScreen(
                dashboardViewModel = dashboardViewModel,
                onConnectGoogleHealth = onConnectGoogleHealth,
                onRefreshDashboard = onRefreshDashboard
            )
            AppDestination.Settings -> SettingsScreen()
        }}
    }}
}}

@Composable
private fun PremiumSidebar(selected: AppDestination, onSelect: (AppDestination) -> Unit, modifier: Modifier = Modifier) {{
    PremiumPanel(modifier = modifier, radius = 32.dp) {{
        Column(modifier = Modifier.fillMaxSize().padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {{
            BrandHeader()
            Spacer(Modifier.height(10.dp))
            AppDestination.values().forEach {{ item ->
                NavigationItem(item = item, selected = item == selected, onClick = {{ onSelect(item) }})
            }}
            Spacer(modifier = Modifier.weight(1f))
            ReleaseBadge()
        }}
    }}
}}

@Composable
private fun PremiumBottomNav(selected: AppDestination, onSelect: (AppDestination) -> Unit, modifier: Modifier = Modifier) {{
    PremiumPanel(modifier = modifier, radius = 28.dp) {{
        Row(modifier = Modifier.fillMaxWidth().padding(8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {{
            AppDestination.values().forEach {{ item ->
                val isSelected = item == selected
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(20.dp))
                        .background(if (isSelected) Lime.copy(alpha = 0.36f) else Color.Transparent)
                        .clickable {{ onSelect(item) }}
                        .padding(vertical = 10.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {{
                    Icon(item.icon, contentDescription = L10n.t(item.label), tint = if (isSelected) Ink else InkSoft, modifier = Modifier.size(22.dp))
                    Spacer(Modifier.height(4.dp))
                    Text(L10n.t(item.label), color = if (isSelected) Ink else InkSoft, fontSize = 11.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }}
            }}
        }}
    }}
}}

@Composable
private fun BrandHeader() {{
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {{
        Box(
            modifier = Modifier
                .size(48.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(Brush.linearGradient(listOf(Lime, Orange, Purple), start = Offset.Zero, end = Offset(140f, 140f))),
            contentAlignment = Alignment.Center
        ) {{
            Icon(Icons.Rounded.AutoAwesome, contentDescription = null, tint = Ink, modifier = Modifier.size(26.dp))
        }}
        Column {{
            Text(L10n.t("BitLut"), color = Ink, fontSize = 22.sp, fontWeight = FontWeight.Black, letterSpacing = (-0.6).sp)
            Text(L10n.t("Health Sync OS"), color = InkSoft, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        }}
    }}
}}

@Composable
private fun NavigationItem(item: AppDestination, selected: Boolean, onClick: () -> Unit) {{
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(if (selected) Lime.copy(alpha = 0.34f) else Color.Transparent)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {{
        Box(
            modifier = Modifier
                .size(34.dp)
                .clip(CircleShape)
                .background(if (selected) White else AirBlue.copy(alpha = 0.55f)),
            contentAlignment = Alignment.Center
        ) {{
            Icon(item.icon, contentDescription = null, tint = if (selected) Ink else InkSoft, modifier = Modifier.size(20.dp))
        }}
        Column {{
            Text(L10n.t(item.label), color = if (selected) Ink else InkSoft, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            Text(L10n.t(item.subtitle), color = InkSoft.copy(alpha = 0.82f), fontSize = 11.sp, fontWeight = FontWeight.Medium)
        }}
    }}
}}

@Composable
private fun ReleaseBadge() {{
    PremiumPanel(modifier = Modifier.fillMaxWidth(), radius = 22.dp, accent = Orange.copy(alpha = 0.22f)) {{
        Row(modifier = Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {{
            Icon(Icons.Rounded.VerifiedUser, contentDescription = null, tint = Orange, modifier = Modifier.size(22.dp))
            Column {{
                Text("v1.5", color = Ink, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Text(L10n.t("Dashboard-first release"), color = InkSoft, fontSize = 11.sp, fontWeight = FontWeight.Medium)
            }}
        }}
    }}
}}

@Composable
private fun SyncScreen(
    dashboardViewModel: DashboardViewModel,
    onConnectGoogleHealth: () -> Unit,
    onRefreshDashboard: () -> Unit
) {{
    val state by dashboardViewModel.state.collectAsState()
    ScreenColumn {{
        ScreenHeader(
            icon = Icons.Rounded.CloudSync,
            title = L10n.t("Synchronization"),
            subtitle = L10n.t("Connect sources and manage available import methods.")
        )
        ActionCard(
            icon = Icons.Rounded.Shield,
            title = L10n.t("Google Health Connect"),
            label = if (state.hasPermissions) L10n.t("Connected") else L10n.t("Not connected"),
            body = if (state.hasPermissions) {
                L10n.t("Read-only access is active. BitLut can show steps, weekly progress and workouts.")
            } else {
                L10n.t("Read-only access is required to show steps, weekly progress and workouts.")
            },
            accent = Lime,
            primaryAction = if (state.hasPermissions) L10n.t("Refresh dashboard") else L10n.t("Connect Google Health"),
            onPrimaryAction = if (state.hasPermissions) onRefreshDashboard else onConnectGoogleHealth
        )
        ActionCard(
            icon = Icons.Rounded.FileUpload,
            title = L10n.t("Huawei Health import"),
            label = if (FeatureFlags.HUAWEI_IMPORT_ENABLED) L10n.t("Enabled") else L10n.t("Locked until Huawei Health Kit approval"),
            body = L10n.t("The import pipeline is preserved in the app. It will be enabled here after Huawei approves Health Kit access."),
            accent = Orange,
            primaryAction = L10n.t("Approval pending"),
            onPrimaryAction = {{}}
        )
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {{
            MiniInfoCard(L10n.t("Manual sync"), L10n.t("Refresh dashboard"), Lime, Modifier.weight(1f))
            MiniInfoCard(L10n.t("Auto sync"), L10n.t("Disabled for review build"), Orange, Modifier.weight(1f))
        }}
        ActionCard(
            icon = Icons.Rounded.Lock,
            title = L10n.t("Data policy"),
            label = L10n.t("Minimum permissions"),
            body = L10n.t("Dashboard uses read-only Google Health data. Write permissions are reserved for the future import stage."),
            accent = Purple,
            primaryAction = L10n.t("Protected"),
            onPrimaryAction = {{}}
        )
    }}
}}

@Composable
private fun SettingsScreen() {{
    ScreenColumn {{
        ScreenHeader(
            icon = Icons.Rounded.Settings,
            title = L10n.t("Settings"),
            subtitle = L10n.t("Release settings")
        )
        ActionCard(
            icon = Icons.Rounded.VerifiedUser,
            title = L10n.t("Current build"),
            label = L10n.t("Stable"),
            body = FeatureFlags.RELEASE_TRACK,
            accent = Lime,
            primaryAction = "v1.5",
            onPrimaryAction = {{}}
        )
        ActionCard(
            icon = Icons.Rounded.Lock,
            title = L10n.t("Huawei feature flag"),
            label = if (FeatureFlags.HUAWEI_IMPORT_ENABLED) L10n.t("Enabled") else L10n.t("Disabled"),
            body = L10n.t("Keep disabled until Huawei Health Kit approval and real-device QA."),
            accent = Orange,
            primaryAction = L10n.t("Protected"),
            onPrimaryAction = {{}}
        )
        ActionCard(
            icon = Icons.Rounded.Security,
            title = L10n.t("Private by design"),
            label = L10n.t("Minimum permissions"),
            body = L10n.t("Health data stays on the device and is requested only when the user grants access."),
            accent = AirBlue,
            primaryAction = L10n.t("Protected"),
            onPrimaryAction = {{}}
        )
    }}
}}

@Composable
private fun ScreenColumn(content: @Composable ColumnScope.() -> Unit) {{
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        content = content
    )
}}

@Composable
private fun ScreenHeader(icon: ImageVector, title: String, subtitle: String) {{
    PremiumPanel(modifier = Modifier.fillMaxWidth(), radius = 32.dp, accent = AirBlue.copy(alpha = 0.42f)) {{
        Row(modifier = Modifier.padding(24.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {{
            Box(
                modifier = Modifier
                    .size(54.dp)
                    .clip(RoundedCornerShape(18.dp))
                    .background(Brush.linearGradient(listOf(Lime, Orange), start = Offset.Zero, end = Offset(120f, 120f))),
                contentAlignment = Alignment.Center
            ) {{
                Icon(icon, contentDescription = null, tint = Ink, modifier = Modifier.size(28.dp))
            }}
            Column(modifier = Modifier.weight(1f)) {{
                Text(title, color = Ink, fontSize = 32.sp, fontWeight = FontWeight.Black, letterSpacing = (-1.0).sp)
                Spacer(Modifier.height(4.dp))
                Text(subtitle, color = InkSoft, fontSize = 15.sp, fontWeight = FontWeight.Medium, lineHeight = 21.sp)
            }}
        }}
    }}
}}

@Composable
private fun ActionCard(
    icon: ImageVector,
    title: String,
    label: String,
    body: String,
    accent: Color,
    primaryAction: String,
    onPrimaryAction: () -> Unit
) {{
    PremiumPanel(modifier = Modifier.fillMaxWidth(), radius = 28.dp, accent = accent.copy(alpha = 0.20f)) {{
        Column(modifier = Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {{
            Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(14.dp)) {{
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(RoundedCornerShape(17.dp))
                        .background(accent.copy(alpha = 0.34f)),
                    contentAlignment = Alignment.Center
                ) {{
                    Icon(icon, contentDescription = null, tint = Ink, modifier = Modifier.size(25.dp))
                }}
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {{
                    Text(label.uppercase(), color = InkSoft, fontSize = 11.sp, fontWeight = FontWeight.Black, letterSpacing = 1.1.sp)
                    Text(title, color = Ink, fontSize = 20.sp, fontWeight = FontWeight.Black, letterSpacing = (-0.4).sp)
                    Text(body, color = InkSoft, fontSize = 14.sp, fontWeight = FontWeight.Medium, lineHeight = 20.sp)
                }}
            }}
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(18.dp))
                    .background(Brush.linearGradient(listOf(accent, Orange)))
                    .clickable(onClick = onPrimaryAction)
                    .padding(horizontal = 18.dp, vertical = 13.dp),
                contentAlignment = Alignment.Center
            ) {{
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {{
                    Icon(Icons.Rounded.Refresh, contentDescription = null, tint = Ink, modifier = Modifier.size(18.dp))
                    Text(primaryAction, color = Ink, fontSize = 14.sp, fontWeight = FontWeight.Black)
                }}
            }}
        }}
    }}
}}

@Composable
private fun MiniInfoCard(label: String, value: String, accent: Color, modifier: Modifier = Modifier) {{
    PremiumPanel(modifier = modifier.height(126.dp), radius = 24.dp, accent = accent.copy(alpha = 0.22f)) {{
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.Center) {{
            Text(label.uppercase(), color = InkSoft, fontSize = 11.sp, fontWeight = FontWeight.Black, letterSpacing = 1.1.sp)
            Spacer(Modifier.height(8.dp))
            Text(value, color = Ink, fontSize = 22.sp, fontWeight = FontWeight.Black, lineHeight = 25.sp)
        }}
    }}
}}

@Composable
private fun PremiumPanel(
    modifier: Modifier = Modifier,
    radius: androidx.compose.ui.unit.Dp = 24.dp,
    accent: Color = AirBlue.copy(alpha = 0.26f),
    content: @Composable ColumnScope.() -> Unit
) {{
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(radius))
            .background(Panel)
            .background(Brush.linearGradient(listOf(White.copy(alpha = 0.90f), accent, White.copy(alpha = 0.76f))))
            .padding(1.dp)
            .clip(RoundedCornerShape(radius))
            .background(White.copy(alpha = 0.72f)),
        content = content
    )
}}

private fun ShellBackground(): Brush = Brush.radialGradient(
    colors = listOf(
        White,
        AirBlue.copy(alpha = 0.72f),
        Lime.copy(alpha = 0.16f),
        White
    ),
    center = Offset(260f, 80f),
    radius = 1200f
)
''', encoding="utf-8")

# Guard against the previous accidental broad replacement if it still exists in the file.
main_text = MAIN.read_text(encoding="utf-8")
main_text = main_text.replace("{dashboard_call}", dashboard_call)
main_text = main_text.replace("{{", "{").replace("}}", "}")
main_text = main_text.replace("Screenandroidx.compose.foundation.layout.Column", "ScreenColumn")
main_text = main_text.replace("content: @Composable Column.() -> Unit", "content: @Composable ColumnScope.() -> Unit")
MAIN.write_text(main_text, encoding="utf-8")

print("Applied unified light Russian shell patch.")
print("Next: ./gradlew :app:compileDebugKotlin --no-daemon && ./gradlew :app:assembleDebug --no-daemon")
