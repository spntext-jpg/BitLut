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
import androidx.compose.material.icons.rounded.Cloud
import androidx.compose.material.icons.rounded.Watch
import androidx.compose.material.icons.rounded.CloudSync
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
                    icon = Icons.Rounded.Cloud,
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
                    accent = HealthAccent.activity,
                    progress = state.stepsProgress
                )
            }
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    MinimalSquareTile(
                        palette = palette,
                        icon = "♥",
                        label = stringResource(R.string.heart_today),
                        value = state.heartRateBpm?.let { "$it ${stringResource(R.string.bpm_unit)}" }
                            ?: stringResource(R.string.no_data_short),
                        accent = HealthAccent.heart,
                        modifier = Modifier.weight(1f),
                        onClick = null
                    )
                    MinimalSquareTile(
                        palette = palette,
                        icon = "☾",
                        label = stringResource(R.string.sleep_today),
                        value = "${formatOneDecimal(state.sleepHours.toDouble())} ${stringResource(R.string.hours_unit)}",
                        accent = HealthAccent.sleep,
                        modifier = Modifier.weight(1f),
                        progress = coerceProgress(state.sleepHours.toDouble(), SLEEP_GOAL_HOURS),
                        onClick = null
                    )
                }
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
                    icon = Icons.Rounded.Cloud,
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
                WeeklySparklineCard(
                    palette = palette,
                    title = stringResource(R.string.steps_7d),
                    values = state.weeklySteps.map { it.steps.toDouble() },
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
                WeeklySparklineCard(
                    palette = palette,
                    title = stringResource(R.string.heart_7d),
                    values = state.weeklyHeartRate.map { it.value ?: 0.0 },
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
            item {
                WeeklySparklineCard(
                    palette = palette,
                    title = stringResource(R.string.sleep_7d),
                    values = state.weeklySleep.map { it.value ?: 0.0 },
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
                icon = Icons.Rounded.Cloud,
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
                icon = Icons.Rounded.Watch,
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
                icon = Icons.Rounded.CloudSync,
                primaryAction = stringResource(R.string.sync_now),
                onPrimaryAction = onSyncNow,
                secondaryAction = stringResource(R.string.import_archive_title),
                onSecondaryAction = onImportArchive
            )
        }
    }
}



/**
 * Generic reference target for the Sleep progress ring on Summary, in hours.
 * Unlike [DashboardUiState.stepsGoal], this is NOT a personalized or
 * user-configurable value — it's the commonly cited adult sleep guideline,
 * used only to give the ring a sense of "how close to a typical night" the
 * person is. If/when per-user sleep goals are added, replace this constant.
 */
private const val SLEEP_GOAL_HOURS = 8.0

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
    tintWithAccent: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = RoundedCornerShape(if (hero) 32.dp else 28.dp)
    val targetCardColor = if (tintWithAccent && palette.dark) {
        // Subtle "Expressive" tint: blend a touch of the metric's accent into the
        // flat dark card color, instead of every card sharing one identical gray.
        lerp(palette.card, accent, 0.10f)
    } else {
        palette.card
    }
    val bg by animateColorAsState(targetCardColor, label = "cardBg")
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
private fun Modifier.pressScale(interactionSource: MutableInteractionSource): Modifier {
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
            if (progress != null) {
                ProgressRingChip(progress = progress, accent = accent, size = 40.dp)
            } else {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(RoundedCornerShape(20.dp))
                        .background(accent.copy(alpha = 0.16f)),
                    contentAlignment = Alignment.Center
                ) {
                    if (icon != null) {
                        Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(20.dp))
                    } else {
                        Text("●", color = accent, fontSize = 15.sp, fontWeight = FontWeight.Black)
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
                    fontSize = 30.sp,
                    lineHeight = 32.sp,
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
private fun ProgressRingChip(
    progress: Float,
    accent: Color,
    size: androidx.compose.ui.unit.Dp,
    centerText: String = "•"
) {
    Box(modifier = Modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.matchParentSize()) {
            val stroke = Stroke(width = 3.5.dp.toPx(), cap = StrokeCap.Round)
            drawArc(
                color = accent.copy(alpha = 0.18f),
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
        Text(centerText, color = accent, fontSize = 13.sp, fontWeight = FontWeight.Black)
    }
}

/** Clamps any progress ratio into the 0f..1f range a ring can safely draw, and
 *  guards against division by zero when [goal] is zero or negative. */
private fun coerceProgress(value: Double, goal: Double): Float =
    if (goal <= 0.0) 0f else (value / goal).toFloat().coerceIn(0f, 1f)

/**
 * 7-day trend card for History: a thick rounded sparkline line with a soft
 * gradient fill underneath, in the Material 3 Expressive style described in
 * the design brief. Title/value reuse the same strings as the existing
 * 7-day average cards — this card supplements them, it doesn't replace them.
 *
 * Safe by construction for the data shapes that actually reach it:
 * - empty list -> flat line at mid-height (no crash, no divide-by-zero)
 * - single-point list -> flat line at mid-height (a "trend" needs >=2 points)
 * - all-equal values (e.g. all zeros, no data yet) -> flat line, not a
 *   division-by-zero from a zero range
 */
@Composable
private fun WeeklySparklineCard(
    palette: BitPalette,
    title: String,
    values: List<Double>,
    accent: Color
) {
    SoftCard(palette = palette, accent = accent, hero = false, tintWithAccent = true) {
        Text(
            text = title,
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 14.sp
        )
        Spacer(Modifier.height(12.dp))
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp)
        ) {
            val w = size.width
            val h = size.height
            if (values.size < 2) {
                // Not enough points for a real trend — draw a flat reference
                // line instead of attempting to plot a single dot.
                drawLine(
                    color = accent.copy(alpha = 0.35f),
                    start = Offset(0f, h / 2f),
                    end = Offset(w, h / 2f),
                    strokeWidth = 4.dp.toPx(),
                    cap = StrokeCap.Round
                )
                return@Canvas
            }

            val maxV = values.max()
            val minV = values.min()
            val range = (maxV - minV).takeIf { it > 0.0 } ?: 1.0
            // When every value is identical (including all-zero placeholder
            // data), `range` falls back to 1.0 above purely to avoid a 0/0 —
            // the line below still renders flat at mid-height either way.
            val stepX = w / (values.size - 1)

            val points = values.mapIndexed { index, v ->
                val x = index * stepX
                val normalized = if (maxV == minV) 0.5f else ((v - minV) / range).toFloat()
                val y = h - (normalized * h * 0.78f + h * 0.11f)
                Offset(x, y)
            }

            val fillPath = androidx.compose.ui.graphics.Path().apply {
                moveTo(points.first().x, h)
                points.forEach { lineTo(it.x, it.y) }
                lineTo(points.last().x, h)
                close()
            }
            drawPath(
                path = fillPath,
                brush = Brush.verticalGradient(
                    listOf(accent.copy(alpha = 0.28f), accent.copy(alpha = 0.0f))
                )
            )

            for (i in 0 until points.size - 1) {
                drawLine(
                    color = accent,
                    start = points[i],
                    end = points[i + 1],
                    strokeWidth = 6.dp.toPx(),
                    cap = StrokeCap.Round
                )
            }
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
    icon: ImageVector,
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
                    Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(18.dp))
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
