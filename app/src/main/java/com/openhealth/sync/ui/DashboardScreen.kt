package com.openhealth.sync.ui

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
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.R
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.util.L10n
import kotlinx.coroutines.delay
import java.text.NumberFormat
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.TextStyle
import java.util.Locale
import kotlin.math.roundToInt

private val CleanWhite = Color(0xFFFFFFFF)
private val Ink = Color(0xFF101418)
private val InkSoft = Color(0xFF59616A)
private val Metal = Color(0xFFBAB8BA)
private val Lime = Color(0xFFC1FF05)
private val Purple = Color(0xFF9E6FC3)
private val Orange = Color(0xFFFF7D32)
private val AirBlue = Color(0xFFC8E1FC)
private val CardBorder = Color(0x1A101418)
private val CardGlass = Color(0xCCFFFFFF)

@Composable
fun DashboardScreen(viewModel: DashboardViewModel, onSyncClick: () -> Unit) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { delay(80); visible = true }
    val alpha by animateFloatAsState(
        targetValue = if (visible) 1f else 0f,
        animationSpec = tween(360, easing = FastOutSlowInEasing),
        label = "dashboardAlpha"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.linearGradient(
                    listOf(CleanWhite, AirBlue.copy(alpha = 0.42f), CleanWhite)
                )
            )
    ) {
        when {
            state.isLoading -> LoadingState()
            !state.hasPermissions -> PermissionState(onConnect = onSyncClick)
            else -> DashboardContent(alpha = alpha, state = state, onRefresh = onSyncClick)
        }
    }
}

@Composable
private fun LoadingState() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(color = Orange, strokeWidth = 4.dp, modifier = Modifier.size(54.dp))
    }
}

@Composable
private fun PermissionState(onConnect: () -> Unit) {
    Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
        PremiumCard(modifier = Modifier.fillMaxWidth(), radius = 32) {
            Column(
                modifier = Modifier.padding(28.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Text("✦", fontSize = 42.sp, color = Orange, textAlign = TextAlign.Center)
                Text(
                    text = stringResource(R.string.dashboard_lock_title),
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Black,
                    color = Ink,
                    textAlign = TextAlign.Center,
                    lineHeight = 30.sp
                )
                Text(
                    text = stringResource(R.string.dashboard_lock_body),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                    color = InkSoft,
                    textAlign = TextAlign.Center,
                    lineHeight = 22.sp
                )
                Button(
                    onClick = onConnect,
                    colors = ButtonDefaults.buttonColors(containerColor = Orange, contentColor = Color.White),
                    shape = RoundedCornerShape(18.dp),
                    modifier = Modifier.fillMaxWidth().height(56.dp)
                ) {
                    Text(stringResource(R.string.dashboard_lock_cta), fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun DashboardContent(alpha: Float, state: DashboardUiState, onRefresh: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .alpha(alpha)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Spacer(Modifier.height(18.dp))
        Header(onRefresh = onRefresh)

        val weeklyTotal = state.weeklySteps.sumOf { it.steps }
        HeroStepsCard(
            steps = state.stepsToday,
            goal = state.stepsGoal,
            progress = state.stepsProgress,
            weeklyTotal = weeklyTotal
        )

        if (state.weeklySteps.any { it.steps > 0 }) {
            WeeklyStepsCard(bars = state.weeklySteps, average = state.weeklyAvg)
        }

        WorkoutsCard(workouts = state.recentWorkouts)

        if (state.stepsToday == 0L && state.weeklySteps.none { it.steps > 0 } && state.recentWorkouts.isEmpty()) {
            EmptyStateCard()
        }

        Spacer(Modifier.height(80.dp))
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
                text = stringResource(R.string.dashboard_title),
                fontSize = 34.sp,
                fontWeight = FontWeight.Black,
                color = Ink,
                letterSpacing = (-0.8).sp
            )
            Text(
                text = stringResource(R.string.dashboard_subtitle),
                fontSize = 15.sp,
                fontWeight = FontWeight.Medium,
                color = InkSoft,
                lineHeight = 20.sp
            )
        }
        Box(
            modifier = Modifier
                .size(54.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(Brush.linearGradient(listOf(Lime, Orange)))
                .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null, onClick = onRefresh),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Rounded.Refresh, contentDescription = null, tint = Ink, modifier = Modifier.size(24.dp))
        }
    }
}

@Composable
private fun HeroStepsCard(steps: Long, goal: Long, progress: Float, weeklyTotal: Long) {
    PremiumCard(modifier = Modifier.fillMaxWidth(), radius = 32, glow = Lime.copy(alpha = 0.38f)) {
        Column(modifier = Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                LabelPill(text = stringResource(R.string.dashboard_today), color = Lime, textColor = Ink)
                Text(
                    text = stringResource(R.string.dashboard_weekly_total, number(weeklyTotal)),
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = InkSoft
                )
            }
            Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = if (steps > 0) number(steps) else stringResource(R.string.empty_dash),
                        fontSize = 66.sp,
                        fontWeight = FontWeight.Black,
                        color = Ink,
                        letterSpacing = (-2.4).sp,
                        lineHeight = 68.sp
                    )
                    Text(
                        text = "${stringResource(R.string.dashboard_steps)} · ${stringResource(R.string.dashboard_goal, number(goal))}",
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = Orange
                    )
                }
                StepsRing(progress = progress, steps = steps)
            }
            ProgressBar(progress = progress)
            Text(
                text = stringResource(R.string.dashboard_pct_goal, (progress * 100).roundToInt()),
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = InkSoft
            )
        }
    }
}

@Composable
private fun WeeklyStepsCard(bars: List<WeeklyBar>, average: Long) {
    PremiumCard(modifier = Modifier.fillMaxWidth(), radius = 28, glow = Orange.copy(alpha = 0.24f)) {
        Column(modifier = Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                LabelPill(text = stringResource(R.string.dashboard_7day), color = Orange, textColor = Color.White)
                Text(stringResource(R.string.dashboard_avg, number(average)), fontSize = 14.sp, fontWeight = FontWeight.Bold, color = InkSoft)
            }
            WeeklyChart(bars)
        }
    }
}

@Composable
private fun WorkoutsCard(workouts: List<ActivitySessionData>) {
    PremiumCard(modifier = Modifier.fillMaxWidth(), radius = 28, glow = Purple.copy(alpha = 0.22f)) {
        Column(modifier = Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                LabelPill(text = stringResource(R.string.dashboard_workouts), color = Purple, textColor = Color.White)
                Text(stringResource(R.string.dashboard_sessions_count, workouts.size), fontSize = 14.sp, fontWeight = FontWeight.Bold, color = InkSoft)
            }
            if (workouts.isEmpty()) {
                Text(
                    text = stringResource(R.string.dashboard_empty_body),
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Medium,
                    color = InkSoft,
                    lineHeight = 21.sp
                )
            } else {
                workouts.forEachIndexed { index, workout ->
                    WorkoutRow(workout)
                    if (index < workouts.lastIndex) Box(Modifier.fillMaxWidth().height(1.dp).background(CardBorder))
                }
            }
        }
    }
}

@Composable
private fun EmptyStateCard() {
    PremiumCard(modifier = Modifier.fillMaxWidth(), radius = 28, glow = AirBlue.copy(alpha = 0.6f)) {
        Column(modifier = Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("✓", fontSize = 34.sp, color = Orange, textAlign = TextAlign.Center)
            Text(stringResource(R.string.dashboard_empty_title), fontSize = 22.sp, fontWeight = FontWeight.Black, color = Ink, textAlign = TextAlign.Center)
            Text(stringResource(R.string.dashboard_empty_body), fontSize = 15.sp, fontWeight = FontWeight.Medium, color = InkSoft, textAlign = TextAlign.Center, lineHeight = 21.sp)
        }
    }
}

@Composable
private fun WeeklyChart(bars: List<WeeklyBar>) {
    val maxSteps = bars.maxOfOrNull { it.steps }?.takeIf { it > 0 } ?: 1L
    val today = LocalDate.now()
    Row(modifier = Modifier.fillMaxWidth().height(142.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.Bottom) {
        bars.forEach { bar ->
            val isToday = bar.date == today
            val fraction = (bar.steps.toFloat() / maxSteps.toFloat()).coerceIn(if (bar.steps > 0) 0.08f else 0f, 1f)
            val anim by animateFloatAsState(targetValue = fraction, animationSpec = tween(800, easing = FastOutSlowInEasing), label = "weeklyBar")
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Bottom, modifier = Modifier.weight(1f).height(142.dp)) {
                Text(
                    text = if (bar.steps > 0) compactNumber(bar.steps) else "—",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (isToday) Orange else InkSoft,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(6.dp))
                Box(
                    modifier = Modifier
                        .width(26.dp)
                        .height((76 * anim).dp.coerceAtLeast(4.dp))
                        .clip(RoundedCornerShape(topStart = 10.dp, topEnd = 10.dp, bottomStart = 6.dp, bottomEnd = 6.dp))
                        .background(if (isToday) Brush.verticalGradient(listOf(Orange, Lime)) else Brush.verticalGradient(listOf(Purple.copy(alpha = 0.85f), AirBlue)))
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = bar.date.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.getDefault()).take(2).replaceFirstChar { it.uppercase(Locale.getDefault()) },
                    fontSize = 12.sp,
                    fontWeight = if (isToday) FontWeight.Black else FontWeight.Bold,
                    color = if (isToday) Ink else InkSoft
                )
            }
        }
    }
}

@Composable
private fun StepsRing(progress: Float, steps: Long) {
    val anim by animateFloatAsState(targetValue = progress, animationSpec = tween(1000, easing = FastOutSlowInEasing), label = "stepsRing")
    Box(modifier = Modifier.size(112.dp), contentAlignment = Alignment.Center) {
        Box(modifier = Modifier.size(112.dp).drawBehind {
            val stroke = 11.dp.toPx()
            val radius = (size.minDimension - stroke) / 2
            drawCircle(color = AirBlue.copy(alpha = 0.7f), radius = radius, style = Stroke(width = stroke, cap = StrokeCap.Round))
            if (anim > 0f) {
                drawArc(
                    brush = Brush.sweepGradient(listOf(Lime, Orange, Purple, Lime)),
                    startAngle = -90f,
                    sweepAngle = 360f * anim,
                    useCenter = false,
                    style = Stroke(width = stroke, cap = StrokeCap.Round)
                )
            }
        })
        Text(
            text = if (steps >= 1000) "${"%.1f".format(Locale.US, steps / 1000.0)}k" else if (steps > 0) steps.toString() else "—",
            fontSize = 20.sp,
            fontWeight = FontWeight.Black,
            color = Ink,
            textAlign = TextAlign.Center
        )
    }
}

@Composable
private fun ProgressBar(progress: Float) {
    val anim by animateFloatAsState(targetValue = progress.coerceIn(0f, 1f), animationSpec = tween(900, easing = FastOutSlowInEasing), label = "progress")
    Box(modifier = Modifier.fillMaxWidth().height(12.dp).clip(CircleShape).background(AirBlue.copy(alpha = 0.75f))) {
        Box(modifier = Modifier.fillMaxWidth(anim.coerceAtLeast(0.02f)).height(12.dp).clip(CircleShape).background(Brush.horizontalGradient(listOf(Lime, Orange))))
    }
}

@Composable
private fun WorkoutRow(workout: ActivitySessionData) {
    val durationMin = ((workout.endTimeMs - workout.startTimeMs) / 60_000L).toInt().coerceAtLeast(0)
    val date = Instant.ofEpochMilli(workout.startTimeMs).atZone(ZoneId.systemDefault()).toLocalDate()
    val dateText = when (date) {
        LocalDate.now() -> stringResource(R.string.dashboard_today_label)
        LocalDate.now().minusDays(1) -> stringResource(R.string.dashboard_yesterday)
        else -> L10n.shortDate(date)
    }
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
            Box(modifier = Modifier.size(50.dp).clip(RoundedCornerShape(18.dp)).background(Brush.linearGradient(listOf(Orange.copy(alpha = 0.92f), Lime.copy(alpha = 0.82f)))), contentAlignment = Alignment.Center) {
                Text(workoutIcon(workout.title), fontSize = 22.sp)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(L10n.workoutTitle(workout.title), fontSize = 17.sp, fontWeight = FontWeight.Black, color = Ink, maxLines = 1)
                Text("${stringResource(R.string.dashboard_workout_duration, durationMin)} · $dateText", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = InkSoft)
            }
        }
        Box(modifier = Modifier.clip(RoundedCornerShape(14.dp)).background(Purple.copy(alpha = 0.16f)).padding(horizontal = 11.dp, vertical = 7.dp)) {
            Text(stringResource(R.string.dashboard_workout_duration, durationMin), fontSize = 13.sp, fontWeight = FontWeight.Black, color = Purple)
        }
    }
}

@Composable
private fun PremiumCard(modifier: Modifier = Modifier, radius: Int = 24, glow: Color = Orange.copy(alpha = 0.18f), content: @Composable () -> Unit) {
    Box(
        modifier = modifier
            .drawBehind { drawCircle(color = glow, radius = size.minDimension * 0.62f, center = center) }
            .clip(RoundedCornerShape(radius.dp))
            .background(CardGlass)
            .drawBehind { drawRoundRect(color = CardBorder, cornerRadius = androidx.compose.ui.geometry.CornerRadius(radius.dp.toPx(), radius.dp.toPx()), style = Stroke(width = 1.dp.toPx())) }
    ) { content() }
}

@Composable
private fun LabelPill(text: String, color: Color, textColor: Color) {
    Box(modifier = Modifier.clip(RoundedCornerShape(999.dp)).background(color).padding(horizontal = 12.dp, vertical = 7.dp)) {
        Text(text = text.uppercase(Locale.getDefault()), fontSize = 12.sp, fontWeight = FontWeight.Black, color = textColor, letterSpacing = 0.8.sp)
    }
}

private fun workoutIcon(title: String): String {
    val t = title.lowercase(Locale.getDefault())
    return when {
        "run" in t -> "🏃"
        "walk" in t -> "🚶"
        "cycl" in t || "bike" in t -> "🚴"
        "swim" in t -> "🏊"
        "strength" in t || "weight" in t -> "🏋️"
        "yoga" in t -> "🧘"
        "hik" in t -> "🥾"
        else -> "⚡"
    }
}

private fun number(value: Long): String = NumberFormat.getIntegerInstance(Locale.getDefault()).format(value)
private fun compactNumber(value: Long): String = if (value >= 10_000) "${NumberFormat.getIntegerInstance(Locale.getDefault()).format(value / 1000)}k" else number(value)
