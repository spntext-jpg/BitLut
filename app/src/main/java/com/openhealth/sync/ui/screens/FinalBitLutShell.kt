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
import androidx.compose.material3.Icon
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow
import com.openhealth.sync.ui.ImportScreen
import com.openhealth.sync.ui.ImportViewModel
import androidx.lifecycle.viewmodel.compose.viewModel

private enum class MainTab(val key: String, val icon: ImageVector) {
    Today("tab_today", Icons.Rounded.Today),
    SevenDays("tab_7days", Icons.Rounded.TrendingUp),
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
    importViewModel: ImportViewModel) {
    var selected by rememberSaveable { mutableStateOf(MainTab.Today) }
    var showArchiveImport by rememberSaveable { mutableStateOf(false) }
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
                        icon = {
                            Icon(
                                imageVector = tab.icon,
                                contentDescription = null,
                                modifier = Modifier.size(24.dp)
                            )
                        },
                        label = {
                            Text(
                                text = when (tab) {
                                    MainTab.Today -> stringResource(R.string.tab_today)
                                    MainTab.SevenDays -> stringResource(R.string.tab_7days)
                                    MainTab.Settings -> stringResource(R.string.tab_settings)
                                },
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
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
            
            if (showArchiveImport) {
                ImportScreen(
                    viewModel = importViewModel,
                    onBack = { showArchiveImport = false }
                )
            } else when (selected) {
                MainTab.Today -> SummaryScreen(palette, dashboardState, onRefresh, onRequestGoogle)
                MainTab.SevenDays -> HistoryScreen(palette, dashboardState, onRequestGoogle)
                MainTab.Settings -> SettingsScreen(palette, syncState, onRefresh, onRequestGoogle, onRequestHuawei, onSyncNow,
                    onImportArchive = { showArchiveImport = true })
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
    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            MinimalTopBar(
                palette = palette,
                title = stringResource(R.string.summary_short_title),
                action = stringResource(R.string.refresh_status),
                onAction = onRefresh
            )
        }

        if (!state.hasPermissions) {
            item {
                MinimalMetricCard(
                    palette = palette,
                    title = stringResource(R.string.connect_google_title),
                    value = stringResource(R.string.no_data_short),
                    unit = stringResource(R.string.connect_google_button),
                    accent = HealthAccent.mind,
                    onClick = onRequestGoogle
                )
            }
        } else {
            item {
                MinimalMetricCard(
                    palette = palette,
                    title = stringResource(R.string.steps_today),
                    value = formatNumber(state.stepsToday),
                    unit = stringResource(R.string.steps_unit),
                    accent = HealthAccent.activity
                )
            }
            item {
                MinimalMetricCard(
                    palette = palette,
                    title = stringResource(R.string.heart_today),
                    value = state.heartRateBpm?.toString() ?: stringResource(R.string.no_data_short),
                    unit = stringResource(R.string.bpm_unit),
                    accent = HealthAccent.heart
                )
            }
            item {
                MinimalMetricCard(
                    palette = palette,
                    title = stringResource(R.string.sleep_today),
                    value = formatOneDecimal(state.sleepHours.toDouble()),
                    unit = stringResource(R.string.hours_unit),
                    accent = HealthAccent.sleep
                )
            }
            item {
                PrimaryButton(
                    text = stringResource(R.string.refresh_status),
                    accent = HealthAccent.activity,
                    onClick = onRefresh
                )
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

        if (!state.hasPermissions) {
            item {
                MinimalMetricCard(
                    palette = palette,
                    title = stringResource(R.string.connect_google_title),
                    value = stringResource(R.string.no_data_short),
                    unit = stringResource(R.string.connect_google_button),
                    accent = HealthAccent.mind,
                    onClick = onRequestGoogle
                )
            }
        } else {
            val stepAvg = (state.weeklySteps).map { it.steps.toDouble() }.safeAverage()
            val sleepAvg = state.weeklySleep.map { it.value ?: 0.0 }.filter { it > 0.0 }.safeAverage()
            val heartAvg = state.weeklyHeartRate.map { it.value ?: 0.0 }.filter { it > 0.0 }.safeAverage()

            item {
                MinimalMetricCard(
                    palette = palette,
                    title = stringResource(R.string.steps_7d),
                    value = formatNumber(stepAvg.toLong()),
                    unit = stringResource(R.string.avg_7d),
                    accent = HealthAccent.activity
                )
            }
            item {
                MinimalMetricCard(
                    palette = palette,
                    title = stringResource(R.string.heart_7d),
                    value = if (heartAvg > 0.0) heartAvg.toLong().toString() else stringResource(R.string.no_data_short),
                    unit = stringResource(R.string.bpm_unit),
                    accent = HealthAccent.heart
                )
            }
            item {
                MinimalMetricCard(
                    palette = palette,
                    title = stringResource(R.string.sleep_7d),
                    value = formatOneDecimal(sleepAvg),
                    unit = stringResource(R.string.hours_unit),
                    accent = HealthAccent.sleep
                )
            }
        }
    }
}



@Composable
private fun SettingsScreen(
    palette: BitPalette,
    syncState: SyncUiState,
    onRefresh: () -> Unit,
    onRequestGoogle: () -> Unit,
    onRequestHuawei: () -> Unit,
    onSyncNow: () -> Unit,
    onImportArchive: () -> Unit
) {
    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            MinimalHeader(
                palette = palette,
                title = stringResource(R.string.tab_settings)
            )
        }

        item {
            SettingsConnectionCard(
                palette = palette,
                title = stringResource(R.string.google_health_connect),
                body = stringResource(R.string.google_connection_body),
                status = stringResource(R.string.refresh_status),
                accent = HealthAccent.mind,
                primaryAction = stringResource(R.string.connect_google_button),
                onPrimaryAction = onRequestGoogle,
                secondaryAction = stringResource(R.string.refresh_status),
                onSecondaryAction = onRefresh
            )
        }

        item {
            SettingsConnectionCard(
                palette = palette,
                title = stringResource(R.string.huawei_health_title),
                body = stringResource(R.string.huawei_connection_body),
                status = stringResource(R.string.refresh_status),
                accent = HealthAccent.activity,
                primaryAction = stringResource(R.string.connect_huawei_button),
                onPrimaryAction = onRequestHuawei,
                secondaryAction = stringResource(R.string.refresh_status),
                onSecondaryAction = onRefresh
            )
        }

        item {
            SettingsConnectionCard(
                palette = palette,
                title = stringResource(R.string.manual_sync_title),
                body = stringResource(R.string.manual_sync_body),
                status = stringResource(R.string.manual_sync_title),
                accent = HealthAccent.sleep,
                primaryAction = stringResource(R.string.sync_now),
                onPrimaryAction = onSyncNow,
                secondaryAction = stringResource(R.string.import_archive_title),
                onSecondaryAction = onImportArchive
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
            .padding(if (hero) 24.dp else 16.dp),
        content = content
    )
}

@Composable
private fun PrimaryButton(
    text: String,
    accent: Color,
    enabled: Boolean = true,
    modifier: Modifier = Modifier.fillMaxWidth(),
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier,
        shape = RoundedCornerShape(22.dp),
        colors = ButtonDefaults.buttonColors(containerColor = accent, contentColor = Color.White)
    ) { Text(text, fontWeight = FontWeight.ExtraBold, maxLines = 1, overflow = TextOverflow.Ellipsis) }
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
    title: String
) {
    Text(
        text = title,
        color = palette.text,
        fontWeight = FontWeight.ExtraBold,
        fontSize = 30.sp,
        modifier = Modifier.fillMaxWidth()
    )
}

@Composable
private fun MinimalMetricCard(
    palette: BitPalette,
    title: String,
    value: String,
    unit: String,
    accent: Color,
    onClick: (() -> Unit)? = null
) {
    SoftCard(palette = palette, accent = accent, hero = false) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 72.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    text = title,
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
                        fontSize = 28.sp,
                        lineHeight = 28.sp
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = unit,
                        color = accent,
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 13.sp,
                        modifier = Modifier.padding(bottom = 3.dp)
                    )
                }
            }
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(20.dp))
                    .background(accent.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center
            ) {
                Text("●", color = accent, fontSize = 15.sp, fontWeight = FontWeight.Black)
            }
        }
        if (onClick != null) {
            Spacer(Modifier.height(10.dp))
            PrimaryButton(text = unit, accent = accent, onClick = onClick)
        }
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
    body: String,
    status: String,
    accent: Color,
    primaryAction: String,
    onPrimaryAction: () -> Unit,
    secondaryAction: String? = null,
    onSecondaryAction: (() -> Unit)? = null
) {
    SoftCard(palette = palette, accent = accent, hero = false) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(18.dp))
                        .background(accent.copy(alpha = 0.16f)),
                    contentAlignment = Alignment.Center
                ) {
                    Text("●", color = accent, fontSize = 14.sp, fontWeight = FontWeight.Black)
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        text = title,
                        color = palette.text,
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 16.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        text = status,
                        color = accent,
                        fontWeight = FontWeight.Bold,
                        fontSize = 12.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }

            Text(
                text = body,
                color = palette.secondaryText,
                fontWeight = FontWeight.Medium,
                fontSize = 13.sp,
                lineHeight = 17.sp,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis
            )

            FlowRow(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                PrimaryButton(
                    text = primaryAction,
                    accent = accent,
                    modifier = Modifier.wrapContentWidth(),
                    onClick = onPrimaryAction
                )
                if (secondaryAction != null && onSecondaryAction != null) {
                    PrimaryButton(
                        text = secondaryAction,
                        accent = accent,
                        modifier = Modifier.wrapContentWidth(),
                        onClick = onSecondaryAction
                    )
                }
            }
        }
    }
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
 * New UI strings should be added to res/values and res/values-ru first.
 */

private fun formatNumber(value: Long): String = String.format(Locale.getDefault(), "%,d", value).replace(',', ' ')
