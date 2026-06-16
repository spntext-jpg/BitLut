from pathlib import Path
import re, shutil, datetime
root = Path('/mnt/data/bitlut_extract')
backup = root / f'.sprint_backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
for rel in ['app/src/main/java/com/openhealth/sync/MainActivity.kt','app/src/main/java/com/openhealth/sync/ui/DashboardScreen.kt','app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt','app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt','app/src/main/AndroidManifest.xml']:
    src=root/rel; dst=backup/rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,dst)
main = r'''package com.openhealth.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import com.openhealth.sync.ui.DashboardScreen
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme
import com.openhealth.sync.util.AppLogger

class MainActivity : ComponentActivity() {

    private val dashboardViewModel: DashboardViewModel by viewModels {
        val app = application as SyncApplication
        DashboardViewModel.provideFactory(app.container.googleHealthManager)
    }

    private val googlePermissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        AppLogger.i("MainActivity", "Health Connect permissions returned: $granted")
        dashboardViewModel.refresh()
        val app = application as SyncApplication
        if (!granted.containsAll(app.container.googleHealthManager.permissions)) {
            Toast.makeText(this, getString(R.string.toast_hc_no_permissions), Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            BitLutExpressiveTheme {
                DashboardScreen(
                    viewModel = dashboardViewModel,
                    onRequestPermissions = { requestGooglePermissionsOrOpenProvider() },
                    onRefresh = { dashboardViewModel.refresh() }
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        dashboardViewModel.refresh()
    }

    private fun requestGooglePermissionsOrOpenProvider() {
        val status = HealthConnectClient.getSdkStatus(this)
        if (status == HealthConnectClient.SDK_AVAILABLE) {
            Toast.makeText(this, getString(R.string.toast_hc_opening), Toast.LENGTH_SHORT).show()
            val app = application as SyncApplication
            googlePermissionLauncher.launch(app.container.googleHealthManager.permissions)
        } else {
            Toast.makeText(this, getString(R.string.toast_hc_required), Toast.LENGTH_LONG).show()
            openUriWithFallback(
                "market://details?id=com.google.android.apps.healthdata",
                "https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata"
            )
        }
    }

    private fun openUriWithFallback(primary: String, fallback: String) {
        runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(primary))) }
            .onFailure { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(fallback))) }
    }
}
'''
(root/'app/src/main/java/com/openhealth/sync/MainActivity.kt').write_text(main)

dashboard = r'''package com.openhealth.sync.ui

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.FitnessCenter
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Shield
import androidx.compose.material.icons.rounded.Timeline
import androidx.compose.material.icons.rounded.WbSunny
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.ui.theme.Blue
import com.openhealth.sync.ui.theme.GlassCard
import com.openhealth.sync.ui.theme.GlowBlue
import com.openhealth.sync.ui.theme.GlowOrange
import com.openhealth.sync.ui.theme.GlowPurple
import com.openhealth.sync.ui.theme.MeshBackground
import com.openhealth.sync.ui.theme.Orange
import com.openhealth.sync.ui.theme.Purple
import com.openhealth.sync.ui.theme.TextPrimary
import com.openhealth.sync.ui.theme.TextSecondary
import com.openhealth.sync.ui.theme.TextTertiary
import com.openhealth.sync.ui.theme.VoidBorder
import kotlinx.coroutines.delay
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale
import kotlin.math.roundToInt

@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel,
    onRequestPermissions: () -> Unit,
    onRefresh: () -> Unit
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { delay(90); visible = true }
    val alpha by animateFloatAsState(
        targetValue = if (visible) 1f else 0f,
        animationSpec = tween(300, easing = FastOutSlowInEasing),
        label = "dashboardEnter"
    )

    Box(modifier = Modifier.fillMaxSize()) {
        MeshBackground()

        Column(
            modifier = Modifier
                .fillMaxSize()
                .alpha(alpha)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Header(onRefresh = onRefresh)

            when {
                state.isLoading -> LoadingState()
                !state.hasPermissions -> PermissionState(onRequestPermissions)
                else -> HealthDashboardContent(state = state, onRefresh = onRefresh)
            }

            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
private fun Header(onRefresh: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "BitLut",
                fontSize = 32.sp,
                fontWeight = FontWeight.Black,
                color = TextPrimary,
                letterSpacing = (-1.2).sp
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = "Google Health intelligence dashboard",
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = TextSecondary
            )
        }
        GlowIconButton(icon = Icons.Rounded.Refresh, onClick = onRefresh)
    }
}

@Composable
private fun LoadingState() {
    Box(modifier = Modifier.fillMaxWidth().height(420.dp), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(color = Blue, strokeWidth = 3.dp)
    }
}

@Composable
private fun PermissionState(onRequestPermissions: () -> Unit) {
    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(32.dp), glowColor = GlowBlue) {
        Column(modifier = Modifier.padding(28.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(Icons.Rounded.Shield, contentDescription = null, tint = Blue, modifier = Modifier.size(42.dp))
            Spacer(Modifier.height(18.dp))
            Text(
                text = "Connect Google Health",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = "BitLut needs read access to show your steps and workouts in a clean premium dashboard.",
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = TextSecondary,
                textAlign = TextAlign.Center,
                lineHeight = 20.sp
            )
            Spacer(Modifier.height(22.dp))
            PrimaryButton(text = "Grant Health Connect access", onClick = onRequestPermissions)
        }
    }
}

@Composable
private fun HealthDashboardContent(state: DashboardUiState, onRefresh: () -> Unit) {
    val weeklyTotal = state.weeklySteps.sumOf { it.steps }
    val workoutCount = state.recentWorkouts.size

    HeroStepsCard(
        stepsToday = state.stepsToday,
        goal = state.stepsGoal,
        progress = state.stepsProgress,
        weeklyTotal = weeklyTotal
    )

    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        KpiCard(
            modifier = Modifier.weight(1f),
            icon = Icons.Rounded.Timeline,
            label = "7-day steps",
            value = if (weeklyTotal > 0) "%,d".format(weeklyTotal) else "—",
            trend = if (state.weeklyAvg > 0) "avg %,d/day".format(state.weeklyAvg) else "no data yet",
            glow = GlowPurple
        )
        KpiCard(
            modifier = Modifier.weight(1f),
            icon = Icons.Rounded.FitnessCenter,
            label = "Workouts",
            value = workoutCount.toString(),
            trend = if (workoutCount == 1) "1 session imported" else "$workoutCount sessions imported",
            glow = GlowOrange
        )
    }

    WeeklyStepsCard(bars = state.weeklySteps)
    WorkoutsCard(workouts = state.recentWorkouts)

    if (state.stepsToday == 0L && weeklyTotal == 0L && state.recentWorkouts.isEmpty()) {
        EmptyState(onRefresh = onRefresh)
    }
}

@Composable
private fun HeroStepsCard(stepsToday: Long, goal: Long, progress: Float, weeklyTotal: Long) {
    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(32.dp), glowColor = GlowBlue, glowRadius = 30.dp) {
        Column(modifier = Modifier.padding(24.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Label("today's steps")
                if (weeklyTotal > 0) Text("%,d this week".format(weeklyTotal), fontSize = 12.sp, color = TextSecondary, fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.height(18.dp))
            Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = if (stepsToday > 0) "%,d".format(stepsToday) else "—",
                        fontSize = 56.sp,
                        fontWeight = FontWeight.Black,
                        color = TextPrimary,
                        letterSpacing = (-2.4).sp,
                        lineHeight = 58.sp
                    )
                    Spacer(Modifier.height(6.dp))
                    Text("Daily goal %,d".format(goal), fontSize = 14.sp, color = TextSecondary, fontWeight = FontWeight.Medium)
                    Spacer(Modifier.height(18.dp))
                    ProgressBar(progress = progress)
                    Spacer(Modifier.height(8.dp))
                    Text("${(progress * 100).roundToInt()}% completed", fontSize = 12.sp, color = TextTertiary, fontWeight = FontWeight.SemiBold)
                }
                Spacer(Modifier.width(18.dp))
                StepsRing(progress = progress, steps = stepsToday)
            }
        }
    }
}

@Composable
private fun KpiCard(modifier: Modifier, icon: ImageVector, label: String, value: String, trend: String, glow: Color) {
    GlassCard(modifier = modifier.height(160.dp), shape = RoundedCornerShape(24.dp), glowColor = glow.copy(alpha = 0.55f)) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.SpaceBetween) {
            IconBadge(icon = icon, color = glow)
            Column {
                Label(label)
                Spacer(Modifier.height(6.dp))
                Text(value, fontSize = 28.sp, fontWeight = FontWeight.Black, color = TextPrimary, letterSpacing = (-0.8).sp)
                Text(trend, fontSize = 12.sp, color = TextSecondary, fontWeight = FontWeight.Medium)
            }
        }
    }
}

@Composable
private fun WeeklyStepsCard(bars: List<WeeklyBar>) {
    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp), glowColor = GlowPurple.copy(alpha = 0.45f)) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Label("weekly steps")
                Text("Last 7 days", fontSize = 12.sp, color = TextSecondary, fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.height(20.dp))
            WeeklyChart(bars)
        }
    }
}

@Composable
private fun WorkoutsCard(workouts: List<ActivitySessionData>) {
    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp), glowColor = GlowOrange.copy(alpha = 0.5f)) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Label("imported workouts")
                Text("${workouts.size} total", fontSize = 12.sp, color = TextSecondary, fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.height(16.dp))
            if (workouts.isEmpty()) {
                Text("No workouts found in Google Health Connect yet.", fontSize = 14.sp, color = TextSecondary, lineHeight = 20.sp)
            } else {
                workouts.forEachIndexed { index, workout ->
                    WorkoutRow(workout)
                    if (index < workouts.lastIndex) {
                        Spacer(Modifier.height(12.dp))
                        Box(Modifier.fillMaxWidth().height(1.dp).background(VoidBorder.copy(alpha = 0.75f)))
                        Spacer(Modifier.height(12.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun EmptyState(onRefresh: () -> Unit) {
    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp), glowColor = GlowBlue.copy(alpha = 0.45f)) {
        Column(modifier = Modifier.padding(22.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(Icons.Rounded.AutoAwesome, contentDescription = null, tint = Blue, modifier = Modifier.size(32.dp))
            Spacer(Modifier.height(12.dp))
            Text("No health data yet", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextPrimary, textAlign = TextAlign.Center)
            Spacer(Modifier.height(6.dp))
            Text("Add data to Google Health Connect, then refresh BitLut.", fontSize = 14.sp, color = TextSecondary, textAlign = TextAlign.Center, lineHeight = 20.sp)
            Spacer(Modifier.height(16.dp))
            SecondaryButton(text = "Refresh dashboard", onClick = onRefresh)
        }
    }
}

@Composable
private fun WeeklyChart(bars: List<WeeklyBar>) {
    val maxSteps = bars.maxOfOrNull { it.steps }?.takeIf { it > 0 } ?: 1L
    val today = LocalDate.now()
    Row(modifier = Modifier.fillMaxWidth().height(132.dp), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.Bottom) {
        bars.forEach { bar ->
            val isToday = bar.date == today
            val target = (bar.steps.toFloat() / maxSteps.toFloat()).coerceIn(if (bar.steps > 0) 0.06f else 0f, 1f)
            val anim by animateFloatAsState(targetValue = target, animationSpec = tween(900, easing = FastOutSlowInEasing), label = "weeklyBar")
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Bottom, modifier = Modifier.weight(1f).height(132.dp)) {
                Text(if (bar.steps > 0) compactNumber(bar.steps) else "—", fontSize = 10.sp, color = if (isToday) Blue else TextSecondary, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                Box(
                    modifier = Modifier
                        .width(22.dp)
                        .height((78 * anim).coerceAtLeast(4f).dp)
                        .clip(RoundedCornerShape(10.dp))
                        .background(if (isToday) Brush.verticalGradient(listOf(Blue, Purple)) else Brush.verticalGradient(listOf(Purple.copy(alpha = 0.65f), Blue.copy(alpha = 0.16f))))
                )
                Spacer(Modifier.height(8.dp))
                Text(bar.date.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.getDefault()).take(2), fontSize = 11.sp, color = if (isToday) Blue else TextTertiary, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun WorkoutRow(workout: ActivitySessionData) {
    val durationMin = ((workout.endTimeMs - workout.startTimeMs) / 60_000L).toInt().coerceAtLeast(1)
    val date = Instant.ofEpochMilli(workout.startTimeMs).atZone(ZoneId.systemDefault()).toLocalDate()
    val dateText = when (date) {
        LocalDate.now() -> "Today"
        LocalDate.now().minusDays(1) -> "Yesterday"
        else -> date.format(DateTimeFormatter.ofPattern("MMM d"))
    }
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
            IconBadge(icon = Icons.Rounded.FitnessCenter, color = Orange)
            Column(modifier = Modifier.weight(1f)) {
                Text(workout.title.ifBlank { "Workout" }, fontSize = 15.sp, fontWeight = FontWeight.Bold, color = TextPrimary, maxLines = 1)
                Text("$dateText · $durationMin min", fontSize = 12.sp, color = TextSecondary, fontWeight = FontWeight.Medium)
            }
        }
        Box(modifier = Modifier.clip(RoundedCornerShape(12.dp)).background(Orange.copy(alpha = 0.14f)).padding(horizontal = 10.dp, vertical = 6.dp)) {
            Text("${durationMin}m", fontSize = 12.sp, color = Orange, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun ProgressBar(progress: Float) {
    Box(modifier = Modifier.fillMaxWidth().height(8.dp).clip(CircleShape).background(VoidBorder.copy(alpha = 0.8f))) {
        Box(modifier = Modifier.fillMaxWidth(progress.coerceIn(0.02f, 1f)).height(8.dp).clip(CircleShape).background(Brush.horizontalGradient(listOf(Blue, Purple))))
    }
}

@Composable
private fun StepsRing(progress: Float, steps: Long) {
    val anim by animateFloatAsState(targetValue = progress.coerceIn(0f, 1f), animationSpec = tween(900, easing = FastOutSlowInEasing), label = "stepsRing")
    Box(modifier = Modifier.size(108.dp), contentAlignment = Alignment.Center) {
        Box(modifier = Modifier.size(108.dp).drawBehind {
            val stroke = 9.dp.toPx()
            val radius = (size.minDimension - stroke) / 2
            drawCircle(color = VoidBorder.copy(alpha = 0.9f), radius = radius, style = Stroke(width = stroke, cap = StrokeCap.Round))
            if (anim > 0f) drawArc(
                brush = Brush.sweepGradient(listOf(Blue, Purple, Orange, Blue)),
                startAngle = -90f,
                sweepAngle = 360f * anim,
                useCenter = false,
                style = Stroke(width = stroke, cap = StrokeCap.Round)
            )
            drawCircle(
                brush = Brush.radialGradient(listOf(Color(0x2619AEF9), Color.Transparent), center = Offset(size.width / 2f, size.height / 2f), radius = size.width * 0.55f),
                radius = size.width * 0.55f
            )
        })
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(Icons.Rounded.WbSunny, contentDescription = null, tint = Blue, modifier = Modifier.size(18.dp))
            Text(compactNumber(steps), fontSize = 17.sp, fontWeight = FontWeight.Black, color = TextPrimary, textAlign = TextAlign.Center)
        }
    }
}

@Composable
private fun GlowIconButton(icon: ImageVector, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(48.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(Color.White.copy(alpha = 0.05f))
            .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null, onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Icon(icon, contentDescription = null, tint = Blue, modifier = Modifier.size(22.dp))
    }
}

@Composable
private fun IconBadge(icon: ImageVector, color: Color) {
    Box(
        modifier = Modifier
            .size(42.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(Brush.linearGradient(listOf(color.copy(alpha = 0.24f), color.copy(alpha = 0.08f)))),
        contentAlignment = Alignment.Center
    ) {
        Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(22.dp))
    }
}

@Composable
private fun PrimaryButton(text: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(18.dp))
            .background(Brush.horizontalGradient(listOf(Blue, Purple)))
            .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null, onClick = onClick)
            .padding(horizontal = 22.dp, vertical = 14.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(text, color = Color.White, fontSize = 15.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun SecondaryButton(text: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(18.dp))
            .background(Color.White.copy(alpha = 0.05f))
            .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null, onClick = onClick)
            .padding(horizontal = 20.dp, vertical = 12.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(text, color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun Label(text: String) {
    Text(text.uppercase(Locale.getDefault()), fontSize = 12.sp, fontWeight = FontWeight.Bold, color = TextSecondary, letterSpacing = 1.1.sp)
}

private fun compactNumber(value: Long): String = when {
    value >= 1_000_000 -> "%.1fm".format(value / 1_000_000.0)
    value >= 1_000 -> "%.1fk".format(value / 1_000.0)
    value > 0 -> value.toString()
    else -> "—"
}
'''
(root/'app/src/main/java/com/openhealth/sync/ui/DashboardScreen.kt').write_text(dashboard)

vm = root/'app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt'
s=vm.read_text()
s=s.replace('val distanceMeters: Double = 0.0,\n    val caloriesKcal: Double = 0.0,\n    val weeklySteps: List<WeeklyBar> = emptyList(),\n    val sleepHours: Double = 0.0,\n    val recentWorkouts: List<ActivitySessionData> = emptyList()','val weeklySteps: List<WeeklyBar> = emptyList(),\n    val recentWorkouts: List<ActivitySessionData> = emptyList()')
s=s.replace('            val distance = googleManager.readDistanceToday()\n            val calories = googleManager.readCaloriesToday()\n            val weekly   = googleManager.readWeeklySteps().map { (date, s) -> WeeklyBar(date, s) }\n            val sleep    = googleManager.readSleepLastNight()\n            val workouts = googleManager.readRecentWorkouts(5)','            val weekly   = googleManager.readWeeklySteps().map { (date, s) -> WeeklyBar(date, s) }\n            val workouts = googleManager.readRecentWorkouts(100)')
s=s.replace('                    distanceMeters  = distance,\n                    caloriesKcal    = calories,\n                    sleepHours      = sleep,\n                    weeklySteps     = weekly,','                    weeklySteps     = weekly,')
vm.write_text(s)

ghm = root/'app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt'
s=ghm.read_text()
old=re.search(r'    val permissions: Set<String> = setOf\(\n.*?\n    \)\n',s,re.S).group(0)
new='''    // Sprint mode: Google Health dashboard only. Keep write/import code in the repo,\n    // but request only read permissions until Huawei Health Kit is approved.\n    val permissions: Set<String> = setOf(\n        HealthPermission.getReadPermission(StepsRecord::class),\n        HealthPermission.getReadPermission(ExerciseSessionRecord::class)\n    )\n'''
s=s.replace(old,new)
s=s.replace('suspend fun readRecentWorkouts(limit: Int = 5)', 'suspend fun readRecentWorkouts(limit: Int = 100)')
ghm.write_text(s)

manifest=root/'app/src/main/AndroidManifest.xml'
s=manifest.read_text()
s=re.sub(r'\n\s*<uses-permission android:name="android.permission.health.WRITE_[^"]+" />','',s)
manifest.write_text(s)
print(f'Patched BitLut sprint. Backup: {backup}')
