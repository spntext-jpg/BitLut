package com.openhealth.sync.ui

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
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
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.R
import com.openhealth.sync.ui.theme.ElectricIndigo
import com.openhealth.sync.ui.theme.ElectricIndigoLt
import com.openhealth.sync.ui.theme.GlassCard
import com.openhealth.sync.ui.theme.GlowIndigo
import com.openhealth.sync.ui.theme.GlowMint
import com.openhealth.sync.ui.theme.MeshBackground
import com.openhealth.sync.ui.theme.NeonMint
import com.openhealth.sync.ui.theme.NeonAmber
import com.openhealth.sync.ui.theme.NeonRose
import com.openhealth.sync.ui.theme.TextPrimary
import com.openhealth.sync.ui.theme.TextSecondary
import com.openhealth.sync.ui.theme.TextTertiary
import com.openhealth.sync.ui.theme.VoidBorder
import kotlinx.coroutines.delay
import java.time.LocalDate
import java.time.format.TextStyle
import java.util.Locale
import kotlin.math.roundToInt

@Composable
fun DashboardScreen(viewModel: DashboardViewModel) {
    val state by viewModel.state.collectAsState()

    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { delay(80); visible = true }
    val alpha by animateFloatAsState(
        targetValue = if (visible) 1f else 0f,
        animationSpec = tween(600, easing = FastOutSlowInEasing),
        label = "dashAlpha"
    )

    Box(modifier = Modifier.fillMaxSize()) {
        MeshBackground()

        if (state.isLoading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = ElectricIndigo, modifier = Modifier.size(48.dp))
            }
            return@Box
        }

        if (!state.hasPermissions) {
            Box(Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
                GlassCard(shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(28.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("🔒", fontSize = 40.sp, textAlign = TextAlign.Center)
                        Spacer(Modifier.height(16.dp))
                        Text(
                            "Connect Google Health\nto see your data",
                            fontSize = 18.sp, fontWeight = FontWeight.Bold,
                            color = TextPrimary, textAlign = TextAlign.Center, lineHeight = 26.sp
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "Go to the Sync tab and connect\nGoogle Health Connect first.",
                            fontSize = 14.sp, color = TextSecondary,
                            textAlign = TextAlign.Center, lineHeight = 20.sp
                        )
                    }
                }
            }
            return@Box
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .alpha(alpha)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Spacer(Modifier.height(16.dp))

            // ── Steps hero ────────────────────────────────────────────────────
            GlassCard(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(32.dp),
                glowColor = GlowIndigo
            ) {
                Row(
                    modifier = Modifier.padding(24.dp).fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            "TODAY", fontSize = 11.sp, fontWeight = FontWeight.SemiBold,
                            color = ElectricIndigoLt, letterSpacing = 1.2.sp
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            text = "%,d".format(state.stepsToday),
                            fontSize = 48.sp, fontWeight = FontWeight.Black,
                            color = TextPrimary, letterSpacing = (-2).sp
                        )
                        Text(
                            "steps  ·  goal ${"%,d".format(state.stepsGoal)}",
                            fontSize = 13.sp, color = TextSecondary
                        )
                        Spacer(Modifier.height(16.dp))
                        // Progress bar
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(0.85f)
                                .height(6.dp)
                                .clip(CircleShape)
                                .background(VoidBorder)
                        ) {
                            val progress by animateFloatAsState(
                                targetValue = state.stepsProgress,
                                animationSpec = tween(1200, easing = FastOutSlowInEasing),
                                label = "stepsProgress"
                            )
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth(progress)
                                    .height(6.dp)
                                    .clip(CircleShape)
                                    .background(
                                        Brush.horizontalGradient(listOf(ElectricIndigo, NeonMint))
                                    )
                            )
                        }
                        Spacer(Modifier.height(6.dp))
                        Text(
                            "${(state.stepsProgress * 100).roundToInt()}% of daily goal",
                            fontSize = 12.sp, color = TextTertiary
                        )
                    }
                    Spacer(Modifier.width(16.dp))
                    // Ring
                    StepsRing(progress = state.stepsProgress, steps = state.stepsToday)
                }
            }

            // ── Stats row ─────────────────────────────────────────────────────
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                StatCard(
                    modifier = Modifier.weight(1f),
                    emoji = "📍",
                    label = "Distance",
                    value = if (state.distanceMeters >= 1000)
                        "${"%.1f".format(state.distanceMeters / 1000)} km"
                    else
                        "${state.distanceMeters.roundToInt()} m",
                    color = NeonMint
                )
                StatCard(
                    modifier = Modifier.weight(1f),
                    emoji = "🔥",
                    label = "Calories",
                    value = "${state.caloriesKcal.roundToInt()} kcal",
                    color = NeonAmber
                )
            }

            // ── Weekly steps chart ────────────────────────────────────────────
            if (state.weeklySteps.isNotEmpty()) {
                GlassCard(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(24.dp)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                "7-DAY STEPS", fontSize = 11.sp, fontWeight = FontWeight.SemiBold,
                                color = ElectricIndigoLt, letterSpacing = 1.2.sp
                            )
                            Text(
                                "avg ${"%,d".format(state.weeklyAvg)}",
                                fontSize = 12.sp, color = TextSecondary
                            )
                        }
                        Spacer(Modifier.height(16.dp))
                        WeeklyChart(bars = state.weeklySteps)
                    }
                }
            }

            // ── Recent workouts ───────────────────────────────────────────────
            if (state.recentWorkouts.isNotEmpty()) {
                GlassCard(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(24.dp),
                    glowColor = GlowMint
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Text(
                            "RECENT WORKOUTS", fontSize = 11.sp, fontWeight = FontWeight.SemiBold,
                            color = ElectricIndigoLt, letterSpacing = 1.2.sp
                        )
                        Spacer(Modifier.height(14.dp))
                        state.recentWorkouts.forEach { workout ->
                            WorkoutRow(workout)
                            Spacer(Modifier.height(10.dp))
                        }
                    }
                }
            }

            Spacer(Modifier.height(88.dp))
        }
    }
}

// ── Steps ring ────────────────────────────────────────────────────────────────

@Composable
private fun StepsRing(progress: Float, steps: Long) {
    val animProgress by animateFloatAsState(
        targetValue = progress,
        animationSpec = tween(1400, easing = FastOutSlowInEasing),
        label = "ringProgress"
    )
    Box(
        modifier = Modifier.size(96.dp),
        contentAlignment = Alignment.Center
    ) {
        Box(
            modifier = Modifier
                .size(96.dp)
                .drawBehind {
                    val stroke = 8.dp.toPx()
                    val radius = (size.minDimension - stroke) / 2
                    // Track
                    drawCircle(
                        color = VoidBorder,
                        radius = radius,
                        style = Stroke(width = stroke, cap = StrokeCap.Round)
                    )
                    // Progress arc
                    drawArc(
                        brush = Brush.sweepGradient(
                            listOf(ElectricIndigo, NeonMint, ElectricIndigo)
                        ),
                        startAngle = -90f,
                        sweepAngle = 360f * animProgress,
                        useCenter = false,
                        style = Stroke(width = stroke, cap = StrokeCap.Round)
                    )
                }
        )
        Text(
            text = if (steps >= 1000) "${"%.1f".format(steps / 1000.0)}k" else steps.toString(),
            fontSize = 16.sp, fontWeight = FontWeight.Bold, color = TextPrimary,
            textAlign = TextAlign.Center
        )
    }
}

// ── Weekly chart ──────────────────────────────────────────────────────────────

@Composable
private fun WeeklyChart(bars: List<WeeklyBar>) {
    val maxSteps = bars.maxOfOrNull { it.steps }?.takeIf { it > 0 } ?: 1L
    val today = LocalDate.now()

    Row(
        modifier = Modifier.fillMaxWidth().height(80.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.Bottom
    ) {
        bars.forEach { bar ->
            val isToday = bar.date == today
            val fraction = (bar.steps.toFloat() / maxSteps.toFloat()).coerceIn(0.05f, 1f)
            val animFraction by animateFloatAsState(
                targetValue = fraction,
                animationSpec = tween(1000, easing = FastOutSlowInEasing),
                label = "barAnim"
            )
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Bottom,
                modifier = Modifier.weight(1f).height(80.dp)
            ) {
                Box(
                    modifier = Modifier
                        .width(20.dp)
                        .height((64 * animFraction).dp)
                        .clip(RoundedCornerShape(topStart = 6.dp, topEnd = 6.dp))
                        .background(
                            if (isToday)
                                Brush.verticalGradient(listOf(NeonMint, ElectricIndigo))
                            else
                                Brush.verticalGradient(
                                    listOf(ElectricIndigo.copy(alpha = 0.6f), ElectricIndigo.copy(alpha = 0.2f))
                                )
                        )
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = bar.date.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.getDefault()).take(2),
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
private fun StatCard(
    modifier: Modifier,
    emoji: String,
    label: String,
    value: String,
    color: Color
) {
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
private fun WorkoutRow(workout: com.openhealth.sync.data.ActivitySessionData) {
    val durationMin = ((workout.endTimeMs - workout.startTimeMs) / 60_000L).toInt()
    val emoji = when {
        workout.title.contains("Run", ignoreCase = true)      -> "🏃"
        workout.title.contains("Walk", ignoreCase = true)     -> "🚶"
        workout.title.contains("Cycl", ignoreCase = true)     -> "🚴"
        workout.title.contains("Swim", ignoreCase = true)     -> "🏊"
        workout.title.contains("Strength", ignoreCase = true) -> "🏋️"
        workout.title.contains("Yoga", ignoreCase = true)     -> "🧘"
        workout.title.contains("Hik", ignoreCase = true)      -> "🥾"
        else -> "⚡"
    }
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(
                        Brush.linearGradient(
                            listOf(ElectricIndigo.copy(alpha = 0.3f), NeonMint.copy(alpha = 0.15f))
                        )
                    ),
                contentAlignment = Alignment.Center
            ) {
                Text(emoji, fontSize = 18.sp)
            }
            Column {
                Text(workout.title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                Text("$durationMin min", fontSize = 12.sp, color = TextSecondary)
            }
        }
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(NeonMint.copy(alpha = 0.12f))
                .padding(horizontal = 10.dp, vertical = 4.dp)
        ) {
            Text("Done", fontSize = 12.sp, color = NeonMint, fontWeight = FontWeight.Medium)
        }
    }
}
