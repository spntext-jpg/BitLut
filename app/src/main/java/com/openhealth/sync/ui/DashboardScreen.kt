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
import com.openhealth.sync.ui.theme.ElectricIndigo
import com.openhealth.sync.ui.theme.ElectricIndigoLt
import com.openhealth.sync.ui.theme.GlassCard
import com.openhealth.sync.ui.theme.GlowIndigo
import com.openhealth.sync.ui.theme.GlowMint
import com.openhealth.sync.ui.theme.MeshBackground
import com.openhealth.sync.ui.theme.NeonAmber
import com.openhealth.sync.ui.theme.NeonMint
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
fun DashboardScreen(viewModel: DashboardViewModel, onSyncClick: () -> Unit) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { delay(100); visible = true }
    val alpha by animateFloatAsState(
        targetValue = if (visible) 1f else 0f,
        animationSpec = tween(500, easing = FastOutSlowInEasing),
        label = "dashAlpha"
    )

    Box(modifier = Modifier.fillMaxSize()) {
        MeshBackground()

        when {
            state.isLoading -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = ElectricIndigo, modifier = Modifier.size(48.dp), strokeWidth = 3.dp)
                }
            }

            !state.hasPermissions -> {
                Box(Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
                    GlassCard(shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(28.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                            Text("🔒", fontSize = 40.sp, textAlign = TextAlign.Center)
                            Spacer(Modifier.height(16.dp))
                            Text(stringResource(R.string.dashboard_lock_title), fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextPrimary, textAlign = TextAlign.Center)
                            Spacer(Modifier.height(8.dp))
                            Text(stringResource(R.string.dashboard_lock_body), fontSize = 14.sp, color = TextSecondary, textAlign = TextAlign.Center, lineHeight = 20.sp)
                        }
                    }
                }
            }

            else -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .alpha(alpha)
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 20.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Spacer(Modifier.height(16.dp))

                    // ── Steps hero ────────────────────────────────────────────
                    val weeklyTotal = state.weeklySteps.sumOf { it.steps }
                    GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(32.dp), glowColor = GlowIndigo) {
                        Column(modifier = Modifier.padding(24.dp)) {
                            // Top row: label + weekly total
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Text(stringResource(R.string.dashboard_today), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = ElectricIndigoLt, letterSpacing = 1.2.sp)
                                if (weeklyTotal > 0) {
                                    Text(
                                        stringResource(R.string.dashboard_weekly_total, "%,d".format(weeklyTotal)),
                                        fontSize = 11.sp, color = TextTertiary
                                    )
                                }
                            }
                            Spacer(Modifier.height(4.dp))

                            // Steps + ring
                            Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = if (state.stepsToday > 0) "%,d".format(state.stepsToday) else "—",
                                        fontSize = 48.sp, fontWeight = FontWeight.Black, color = TextPrimary, letterSpacing = (-2).sp
                                    )
                                    Text(
                                        "${stringResource(R.string.dashboard_steps)}  ·  ${stringResource(R.string.dashboard_goal, "%,d".format(state.stepsGoal))}",
                                        fontSize = 13.sp, color = TextSecondary
                                    )
                                    Spacer(Modifier.height(16.dp))
                                    Box(modifier = Modifier.fillMaxWidth(0.85f).height(6.dp).clip(CircleShape).background(VoidBorder)) {
                                        val progress by animateFloatAsState(targetValue = state.stepsProgress, animationSpec = tween(1200, easing = FastOutSlowInEasing), label = "prog")
                                        Box(modifier = Modifier.fillMaxWidth(progress.coerceAtLeast(0.01f)).height(6.dp).clip(CircleShape).background(Brush.horizontalGradient(listOf(ElectricIndigo, NeonMint))))
                                    }
                                    Spacer(Modifier.height(6.dp))
                                    Text(stringResource(R.string.dashboard_pct_goal, (state.stepsProgress * 100).roundToInt()), fontSize = 12.sp, color = TextTertiary)
                                }
                                Spacer(Modifier.width(16.dp))
                                StepsRing(progress = state.stepsProgress, steps = state.stepsToday)
                            }
                        }
                    }

                    // ── Stats row ─────────────────────────────────────────────
                    val hasDistance = state.distanceMeters > 0
                    val hasCalories = state.caloriesKcal > 0
                    val hasSleep    = state.sleepHours > 0
                    if (hasDistance || hasCalories || hasSleep) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            if (hasDistance) StatCard(Modifier.weight(1f), "📍", stringResource(R.string.dashboard_distance),
                                if (state.distanceMeters >= 1000) "${"%.1f".format(state.distanceMeters / 1000)} km" else "${state.distanceMeters.roundToInt()} m", NeonMint)
                            if (hasCalories) StatCard(Modifier.weight(1f), "🔥", stringResource(R.string.dashboard_calories), "${state.caloriesKcal.roundToInt()} kcal", NeonAmber)
                            if (hasSleep)    StatCard(Modifier.weight(1f), "🌙", stringResource(R.string.dashboard_sleep), "${"%.1f".format(state.sleepHours)}h", ElectricIndigoLt)
                        }
                    }

                    // ── Weekly chart with step counts ─────────────────────────
                    if (state.weeklySteps.any { it.steps > 0 }) {
                        GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp)) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                    Text(stringResource(R.string.dashboard_7day), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = ElectricIndigoLt, letterSpacing = 1.2.sp)
                                    Text(stringResource(R.string.dashboard_avg, "%,d".format(state.weeklyAvg)), fontSize = 12.sp, color = TextSecondary)
                                }
                                Spacer(Modifier.height(16.dp))
                                WeeklyChart(bars = state.weeklySteps)
                                // Step counts below chart
                                Spacer(Modifier.height(8.dp))
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                                    state.weeklySteps.forEach { bar ->
                                        val isToday = bar.date == LocalDate.now()
                                        Text(
                                            text = if (bar.steps > 0) "%,d".format(bar.steps) else "—",
                                            fontSize = 9.sp,
                                            color = if (isToday) NeonMint else TextTertiary,
                                            fontWeight = if (isToday) FontWeight.Bold else FontWeight.Normal,
                                            modifier = Modifier.weight(1f),
                                            textAlign = TextAlign.Center
                                        )
                                    }
                                }
                            }
                        }
                    }

                    // ── Workouts with stats ───────────────────────────────────
                    if (state.recentWorkouts.isNotEmpty()) {
                        GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp), glowColor = GlowMint) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                // Summary stats above workout list
                                val totalWorkoutMin = state.recentWorkouts.sumOf { (it.endTimeMs - it.startTimeMs) / 60_000L }
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                    Text(stringResource(R.string.dashboard_workouts), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = ElectricIndigoLt, letterSpacing = 1.2.sp)
                                    Text(
                                        stringResource(R.string.dashboard_workout_duration, totalWorkoutMin.toInt()) + "  ·  ${state.recentWorkouts.size} sessions",
                                        fontSize = 11.sp, color = TextSecondary
                                    )
                                }
                                Spacer(Modifier.height(14.dp))
                                state.recentWorkouts.forEachIndexed { idx, workout ->
                                    WorkoutRow(workout)
                                    if (idx < state.recentWorkouts.lastIndex) {
                                        Spacer(Modifier.height(10.dp))
                                        Box(modifier = Modifier.fillMaxWidth().height(1.dp).background(VoidBorder))
                                        Spacer(Modifier.height(10.dp))
                                    }
                                }
                            }
                        }
                    }

                    // ── Empty state ───────────────────────────────────────────
                    if (state.stepsToday == 0L && state.weeklySteps.none { it.steps > 0 } && state.recentWorkouts.isEmpty()) {
                        GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp), glowColor = GlowMint) {
                            Column(modifier = Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("✅", fontSize = 32.sp, textAlign = TextAlign.Center)
                                Spacer(Modifier.height(12.dp))
                                Text(stringResource(R.string.dashboard_empty_title), fontSize = 16.sp, fontWeight = FontWeight.Bold, color = TextPrimary, textAlign = TextAlign.Center)
                                Spacer(Modifier.height(8.dp))
                                Text(stringResource(R.string.dashboard_empty_body), fontSize = 14.sp, color = TextSecondary, textAlign = TextAlign.Center, lineHeight = 20.sp)
                            }
                        }
                    }

                    SyncPillButton(onClick = onSyncClick)
                    Spacer(Modifier.height(72.dp))
                }
            }
        }
    }
}

// ── Sync pill ─────────────────────────────────────────────────────────────────

@Composable
fun SyncPillButton(onClick: () -> Unit, modifier: Modifier = Modifier) {
    Box(modifier = modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(50.dp))
                .background(Brush.horizontalGradient(listOf(ElectricIndigo, ElectricIndigoLt)))
                .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null, onClick = onClick)
                .padding(horizontal = 32.dp, vertical = 14.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Icon(Icons.Rounded.Refresh, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
                Text(stringResource(R.string.sync_now_button), fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = Color.White, letterSpacing = 0.3.sp)
            }
        }
    }
}

// ── Steps ring ────────────────────────────────────────────────────────────────

@Composable
private fun StepsRing(progress: Float, steps: Long) {
    val anim by animateFloatAsState(targetValue = progress, animationSpec = tween(1400, easing = FastOutSlowInEasing), label = "ring")
    Box(modifier = Modifier.size(96.dp), contentAlignment = Alignment.Center) {
        Box(modifier = Modifier.size(96.dp).drawBehind {
            val stroke = 8.dp.toPx()
            val radius = (size.minDimension - stroke) / 2
            drawCircle(color = VoidBorder, radius = radius, style = Stroke(width = stroke, cap = StrokeCap.Round))
            if (anim > 0f) drawArc(brush = Brush.sweepGradient(listOf(ElectricIndigo, NeonMint, ElectricIndigo)), startAngle = -90f, sweepAngle = 360f * anim, useCenter = false, style = Stroke(width = stroke, cap = StrokeCap.Round))
        })
        Text(
            text = if (steps >= 1000) "${"%.1f".format(steps / 1000.0)}k" else if (steps > 0) steps.toString() else "—",
            fontSize = 15.sp, fontWeight = FontWeight.Bold, color = TextPrimary, textAlign = TextAlign.Center
        )
    }
}

// ── Weekly chart ──────────────────────────────────────────────────────────────

@Composable
private fun WeeklyChart(bars: List<WeeklyBar>) {
    val maxSteps = bars.maxOfOrNull { it.steps }?.takeIf { it > 0 } ?: 1L
    val today = LocalDate.now()
    Row(modifier = Modifier.fillMaxWidth().height(80.dp), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.Bottom) {
        bars.forEach { bar ->
            val isToday = bar.date == today
            val fraction = (bar.steps.toFloat() / maxSteps.toFloat()).coerceIn(if (bar.steps > 0) 0.05f else 0f, 1f)
            val anim by animateFloatAsState(targetValue = fraction, animationSpec = tween(1000, easing = FastOutSlowInEasing), label = "bar")
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Bottom, modifier = Modifier.weight(1f).height(80.dp)) {
                if (anim > 0f) Box(modifier = Modifier.width(20.dp).height((64 * anim).dp).clip(RoundedCornerShape(topStart = 6.dp, topEnd = 6.dp)).background(
                    if (isToday) Brush.verticalGradient(listOf(NeonMint, ElectricIndigo))
                    else Brush.verticalGradient(listOf(ElectricIndigo.copy(alpha = 0.6f), ElectricIndigo.copy(alpha = 0.2f)))
                ))
                else Box(modifier = Modifier.width(20.dp).height(3.dp).clip(CircleShape).background(VoidBorder))
                Spacer(Modifier.height(4.dp))
                Text(
                    bar.date.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.getDefault()).take(2),
                    fontSize = 10.sp,
                    color = if (isToday) NeonMint else TextTertiary,
                    fontWeight = if (isToday) FontWeight.Bold else FontWeight.Normal
                )
            }
        }
    }
}

// ── Stat card ─────────────────────────────────────────────────────────────────

@Composable
private fun StatCard(modifier: Modifier, emoji: String, label: String, value: String, color: Color) {
    GlassCard(modifier = modifier, shape = RoundedCornerShape(20.dp), glowColor = color.copy(alpha = 0.2f)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(emoji, fontSize = 22.sp)
            Spacer(Modifier.height(8.dp))
            Text(value, fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
            Text(label, fontSize = 12.sp, color = TextSecondary)
        }
    }
}

// ── Workout row ───────────────────────────────────────────────────────────────

@Composable
private fun WorkoutRow(workout: ActivitySessionData) {
    val durationMin = ((workout.endTimeMs - workout.startTimeMs) / 60_000L).toInt()
    val date = Instant.ofEpochMilli(workout.startTimeMs).atZone(ZoneId.systemDefault()).toLocalDate()
    val todayStr = stringResource(R.string.dashboard_today_label)
    val yestStr  = stringResource(R.string.dashboard_yesterday)
    val dateStr  = when (date) {
        LocalDate.now()              -> todayStr
        LocalDate.now().minusDays(1) -> yestStr
        else -> date.format(DateTimeFormatter.ofPattern("MMM d"))
    }
    val emoji = when {
        workout.title.contains("Run",      ignoreCase = true) -> "🏃"
        workout.title.contains("Walk",     ignoreCase = true) -> "🚶"
        workout.title.contains("Cycl",     ignoreCase = true) -> "🚴"
        workout.title.contains("Swim",     ignoreCase = true) -> "🏊"
        workout.title.contains("Strength", ignoreCase = true) -> "🏋️"
        workout.title.contains("Yoga",     ignoreCase = true) -> "🧘"
        workout.title.contains("Hik",      ignoreCase = true) -> "🥾"
        else -> "⚡"
    }
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.size(44.dp).clip(RoundedCornerShape(14.dp)).background(Brush.linearGradient(listOf(ElectricIndigo.copy(alpha = 0.3f), NeonMint.copy(alpha = 0.15f)))), contentAlignment = Alignment.Center) {
                Text(emoji, fontSize = 20.sp)
            }
            Column {
                Text(workout.title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                Text(
                    stringResource(R.string.dashboard_workout_duration, durationMin) + "  ·  $dateStr",
                    fontSize = 12.sp, color = TextSecondary
                )
            }
        }
        // Duration badge
        Box(modifier = Modifier.clip(RoundedCornerShape(10.dp)).background(ElectricIndigo.copy(alpha = 0.18f)).padding(horizontal = 10.dp, vertical = 5.dp)) {
            Text(
                stringResource(R.string.dashboard_workout_duration, durationMin),
                fontSize = 12.sp, color = ElectricIndigoLt, fontWeight = FontWeight.SemiBold
            )
        }
    }
}
