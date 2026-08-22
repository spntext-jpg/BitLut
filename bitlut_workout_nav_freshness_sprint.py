#!/usr/bin/env python3
"""BitLut sprint patch: richer workouts, expressive navigation, truthful data freshness.

Run from repository root:
    python3 bitlut_workout_nav_freshness_sprint.py --apply
    python3 bitlut_workout_nav_freshness_sprint.py --verify

This patch intentionally does not commit or push automatically.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = ROOT / ".bitlut_patch_backup"

GOOGLE = Path("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
CACHE = Path("app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt")
DASHBOARD_VM = Path("app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt")
SHELL = Path("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
NAV = Path("app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt")
STRINGS_EN = Path("app/src/main/res/values/strings.xml")
STRINGS_RU = Path("app/src/main/res/values-ru/strings.xml")
VERIFY = Path("scripts/verify_workout_nav_freshness_sprint.py")
APP_GRADLE = Path("app/build.gradle.kts")

TARGETS = [GOOGLE, CACHE, DASHBOARD_VM, SHELL, NAV, STRINGS_EN, STRINGS_RU, APP_GRADLE]


def die(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def read(path: Path) -> str:
    full = ROOT / path
    if not full.exists():
        die(f"Missing required file: {path}")
    return full.read_text(encoding="utf-8")


def write_if_changed(path: Path, text: str) -> bool:
    full = ROOT / path
    old = full.read_text(encoding="utf-8") if full.exists() else None
    if old == text:
        print(f"   unchanged: {path}")
        return False
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(text, encoding="utf-8")
    print(f"   updated:   {path}")
    return True


def replace_once(text: str, old: str, new: str, desc: str) -> str:
    count = text.count(old)
    if count == 1:
        return text.replace(old, new, 1)
    if count == 0 and new in text:
        print(f"   already applied: {desc}")
        return text
    die(f"Expected exactly one anchor for {desc!r}; found {count}")


def replace_between(text: str, start: str, end: str, replacement: str, desc: str) -> str:
    start_count = text.count(start)
    end_count = text.count(end)
    if start_count != 1 or end_count != 1:
        if replacement in text:
            print(f"   already applied: {desc}")
            return text
        die(f"Cannot safely isolate {desc}: start={start_count}, end={end_count}")
    a = text.index(start)
    b = text.index(end, a)
    return text[:a] + replacement + text[b:]


def backup_targets() -> None:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_workout_nav_freshness")
    dst_root = BACKUP_ROOT / stamp
    for rel in TARGETS:
        src = ROOT / rel
        if not src.exists():
            die(f"Missing required file before backup: {rel}")
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"==> Backup: {dst_root.relative_to(ROOT)}")


ACTIVITY_SESSION_OLD = '''data class ActivitySessionData(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val title: String = "Huawei activity",
    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT,
    val distanceMeters: Double? = null
)'''

ACTIVITY_SESSION_NEW = '''data class ActivitySessionData(
    val startTimeMs: Long,
    val endTimeMs: Long,
    val title: String = "Huawei activity",
    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT,
    val distanceMeters: Double? = null,
    val activeCaloriesKcal: Double? = null,
    val elevationMeters: Double? = null,
    val steps: Long? = null
)'''

DAILY_WINDOW_NEW = '''    private data class SessionMetricAccumulator(
        var steps: Double = 0.0,
        var distanceMeters: Double = 0.0,
        var activeCaloriesKcal: Double = 0.0,
        var elevationMeters: Double = 0.0
    )

    private data class DashboardActivityWindow(
        val dailyActivity: List<DailyActivitySummary>,
        val workouts: List<ActivitySessionData>
    )

    /**
     * Reads each already-approved activity stream once for the dashboard window,
     * groups it by day, and attributes overlapping records to the two workout
     * cards that are actually displayed. This avoids one Health Connect query
     * per workout and does not request any new health category.
     */
    private suspend fun readDailyActivitySummaries(
        client: HealthConnectClient,
        daysBack: Int,
        workouts: List<ActivitySessionData>
    ): DashboardActivityWindow {
        val safeDays = daysBack.coerceIn(14, 60)
        val zone = ZoneId.systemDefault()
        val today = LocalDate.now()
        val firstDay = today.minusDays((safeDays - 1).toLong())
        val dates = (0 until safeDays).map { firstDay.plusDays(it.toLong()) }
        val start = firstDay.atStartOfDay(zone).toInstant()
        val end = Instant.now()
        val range = TimeRangeFilter.between(start, end)
        val origins = selectedDataOrigins()

        val stepsByDay = dates.associateWith { 0L }.toMutableMap()
        val distanceByDay = dates.associateWith { 0.0 }.toMutableMap()
        val caloriesByDay = dates.associateWith { 0.0 }.toMutableMap()
        val elevationByDay = dates.associateWith { 0.0 }.toMutableMap()
        val floorsByDay = dates.associateWith { 0.0 }.toMutableMap()
        val workoutMinutesByDay = dates.associateWith { 0L }.toMutableMap()
        val workoutCountByDay = dates.associateWith { 0 }.toMutableMap()
        val longestWorkoutByDay = dates.associateWith { 0L }.toMutableMap()

        val displayedWorkouts = workouts.take(2)
        val sessionMetrics = displayedWorkouts.associate {
            Pair(it.startTimeMs, it.endTimeMs) to SessionMetricAccumulator()
        }.toMutableMap()

        fun dateOf(epochMs: Long): LocalDate =
            Instant.ofEpochMilli(epochMs).atZone(zone).toLocalDate()

        fun overlapFraction(recordStartMs: Long, recordEndMs: Long, session: ActivitySessionData): Double {
            if (recordEndMs <= recordStartMs || session.endTimeMs <= session.startTimeMs) return 0.0
            val overlapStart = maxOf(recordStartMs, session.startTimeMs)
            val overlapEnd = minOf(recordEndMs, session.endTimeMs)
            if (overlapEnd <= overlapStart) return 0.0
            return (overlapEnd - overlapStart).toDouble() / (recordEndMs - recordStartMs).toDouble()
        }

        client.readRecords(
            ReadRecordsRequest(
                recordType = StepsRecord::class,
                timeRangeFilter = range,
                dataOriginFilter = origins
            )
        ).records.forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in stepsByDay) stepsByDay[date] = (stepsByDay[date] ?: 0L) + record.count
            val startMs = record.startTime.toEpochMilli()
            val endMs = record.endTime.toEpochMilli()
            displayedWorkouts.forEach { session ->
                val fraction = overlapFraction(startMs, endMs, session)
                if (fraction > 0.0) {
                    sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.steps =
                        (sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.steps ?: 0.0) + record.count.toDouble() * fraction
                }
            }
        }

        client.readRecords(
            ReadRecordsRequest(
                recordType = DistanceRecord::class,
                timeRangeFilter = range,
                dataOriginFilter = origins
            )
        ).records.forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in distanceByDay) distanceByDay[date] = (distanceByDay[date] ?: 0.0) + record.distance.inMeters
            val startMs = record.startTime.toEpochMilli()
            val endMs = record.endTime.toEpochMilli()
            displayedWorkouts.forEach { session ->
                val fraction = overlapFraction(startMs, endMs, session)
                if (fraction > 0.0) {
                    sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.distanceMeters =
                        (sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.distanceMeters ?: 0.0) + record.distance.inMeters * fraction
                }
            }
        }

        client.readRecords(
            ReadRecordsRequest(
                recordType = ActiveCaloriesBurnedRecord::class,
                timeRangeFilter = range,
                dataOriginFilter = origins
            )
        ).records.forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in caloriesByDay) caloriesByDay[date] = (caloriesByDay[date] ?: 0.0) + record.energy.inKilocalories
            val startMs = record.startTime.toEpochMilli()
            val endMs = record.endTime.toEpochMilli()
            displayedWorkouts.forEach { session ->
                val fraction = overlapFraction(startMs, endMs, session)
                if (fraction > 0.0) {
                    sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.activeCaloriesKcal =
                        (sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.activeCaloriesKcal ?: 0.0) + record.energy.inKilocalories * fraction
                }
            }
        }

        client.readRecords(
            ReadRecordsRequest(
                recordType = ElevationGainedRecord::class,
                timeRangeFilter = range,
                dataOriginFilter = origins
            )
        ).records.forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in elevationByDay) elevationByDay[date] = (elevationByDay[date] ?: 0.0) + record.elevation.inMeters
            val startMs = record.startTime.toEpochMilli()
            val endMs = record.endTime.toEpochMilli()
            displayedWorkouts.forEach { session ->
                val fraction = overlapFraction(startMs, endMs, session)
                if (fraction > 0.0) {
                    sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.elevationMeters =
                        (sessionMetrics[Pair(session.startTimeMs, session.endTimeMs)]?.elevationMeters ?: 0.0) + record.elevation.inMeters * fraction
                }
            }
        }

        client.readRecords(
            ReadRecordsRequest(
                recordType = FloorsClimbedRecord::class,
                timeRangeFilter = range,
                dataOriginFilter = origins
            )
        ).records.forEach { record ->
            val date = record.startTime.atZone(zone).toLocalDate()
            if (date in floorsByDay) floorsByDay[date] = (floorsByDay[date] ?: 0.0) + record.floors
        }

        val rangeStartMs = start.toEpochMilli()
        workouts.asSequence()
            .filter { it.startTimeMs >= rangeStartMs && it.endTimeMs > it.startTimeMs }
            .distinctBy { Pair(it.startTimeMs, it.endTimeMs) }
            .forEach { workout ->
                val date = dateOf(workout.startTimeMs)
                if (date !in workoutMinutesByDay) return@forEach
                val duration = ((workout.endTimeMs - workout.startTimeMs) / 60_000L).coerceAtLeast(1L)
                workoutMinutesByDay[date] = (workoutMinutesByDay[date] ?: 0L) + duration
                workoutCountByDay[date] = (workoutCountByDay[date] ?: 0) + 1
                longestWorkoutByDay[date] = maxOf(longestWorkoutByDay[date] ?: 0L, duration)
            }

        val dailyActivity = dates.map { date ->
            DailyActivitySummary(
                date = date,
                steps = stepsByDay[date] ?: 0L,
                distanceMeters = distanceByDay[date] ?: 0.0,
                caloriesKcal = caloriesByDay[date] ?: 0.0,
                elevationMeters = elevationByDay[date] ?: 0.0,
                floors = floorsByDay[date] ?: 0.0,
                workoutMinutes = workoutMinutesByDay[date] ?: 0L,
                workoutCount = workoutCountByDay[date] ?: 0,
                longestWorkoutMinutes = longestWorkoutByDay[date] ?: 0L
            )
        }

        val enrichedWorkouts = workouts.map { workout ->
            val metrics = sessionMetrics[Pair(workout.startTimeMs, workout.endTimeMs)]
            if (metrics == null) {
                workout
            } else {
                workout.copy(
                    distanceMeters = metrics.distanceMeters.takeIf { it > 0.0 } ?: workout.distanceMeters,
                    activeCaloriesKcal = metrics.activeCaloriesKcal.takeIf { it > 0.0 },
                    elevationMeters = metrics.elevationMeters.takeIf { it > 0.0 },
                    steps = metrics.steps.toLong().takeIf { it > 0L }
                )
            }
        }

        return DashboardActivityWindow(dailyActivity = dailyActivity, workouts = enrichedWorkouts)
    }

'''

CACHE_SAVE_NEW = '''    /**
     * Persists the latest cache read time and separately tracks when the
     * underlying dashboard values last changed. Background refreshes therefore
     * keep cache freshness semantics intact without making the UI claim that
     * unchanged data became new simply because the app was opened.
     *
     * @return epoch millis when the currently displayed data first changed.
     */
    fun save(snapshot: GoogleDashboardSnapshot): Long {
        val previous = try { load() } catch (_: Exception) { null }
        val now = System.currentTimeMillis()
        val dataChangedAtMs = if (previous?.snapshot == snapshot && previous.dataChangedAtMs > 0L) {
            previous.dataChangedAtMs
        } else {
            now
        }

        return try {
            val json = snapshotToJson(snapshot)
            prefs.edit()
                .putString(sourceKey(KEY_SNAPSHOT_JSON), json.toString())
                .putLong(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS), now)
                .putLong(sourceKey(KEY_SNAPSHOT_DATA_CHANGED_AT_MS), dataChangedAtMs)
                .apply()
            AppLogger.d(TAG, "Dashboard snapshot cached (stepsToday=${snapshot.stepsToday}, dataChangedAtMs=$dataChangedAtMs)")
            dataChangedAtMs
        } catch (e: Exception) {
            // Caching is a best-effort optimization. A failure here must never
            // crash sync or the dashboard load path.
            AppLogger.e(TAG, "Failed to cache dashboard snapshot: ${e.message}", e)
            previous?.dataChangedAtMs ?: 0L
        }
    }

'''

WORKOUT_UI_NEW = '''/**
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

    fun duration() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_duration_label),
        stringResource(R.string.workout_duration_value, durationMinutes)
    )
    fun distance() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_distance_label),
        distanceKm?.let { stringResource(R.string.distance_today_value, formatOneDecimal(it)) } ?: noData
    )
    fun caloriesMetric() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_calories_label),
        calories?.let { stringResource(R.string.workout_calories_value, it.toLong()) } ?: noData
    )
    fun elevationMetric() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_elevation_label),
        elevation?.let { stringResource(R.string.workout_elevation_value, it.toLong()) } ?: noData
    )
    fun stepsMetric() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_steps_label),
        steps?.let(::formatNumber) ?: noData
    )
    fun started() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_started_label),
        formatWorkoutDateTime(session.startTimeMs)
    )
    fun ended() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_ended_label),
        formatWorkoutClockTime(session.endTimeMs)
    )
    fun pace() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_pace_label),
        paceMinutesPerKm?.let { stringResource(R.string.workout_pace_value, formatPace(it)) } ?: noData
    )
    fun speed() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_speed_label),
        averageSpeedKmh?.let { stringResource(R.string.workout_speed_value, formatOneDecimal(it)) } ?: noData
    )
    fun swimPace() = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_swim_pace_label),
        swimPaceMinutesPer100m?.let { stringResource(R.string.workout_swim_pace_value, formatPace(it)) } ?: noData
    )

    return when (session.exerciseType) {
        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING,
        ExerciseSessionRecord.EXERCISE_TYPE_WALKING -> listOf(duration(), distance(), pace(), caloriesMetric())

        ExerciseSessionRecord.EXERCISE_TYPE_BIKING -> listOf(duration(), distance(), speed(), elevationMetric())

        ExerciseSessionRecord.EXERCISE_TYPE_HIKING -> listOf(duration(), distance(), elevationMetric(), caloriesMetric())

        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER,
        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL -> listOf(duration(), distance(), swimPace(), caloriesMetric())

        ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING,
        ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING -> listOf(duration(), caloriesMetric(), stepsMetric(), started())

        ExerciseSessionRecord.EXERCISE_TYPE_YOGA,
        ExerciseSessionRecord.EXERCISE_TYPE_PILATES -> listOf(duration(), caloriesMetric(), started(), ended())

        else -> listOf(duration(), distance(), caloriesMetric(), started())
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
                        valueColor = accent,
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

'''

NAV_TARGET = '''package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustMotion
import com.openhealth.sync.ui.theme.AugustRadius

private const val SECRET_TAP_COUNT = 5
private const val SECRET_TAP_WINDOW_MS = 2000L

/**
 * Compact August v3 navigation dock inspired by the 2026 Material 3 Expressive
 * short-navigation pattern: persistent destination labels, strong selected
 * state, generous targets, and motion driven by direct interaction state.
 *
 * Sync remains an action rather than pretending to be a navigation destination.
 * No blur dependency is required.
 */
@Composable
internal fun AugustBottomNav(
    selected: MainTab,
    onSelected: (MainTab) -> Unit,
    onSecretLogViewerTriggered: () -> Unit = {},
    onRefreshClick: () -> Unit = {}
) {
    var secretTapCount by remember { mutableIntStateOf(0) }
    var lastSecretTapAtMs by remember { mutableLongStateOf(0L) }
    val shellShape = remember { RoundedCornerShape(28.dp) }

    fun onSettingsTabTapped() {
        val now = System.currentTimeMillis()
        secretTapCount = if (now - lastSecretTapAtMs <= SECRET_TAP_WINDOW_MS) secretTapCount + 1 else 1
        lastSecretTapAtMs = now
        if (secretTapCount >= SECRET_TAP_COUNT) {
            secretTapCount = 0
            onSecretLogViewerTriggered()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .shadow(
                    elevation = AugustElevation.HeroShadowElevation,
                    shape = shellShape,
                    ambientColor = AugustElevation.HeroShadowColor.copy(alpha = AugustElevation.HeroShadowAlpha),
                    spotColor = AugustElevation.HeroShadowColor.copy(alpha = AugustElevation.HeroShadowAlpha)
                )
                .clip(shellShape)
                .background(AugustColor.Navy)
                .border(1.dp, AugustColor.BorderDark, shellShape)
                .padding(horizontal = 8.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            AugustDestination(
                modifier = Modifier.weight(1f),
                tab = MainTab.Today,
                selected = selected == MainTab.Today,
                onClick = { onSelected(MainTab.Today) }
            )
            AugustSyncAction(onClick = onRefreshClick)
            AugustDestination(
                modifier = Modifier.weight(1f),
                tab = MainTab.Settings,
                selected = selected == MainTab.Settings,
                onClick = {
                    onSettingsTabTapped()
                    onSelected(MainTab.Settings)
                }
            )
        }
    }
}

@Composable
private fun AugustDestination(
    modifier: Modifier,
    tab: MainTab,
    selected: Boolean,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val focused by interactionSource.collectIsFocusedAsState()
    val shape = remember { RoundedCornerShape(20.dp) }
    val iconShape = remember { RoundedCornerShape(11.dp) }
    val label = when (tab) {
        MainTab.Today -> stringResource(R.string.tab_today)
        MainTab.Settings -> stringResource(R.string.tab_settings)
    }

    val container by animateColorAsState(
        targetValue = if (selected) AugustColor.Surface else Color.Transparent,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationContainer"
    )
    val contentColor by animateColorAsState(
        targetValue = if (selected) AugustColor.Ink else AugustColor.DarkSecondaryText,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationContent"
    )
    val iconTile by animateColorAsState(
        targetValue = if (selected) AugustColor.Lime else AugustColor.NavySoft,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationIconTile"
    )
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.96f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "destinationPressScale"
    )
    val iconSize by animateDpAsState(
        targetValue = if (selected) 21.dp else 20.dp,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationIconSize"
    )

    Column(
        modifier = modifier
            .height(58.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .clip(shape)
            .background(container)
            .border(
                width = if (focused) 2.dp else 0.dp,
                color = if (focused) AugustColor.Purple else Color.Transparent,
                shape = shape
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                role = Role.Tab,
                onClick = onClick
            )
            .padding(horizontal = 6.dp, vertical = 5.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .size(30.dp)
                .clip(iconShape)
                .background(iconTile),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = tab.icon,
                contentDescription = label,
                tint = if (selected) AugustColor.LimeInk else contentColor,
                modifier = Modifier.size(iconSize)
            )
        }
        Spacer(Modifier.height(3.dp))
        Text(
            text = label,
            color = contentColor,
            fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.SemiBold,
            fontSize = 10.sp,
            maxLines = 1
        )
    }
}

@Composable
private fun AugustSyncAction(onClick: () -> Unit) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val focused by interactionSource.collectIsFocusedAsState()
    val shape = remember { RoundedCornerShape(20.dp) }
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.94f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncPressScale"
    )
    val rotation by animateFloatAsState(
        targetValue = if (pressed) -24f else 0f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncPressRotation"
    )
    val fill by animateColorAsState(
        targetValue = if (pressed) AugustColor.LimeActive else AugustColor.Lime,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncFill"
    )

    Box(
        modifier = Modifier
            .size(58.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                translationY = -2.dp.toPx()
            }
            .shadow(
                elevation = AugustElevation.ButtonShadowElevation,
                shape = shape,
                ambientColor = AugustColor.Lime.copy(alpha = 0.18f),
                spotColor = AugustColor.Lime.copy(alpha = 0.18f)
            )
            .clip(shape)
            .background(fill)
            .border(
                width = if (focused) 2.dp else 0.dp,
                color = if (focused) AugustColor.Purple else Color.Transparent,
                shape = shape
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                role = Role.Button,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = Icons.Rounded.Refresh,
            contentDescription = stringResource(R.string.sync_now),
            tint = AugustColor.LimeInk,
            modifier = Modifier
                .size(27.dp)
                .graphicsLayer { rotationZ = rotation }
        )
    }
}
'''

STRINGS_EN_ADD = '''    <string name="workout_stat_speed_label">Avg speed</string>
    <string name="workout_stat_calories_label">Calories</string>
    <string name="workout_stat_elevation_label">Elevation</string>
    <string name="workout_stat_steps_label">Steps</string>
    <string name="workout_stat_started_label">Started</string>
    <string name="workout_stat_ended_label">Finished</string>
    <string name="workout_stat_swim_pace_label">Pace / 100 m</string>
    <string name="workout_speed_value">%1$s km/h</string>
    <string name="workout_calories_value">%1$d kcal</string>
    <string name="workout_elevation_value">%1$d m</string>
    <string name="workout_swim_pace_value">%1$s /100 m</string>
'''

STRINGS_RU_ADD = '''    <string name="workout_stat_speed_label">Ср. скорость</string>
    <string name="workout_stat_calories_label">Калории</string>
    <string name="workout_stat_elevation_label">Набор</string>
    <string name="workout_stat_steps_label">Шаги</string>
    <string name="workout_stat_started_label">Начало</string>
    <string name="workout_stat_ended_label">Финиш</string>
    <string name="workout_stat_swim_pace_label">Темп / 100 м</string>
    <string name="workout_speed_value">%1$s км/ч</string>
    <string name="workout_calories_value">%1$d ккал</string>
    <string name="workout_elevation_value">%1$d м</string>
    <string name="workout_swim_pace_value">%1$s /100 м</string>
'''

VERIFY_TARGET = r'''#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        errors.append(f"Missing {rel}")
        return ""
    return path.read_text(encoding="utf-8")

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
cache = read("app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt")
vm = read("app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
nav = read("app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt")
strings_en = read("app/src/main/res/values/strings.xml")
strings_ru = read("app/src/main/res/values-ru/strings.xml")
app_gradle = read("app/build.gradle.kts")

for field in ["activeCaloriesKcal: Double?", "elevationMeters: Double?", "steps: Long?"]:
    require(field in google, f"Workout metric field missing: {field}")
require("SessionMetricAccumulator" in google, "bulk workout metric accumulator missing")
require("displayedWorkouts = workouts.take(2)" in google, "metric attribution is not bounded to displayed workouts")
require("overlapFraction" in google, "time-overlap attribution helper missing")
require("DashboardActivityWindow" in google, "dashboard activity result wrapper missing")
require("activeCaloriesKcal = metrics.activeCaloriesKcal" in google, "calories are not attributed to workouts")
require("elevationMeters = metrics.elevationMeters" in google, "elevation is not attributed to workouts")
require("steps = metrics.steps.toLong()" in google, "steps are not attributed to workouts")

for field in ["activeCaloriesKcal", "elevationMeters", 'w.steps?.let { put("steps", it) }']:
    require(field in cache, f"cached workout metric missing: {field}")
require("private const val KEY_SNAPSHOT_DATA_CHANGED_AT_MS" in cache, "data-changed timestamp key missing")
require("val dataChangedAtMs" in cache, "CachedSnapshot dataChangedAtMs missing")
require("previous?.snapshot == snapshot" in cache, "cache does not preserve timestamp for identical data")
require("KEY_SNAPSHOT_SAVED_AT_MS" in cache, "cache freshness timestamp must remain intact")
require("lastUpdatedAtMs = cached.dataChangedAtMs" in vm, "cold start does not use data-change time")
require("val dataChangedAtMs = snapshotCache.save(snapshot)" in vm, "live load does not get data-change time")
require("lastUpdatedAtMs = dataChangedAtMs" in vm, "UI freshness still uses app-open wall clock")
require("lastUpdatedAtMs = System.currentTimeMillis()" not in vm, "app-open timestamp bug remains")

require("workoutMetricDisplays" in shell, "type-aware workout metrics missing")
for marker in [
    "EXERCISE_TYPE_RUNNING", "EXERCISE_TYPE_WALKING", "EXERCISE_TYPE_BIKING",
    "EXERCISE_TYPE_HIKING", "EXERCISE_TYPE_SWIMMING_POOL", "EXERCISE_TYPE_STRENGTH_TRAINING",
    "workout_stat_speed_label", "workout_stat_calories_label", "workout_stat_elevation_label"
]:
    require(marker in shell, f"workout UI marker missing: {marker}")
require("metrics.take(4).chunked(2)" in shell, "workout cards are not capped to four metrics")
require("state.lastUpdatedAtMs" in shell, "header does not use displayed-data freshness")
require("syncState.lastSyncTime" not in shell, "header still depends on sync-completion clock")

require("Compact August v3 navigation dock" in nav, "new navigation dock missing")
require("text = label" in nav, "destination labels are not persistently rendered")
require("destinationPressScale" in nav, "destination press motion missing")
require("syncPressRotation" in nav, "sync press rotation missing")
require("AugustColor.LimeActive" in nav, "sync active state missing")
require("Role.Tab" in nav and "Role.Button" in nav, "navigation semantics missing")
require("navigationBarsPadding()" in nav, "gesture-navigation inset handling missing")
require("dev.chrisbanes.haze" not in nav and "dev.chrisbanes.haze" not in app_gradle, "Haze was reintroduced")

for key in [
    "workout_stat_speed_label", "workout_stat_calories_label", "workout_stat_elevation_label",
    "workout_stat_steps_label", "workout_stat_started_label", "workout_stat_ended_label",
    "workout_stat_swim_pace_label", "workout_speed_value", "workout_calories_value",
    "workout_elevation_value", "workout_swim_pace_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

for forbidden in ["HeartRateRecord", "SleepSessionRecord", "OxygenSaturationRecord"]:
    require(forbidden not in google, f"new out-of-scope health category leaked in: {forbidden}")

if errors:
    print("BitLut workout/nav/freshness verification FAILED:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut workout/nav/freshness static verification passed.")
'''


def patch_google() -> None:
    text = read(GOOGLE)
    text = replace_once(text, ACTIVITY_SESSION_OLD, ACTIVITY_SESSION_NEW, "ActivitySessionData metrics")

    old_snapshot = '''            val recentWorkouts = readRecentWorkouts(200)
            val dailyActivity = readDailyActivitySummaries(
                client = client,
                daysBack = DASHBOARD_HISTORY_DAYS,
                workouts = recentWorkouts
            )
            val today = LocalDate.now()
            val todayActivity = dailyActivity.firstOrNull { it.date == today }

            GoogleDashboardSnapshot(
                stepsToday = todayActivity?.steps ?: 0L,
                distanceMeters = todayActivity?.distanceMeters ?: 0.0,
                caloriesKcal = todayActivity?.caloriesKcal ?: 0.0,
                workoutMinutesToday = todayActivity?.workoutMinutes ?: 0L,
                activeHoursToday = 0,
                recentWorkouts = recentWorkouts.take(2),
                dailyActivity = dailyActivity
            )'''
    new_snapshot = '''            val recentWorkouts = readRecentWorkouts(200)
            val activityWindow = readDailyActivitySummaries(
                client = client,
                daysBack = DASHBOARD_HISTORY_DAYS,
                workouts = recentWorkouts
            )
            val today = LocalDate.now()
            val todayActivity = activityWindow.dailyActivity.firstOrNull { it.date == today }

            GoogleDashboardSnapshot(
                stepsToday = todayActivity?.steps ?: 0L,
                distanceMeters = todayActivity?.distanceMeters ?: 0.0,
                caloriesKcal = todayActivity?.caloriesKcal ?: 0.0,
                workoutMinutesToday = todayActivity?.workoutMinutes ?: 0L,
                activeHoursToday = 0,
                recentWorkouts = activityWindow.workouts.take(2),
                dailyActivity = activityWindow.dailyActivity
            )'''
    text = replace_once(text, old_snapshot, new_snapshot, "dashboard activity window")

    start = '''    /**
     * Reads the already-approved activity records once for a bounded window'''
    end = '''    /**
     * Week-over-week comparison for the three activity-only metrics BitLut'''
    text = replace_between(text, start, end, DAILY_WINDOW_NEW, "bulk daily/session metric reader")
    write_if_changed(GOOGLE, text)


def patch_cache() -> None:
    text = read(CACHE)
    start = '''    /** Persists [snapshot] plus the moment it was captured (epoch millis). */
    fun save(snapshot: GoogleDashboardSnapshot) {'''
    end = '''    /** Returns the last cached snapshot, or null if none was ever saved or it is corrupt. */'''
    text = replace_between(text, start, end, CACHE_SAVE_NEW, "cache timestamps")

    old_load = '''        val savedAtMs = prefs.getLong(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS), 0L)
        return try {
            val snapshot = snapshotFromJson(JSONObject(raw))
            CachedSnapshot(snapshot = snapshot, savedAtMs = savedAtMs)'''
    new_load = '''        val savedAtMs = prefs.getLong(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS), 0L)
        val dataChangedAtMs = prefs.getLong(sourceKey(KEY_SNAPSHOT_DATA_CHANGED_AT_MS), savedAtMs)
        return try {
            val snapshot = snapshotFromJson(JSONObject(raw))
            CachedSnapshot(snapshot = snapshot, savedAtMs = savedAtMs, dataChangedAtMs = dataChangedAtMs)'''
    text = replace_once(text, old_load, new_load, "load dataChangedAtMs")

    old_clear = '''            .remove(sourceKey(KEY_SNAPSHOT_JSON))
            .remove(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS))
            .apply()'''
    new_clear = '''            .remove(sourceKey(KEY_SNAPSHOT_JSON))
            .remove(sourceKey(KEY_SNAPSHOT_SAVED_AT_MS))
            .remove(sourceKey(KEY_SNAPSHOT_DATA_CHANGED_AT_MS))
            .apply()'''
    text = replace_once(text, old_clear, new_clear, "clear dataChangedAtMs")

    old_json = '''                put("exerciseType", w.exerciseType)
                w.distanceMeters?.let { put("distanceMeters", it) }'''
    new_json = '''                put("exerciseType", w.exerciseType)
                w.distanceMeters?.let { put("distanceMeters", it) }
                w.activeCaloriesKcal?.let { put("activeCaloriesKcal", it) }
                w.elevationMeters?.let { put("elevationMeters", it) }
                w.steps?.let { put("steps", it) }'''
    if 'w.activeCaloriesKcal?.let { put("activeCaloriesKcal", it) }' not in text:
        text = replace_once(text, old_json, new_json, "cache workout metrics")
    else:
        print("   already applied: cache workout metrics")

    old_from = '''                    ),
                    distanceMeters = if (item.has("distanceMeters")) item.optDouble("distanceMeters") else null
                )'''
    new_from = '''                    ),
                    distanceMeters = if (item.has("distanceMeters")) item.optDouble("distanceMeters") else null,
                    activeCaloriesKcal = if (item.has("activeCaloriesKcal")) item.optDouble("activeCaloriesKcal") else null,
                    elevationMeters = if (item.has("elevationMeters")) item.optDouble("elevationMeters") else null,
                    steps = if (item.has("steps")) item.optLong("steps") else null
                )'''
    text = replace_once(text, old_from, new_from, "restore workout metrics")

    old_keys = '''        private const val KEY_SNAPSHOT_JSON = "dashboard_snapshot_cache_json"
        private const val KEY_SNAPSHOT_SAVED_AT_MS = "dashboard_snapshot_cache_saved_at_ms"'''
    new_keys = '''        private const val KEY_SNAPSHOT_JSON = "dashboard_snapshot_cache_json"
        private const val KEY_SNAPSHOT_SAVED_AT_MS = "dashboard_snapshot_cache_saved_at_ms"
        private const val KEY_SNAPSHOT_DATA_CHANGED_AT_MS = "dashboard_snapshot_data_changed_at_ms"'''
    if "private const val KEY_SNAPSHOT_DATA_CHANGED_AT_MS" not in text:
        text = replace_once(text, old_keys, new_keys, "cache data-change key")
    else:
        print("   already applied: cache data-change key")

    old_cached = '''/** A cached snapshot plus when it was captured, so the UI can show e.g. "updated 4m ago". */
data class CachedSnapshot(
    val snapshot: GoogleDashboardSnapshot,
    val savedAtMs: Long
)'''
    new_cached = '''/** Cache transport freshness and semantic data freshness are intentionally separate. */
data class CachedSnapshot(
    val snapshot: GoogleDashboardSnapshot,
    val savedAtMs: Long,
    val dataChangedAtMs: Long
)'''
    text = replace_once(text, old_cached, new_cached, "CachedSnapshot data-change time")
    write_if_changed(CACHE, text)


def patch_dashboard_vm() -> None:
    text = read(DASHBOARD_VM)
    text = replace_once(text, "lastUpdatedAtMs = cached.savedAtMs", "lastUpdatedAtMs = cached.dataChangedAtMs", "cold-start data freshness")
    old = '''                    snapshotCache.save(snapshot)
                    updateAchievementsFor(snapshot)
                    readAchievementsIntoState(
                        current.withSnapshot(snapshot).copy(
                            hasPermissions = true,
                            permissionsChecked = true,
                            isFromCache = false,
                            lastUpdatedAtMs = System.currentTimeMillis()
                        )
                    )'''
    new = '''                    val dataChangedAtMs = snapshotCache.save(snapshot)
                    updateAchievementsFor(snapshot)
                    readAchievementsIntoState(
                        current.withSnapshot(snapshot).copy(
                            hasPermissions = true,
                            permissionsChecked = true,
                            isFromCache = false,
                            lastUpdatedAtMs = dataChangedAtMs
                        )
                    )'''
    text = replace_once(text, old, new, "live data freshness")
    write_if_changed(DASHBOARD_VM, text)


def patch_shell() -> None:
    text = read(SHELL)
    old_call = '''                MainTab.Today -> SummaryScreen(
                    palette, dashboardState, syncState.selectedDataSource, syncState.lastSyncTime, onRefresh, wrappedOnRequestGoogle,
                    onEditLayout = { showCardLayoutEditor = true },
                    cardLayoutVersion = cardLayoutVersion
                )'''
    new_call = '''                MainTab.Today -> SummaryScreen(
                    palette, dashboardState, syncState.selectedDataSource, onRefresh, wrappedOnRequestGoogle,
                    onEditLayout = { showCardLayoutEditor = true },
                    cardLayoutVersion = cardLayoutVersion
                )'''
    text = replace_once(text, old_call, new_call, "SummaryScreen freshness source")

    old_sig = '''    state: DashboardUiState,
    dataSource: HealthDataSource,
    lastSyncTime: String,
    onRefresh: () -> Unit,'''
    new_sig = '''    state: DashboardUiState,
    dataSource: HealthDataSource,
    onRefresh: () -> Unit,'''
    text = replace_once(text, old_sig, new_sig, "SummaryScreen signature")

    old_trailing = '''                trailing = formatDashboardSourceStatus(dataSource, lastSyncTime),'''
    new_trailing = '''                trailing = formatDashboardSourceStatus(
                    source = dataSource,
                    lastUpdatedAtMs = state.lastUpdatedAtMs,
                    isFromCache = state.isFromCache
                ),'''
    text = replace_once(text, old_trailing, new_trailing, "truthful header freshness")

    start = '''/**
 * Premium summary of one of the two most recent exercise sessions.'''
    end = '''private fun formatWorkoutDateTime(epochMs: Long): String ='''
    text = replace_between(text, start, end, WORKOUT_UI_NEW, "type-aware workout cards")

    old_status = '''@Composable
private fun formatDashboardSourceStatus(source: HealthDataSource, lastSyncTime: String): String {
    val sourceName = when (source) {
        HealthDataSource.HUAWEI_HEALTH -> stringResource(R.string.data_source_huawei_title)
        HealthDataSource.GOOGLE_FIT -> stringResource(R.string.data_source_google_fit_title)
    }
    val whenText = lastSyncTime.takeIf { it.isNotBlank() && it != "sync_no_data" }
        ?: stringResource(R.string.no_data_short)
    return "$sourceName · $whenText"
}'''
    new_status = '''@Composable
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
}'''
    text = replace_once(text, old_status, new_status, "source status freshness")
    write_if_changed(SHELL, text)


def patch_nav() -> None:
    text = read(NAV)
    if text == NAV_TARGET:
        print(f"   unchanged: {NAV}")
        return
    required = ["internal fun AugustBottomNav(", "private fun AugustRefreshButton(", "private fun AugustNavButton("]
    if not all(marker in text for marker in required):
        die("GlassNavigation.kt has drifted from the August v3 build-fix baseline; refusing full rewrite")
    if "dev.chrisbanes.haze" in text:
        die("Haze unexpectedly exists in current navigation; resolve baseline before this sprint")
    write_if_changed(NAV, NAV_TARGET)


def patch_strings(path: Path, additions: str) -> None:
    text = read(path)
    if 'name="workout_stat_speed_label"' in text:
        print(f"   unchanged: {path} (new workout strings already present)")
        return
    match = re.search(r'(?m)^    <string name="workout_pace_value">.*?</string>\n', text)
    if match is None:
        die(f"Could not locate workout string anchor in {path}")
    anchor = match.group(0)
    text = text[:match.end()] + additions + text[match.end():]
    write_if_changed(path, text)


def write_verifier() -> None:
    write_if_changed(VERIFY, VERIFY_TARGET)
    (ROOT / VERIFY).chmod(0o755)


def apply_patch() -> None:
    for rel in TARGETS:
        if not (ROOT / rel).exists():
            die(f"Run from the BitLut repository root; missing {rel}")
    backup_targets()
    print("==> Enriching workout data from existing activity streams")
    patch_google()
    print("==> Separating cache freshness from semantic data freshness")
    patch_cache()
    patch_dashboard_vm()
    print("==> Rendering type-aware four-metric workout cards")
    patch_shell()
    patch_strings(STRINGS_EN, STRINGS_EN_ADD)
    patch_strings(STRINGS_RU, STRINGS_RU_ADD)
    print("==> Rebuilding bottom navigation as an expressive labeled dock")
    patch_nav()
    print("==> Writing focused sprint verifier")
    write_verifier()
    print("==> Patch applied")


def run_command(command: list[str]) -> None:
    print("==>", " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        die(f"Command failed with exit code {result.returncode}: {' '.join(command)}")


def verify(run_build: bool) -> None:
    if not (ROOT / VERIFY).exists():
        write_verifier()
    run_command([sys.executable, str(VERIFY)])
    if run_build:
        gradlew = ROOT / "gradlew"
        if not gradlew.exists():
            die("gradlew not found")
        gradlew.chmod(gradlew.stat().st_mode | 0o111)
        run_command([
            "./gradlew", ":app:assembleDebug", "--no-daemon", "--max-workers=1", "--no-watch-fs", "--console=plain",
            '-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8',
            "-Pkotlin.compiler.execution.strategy=in-process",
        ])
        print("==> Codespaces build verification passed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--no-build", action="store_true", help="With --verify, run static checks only")
    args = parser.parse_args()
    if not args.apply and not args.verify:
        parser.error("Choose --apply, --verify, or both")
    if args.apply:
        apply_patch()
    if args.verify:
        verify(run_build=not args.no_build)


if __name__ == "__main__":
    main()
