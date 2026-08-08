#!/usr/bin/env python3
"""
BitLut patch: Phase 1 features -- pace/distance on workout cards + workout
type filter.

1. Pace + distance on workout cards (item 1 of the agreed Phase 1 plan).
   ActivitySessionData gains distanceMeters. GoogleHealthManager computes it
   with ONE bulk DistanceRecord read per sync (not one query per session --
   that would multiply into up to `limit` extra Health Connect calls and
   risks the rate-limit cascade documented in CLAUDE.md Gotcha 4), then
   locally attributes each record's meters to whichever session(s) it
   overlaps in time. No new Huawei scope or Health Connect permission --
   READ_DISTANCE is already granted, this only reads it differently.

   The workout card itself is redesigned to a max of 4 stat slots per your
   instruction: When + Duration always show, Distance + Pace only show when
   the session actually has a meaningful distance (pace itself is only
   computed above 500m, to avoid a nonsense value from GPS drift on a
   strength/yoga session with no real distance).

2. Workout type / minimum-duration filter (item 3). New WorkoutFilterPrefs
   (same SharedPreferences pattern as GoalPrefs) applied in
   GoogleHealthManager.writeSnapshot() right before workout sessions are
   written -- steps/distance/calories for that time are untouched, they
   come from Huawei's separate continuous streams. Settings UI added as
   its own self-contained section (local state + direct SharedPreferences
   reads via WorkoutFilterPrefs), so this does NOT thread new state through
   DashboardViewModel/MainActivity/FinalBitLutShell -- keeps the change
   contained to GoogleHealthManager + one new file + one Settings section,
   matching the "low risk" scope this was paired on.

Assumes the Elevation-card-removal patch has already been run (or run it
right after this one -- the two don't overlap and are safe in either order).

Run from the repo root:
    python3 add_workout_pace_and_filter.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

GHM = "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
CACHE = "app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt"
UI = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
STRINGS_EN = "app/src/main/res/values/strings.xml"
STRINGS_RU = "app/src/main/res/values-ru/strings.xml"
FILTER_PREFS = "app/src/main/java/com/openhealth/sync/config/WorkoutFilterPrefs.kt"

TARGET_FILES_MUST_EXIST = [GHM, CACHE, UI, STRINGS_EN, STRINGS_RU]


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
    if not src.exists():
        return
    dst = BACKUP_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def apply_edit(rel_path: str, old: str, new: str, desc: str) -> bool:
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    old_count = text.count(old)
    if old_count == 0:
        if text.count(new) >= 1:
            print(f"   (already applied, skipping) {desc}")
            return False
        die(f"Anchor not found for '{desc}' in {rel_path}, and patched text "
            f"is also absent. File may have changed since this script was "
            f"written -- aborting rather than guessing.")

    if old_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {old_count}. Aborting rather than guessing "
            f"which one to patch.")

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def apply_insertion(rel_path: str, anchor: str, new_with_anchor: str, unique_marker: str, desc: str) -> bool:
    """For edits that insert new text immediately before an unchanged anchor.
    `anchor` stays intact as a suffix of `new_with_anchor`, so checking
    anchor-count-first (like apply_edit does) would never see it as "gone"
    and would reapply forever. Idempotency here is decided by
    `unique_marker`, a string that only exists once the insertion has
    happened.
    """
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"   (already applied, skipping) {desc}")
        return False

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {anchor_count}. Aborting rather than "
            f"guessing which one to patch.")

    path.write_text(text.replace(anchor, new_with_anchor, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def create_workout_filter_prefs() -> None:
    path = ROOT / FILTER_PREFS
    if path.exists():
        print(f"   (already exists, skipping) create {FILTER_PREFS}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '''package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.remote.HuaweiConfig

/**
 * Lets the person exclude specific workout types, or workouts shorter than a
 * minimum duration, from being written to Health Connect as discrete
 * ExerciseSessionRecord entries -- e.g. "don't sync walks under 5 minutes".
 *
 * This only filters the workout SESSION entries themselves. Steps, distance,
 * and calories for that same time window come from Huawei's separate
 * continuous data streams (see GoogleHealthManager.writeSnapshot()) and are
 * completely unaffected by this filter -- a filtered-out walk still counts
 * toward the day's step total, it just doesn't show up as its own workout
 * card. No new Huawei scope or Health Connect permission is involved: this
 * is purely app-side filtering of data that's already being read.
 *
 * Defaults to "everything syncs" (0-minute minimum, nothing excluded), so
 * existing installs see no behavior change until the person explicitly
 * opens Settings and changes something.
 */
class WorkoutFilterPrefs(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun minDurationMinutes(): Int = prefs.getInt(KEY_MIN_DURATION_MINUTES, 0)

    fun setMinDurationMinutes(value: Int) {
        require(value >= 0) { "Minimum duration cannot be negative" }
        prefs.edit().putInt(KEY_MIN_DURATION_MINUTES, value).apply()
    }

    fun excludedExerciseTypes(): Set<Int> =
        prefs.getStringSet(KEY_EXCLUDED_EXERCISE_TYPES, emptySet())
            .orEmpty()
            .mapNotNull { it.toIntOrNull() }
            .toSet()

    fun setExcludedExerciseTypes(types: Set<Int>) {
        prefs.edit()
            .putStringSet(KEY_EXCLUDED_EXERCISE_TYPES, types.map { it.toString() }.toSet())
            .apply()
    }

    /** Applied right before a freshly-read batch of sessions is written to Health Connect. */
    fun apply(sessions: List<ActivitySessionData>): List<ActivitySessionData> {
        val minDurationMs = minDurationMinutes() * 60_000L
        val excluded = excludedExerciseTypes()
        if (minDurationMs <= 0L && excluded.isEmpty()) return sessions
        return sessions.filter { session ->
            val durationMs = session.endTimeMs - session.startTimeMs
            durationMs >= minDurationMs && session.exerciseType !in excluded
        }
    }

    companion object {
        private const val KEY_MIN_DURATION_MINUTES = "workout_filter_min_duration_minutes"
        private const val KEY_EXCLUDED_EXERCISE_TYPES = "workout_filter_excluded_exercise_types"

        /** Preset chips offered in Settings for the minimum-duration filter. */
        val MIN_DURATION_PRESETS_MINUTES = listOf(0, 5, 10, 15, 30)
    }
}
''',
        encoding="utf-8",
    )
    print(f"   created: {FILTER_PREFS}")


def patch_google_health_manager() -> None:
    print("==> GoogleHealthManager.kt: distance-per-session + workout filter")

    apply_edit(
        GHM,
        old='data class ActivitySessionData(\n'
            '    val startTimeMs: Long,\n'
            '    val endTimeMs: Long,\n'
            '    val title: String = "Huawei activity",\n'
            '    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT\n'
            ')',
        new='data class ActivitySessionData(\n'
            '    val startTimeMs: Long,\n'
            '    val endTimeMs: Long,\n'
            '    val title: String = "Huawei activity",\n'
            '    val exerciseType: Int = ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT,\n'
            '    val distanceMeters: Double? = null\n'
            ')',
        desc="add distanceMeters to ActivitySessionData",
    )

    apply_edit(
        GHM,
        old='class GoogleHealthManager(\n'
            '    private val context: Context,\n'
            '    private val dataSourcePrefs: DataSourcePrefs = DataSourcePrefs(context)\n'
            ') : HealthConnectManager {',
        new='class GoogleHealthManager(\n'
            '    private val context: Context,\n'
            '    private val dataSourcePrefs: DataSourcePrefs = DataSourcePrefs(context),\n'
            '    private val workoutFilterPrefs: com.openhealth.sync.config.WorkoutFilterPrefs = com.openhealth.sync.config.WorkoutFilterPrefs(context)\n'
            ') : HealthConnectManager {',
        desc="add WorkoutFilterPrefs dependency to GoogleHealthManager",
    )

    apply_edit(
        GHM,
        old='            "activitySessions" to writeActivitySessionsBatch(snapshot.activities)',
        new='            "activitySessions" to writeActivitySessionsBatch(workoutFilterPrefs.apply(snapshot.activities))',
        desc="apply workout filter before writing activity sessions",
    )

    apply_edit(
        GHM,
        old='    suspend fun readRecentWorkouts(limit: Int = 5): List<ActivitySessionData> {\n'
            '        val client = resolveClient() ?: return emptyList()\n'
            '        return try {\n'
            '            val start = LocalDate.now().minusDays(30).atStartOfDay(ZoneId.systemDefault()).toInstant()\n'
            '            client.readRecords(\n'
            '                ReadRecordsRequest(\n'
            '                    recordType = ExerciseSessionRecord::class,\n'
            '                    timeRangeFilter = TimeRangeFilter.between(start, Instant.now()),\n'
            '                    dataOriginFilter = selectedDataOrigins()\n'
            '                )\n'
            '            ).records\n'
            '                .sortedByDescending { it.startTime }\n'
            '                .take(limit)\n'
            '                .map {\n'
            '                    ActivitySessionData(\n'
            '                        startTimeMs = it.startTime.toEpochMilli(),\n'
            '                        endTimeMs = it.endTime.toEpochMilli(),\n'
            '                        title = workoutDisplayName(it.title, it.exerciseType),\n'
            '                        exerciseType = it.exerciseType\n'
            '                    )\n'
            '                }\n'
            '        } catch (e: CancellationException) {\n'
            '            throw e\n'
            '        } catch (e: Exception) {\n'
            '            AppLogger.e(TAG, "readRecentWorkouts failed: ${e.message}", e)\n'
            '            emptyList()\n'
            '        }\n'
            '    }',
        new='    suspend fun readRecentWorkouts(limit: Int = 5): List<ActivitySessionData> {\n'
            '        val client = resolveClient() ?: return emptyList()\n'
            '        return try {\n'
            '            val start = LocalDate.now().minusDays(30).atStartOfDay(ZoneId.systemDefault()).toInstant()\n'
            '            val end = Instant.now()\n'
            '            val sessions = client.readRecords(\n'
            '                ReadRecordsRequest(\n'
            '                    recordType = ExerciseSessionRecord::class,\n'
            '                    timeRangeFilter = TimeRangeFilter.between(start, end),\n'
            '                    dataOriginFilter = selectedDataOrigins()\n'
            '                )\n'
            '            ).records\n'
            '                .sortedByDescending { it.startTime }\n'
            '                .take(limit)\n'
            '\n'
            '            val distanceBySessionId = if (sessions.isEmpty()) emptyMap() else readDistanceForSessions(client, sessions, start, end)\n'
            '\n'
            '            sessions.map {\n'
            '                ActivitySessionData(\n'
            '                    startTimeMs = it.startTime.toEpochMilli(),\n'
            '                    endTimeMs = it.endTime.toEpochMilli(),\n'
            '                    title = workoutDisplayName(it.title, it.exerciseType),\n'
            '                    exerciseType = it.exerciseType,\n'
            '                    distanceMeters = distanceBySessionId[it.metadata.id]\n'
            '                )\n'
            '            }\n'
            '        } catch (e: CancellationException) {\n'
            '            throw e\n'
            '        } catch (e: Exception) {\n'
            '            AppLogger.e(TAG, "readRecentWorkouts failed: ${e.message}", e)\n'
            '            emptyList()\n'
            '        }\n'
            '    }\n'
            '\n'
            '    /**\n'
            '     * Health Connect\'s ExerciseSessionRecord carries no distance of its own --\n'
            '     * only DistanceRecord does, as a separate stream. Computing a per-workout\n'
            '     * distance (for the pace shown on the workout card) by querying\n'
            '     * DistanceRecord once per session would multiply into up to `limit` extra\n'
            '     * Health Connect calls per sync, which risks the rate-limit cascade\n'
            '     * documented in CLAUDE.md Gotcha 4. Instead this reads DistanceRecord\n'
            '     * ONCE for the whole window and locally attributes each record\'s meters\n'
            '     * to whichever session(s) it overlaps in time, weighted by the fraction\n'
            '     * of the record\'s own duration that falls inside that session. Huawei\'s\n'
            '     * distance is written from a continuous delta stream (see\n'
            '     * HuaweiHealthManager.readDistance), not one blob per day, so this\n'
            '     * attribution is meaningfully accurate rather than smearing a whole\n'
            '     * day\'s distance onto one short workout.\n'
            '     */\n'
            '    private suspend fun readDistanceForSessions(\n'
            '        client: HealthConnectClient,\n'
            '        sessions: List<ExerciseSessionRecord>,\n'
            '        start: Instant,\n'
            '        end: Instant\n'
            '    ): Map<String, Double> {\n'
            '        val distanceRecords = try {\n'
            '            client.readRecords(\n'
            '                ReadRecordsRequest(\n'
            '                    recordType = DistanceRecord::class,\n'
            '                    timeRangeFilter = TimeRangeFilter.between(start, end),\n'
            '                    dataOriginFilter = selectedDataOrigins()\n'
            '                )\n'
            '            ).records\n'
            '        } catch (e: CancellationException) {\n'
            '            throw e\n'
            '        } catch (e: Exception) {\n'
            '            AppLogger.e(TAG, "readDistanceForSessions failed: ${e.message}", e)\n'
            '            return emptyMap()\n'
            '        }\n'
            '\n'
            '        if (distanceRecords.isEmpty()) return emptyMap()\n'
            '\n'
            '        val result = HashMap<String, Double>(sessions.size)\n'
            '        for (session in sessions) {\n'
            '            var totalMeters = 0.0\n'
            '            for (record in distanceRecords) {\n'
            '                val overlapStart = maxOf(record.startTime, session.startTime)\n'
            '                val overlapEnd = minOf(record.endTime, session.endTime)\n'
            '                if (!overlapEnd.isAfter(overlapStart)) continue\n'
            '                val recordDurationMs = (record.endTime.toEpochMilli() - record.startTime.toEpochMilli()).coerceAtLeast(1L)\n'
            '                val overlapMs = overlapEnd.toEpochMilli() - overlapStart.toEpochMilli()\n'
            '                val overlapFraction = overlapMs.toDouble() / recordDurationMs.toDouble()\n'
            '                totalMeters += record.distance.inMeters * overlapFraction\n'
            '            }\n'
            '            if (totalMeters > 0.0) {\n'
            '                result[session.metadata.id] = totalMeters\n'
            '            }\n'
            '        }\n'
            '        return result\n'
            '    }',
        desc="compute per-session distance via bulk DistanceRecord read + overlap-sum",
    )


def patch_snapshot_cache() -> None:
    print("==> DashboardSnapshotCache.kt: persist distanceMeters")

    apply_edit(
        CACHE,
        old='            arr.put(JSONObject().apply {\n'
            '                put("startTimeMs", w.startTimeMs)\n'
            '                put("endTimeMs", w.endTimeMs)\n'
            '                put("title", w.title)\n'
            '                put("exerciseType", w.exerciseType)\n'
            '            })',
        new='            arr.put(JSONObject().apply {\n'
            '                put("startTimeMs", w.startTimeMs)\n'
            '                put("endTimeMs", w.endTimeMs)\n'
            '                put("title", w.title)\n'
            '                put("exerciseType", w.exerciseType)\n'
            '                w.distanceMeters?.let { put("distanceMeters", it) }\n'
            '            })',
        desc="write distanceMeters into cached workout JSON when present",
    )

    apply_edit(
        CACHE,
        old='                    exerciseType = item.optInt(\n'
            '                        "exerciseType",\n'
            '                        androidx.health.connect.client.records.ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT\n'
            '                    )\n'
            '                )',
        new='                    exerciseType = item.optInt(\n'
            '                        "exerciseType",\n'
            '                        androidx.health.connect.client.records.ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT\n'
            '                    ),\n'
            '                    distanceMeters = if (item.has("distanceMeters")) item.optDouble("distanceMeters") else null\n'
            '                )',
        desc="read distanceMeters back out of cached workout JSON",
    )


def patch_ui() -> None:
    print("==> FinalBitLutShell.kt: redesigned workout card (max 4 stats) + filter settings UI")

    apply_edit(
        UI,
        old='                Spacer(Modifier.height(5.dp))\n'
            '                if (session != null && durationMinutes != null) {\n'
            '                    Row(verticalAlignment = Alignment.CenterVertically) {\n'
            '                        Text(\n'
            '                            text = formatWorkoutDateTime(session.startTimeMs),\n'
            '                            color = palette.secondaryText,\n'
            '                            fontWeight = FontWeight.SemiBold,\n'
            '                            fontSize = 12.sp,\n'
            '                            maxLines = 1,\n'
            '                            overflow = TextOverflow.Ellipsis,\n'
            '                            modifier = Modifier.weight(1f)\n'
            '                        )\n'
            '                        Spacer(Modifier.width(8.dp))\n'
            '                        Text(\n'
            '                            text = stringResource(R.string.workout_total_minutes, durationMinutes),\n'
            '                            color = accent,\n'
            '                            fontWeight = FontWeight.Black,\n'
            '                            fontSize = 12.sp,\n'
            '                            maxLines = 1\n'
            '                        )\n'
            '                    }\n'
            '                } else {\n'
            '                    Text(\n'
            '                        text = emptyText,\n'
            '                        color = palette.secondaryText,\n'
            '                        fontWeight = FontWeight.Medium,\n'
            '                        fontSize = 12.sp,\n'
            '                        lineHeight = 17.sp\n'
            '                    )\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '}\n'
            '\n'
            'private fun formatWorkoutDateTime(epochMs: Long): String =',
        new='                Spacer(Modifier.height(9.dp))\n'
            '                if (session != null && durationMinutes != null) {\n'
            '                    val distanceKm = session.distanceMeters?.takeIf { it > 0.0 }?.let { it / 1000.0 }\n'
            '                    val paceMinutesPerKm = if (\n'
            '                        durationMinutes > 0 &&\n'
            '                        session.distanceMeters != null &&\n'
            '                        session.distanceMeters >= MIN_DISTANCE_METERS_FOR_PACE\n'
            '                    ) {\n'
            '                        durationMinutes.toDouble() / (session.distanceMeters / 1000.0)\n'
            '                    } else {\n'
            '                        null\n'
            '                    }\n'
            '                    WorkoutStatsGrid(\n'
            '                        palette = palette,\n'
            '                        accent = accent,\n'
            '                        whenText = formatWorkoutDateTime(session.startTimeMs),\n'
            '                        durationMinutes = durationMinutes,\n'
            '                        distanceKm = distanceKm,\n'
            '                        paceMinutesPerKm = paceMinutesPerKm\n'
            '                    )\n'
            '                } else {\n'
            '                    Text(\n'
            '                        text = emptyText,\n'
            '                        color = palette.secondaryText,\n'
            '                        fontWeight = FontWeight.Medium,\n'
            '                        fontSize = 12.sp,\n'
            '                        lineHeight = 17.sp\n'
            '                    )\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '}\n'
            '\n'
            '/**\n'
            ' * Up to 4 stat slots for a workout card, matching the "no more than 4 main\n'
            ' * parameters" limit: when + duration are always shown (every session has\n'
            ' * them), distance + pace only appear when the session actually has a\n'
            ' * meaningful distance -- strength training, yoga, etc. simply show the\n'
            ' * first two and skip the second row entirely, rather than inventing a\n'
            ' * "0.0 km" that isn\'t real.\n'
            ' */\n'
            '@Composable\n'
            'private fun WorkoutStatsGrid(\n'
            '    palette: BitPalette,\n'
            '    accent: Color,\n'
            '    whenText: String,\n'
            '    durationMinutes: Long,\n'
            '    distanceKm: Double?,\n'
            '    paceMinutesPerKm: Double?\n'
            ') {\n'
            '    Column {\n'
            '        Row(modifier = Modifier.fillMaxWidth()) {\n'
            '            WorkoutStat(\n'
            '                modifier = Modifier.weight(1f),\n'
            '                palette = palette,\n'
            '                valueColor = palette.text,\n'
            '                label = stringResource(R.string.workout_stat_when_label),\n'
            '                value = whenText\n'
            '            )\n'
            '            WorkoutStat(\n'
            '                modifier = Modifier.weight(1f),\n'
            '                palette = palette,\n'
            '                valueColor = accent,\n'
            '                label = stringResource(R.string.workout_stat_duration_label),\n'
            '                value = stringResource(R.string.workout_duration_value, durationMinutes)\n'
            '            )\n'
            '        }\n'
            '        if (distanceKm != null || paceMinutesPerKm != null) {\n'
            '            Spacer(Modifier.height(10.dp))\n'
            '            Row(modifier = Modifier.fillMaxWidth()) {\n'
            '                WorkoutStat(\n'
            '                    modifier = Modifier.weight(1f),\n'
            '                    palette = palette,\n'
            '                    valueColor = accent,\n'
            '                    label = stringResource(R.string.workout_stat_distance_label),\n'
            '                    value = distanceKm?.let { stringResource(R.string.distance_today_value, formatOneDecimal(it)) }\n'
            '                        ?: stringResource(R.string.no_data_short)\n'
            '                )\n'
            '                WorkoutStat(\n'
            '                    modifier = Modifier.weight(1f),\n'
            '                    palette = palette,\n'
            '                    valueColor = accent,\n'
            '                    label = stringResource(R.string.workout_stat_pace_label),\n'
            '                    value = paceMinutesPerKm?.let { stringResource(R.string.workout_pace_value, formatPace(it)) }\n'
            '                        ?: stringResource(R.string.no_data_short)\n'
            '                )\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '}\n'
            '\n'
            '@Composable\n'
            'private fun WorkoutStat(\n'
            '    modifier: Modifier = Modifier,\n'
            '    palette: BitPalette,\n'
            '    valueColor: Color,\n'
            '    label: String,\n'
            '    value: String\n'
            ') {\n'
            '    Column(modifier = modifier) {\n'
            '        Text(\n'
            '            text = label.uppercase(Locale.getDefault()),\n'
            '            color = palette.secondaryText,\n'
            '            fontWeight = FontWeight.Black,\n'
            '            fontSize = 9.sp,\n'
            '            maxLines = 1,\n'
            '            overflow = TextOverflow.Ellipsis\n'
            '        )\n'
            '        Spacer(Modifier.height(2.dp))\n'
            '        Text(\n'
            '            text = value,\n'
            '            color = valueColor,\n'
            '            fontWeight = FontWeight.Black,\n'
            '            fontSize = 13.sp,\n'
            '            maxLines = 1,\n'
            '            overflow = TextOverflow.Ellipsis\n'
            '        )\n'
            '    }\n'
            '}\n'
            '\n'
            '/** Pace shown as "M:SS" per km, e.g. "5:32". Truncates rather than rounds -- off by at most 1 second, not worth a new import for. */\n'
            'private fun formatPace(minutesPerKm: Double): String {\n'
            '    val totalSeconds = (minutesPerKm * 60.0).toInt().coerceAtLeast(0)\n'
            '    val minutes = totalSeconds / 60\n'
            '    val seconds = totalSeconds % 60\n'
            '    return "$minutes:${seconds.toString().padStart(2, \'0\')}"\n'
            '}\n'
            '\n'
            '/** Below this, a computed pace is more noise than signal (GPS drift, a few meters of wandering before/after the real activity). */\n'
            'private const val MIN_DISTANCE_METERS_FOR_PACE = 500.0\n'
            '\n'
            'private fun formatWorkoutDateTime(epochMs: Long): String =',
        desc="redesign WorkoutRecencyCard's stats into a max-4 grid (when/duration/distance/pace)",
    )

    apply_insertion(
        UI,
        anchor='        Text(\n'
            '            text = stringResource(R.string.data_scopes_link),',
        new_with_anchor='        Text(\n'
            '            text = stringResource(R.string.workout_filter_section_title),\n'
            '            color = palette.text,\n'
            '            fontWeight = FontWeight.ExtraBold,\n'
            '            fontSize = 18.sp\n'
            '        )\n'
            '        SoftCard(palette = palette, accent = HealthAccent.activity, tintWithAccent = true) {\n'
            '            val context = LocalContext.current\n'
            '            val workoutFilterPrefs = remember { com.openhealth.sync.config.WorkoutFilterPrefs(context) }\n'
            '            var minDurationMinutes by remember { mutableStateOf(workoutFilterPrefs.minDurationMinutes()) }\n'
            '            var excludedTypes by remember { mutableStateOf(workoutFilterPrefs.excludedExerciseTypes()) }\n'
            '\n'
            '            Text(\n'
            '                text = stringResource(R.string.workout_filter_section_body),\n'
            '                color = palette.secondaryText,\n'
            '                fontWeight = FontWeight.Medium,\n'
            '                fontSize = 13.sp,\n'
            '                lineHeight = 18.sp\n'
            '            )\n'
            '            Spacer(Modifier.height(14.dp))\n'
            '            Text(\n'
            '                text = stringResource(R.string.workout_filter_min_duration_label),\n'
            '                color = palette.text,\n'
            '                fontWeight = FontWeight.Bold,\n'
            '                fontSize = 13.sp\n'
            '            )\n'
            '            Spacer(Modifier.height(8.dp))\n'
            '            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {\n'
            '                com.openhealth.sync.config.WorkoutFilterPrefs.MIN_DURATION_PRESETS_MINUTES.forEach { minutes ->\n'
            '                    val selected = minDurationMinutes == minutes\n'
            '                    Box(\n'
            '                        modifier = Modifier\n'
            '                            .clip(RoundedCornerShape(99.dp))\n'
            '                            .background(if (selected) HealthAccent.activity else palette.stroke.copy(alpha = 0.3f))\n'
            '                            .clickable {\n'
            '                                minDurationMinutes = minutes\n'
            '                                workoutFilterPrefs.setMinDurationMinutes(minutes)\n'
            '                            }\n'
            '                            .padding(horizontal = 12.dp, vertical = 7.dp)\n'
            '                    ) {\n'
            '                        Text(\n'
            '                            text = if (minutes == 0) {\n'
            '                                stringResource(R.string.workout_filter_min_duration_off)\n'
            '                            } else {\n'
            '                                stringResource(R.string.workout_filter_min_duration_value, minutes)\n'
            '                            },\n'
            '                            color = if (selected) Color.White else palette.text,\n'
            '                            fontWeight = FontWeight.Bold,\n'
            '                            fontSize = 12.sp\n'
            '                        )\n'
            '                    }\n'
            '                }\n'
            '            }\n'
            '            Spacer(Modifier.height(16.dp))\n'
            '            val categories = listOf(\n'
            '                stringResource(R.string.workout_filter_type_walking) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_WALKING),\n'
            '                stringResource(R.string.workout_filter_type_running) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_RUNNING),\n'
            '                stringResource(R.string.workout_filter_type_biking) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_BIKING),\n'
            '                stringResource(R.string.workout_filter_type_swimming) to listOf(\n'
            '                    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL,\n'
            '                    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER\n'
            '                ),\n'
            '                stringResource(R.string.workout_filter_type_strength) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING),\n'
            '                stringResource(R.string.workout_filter_type_hiking) to listOf(ExerciseSessionRecord.EXERCISE_TYPE_HIKING)\n'
            '            )\n'
            '            categories.forEachIndexed { index, (label, exerciseTypes) ->\n'
            '                WidgetVisibilityRow(\n'
            '                    palette = palette,\n'
            '                    label = label,\n'
            '                    accent = HealthAccent.activity,\n'
            '                    checked = exerciseTypes.none { it in excludedTypes },\n'
            '                    onCheckedChange = { checked ->\n'
            '                        val updated = if (checked) {\n'
            '                            excludedTypes - exerciseTypes.toSet()\n'
            '                        } else {\n'
            '                            excludedTypes + exerciseTypes.toSet()\n'
            '                        }\n'
            '                        excludedTypes = updated\n'
            '                        workoutFilterPrefs.setExcludedExerciseTypes(updated)\n'
            '                    },\n'
            '                    isLast = index == categories.lastIndex\n'
            '                )\n'
            '            }\n'
            '        }\n'
            '\n'
            '        Text(\n'
            '            text = stringResource(R.string.data_scopes_link),',
        unique_marker='com.openhealth.sync.config.WorkoutFilterPrefs(context)',
        desc="add workout filter section to Settings (min-duration chips + per-type toggles)",
    )


def patch_strings() -> None:
    print("==> strings.xml: workout card + filter strings (EN)")
    apply_edit(
        STRINGS_EN,
        old='    <string name="workout_total_minutes">%1$d min total</string>',
        new='    <string name="workout_stat_when_label">When</string>\n'
            '    <string name="workout_stat_duration_label">Duration</string>\n'
            '    <string name="workout_stat_distance_label">Distance</string>\n'
            '    <string name="workout_stat_pace_label">Pace</string>\n'
            '    <string name="workout_duration_value">%1$d min</string>\n'
            '    <string name="workout_pace_value">%1$s /km</string>\n'
            '    <string name="workout_filter_section_title">Workout filtering</string>\n'
            '    <string name="workout_filter_section_body">Choose which workouts get synced as their own workout cards. Steps, distance, and calories for that time still sync either way.</string>\n'
            '    <string name="workout_filter_min_duration_label">Minimum duration</string>\n'
            '    <string name="workout_filter_min_duration_off">Off</string>\n'
            '    <string name="workout_filter_min_duration_value">%1$d min</string>\n'
            '    <string name="workout_filter_type_walking">Walking</string>\n'
            '    <string name="workout_filter_type_running">Running</string>\n'
            '    <string name="workout_filter_type_biking">Biking</string>\n'
            '    <string name="workout_filter_type_swimming">Swimming</string>\n'
            '    <string name="workout_filter_type_strength">Strength training</string>\n'
            '    <string name="workout_filter_type_hiking">Hiking</string>',
        desc="add workout card + filter strings (EN)",
    )

    print("==> strings.xml: workout card + filter strings (RU)")
    apply_edit(
        STRINGS_RU,
        old='    <string name="workout_total_minutes">%1$d мин всего</string>',
        new='    <string name="workout_stat_when_label">Когда</string>\n'
            '    <string name="workout_stat_duration_label">Время</string>\n'
            '    <string name="workout_stat_distance_label">Дистанция</string>\n'
            '    <string name="workout_stat_pace_label">Темп</string>\n'
            '    <string name="workout_duration_value">%1$d мин</string>\n'
            '    <string name="workout_pace_value">%1$s /км</string>\n'
            '    <string name="workout_filter_section_title">Фильтр тренировок</string>\n'
            '    <string name="workout_filter_section_body">Выбери, какие тренировки синкать отдельными карточками. Шаги, дистанция и калории за это время синкаются в любом случае.</string>\n'
            '    <string name="workout_filter_min_duration_label">Минимальная длительность</string>\n'
            '    <string name="workout_filter_min_duration_off">Выкл.</string>\n'
            '    <string name="workout_filter_min_duration_value">%1$d мин</string>\n'
            '    <string name="workout_filter_type_walking">Ходьба</string>\n'
            '    <string name="workout_filter_type_running">Бег</string>\n'
            '    <string name="workout_filter_type_biking">Велосипед</string>\n'
            '    <string name="workout_filter_type_swimming">Плавание</string>\n'
            '    <string name="workout_filter_type_strength">Силовая тренировка</string>\n'
            '    <string name="workout_filter_type_hiking">Поход</string>',
        desc="add workout card + filter strings (RU)",
    )


def main() -> None:
    print("==> Checking target files exist")
    for rel in TARGET_FILES_MUST_EXIST:
        if not (ROOT / rel).exists():
            die(f"Expected file not found: {rel} (run this from the repo root)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES_MUST_EXIST + [FILTER_PREFS]:
        backup_file(rel)

    create_workout_filter_prefs()
    patch_google_health_manager()
    patch_snapshot_cache()
    patch_ui()
    patch_strings()

    print("==> Best-effort compile check")
    gradlew = ROOT / "gradlew"
    if gradlew.exists():
        result = subprocess.run(
            ["./gradlew", ":app:compileDebugKotlin", "--console=plain"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            die("compileDebugKotlin failed -- NOT committing or pushing. "
                "Fix the error above (or paste it back) before re-running.")
        print("==> Compile check passed")
    else:
        print("   gradlew not found -- skipping compile check (unexpected outside "
              "a throwaway sandbox; NOT committing automatically).")
        return

    print("==> git add / commit / push")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m",
         "Add workout pace/distance to workout cards (max 4 stats) and a "
         "workout type/duration filter in Settings"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
