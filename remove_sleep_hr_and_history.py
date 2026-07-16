#!/usr/bin/env python3
"""
remove_sleep_hr_and_history.py

BitLut patch script -- sprint 2026-07-14.

Removes Sleep / heart-rate / SpO2 / stress and the History screen from the
codebase COMPLETELY (not just hidden/disabled, as earlier sprints left them)
-- deletes dead data fields, JSON (de)serialization, composables, string
resources, and the History-only bar-chart infrastructure that has zero
remaining callers once History itself is gone.

Run from the repo root inside your Codespace:
    python3 remove_sleep_hr_and_history.py

Conventions followed (see CLAUDE.md):
  - Backs up every touched file to
    .bitlut_patch_backup/<timestamp>_remove_sleep_hr_and_history/ before
    writing anything.
  - Every edit is a regex-anchored (old_str -> new_str substring) replace,
    never line-number-anchored. Each anchor's count is verified == 1 before
    applying; aborts loudly (no guessing, no fallback match) otherwise.
  - Idempotency: checks whether the NEW text is already present FIRST, and
    skips that edit (not an error) if so -- safe to re-run this script.
  - Two files are deleted outright (not edited): MetricCharts.kt and
    MetricBarReflectionTest.kt, both fully orphaned by this change once
    History's bar-chart infrastructure goes.
  - Best-effort `./gradlew :app:compileDebugKotlin` + `:app:processDebugResources`
    gate; only commits/pushes if both pass (or gradlew is absent, e.g. a
    throwaway test sandbox).
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / f"{TIMESTAMP}_remove_sleep_hr_and_history"

touched_files = set()
edits_applied = 0
edits_skipped = 0


def log(msg):
    print(f"==> {msg}")


def backup(path: Path):
    if path in touched_files:
        return
    touched_files.add(path)
    rel = path.relative_to(ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, dest)


def apply_edit(rel_path: str, description: str, old: str, new: str):
    """Regex-anchored (exact substring) replace. Idempotent, count-verified.

    Checks the OLD anchor's count FIRST, not the new text's presence -- a
    short/generic `new` fragment (e.g. just the next function's signature,
    used only to mark where a deleted block ends) can coincidentally already
    exist in an untouched file, which would produce a false "already
    applied" skip if checked first. Old-anchor-absent is the trustworthy
    signal for "already applied"; we only trust it once we've also confirmed
    the new text is there, and abort loudly if neither is true (file has
    diverged from what this script expects).
    """
    global edits_applied, edits_skipped
    path = ROOT / rel_path
    if not path.exists():
        print(f"    !! ABORT: {rel_path} does not exist")
        sys.exit(1)
    text = path.read_text(encoding="utf-8")

    count = text.count(old)
    if count == 1:
        backup(path)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        print(f"    OK: {description}")
        edits_applied += 1
        return

    if count == 0:
        if (not new.strip()) or new in text:
            print(f"    (already applied) {description}")
            edits_skipped += 1
            return
        print(f"    !! ABORT: anchor not found in {rel_path}, and replacement text isn't there either")
        print(f"       description: {description}")
        print("       the file may have diverged from what this script expects -- not guessing, stopping here")
        sys.exit(1)

    print(f"    !! ABORT: expected exactly 1 match for anchor in {rel_path}")
    print(f"       description: {description}")
    print(f"       found: {count} match(es) (ambiguous, refusing to guess which one)")
    sys.exit(1)


def delete_file(rel_path: str, description: str):
    global edits_applied, edits_skipped
    path = ROOT / rel_path
    if not path.exists():
        print(f"    (already applied) {description}")
        edits_skipped += 1
        return
    backup(path)
    path.unlink()
    print(f"    OK: {description}")
    edits_applied += 1


log("Step 1/15: HealthDataContracts.kt -- drop dead daysBack param from the interface")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HealthDataContracts.kt",
    "readDashboardSnapshot() interface signature loses daysBack",
    old='    suspend fun readDashboardSnapshot(daysBack: Int): GoogleDashboardSnapshot?',
    new='    suspend fun readDashboardSnapshot(): GoogleDashboardSnapshot?',
)

log("Step 2/15: GoogleHealthManager.kt -- delete WorkoutTypeSummary/MetricBar types + bar-range helpers")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt",
    "delete WorkoutTypeSummary, MetricBar, computeMetricBarRanges, bucketsOfEqualSize, calendarMonthBuckets; strip sleep/HR/SpO2/stress/stepsBars/workoutSummaries fields from GoogleDashboardSnapshot",
    old='''data class WorkoutTypeSummary(
    val exerciseType: Int,
    val displayName: String,
    val sessionCount: Int,
    val totalDurationMinutes: Long
)

data class GoogleDashboardSnapshot(
    val stepsToday: Long,
    val distanceMeters: Double,
    val caloriesKcal: Double,
    val workoutMinutesToday: Long,
    val activeHoursToday: Int,
    val sleepHours: Double,
    val sleepQualityScore: Int?,
    val heartRateBpm: Long?,
    val heartRateTodayBars: List<MetricBar>,
    val stressScore: Int?,
    val spo2Percent: Double?,
    val stepsBars: List<MetricBar>,
    val sleepBars: List<MetricBar>,
    val heartRateBars: List<MetricBar>,
    val recentWorkouts: List<ActivitySessionData>,
    val workoutSummaries: List<WorkoutTypeSummary>
)

data class MetricBar(
    val startDate: LocalDate,
    val endDate: LocalDate,
    val value: Double
)

fun computeMetricBarRanges(daysBack: Int, today: LocalDate = LocalDate.now()): List<Pair<LocalDate, LocalDate>> {
    return when (daysBack) {
        7 -> (0 until 7).map { index ->
            val day = today.minusDays((6 - index).toLong())
            day to day
        }
        14 -> (0 until 7).map { index ->
            val start = today.minusDays((13 - index * 2).toLong())
            start to start.plusDays(1)
        }
        30 -> bucketsOfEqualSize(daysBack, bucketCount = 5, today = today)
        60 -> bucketsOfEqualSize(daysBack, bucketCount = 8, today = today)
        90 -> bucketsOfEqualSize(daysBack, bucketCount = 13, today = today)
        180 -> calendarMonthBuckets(monthCount = 6, today = today)
        365 -> calendarMonthBuckets(monthCount = 12, today = today)
        else -> bucketsOfEqualSize(daysBack, bucketCount = (daysBack / 7).coerceIn(1, 13), today = today)
    }
}

private fun bucketsOfEqualSize(totalDays: Int, bucketCount: Int, today: LocalDate): List<Pair<LocalDate, LocalDate>> {
    val safeDays = totalDays.coerceAtLeast(1)
    val safeBuckets = bucketCount.coerceAtLeast(1)
    val startDate = today.minusDays((safeDays - 1).toLong())
    val baseSize = safeDays / safeBuckets
    val remainder = safeDays % safeBuckets
    val ranges = mutableListOf<Pair<LocalDate, LocalDate>>()
    var cursor = startDate

    for (index in 0 until safeBuckets) {
        val size = (baseSize + if (index < remainder) 1 else 0).coerceAtLeast(1)
        val end = cursor.plusDays((size - 1).toLong())
        ranges.add(cursor to minOf(end, today))
        cursor = end.plusDays(1)
        if (cursor > today) break
    }

    return ranges
}

private fun calendarMonthBuckets(monthCount: Int, today: LocalDate): List<Pair<LocalDate, LocalDate>> {
    return (0 until monthCount).map { index ->
        val monthStart = today.withDayOfMonth(1).minusMonths((monthCount - 1 - index).toLong())
        val monthEnd = monthStart.plusMonths(1).minusDays(1)
        monthStart to minOf(monthEnd, today)
    }
}''',
    new='''data class GoogleDashboardSnapshot(
    val stepsToday: Long,
    val distanceMeters: Double,
    val caloriesKcal: Double,
    val workoutMinutesToday: Long,
    val activeHoursToday: Int,
    val recentWorkouts: List<ActivitySessionData>
)''',
)
log("Step 3/15: GoogleHealthManager.kt -- trim readDashboardSnapshot() itself")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt",
    "readDashboardSnapshot() drops daysBack param",
    old='    override suspend fun readDashboardSnapshot(daysBack: Int): GoogleDashboardSnapshot? {',
    new='    override suspend fun readDashboardSnapshot(): GoogleDashboardSnapshot? {',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt",
    "readDashboardSnapshot() constructor call drops sleep/HR/SpO2/stress/stepsBars/workoutSummaries fields",
    old='''            GoogleDashboardSnapshot(
                stepsToday = stepsToday,
                distanceMeters = distanceMeters,
                caloriesKcal = caloriesKcal,
                workoutMinutesToday = readWorkoutMinutesToday(),
                activeHoursToday = readActiveHoursToday(),
                sleepHours = 0.0,
                sleepQualityScore = null,
                heartRateBpm = null,
                heartRateTodayBars = emptyList(),
                stressScore = null,
                spo2Percent = null,
                // Sprint (2026-07-10): stepsBars and workoutSummaries fed the
                // History screen's bar chart and per-type workout list --
                // unreachable UI for several sprints now (History was removed
                // from the bottom nav entirely). readStepsBars alone was one
                // Health Connect call PER DAY in range (7 separate calls for
                // the default 7-day range), so this cuts ~9 wasted API calls
                // out of every single load(). Confirmed from a real device
                // log: those wasted calls were a direct contributor to
                // "Rate limited request quota has been exceeded" once
                // sync-on-resume made load() fire far more often than before.
                stepsBars = emptyList(),
                sleepBars = emptyList(),
                heartRateBars = emptyList(),
                recentWorkouts = readRecentWorkouts(5),
                workoutSummaries = emptyList()
            )''',
    new='''            // Sprint (2026-07-14): sleep/heart-rate/SpO2/stress and the
            // History-only stepsBars/workoutSummaries fields were removed
            // from GoogleDashboardSnapshot entirely (not just hardcoded to
            // empty/null) -- Huawei's individual-developer tier can't supply
            // the former, and History itself was removed from the bottom nav
            // in an earlier sprint, so both were dead weight kept only for
            // source compatibility. See CLAUDE.md for the platform-tier
            // rationale on sleep/HR/SpO2/stress specifically.
            GoogleDashboardSnapshot(
                stepsToday = stepsToday,
                distanceMeters = distanceMeters,
                caloriesKcal = caloriesKcal,
                workoutMinutesToday = readWorkoutMinutesToday(),
                activeHoursToday = readActiveHoursToday(),
                recentWorkouts = readRecentWorkouts(5)
            )''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt",
    "readWeekOverWeekComparison() doc comment drops stale History reference",
    old='''     * This intentionally does not require any new Huawei scope or Health
     * Connect permission -- it's a different aggregation of data BitLut
     * already reads for the dashboard and history screens.
     */''',
    new='''     * This intentionally does not require any new Huawei scope or Health
     * Connect permission -- it's a different aggregation of data BitLut
     * already reads for the dashboard screen.
     */''',
)

log("Step 4/15: GoogleHealthManager.kt -- delete readWorkoutSummariesByType() (History-only, zero callers)")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt",
    "delete readWorkoutSummariesByType()",
    old='''    suspend fun readWorkoutSummariesByType(daysBack: Int): List<WorkoutTypeSummary> {
        val client = resolveClient() ?: return emptyList()
        return try {
            val start = LocalDate.now().minusDays(daysBack.toLong().coerceAtLeast(1L) - 1L)
                .atStartOfDay(ZoneId.systemDefault()).toInstant()
            val end = Instant.now()

            val allRecords = mutableListOf<ExerciseSessionRecord>()
            var pageToken: String? = null

            do {
                val response = client.readRecords(
                    ReadRecordsRequest(
                        recordType = ExerciseSessionRecord::class,
                        timeRangeFilter = TimeRangeFilter.between(start, end),
                        pageToken = pageToken
                    )
                )
                allRecords.addAll(response.records)
                pageToken = response.pageToken
            } while (pageToken != null)

            allRecords
                .groupBy { it.exerciseType }
                .map { (type, sessions) ->
                    val totalMinutes = sessions.sumOf { session ->
                        java.time.Duration.between(session.startTime, session.endTime).toMinutes().coerceAtLeast(0L)
                    }
                    WorkoutTypeSummary(
                        exerciseType = type,
                        displayName = exerciseTypeName(type),
                        sessionCount = sessions.size,
                        totalDurationMinutes = totalMinutes
                    )
                }
                .sortedByDescending { it.totalDurationMinutes }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.e(TAG, "readWorkoutSummariesByType failed: ${e.message}", e)
            emptyList()
        }
    }

    suspend fun readWorkoutMinutesToday(): Long {''',
    new='''    suspend fun readWorkoutMinutesToday(): Long {''',
)

log("Step 5/15: GoogleHealthManager.kt -- delete readStepsBars() (History-only, zero callers)")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt",
    "delete readStepsBars()",
    old='''    suspend fun readStepsBars(daysBack: Int): List<MetricBar> {
        val client = resolveClient() ?: return emptyList()
        val ranges = computeMetricBarRanges(daysBack)
        return ranges.map { (start, end) ->
            val rangeStart = start.atStartOfDay(ZoneId.systemDefault()).toInstant()
            val rangeEnd = end.plusDays(1).atStartOfDay(ZoneId.systemDefault()).toInstant()
            val steps = try {
                val response = client.aggregate(
                    AggregateRequest(
                        metrics = setOf(StepsRecord.COUNT_TOTAL),
                        timeRangeFilter = TimeRangeFilter.between(rangeStart, rangeEnd)
                    )
                )
                response[StepsRecord.COUNT_TOTAL] ?: 0L
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "readStepsBars failed for $start..$end: ${e.message}", e)
                0L
            }
            MetricBar(start, end, steps.toDouble())
        }
    }

    suspend fun readDistanceToday(): Double {''',
    new='''    suspend fun readDistanceToday(): Double {''',
)
log("Step 6/15: DashboardSnapshotCache.kt -- drop sleep/HR/SpO2/stress/stepsBars/workoutSummaries JSON fields")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt",
    "snapshotToJson() drops the removed fields",
    old='''    private fun snapshotToJson(s: GoogleDashboardSnapshot): JSONObject = JSONObject().apply {
        put("stepsToday", s.stepsToday)
        put("distanceMeters", s.distanceMeters)
        put("caloriesKcal", s.caloriesKcal)
        put("workoutMinutesToday", s.workoutMinutesToday)
        put("activeHoursToday", s.activeHoursToday)
        put("sleepHours", s.sleepHours)
        put("sleepQualityScore", s.sleepQualityScore ?: JSONObject.NULL)
        put("heartRateBpm", s.heartRateBpm ?: JSONObject.NULL)
        put("stressScore", s.stressScore ?: JSONObject.NULL)
        put("spo2Percent", s.spo2Percent ?: JSONObject.NULL)
        put("stepsBars", barsToJson(s.stepsBars))
        put("sleepBars", barsToJson(s.sleepBars))
        put("heartRateBars", barsToJson(s.heartRateBars))
        put("heartRateTodayBars", barsToJson(s.heartRateTodayBars))
        put("recentWorkouts", workoutsToJson(s.recentWorkouts))
        put("workoutSummaries", summariesToJson(s.workoutSummaries))
    }''',
    new='''    private fun snapshotToJson(s: GoogleDashboardSnapshot): JSONObject = JSONObject().apply {
        put("stepsToday", s.stepsToday)
        put("distanceMeters", s.distanceMeters)
        put("caloriesKcal", s.caloriesKcal)
        put("workoutMinutesToday", s.workoutMinutesToday)
        put("activeHoursToday", s.activeHoursToday)
        put("recentWorkouts", workoutsToJson(s.recentWorkouts))
    }''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt",
    "snapshotFromJson() drops the removed fields",
    old='''    private fun snapshotFromJson(o: JSONObject): GoogleDashboardSnapshot = GoogleDashboardSnapshot(
        stepsToday = o.optLong("stepsToday", 0L),
        distanceMeters = o.optDouble("distanceMeters", 0.0),
        caloriesKcal = o.optDouble("caloriesKcal", 0.0),
        workoutMinutesToday = o.optLong("workoutMinutesToday", 0L),
        activeHoursToday = o.optInt("activeHoursToday", 0),
        sleepHours = o.optDouble("sleepHours", 0.0),
        sleepQualityScore = o.optIntOrNull("sleepQualityScore"),
        heartRateBpm = o.optLongOrNull("heartRateBpm"),
        heartRateTodayBars = barsFromJson(o.optJSONArray("heartRateTodayBars")),
        stressScore = o.optIntOrNull("stressScore"),
        spo2Percent = o.optDoubleOrNull("spo2Percent"),
        stepsBars = barsFromJson(o.optJSONArray("stepsBars")),
        sleepBars = barsFromJson(o.optJSONArray("sleepBars")),
        heartRateBars = barsFromJson(o.optJSONArray("heartRateBars")),
        recentWorkouts = workoutsFromJson(o.optJSONArray("recentWorkouts")),
        workoutSummaries = summariesFromJson(o.optJSONArray("workoutSummaries"))
    )''',
    new='''    private fun snapshotFromJson(o: JSONObject): GoogleDashboardSnapshot = GoogleDashboardSnapshot(
        stepsToday = o.optLong("stepsToday", 0L),
        distanceMeters = o.optDouble("distanceMeters", 0.0),
        caloriesKcal = o.optDouble("caloriesKcal", 0.0),
        workoutMinutesToday = o.optLong("workoutMinutesToday", 0L),
        activeHoursToday = o.optInt("activeHoursToday", 0),
        recentWorkouts = workoutsFromJson(o.optJSONArray("recentWorkouts"))
    )''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt",
    "delete now-unused barsToJson/barsFromJson/summariesToJson/summariesFromJson/optXxxOrNull helpers",
    old='''    private fun barsToJson(bars: List<MetricBar>): JSONArray {
        val arr = JSONArray()
        bars.forEach { bar ->
            arr.put(JSONObject().apply {
                put("startDate", bar.startDate.toString())
                put("endDate", bar.endDate.toString())
                put("value", bar.value)
            })
        }
        return arr
    }

    private fun barsFromJson(arr: JSONArray?): List<MetricBar> {
        if (arr == null) return emptyList()
        val out = ArrayList<MetricBar>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            try {
                out.add(
                    MetricBar(
                        startDate = java.time.LocalDate.parse(item.getString("startDate")),
                        endDate = java.time.LocalDate.parse(item.getString("endDate")),
                        value = item.optDouble("value", 0.0)
                    )
                )
            } catch (_: Exception) {
                // Skip a single corrupt bar rather than discarding the whole cache entry.
            }
        }
        return out
    }

    private fun workoutsToJson(workouts: List<ActivitySessionData>): JSONArray {
        val arr = JSONArray()
        workouts.forEach { w ->
            arr.put(JSONObject().apply {
                put("startTimeMs", w.startTimeMs)
                put("endTimeMs", w.endTimeMs)
                put("title", w.title)
                put("exerciseType", w.exerciseType)
            })
        }
        return arr
    }

    private fun workoutsFromJson(arr: JSONArray?): List<ActivitySessionData> {
        if (arr == null) return emptyList()
        val out = ArrayList<ActivitySessionData>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            out.add(
                ActivitySessionData(
                    startTimeMs = item.optLong("startTimeMs", 0L),
                    endTimeMs = item.optLong("endTimeMs", 0L),
                    title = item.optString("title", "Huawei activity"),
                    exerciseType = item.optInt(
                        "exerciseType",
                        androidx.health.connect.client.records.ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT
                    )
                )
            )
        }
        return out
    }

    private fun summariesToJson(summaries: List<WorkoutTypeSummary>): JSONArray {
        val arr = JSONArray()
        summaries.forEach { s ->
            arr.put(JSONObject().apply {
                put("exerciseType", s.exerciseType)
                put("displayName", s.displayName)
                put("sessionCount", s.sessionCount)
                put("totalDurationMinutes", s.totalDurationMinutes)
            })
        }
        return arr
    }

    private fun summariesFromJson(arr: JSONArray?): List<WorkoutTypeSummary> {
        if (arr == null) return emptyList()
        val out = ArrayList<WorkoutTypeSummary>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            out.add(
                WorkoutTypeSummary(
                    exerciseType = item.optInt("exerciseType", 0),
                    displayName = item.optString("displayName", ""),
                    sessionCount = item.optInt("sessionCount", 0),
                    totalDurationMinutes = item.optLong("totalDurationMinutes", 0L)
                )
            )
        }
        return out
    }

    private fun JSONObject.optIntOrNull(key: String): Int? =
        if (isNull(key) || !has(key)) null else optInt(key)

    private fun JSONObject.optLongOrNull(key: String): Long? =
        if (isNull(key) || !has(key)) null else optLong(key)

    private fun JSONObject.optDoubleOrNull(key: String): Double? =
        if (isNull(key) || !has(key)) null else optDouble(key)

    companion object {
        private const val KEY_SNAPSHOT_JSON = "dashboard_snapshot_cache_json"
        private const val KEY_SNAPSHOT_SAVED_AT_MS = "dashboard_snapshot_cache_saved_at_ms"
    }
}''',
    new='''    private fun workoutsToJson(workouts: List<ActivitySessionData>): JSONArray {
        val arr = JSONArray()
        workouts.forEach { w ->
            arr.put(JSONObject().apply {
                put("startTimeMs", w.startTimeMs)
                put("endTimeMs", w.endTimeMs)
                put("title", w.title)
                put("exerciseType", w.exerciseType)
            })
        }
        return arr
    }

    private fun workoutsFromJson(arr: JSONArray?): List<ActivitySessionData> {
        if (arr == null) return emptyList()
        val out = ArrayList<ActivitySessionData>(arr.length())
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            out.add(
                ActivitySessionData(
                    startTimeMs = item.optLong("startTimeMs", 0L),
                    endTimeMs = item.optLong("endTimeMs", 0L),
                    title = item.optString("title", "Huawei activity"),
                    exerciseType = item.optInt(
                        "exerciseType",
                        androidx.health.connect.client.records.ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT
                    )
                )
            )
        }
        return out
    }

    companion object {
        private const val KEY_SNAPSHOT_JSON = "dashboard_snapshot_cache_json"
        private const val KEY_SNAPSHOT_SAVED_AT_MS = "dashboard_snapshot_cache_saved_at_ms"
    }
}''',
)

log("Step 7/15: SyncWorker.kt -- drop dead daysBack=7 argument")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt",
    "readDashboardSnapshot() call drops daysBack = 7",
    old='            val freshSnapshot = googleManager.readDashboardSnapshot(daysBack = 7)',
    new='            val freshSnapshot = googleManager.readDashboardSnapshot()',
)
log("Step 8/15: DashboardViewModel.kt -- drop HISTORY_RANGE_OPTIONS, dead imports, state fields, onHistoryRangeSelected()")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt",
    "drop unused MetricBar/WorkoutTypeSummary imports",
    old='''import com.openhealth.sync.data.GoogleDashboardSnapshot
import com.openhealth.sync.data.MetricBar
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison
import com.openhealth.sync.data.WorkoutTypeSummary
import com.openhealth.sync.util.AppLogger''',
    new='''import com.openhealth.sync.data.GoogleDashboardSnapshot
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison
import com.openhealth.sync.util.AppLogger''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt",
    "drop HISTORY_RANGE_OPTIONS constant",
    old='''private const val TAG = "DashboardViewModel"

/** Selectable History range options, in days. Order matters for the chip row UI. */
val HISTORY_RANGE_OPTIONS = listOf(7, 14, 30, 60, 90, 180, 365)''',
    new='''private const val TAG = "DashboardViewModel"''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt",
    "drop stepsBars + sleep/HR/SpO2/stress + selectedHistoryRangeDays + workoutSummaries fields from DashboardUiState",
    old='''    val stepsBars: List<MetricBar> = emptyList(),
    val sleepHours: Double = 0.0,
    val sleepQualityScore: Int? = null,
    val heartRateBpm: Long? = null,
    val heartRateTodayBars: List<MetricBar> = emptyList(),
    val stressScore: Int? = null,
    val spo2Percent: Double? = null,
    val sleepBars: List<MetricBar> = emptyList(),
    val heartRateBars: List<MetricBar> = emptyList(),
    val recentWorkouts: List<ActivitySessionData> = emptyList(),
    val selectedHistoryRangeDays: Int = 7,
    val workoutSummaries: List<WorkoutTypeSummary> = emptyList(),
    val visibleWidgets: Map<DashboardWidget, Boolean> = DashboardWidget.entries.associateWith { true },''',
    new='''    val recentWorkouts: List<ActivitySessionData> = emptyList(),
    val visibleWidgets: Map<DashboardWidget, Boolean> = DashboardWidget.entries.associateWith { true },''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt",
    "delete onHistoryRangeSelected()",
    old='''    /** Called when the person taps a different range chip (7/14/30/60/90/180/365) on History. */
    fun onHistoryRangeSelected(days: Int) {
        if (days == _state.value.selectedHistoryRangeDays) return
        _state.update { it.copy(selectedHistoryRangeDays = days) }
        load()
    }

    /** Called from the Settings widget-visibility toggles. Persists immediately and
     *  updates the in-memory state so Summary/History reflect the change without a
     *  full reload (no Health Connect calls needed — this is purely a display
     *  preference, not new data). */''',
    new='''    /** Called from the Settings widget-visibility toggles. Persists immediately and
     *  updates the in-memory state so Summary reflects the change without a
     *  full reload (no Health Connect calls needed — this is purely a display
     *  preference, not new data). */''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt",
    "load() calls readDashboardSnapshot() with no rangeDays argument",
    old='''            val previous = _state.value
            val rangeDays = previous.selectedHistoryRangeDays
            val snapshot = googleManager.readDashboardSnapshot(rangeDays)''',
    new='''            val snapshot = googleManager.readDashboardSnapshot()''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt",
    "withSnapshot() drops sleep/HR/SpO2/stress/stepsBars/workoutSummaries mapping",
    old='''    private fun DashboardUiState.withSnapshot(snapshot: GoogleDashboardSnapshot): DashboardUiState =
        copy(
            isLoading       = false,
            hasPermissions  = true,
            stepsToday      = snapshot.stepsToday,
            distanceMeters  = snapshot.distanceMeters,
            caloriesKcal    = snapshot.caloriesKcal,
            workoutMinutesToday = snapshot.workoutMinutesToday,
            activeHoursToday = snapshot.activeHoursToday,
            sleepHours      = snapshot.sleepHours,
            sleepQualityScore = snapshot.sleepQualityScore,
            heartRateBpm    = snapshot.heartRateBpm,
            heartRateTodayBars = snapshot.heartRateTodayBars.ifEmpty { heartRateTodayBars },
            stressScore     = snapshot.stressScore,
            spo2Percent     = snapshot.spo2Percent,
            sleepBars       = snapshot.sleepBars.ifEmpty { sleepBars },
            heartRateBars   = snapshot.heartRateBars.ifEmpty { heartRateBars },
            stepsBars       = snapshot.stepsBars.ifEmpty { stepsBars },
            recentWorkouts  = snapshot.recentWorkouts.ifEmpty { recentWorkouts },
            workoutSummaries = snapshot.workoutSummaries.ifEmpty { workoutSummaries }
        )''',
    new='''    private fun DashboardUiState.withSnapshot(snapshot: GoogleDashboardSnapshot): DashboardUiState =
        copy(
            isLoading       = false,
            hasPermissions  = true,
            stepsToday      = snapshot.stepsToday,
            distanceMeters  = snapshot.distanceMeters,
            caloriesKcal    = snapshot.caloriesKcal,
            workoutMinutesToday = snapshot.workoutMinutesToday,
            activeHoursToday = snapshot.activeHoursToday,
            recentWorkouts  = snapshot.recentWorkouts.ifEmpty { recentWorkouts }
        )''',
)

log("Step 9/15: MainActivity.kt -- drop onHistoryRangeSelected wiring")
apply_edit(
    "app/src/main/java/com/openhealth/sync/MainActivity.kt",
    "drop onHistoryRangeSelected callback wiring",
    old='''                    onImportArchive = { openHuaweiArchiveImport() },
                    onHistoryRangeSelected = { days ->
                        dashboardViewModel.onHistoryRangeSelected(days)
                    },
                    onWidgetVisibilityChanged = { widget, visible ->
                        dashboardViewModel.setWidgetVisible(widget, visible)
                    },''',
    new='''                    onImportArchive = { openHuaweiArchiveImport() },
                    onWidgetVisibilityChanged = { widget, visible ->
                        dashboardViewModel.setWidgetVisible(widget, visible)
                    },''',
)
log("Step 10/15: FinalBitLutShell.kt -- imports, dead param, stale comment")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "drop WorkoutTypeSummary/MetricBar/HISTORY_RANGE_OPTIONS imports",
    old='''import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.WorkoutTypeSummary
import com.openhealth.sync.data.MetricBar
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison
import com.openhealth.sync.config.DashboardWidget
import com.openhealth.sync.config.GoalPrefs
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.DashboardUiState
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.HISTORY_RANGE_OPTIONS
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme''',
    new='''import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison
import com.openhealth.sync.config.DashboardWidget
import com.openhealth.sync.config.GoalPrefs
import com.openhealth.sync.platform.HmsCoreHelper
import com.openhealth.sync.ui.DashboardUiState
import com.openhealth.sync.ui.DashboardViewModel
import com.openhealth.sync.ui.SyncUiState
import com.openhealth.sync.ui.SyncViewModel
import com.openhealth.sync.ui.theme.BitLutExpressiveTheme''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "drop onHistoryRangeSelected parameter from FinalBitLutShell()",
    old='''    onImportArchive: () -> Unit = {},
    onHistoryRangeSelected: (Int) -> Unit = {},
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit = { _, _ -> },''',
    new='''    onImportArchive: () -> Unit = {},
    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit = { _, _ -> },''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "drop stale 'History lock screen' mention from wrappedOnRequestGoogle comment",
    old='''    // call site (Summary lock screen, History lock screen, Settings) without
    // changing any of them individually.''',
    new='''    // call site (Summary lock screen, Settings) without changing any of
    // them individually.''',
)

log("Step 11/15: FinalBitLutShell.kt -- delete HistoryScreen, HistoryRangeChips, WorkoutTypeCard")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "delete HistoryScreen/HistoryRangeChips/WorkoutTypeCard composables (all unreachable from MainTab nav dispatch)",
    old='''@Composable
private fun HistoryScreen(
    palette: BitPalette,
    state: DashboardUiState,
    onRequestGoogle: () -> Unit,
    onRangeSelected: (Int) -> Unit
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

        if (!state.showConnectLockScreen && state.hasPermissions) {
            item {
                HistoryRangeChips(
                    palette = palette,
                    selectedDays = state.selectedHistoryRangeDays,
                    onRangeSelected = onRangeSelected
                )
            }
        }

        if (state.showConnectLockScreen) {
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
        } else if (state.isLoading && state.stepsBars.isEmpty()) {
            item { DashboardLoadingCard(palette = palette) }
        } else {
            val rangeDays = state.selectedHistoryRangeDays
            val stepsTotal = state.stepsBars.sumOf { it.value }

            if (state.isWidgetVisible(DashboardWidget.STEPS)) {
                item {
                    MetricBarChartCard(
                        palette = palette,
                        title = stringResource(R.string.steps_label_days, rangeDays),
                        periodValueLabel = stringResource(R.string.period_total_steps, formatNumber(stepsTotal.toLong())),
                        bars = state.stepsBars,
                        accent = HealthAccent.activity,
                        valueFormatter = { formatNumber(it.toLong()) }
                    )
                }
            }

            if (state.isWidgetVisible(DashboardWidget.WORKOUTS) && state.workoutSummaries.isNotEmpty()) {
                item {
                    Text(
                        text = stringResource(R.string.workouts_section_title),
                        color = palette.text,
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 18.sp,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
                items(state.workoutSummaries) { summary ->
                    WorkoutTypeCard(palette = palette, summary = summary)
                }
            }
        }
    }
}

/**
 * Scrollable row of range chips (7/14/30/60/90/180/365 days) for the History screen,
 * placed on its own row below the screen title rather than sharing the title's row —
 * this avoids the kind of overflow/wrap risk that the Settings buttons had before
 * they were switched to FlowRow (a 7-chip row needs its own horizontal space, and
 * fighting the title for space on one line would risk the title getting clipped on
 * narrower screens or longer locale strings).
 */
@Composable
private fun HistoryRangeChips(
    palette: BitPalette,
    selectedDays: Int,
    onRangeSelected: (Int) -> Unit
) {
    LazyRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp, alignment = Alignment.End)
    ) {
        items(HISTORY_RANGE_OPTIONS) { days ->
            val selected = days == selectedDays
            val interactionSource = remember { MutableInteractionSource() }
            Box(
                modifier = Modifier
                    .pressScale(interactionSource)
                    .clip(RoundedCornerShape(99.dp))
                    .background(if (selected) HealthAccent.activity else palette.card)
                    .border(1.dp, if (selected) Color.Transparent else palette.stroke, RoundedCornerShape(99.dp))
                    .clickable(
                        interactionSource = interactionSource,
                        indication = null
                    ) { onRangeSelected(days) }
                    .padding(horizontal = 14.dp, vertical = 8.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = stringResource(R.string.history_range_days_short, days),
                    color = if (selected) Color.White else palette.secondaryText,
                    fontWeight = FontWeight.Black,
                    fontSize = 13.sp,
                    maxLines = 1
                )
            }
        }
    }
}

/**
 * Workout-type card for History: shown once per exercise type that has at least one
 * session in the currently selected range (no card for types with zero sessions).
 * Shows the localized exercise name (already handled by exerciseTypeName in
 * GoogleHealthManager — e.g. "Бег" for running), session count, and total duration.
 */
@Composable
private fun WorkoutTypeCard(
    palette: BitPalette,
    summary: WorkoutTypeSummary
) {
    SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    text = summary.displayName,
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 16.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = stringResource(R.string.workout_sessions_count, summary.sessionCount),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp
                )
            }
            Text(
                text = stringResource(R.string.workout_total_minutes, summary.totalDurationMinutes),
                color = HealthAccent.activity,
                fontWeight = FontWeight.Black,
                fontSize = 15.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

/**
 * Last imported workout (sprint 2026-07-08). state.recentWorkouts is already
 * sorted most-recent-first by GoogleHealthManager.readRecentWorkouts, so the''',
    new='''/**
 * Last imported workout (sprint 2026-07-08). state.recentWorkouts is already
 * sorted most-recent-first by GoogleHealthManager.readRecentWorkouts, so the''',
)
log("Step 12/15: FinalBitLutShell.kt -- delete MiniSparkline + unused Offset import")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "delete MiniSparkline (zero callers, depended on the now-deleted MetricBar type)",
    old='''@Composable
private fun MiniSparkline(
    bars: List<MetricBar>,
    accent: Color,
    modifier: Modifier = Modifier
) {
    Canvas(modifier = modifier) {
        val values = bars.map { it.value }.filter { it > 0.0 }
        if (values.size < 2) return@Canvas
        val min = values.minOrNull() ?: 0.0
        val max = values.maxOrNull() ?: 1.0
        val range = (max - min).takeIf { it > 0.0 } ?: 1.0
        val step = size.width / (values.size - 1).coerceAtLeast(1)
        var last: Offset? = null
        values.forEachIndexed { index, value ->
            val x = step * index
            val y = size.height - (((value - min) / range).toFloat() * size.height)
            val point = Offset(x, y.coerceIn(0f, size.height))
            last?.let { drawLine(accent, it, point, strokeWidth = 4.dp.toPx(), cap = StrokeCap.Round) }
            last = point
        }
    }
}

/**
 * Week-over-week comparison card (v1.9.12, sprint 4). Shows steps/distance/
 * calories change vs the previous 7 days as a signed percentage, or "first
 * tracked week" copy when there's no previous-week baseline to compare
 * against (WeekComparison.*PercentChange() returns null in that case).
 */
@Composable
private fun WeeklyComparisonCard(palette: BitPalette, comparison: WeekComparison) {
    SoftCard(palette = palette, accent = HealthAccent.mind, tintWithAccent = true) {''',
    new='''/**
 * Week-over-week comparison card (v1.9.12, sprint 4). Shows steps/distance/
 * calories change vs the previous 7 days as a signed percentage, or "first
 * tracked week" copy when there's no previous-week baseline to compare
 * against (WeekComparison.*PercentChange() returns null in that case).
 */
@Composable
private fun WeeklyComparisonCard(palette: BitPalette, comparison: WeekComparison) {
    SoftCard(palette = palette, accent = HealthAccent.mind, tintWithAccent = true) {''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "drop now-unused Offset import (only MiniSparkline used it)",
    old='''import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.geometry.Offset''',
    new='''import androidx.compose.ui.graphics.StrokeCap''',
)

log("Step 13/15: FinalBitLutShell.kt -- delete formatBarValueShort/barDateLabel (History-only, zero callers)")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "delete formatBarValueShort()/barDateLabel() and the stale doc comment describing the deleted History bar-chart widget",
    old='''/** Clamps any progress ratio into the 0f..1f range a ring can safely draw, and
 *  guards against division by zero when [goal] is zero or negative. */
private fun coerceProgress(value: Double, goal: Double): Float =
    if (goal <= 0.0) 0f else (value / goal).toFloat().coerceIn(0f, 1f)

/**
 * Combined count + trend widget for History: shows the period-aggregate value at
 * the top (e.g. total steps across the selected range) and a proportional-height
 * bar chart below it, one bar per MetricBar from computeMetricBarRanges, each
 * labeled with its value and a short date label. This replaces the earlier design
 * of two separate cards (an average-value card plus a standalone sparkline card)
 * with a single merged widget, per the latest design direction.
 *
 * Bar label granularity follows the bar's own date span: a single-day bar shows
 * the day-of-month, a multi-day bar shows a week-style short range, and the
 * 180/365-day cases (whose bars are real calendar months) show the month
 * abbreviation in the current locale.
 *
 * Safe by construction: an empty bar list (e.g. permission edge case) renders
 * nothing rather than dividing by zero; an all-zero bar list renders all bars at
 * minimum height rather than NaN-height bars.
 */
/** Short numeric label above a bar (e.g. "1.2k" for 1200 steps, "72" for bpm). */
internal fun formatBarValueShort(value: Double): String = when {
    value <= 0.0 -> "0"
    value >= 1000.0 -> String.format(Locale.getDefault(), "%.1fk", value / 1000.0)
    value == value.toLong().toDouble() -> value.toLong().toString()
    else -> String.format(Locale.getDefault(), "%.1f", value)
}

/** Short date label under a bar: day-of-month for single-day bars, month
 *  abbreviation for real calendar-month bars (180/365-day ranges), otherwise a
 *  compact day-range for the multi-day week-style buckets. */
internal fun barDateLabel(bar: MetricBar): String {
    val isWholeMonth = bar.startDate.dayOfMonth == 1 &&
        bar.endDate == bar.startDate.plusMonths(1).minusDays(1)
    return when {
        isWholeMonth -> bar.startDate.month.getDisplayName(java.time.format.TextStyle.SHORT, Locale.getDefault())
        bar.startDate == bar.endDate -> bar.startDate.dayOfMonth.toString()
        else -> "${bar.startDate.dayOfMonth}–${bar.endDate.dayOfMonth}"
    }
}

private fun List<Double>.safeAverage(): Double =
    if (isEmpty()) 0.0 else average()''',
    new='''/** Clamps any progress ratio into the 0f..1f range a ring can safely draw, and
 *  guards against division by zero when [goal] is zero or negative. */
private fun coerceProgress(value: Double, goal: Double): Float =
    if (goal <= 0.0) 0f else (value / goal).toFloat().coerceIn(0f, 1f)

private fun List<Double>.safeAverage(): Double =
    if (isEmpty()) 0.0 else average()''',
)

log("Step 14/15: FinalBitLutShell.kt -- HealthAccent/BitPalette cleanup + stale doc-comment fixes")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "Manual Sync card accent renamed sleep -> violet",
    old='            accent = HealthAccent.sleep,',
    new='            accent = HealthAccent.violet,',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "HealthAccent object: delete unused .heart, rename .sleep -> .violet, fix stale doc comment about a nonexistent Sleep ring",
    old='''/**
 * Generic reference target for the Sleep progress ring on Summary, in hours.
 * Unlike [DashboardUiState.stepsGoal], this is NOT a personalized or
 * user-configurable value — it's the commonly cited adult sleep guideline,
 * used only to give the ring a sense of "how close to a typical night" the
 * person is. If/when per-user sleep goals are added, replace this constant.
 */
internal object HealthAccent {
    val activity = Color(0xFFFF6B5A)
    val sleep = Color(0xFF9E6FC3)
    val heart = Color(0xFFFF453A)
    val mind = Color(0xFF5FE0C6)
    val cardLight = Color.White
    val cardDark = Color(0xCC1C1C1E)
    val systemLight = Color(0xFFF2F2F7)
}''',
    new='''/**
 * Shared accent-color palette used across cards and icons throughout the app.
 * These are purely visual accents (not tied to any specific health metric) --
 * [violet] in particular is just the app's fourth decorative accent color
 * (currently used for the Manual Sync card in Settings), not an indicator of
 * any sleep-related feature or data.
 */
internal object HealthAccent {
    val activity = Color(0xFFFF6B5A)
    val violet = Color(0xFF9E6FC3)
    val mind = Color(0xFF5FE0C6)
    val cardLight = Color.White
    val cardDark = Color(0xCC1C1C1E)
    val systemLight = Color(0xFFF2F2F7)
}''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "BitPalette: delete unused sleep/heart fields (confirmed zero reads, only ever assigned)",
    old='''internal data class BitPalette(
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
        // light() intentionally uses its own, slightly more saturated accent
        // values rather than HealthAccent's dark-mode hexes verbatim: the same
        // glow-tinted accent that reads as rich against a near-black card
        // washes out and looks chalky against white, so a small amount of
        // per-theme accent tuning is correct design, not drift -- unlike the
        // old dark() values below, which differed from HealthAccent by a few
        // hex units for no reason and would have drifted further over time.
        fun light(): BitPalette = BitPalette(
            dark = false,
            systemBackground = Color(0xFFF6F4F1),
            card = Color.White,
            text = Color(0xFF111318),
            secondaryText = Color(0xFF6E6E73),
            stroke = Color(0x1A111318),
            activity = Color(0xFFFF6B5F),
            sleep = Color(0xFF7B61FF),
            mind = Color(0xFF46C7B7),
            heart = Color(0xFFE53935),
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFFF6F4F1), Color(0xFFFFFFFF)))
        )
        // dark() now matches HealthAccent exactly (single source of truth):
        // previously activity was FF6B5F here vs FF6B5A in HealthAccent, and
        // sleep had three different values across the file (FF6B5A's sibling
        // mismatch, 9E6FC3 here, 7B61FF in light(), 6D5DF6 in the old
        // HealthAccent) -- imperceptible individually, but exactly the kind
        // of token drift that compounds into visible inconsistency over time.
        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = Color(0xFF0C0C0E),
            card = Color(0xCC1C1C1E),
            text = Color(0xFFF8F8F8),
            secondaryText = Color(0xFF8E8E93),
            stroke = Color(0x22FFFFFF),
            activity = HealthAccent.activity,
            sleep = HealthAccent.sleep,
            mind = HealthAccent.mind,
            heart = HealthAccent.heart,
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFF0C0C0E), Color(0xFF1C1C1E)))
        )
    }
}''',
    new='''internal data class BitPalette(
    val dark: Boolean,
    val systemBackground: Color,
    val card: Color,
    val text: Color,
    val secondaryText: Color,
    val stroke: Color,
    val activity: Color,
    val mind: Color,
    val backgroundBrush: Brush
) {
    companion object {
        // light() intentionally uses its own, slightly more saturated accent
        // values rather than HealthAccent's dark-mode hexes verbatim: the same
        // glow-tinted accent that reads as rich against a near-black card
        // washes out and looks chalky against white, so a small amount of
        // per-theme accent tuning is correct design, not drift.
        fun light(): BitPalette = BitPalette(
            dark = false,
            systemBackground = Color(0xFFF6F4F1),
            card = Color.White,
            text = Color(0xFF111318),
            secondaryText = Color(0xFF6E6E73),
            stroke = Color(0x1A111318),
            activity = Color(0xFFFF6B5F),
            mind = Color(0xFF46C7B7),
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFFF6F4F1), Color(0xFFFFFFFF)))
        )
        // dark() reuses HealthAccent directly (single source of truth) rather
        // than redeclaring near-duplicate hex values that could drift apart.
        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = Color(0xFF0C0C0E),
            card = Color(0xCC1C1C1E),
            text = Color(0xFFF8F8F8),
            secondaryText = Color(0xFF8E8E93),
            stroke = Color(0x22FFFFFF),
            activity = HealthAccent.activity,
            mind = HealthAccent.mind,
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFF0C0C0E), Color(0xFF1C1C1E)))
        )
    }
}''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "fix stale MinimalSquareTile doc comment (tiles are calories/workout-minutes/active-hours, not Heart/Sleep)",
    old='''/**
 * Square tile for the 2x2 Summary grid (Heart/Sleep sit side by side under the
 * full-width Steps hero card). Follows the "traffic light" rule: exactly three
 * elements on the tile — a filled icon chip, one large value, one small label.
 * No secondary text, no extra rows — the number does the talking.
 */''',
    new='''/**
 * Square tile for the 2x2 Summary grid (calories/workout-minutes/active-hours
 * sit side by side under the full-width Steps hero card). Follows the
 * "traffic light" rule: exactly three elements on the tile — a filled icon
 * chip, one large value, one small label. No secondary text, no extra rows —
 * the number does the talking.
 */''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "fix stale ProgressRingChip doc comment (no Sleep ring exists)",
    old='''/**
 * Compact progress ring used as the icon-chip replacement on Summary tiles that
 * have a real goal to show (Steps vs daily goal, Sleep vs the 8h reference).
 * [progress] is expected pre-clamped to 0f..1f by the caller (see [coerceProgress]).
 */''',
    new='''/**
 * Compact progress ring used as the icon-chip replacement on Summary tiles that
 * have a real goal to show (currently just Steps vs the daily goal).
 * [progress] is expected pre-clamped to 0f..1f by the caller (see [coerceProgress]).
 */''',
)

log("Step 15/15: small comment fixes in GlassNavigation.kt, BitLutExpressiveTheme.kt, AchievementsStore.kt")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt",
    "drop stale sleep/heart accent mention in the refresh-button comment",
    old='''/**
 * Warm orange, sprint 2026-07-09: distinct from every existing accent
 * (activity/mind/sleep/heart) on purpose, so the refresh button reads as its
 * own clearly-tappable action rather than belonging to either tab.
 */''',
    new='''/**
 * Warm orange, sprint 2026-07-09: distinct from every existing accent
 * (activity/mind/violet) on purpose, so the refresh button reads as its
 * own clearly-tappable action rather than belonging to either tab.
 */''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/theme/BitLutExpressiveTheme.kt",
    "fix stale BitPalette.sleep/heart comments (fields deleted)",
    old='''val Orange         = Color(0xFFFF6B5A)   // HealthAccent.activity -- the one true "activity" accent
val OrangeDim      = Color(0xFFE25A4B)
val Purple         = Color(0xFF9E6FC3)   // BitPalette.dark().sleep -- the one true "sleep" accent
val Mind           = Color(0xFF5FE0C6)   // BitPalette.dark().mind / HealthAccent.mind

// Semantic
val Success        = Color(0xFF22C55E)
val Warning        = Color(0xFFF59E0B)
val Danger         = Color(0xFFFF453A)   // BitPalette.dark().heart''',
    new='''val Orange         = Color(0xFFFF6B5A)   // HealthAccent.activity -- the one true "activity" accent
val OrangeDim      = Color(0xFFE25A4B)
val Purple         = Color(0xFF9E6FC3)   // HealthAccent.violet -- the one true purple/tertiary accent
val Mind           = Color(0xFF5FE0C6)   // BitPalette.dark().mind / HealthAccent.mind

// Semantic
val Success        = Color(0xFF22C55E)
val Warning        = Color(0xFFF59E0B)
val Danger         = Color(0xFFFF453A)   // the app's one true error/danger accent''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/AchievementsStore.kt",
    "drop reference to the deleted computeMetricBarRanges() in a comment",
    old=''' * Health Connect's own aggregate queries only cover the range you ask for
 * (7/30/365 days via computeMetricBarRanges); there is no "give me my best''',
    new=''' * Health Connect's own aggregate queries only cover the range you ask for;
 * there is no "give me my best''',
)
log("Step 16: delete files fully orphaned by this change")
delete_file(
    "app/src/main/java/com/openhealth/sync/ui/components/MetricCharts.kt",
    "delete MetricCharts.kt (existed only for MetricBarChartCard, which had zero callers left)",
)
delete_file(
    "app/src/test/java/com/openhealth/sync/data/MetricBarReflectionTest.kt",
    "delete MetricBarReflectionTest.kt (only exercised the now-deleted MetricBar type)",
)

log("Step 17: values/strings.xml -- drop History-only and dead sleep/HR-named strings")
apply_edit(
    "app/src/main/res/values/strings.xml",
    "drop tab_history/history_title/history_subtitle",
    old='''    <string name="app_name">BitLut</string>
    <string name="tab_summary">Summary</string>
    <string name="tab_history">History</string>
    <string name="tab_settings">Settings</string>
    <string name="summary_title">Health Summary</string>
    <string name="history_title">History</string>
    <string name="history_subtitle">Seven-day trends for your core health metrics.</string>
    <string name="settings_title">Settings</string>''',
    new='''    <string name="app_name">BitLut</string>
    <string name="tab_summary">Summary</string>
    <string name="tab_settings">Settings</string>
    <string name="summary_title">Health Summary</string>
    <string name="settings_title">Settings</string>''',
)
apply_edit(
    "app/src/main/res/values/strings.xml",
    "drop permissions_body (dead, mentioned removed History)",
    old='''    <string name="permissions_required">Permissions required</string>
    <string name="permissions_body">Grant Health Connect access to show Summary and History.</string>
    <string name="empty_value">No data</string>''',
    new='''    <string name="permissions_required">Permissions required</string>
    <string name="empty_value">No data</string>''',
)
apply_edit(
    "app/src/main/res/values/strings.xml",
    "drop bpm/steps_label_days/history_range_days_short/period_total_steps/workouts_section_title/workout_sessions_count (all dead, History-only or HR-only)",
    old='''    <string name="bpm">bpm</string>
    <string name="steps_7d">Steps, 7 days</string>
    <string name="steps_label_days">Steps, %1$d days</string>
    <string name="avg_label_days">%1$d-day average</string>
    <string name="history_range_days_short">%1$d d</string>
    <string name="period_total_steps">Total: %1$s steps</string>
    <string name="workouts_section_title">Workouts</string>
    <string name="workout_sessions_count">%1$d sessions</string>
    <string name="workout_total_minutes">%1$d min total</string>
    <string name="widget_visibility_section_title">Widgets</string>
    <string name="widget_visibility_section_body">Choose which widgets to show on the dashboard and in history.</string>
    <string name="widget_toggle_steps">Steps</string>''',
    new='''    <string name="steps_7d">Steps, 7 days</string>
    <string name="avg_label_days">%1$d-day average</string>
    <string name="workout_total_minutes">%1$d min total</string>
    <string name="widget_visibility_section_title">Widgets</string>
    <string name="widget_visibility_section_body">Choose which widgets to show on the dashboard.</string>
    <string name="widget_toggle_steps">Steps</string>''',
)
apply_edit(
    "app/src/main/res/values/strings.xml",
    "drop onboarding_step5/history_title_final/avg_bpm_7d/connect_google_history_body (dead, History- or HR-named)",
    old='''    <string name="onboarding_step4">Run sync or import an export file.</string>
    <string name="onboarding_step5">View your data in Summary and History.</string>
    <string name="onboarding_import_hint">Huawei Health Kit access may require approval before live sync works.</string>
    <string name="onboarding_continue">Continue</string>
    <string name="summary_title_final">Summary</string>
    <string name="history_title_final">History</string>
    <string name="settings_title_final">Settings</string>
    <string name="sync_now_final">Sync now</string>
    <string name="health_kit_status_final">Health Kit status</string>
    <string name="refresh_short">Refresh</string>
    <string name="summary_steps_today">Steps today</string>
    <string name="avg_steps_7d">Average steps over 7 days</string>
    <string name="avg_bpm_7d">Average bpm over 7 days</string>
    <string name="connect_google_title">Google Health Connect</string>
    <string name="connect_google_body">BitLut needs read and write permissions to show data and export imported Huawei Health data.</string>
    <string name="connect_google_history_body">Connect Google Health to see seven-day history.</string>
    <string name="connect_google_button">Connect Google Health</string>
    <string name="huawei_health">Huawei Health</string>''',
    new='''    <string name="onboarding_step4">Run sync or import an export file.</string>
    <string name="onboarding_import_hint">Huawei Health Kit access may require approval before live sync works.</string>
    <string name="onboarding_continue">Continue</string>
    <string name="summary_title_final">Summary</string>
    <string name="settings_title_final">Settings</string>
    <string name="sync_now_final">Sync now</string>
    <string name="health_kit_status_final">Health Kit status</string>
    <string name="refresh_short">Refresh</string>
    <string name="summary_steps_today">Steps today</string>
    <string name="avg_steps_7d">Average steps over 7 days</string>
    <string name="connect_google_title">Google Health Connect</string>
    <string name="connect_google_body">BitLut needs read and write permissions to show data and export imported Huawei Health data.</string>
    <string name="connect_google_button">Connect Google Health</string>
    <string name="huawei_health">Huawei Health</string>''',
)
apply_edit(
    "app/src/main/res/values/strings.xml",
    "drop bpm_unit (dead, HR-only)",
    old='''    <string name="hours_unit">h</string>
    <string name="bpm_unit">bpm</string>
    <string name="workouts">Workouts</string>''',
    new='''    <string name="hours_unit">h</string>
    <string name="workouts">Workouts</string>''',
)
apply_edit(
    "app/src/main/res/values/strings.xml",
    "drop history_short_title/tab_7days (dead, History-only)",
    old='''    <string name="summary_short_title">Summary</string>
    <string name="history_short_title">History</string>
    <string name="tab_7days">7 days</string>
    <string name="google_health_connect">Google Health Connect</string>''',
    new='''    <string name="summary_short_title">Summary</string>
    <string name="google_health_connect">Google Health Connect</string>''',
)

log("Step 18: values-ru/strings.xml -- mirror the same removals")
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "drop tab_history/history_title/history_subtitle (ru)",
    old='''    <string name="app_name">BitLut</string>
    <string name="tab_summary">Сводка</string>
    <string name="tab_history">История</string>
    <string name="tab_settings">Настройки</string>
    <string name="summary_title">Сводка здоровья</string>
    <string name="history_title">История</string>
    <string name="history_subtitle">Динамика основных показателей здоровья за последние 7 дней.</string>
    <string name="settings_title">Настройки</string>''',
    new='''    <string name="app_name">BitLut</string>
    <string name="tab_summary">Сводка</string>
    <string name="tab_settings">Настройки</string>
    <string name="summary_title">Сводка здоровья</string>
    <string name="settings_title">Настройки</string>''',
)
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "drop permissions_body (ru)",
    old='''    <string name="permissions_required">Нужны разрешения</string>
    <string name="permissions_body">Разрешите доступ Health Connect, чтобы видеть сводку и историю.</string>
    <string name="empty_value">Нет данных</string>''',
    new='''    <string name="permissions_required">Нужны разрешения</string>
    <string name="empty_value">Нет данных</string>''',
)
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "drop bpm/steps_label_days/history_range_days_short/period_total_steps/workouts_section_title/workout_sessions_count (ru)",
    old='''    <string name="bpm">уд/мин</string>
    <string name="steps_7d">Шаги за 7 дней</string>
    <string name="steps_label_days">Шаги за %1$d дн.</string>
    <string name="avg_label_days">Среднее за %1$d дн.</string>
    <string name="history_range_days_short">%1$d дн.</string>
    <string name="period_total_steps">Всего: %1$s шагов</string>
    <string name="workouts_section_title">Тренировки</string>
    <string name="workout_sessions_count">%1$d сессий</string>
    <string name="workout_total_minutes">%1$d мин всего</string>
    <string name="widget_visibility_section_title">Виджеты</string>
    <string name="widget_visibility_section_body">Выберите, какие виджеты показывать на главном экране и в истории.</string>
    <string name="widget_toggle_steps">Шаги</string>''',
    new='''    <string name="steps_7d">Шаги за 7 дней</string>
    <string name="avg_label_days">Среднее за %1$d дн.</string>
    <string name="workout_total_minutes">%1$d мин всего</string>
    <string name="widget_visibility_section_title">Виджеты</string>
    <string name="widget_visibility_section_body">Выберите, какие виджеты показывать на главном экране.</string>
    <string name="widget_toggle_steps">Шаги</string>''',
)
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "drop onboarding_step5/history_title_final/avg_bpm_7d/connect_google_history_body (ru)",
    old='''    <string name="onboarding_step5">Смотрите данные в Сводке и Истории.</string>
    <string name="onboarding_import_hint">Для live-синхронизации Huawei Health Kit может потребоваться одобрение.</string>
    <string name="onboarding_continue">Продолжить</string>
    <string name="summary_title_final">Сводка</string>
    <string name="history_title_final">История</string>
    <string name="settings_title_final">Настройки</string>
    <string name="sync_now_final">Синхронизировать</string>
    <string name="health_kit_status_final">Статус Health Kit</string>
    <string name="refresh_short">Обновить</string>
    <string name="summary_steps_today">Шаги сегодня</string>
    <string name="avg_steps_7d">Среднее количество шагов за 7 дней</string>
    <string name="avg_bpm_7d">Средний пульс за 7 дней</string>
    <string name="connect_google_title">Google Health Connect</string>
    <string name="connect_google_body">BitLut нужны разрешения на чтение и запись, чтобы показывать данные и экспортировать импорт Huawei Health.</string>
    <string name="connect_google_history_body">Подключите Google Health, чтобы увидеть историю за 7 дней.</string>
    <string name="connect_google_button">Подключить Google Health</string>
    <string name="huawei_health">Huawei Health</string>''',
    new='''    <string name="onboarding_import_hint">Для live-синхронизации Huawei Health Kit может потребоваться одобрение.</string>
    <string name="onboarding_continue">Продолжить</string>
    <string name="summary_title_final">Сводка</string>
    <string name="settings_title_final">Настройки</string>
    <string name="sync_now_final">Синхронизировать</string>
    <string name="health_kit_status_final">Статус Health Kit</string>
    <string name="refresh_short">Обновить</string>
    <string name="summary_steps_today">Шаги сегодня</string>
    <string name="avg_steps_7d">Среднее количество шагов за 7 дней</string>
    <string name="connect_google_title">Google Health Connect</string>
    <string name="connect_google_body">BitLut нужны разрешения на чтение и запись, чтобы показывать данные и экспортировать импорт Huawei Health.</string>
    <string name="connect_google_button">Подключить Google Health</string>
    <string name="huawei_health">Huawei Health</string>''',
)
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "drop bpm_unit (ru)",
    old='''    <string name="hours_unit">ч</string>
    <string name="bpm_unit">уд/мин</string>
    <string name="workouts">Тренировки</string>''',
    new='''    <string name="hours_unit">ч</string>
    <string name="workouts">Тренировки</string>''',
)
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "drop history_short_title/tab_7days (ru)",
    old='''    <string name="summary_short_title">Сводка</string>
    <string name="history_short_title">История</string>
    <string name="tab_7days">7 дней</string>
    <string name="google_health_connect">Google Health Connect</string>''',
    new='''    <string name="summary_short_title">Сводка</string>
    <string name="google_health_connect">Google Health Connect</string>''',
)
log("Step 19: CLAUDE.md -- keep the architecture map / gotchas accurate")
apply_edit(
    "CLAUDE.md",
    "Current status: sleep/HR/SpO2/stress + History bullets updated",
    old='''- **Sleep / heart-rate / SpO2 / stress are intentionally absent everywhere**
  -- not requested from HUAWEI, not read/written to Health Connect, no UI
  for them. HUAWEI's advanced data tier is not available to individual
  developers at all (confirmed from HUAWEI's own docs), regardless of
  application quality -- this is a platform policy, not a fixable bug. If
  asked to add these, the honest answer is "would require registering as a
  HUAWEI enterprise developer first."
- **Screens: exactly 2** -- Today (Summary) and Settings. The History screen
  was removed from the bottom nav (its composables/logic are left in the
  codebase, unreachable, not deleted -- see Conventions below).''',
    new='''- **Sleep / heart-rate / SpO2 / stress are intentionally absent everywhere**
  -- not requested from HUAWEI, not read/written to Health Connect, no UI
  for them, and (as of 2026-07-14) no dead fields/serialization/color
  tokens for them left in the codebase either -- removed in full, not just
  disabled, down to `GoogleDashboardSnapshot`, `DashboardUiState`,
  `DashboardSnapshotCache` JSON (de)serialization, and the old
  `HealthAccent.heart`/`BitPalette.heart` color tokens. HUAWEI's advanced
  data tier is not available to individual developers at all (confirmed
  from HUAWEI's own docs), regardless of application quality -- this is a
  platform policy, not a fixable bug. If asked to add these, the honest
  answer is "would require registering as a HUAWEI enterprise developer
  first."
- **Screens: exactly 2** -- Today (Summary) and Settings. The History
  screen was removed from the bottom nav in an earlier sprint; as of
  2026-07-14 its code (`HistoryScreen`, `HistoryRangeChips`,
  `WorkoutTypeCard`, `readStepsBars`, `readWorkoutSummariesByType`,
  `computeMetricBarRanges` and its bucket helpers, the `MetricBar` type,
  the whole `MetricCharts.kt` file, and the now-dead `daysBack` parameter
  that only ever existed to feed History's range chips) was deleted
  outright rather than left dormant -- see Conventions below for why this
  is now the standing precedent instead of "leave it dormant."''',
)
apply_edit(
    "CLAUDE.md",
    "Architecture map: GoogleHealthManager.kt row notes daysBack is gone",
    old='| `data/GoogleHealthManager.kt` | Reads/writes Health Connect. `readDashboardSnapshot()` reads today\'s steps/distance/calories via `readRecords()` + manual sum, **not** `aggregate()` (see Gotcha 1). Coalesces concurrent permission checks behind a mutex + 3s cache (see Gotcha 6). |',
    new='| `data/GoogleHealthManager.kt` | Reads/writes Health Connect. `readDashboardSnapshot()` (no `daysBack` param since 2026-07-14 -- it was only ever fed by History\'s now-deleted range chips) reads today\'s steps/distance/calories via `readRecords()` + manual sum, **not** `aggregate()` (see Gotcha 1). Coalesces concurrent permission checks behind a mutex + 3s cache (see Gotcha 6). |',
)
apply_edit(
    "CLAUDE.md",
    "Architecture map: FinalBitLutShell.kt row -- HistoryScreen/WorkoutTypeCard no longer exist",
    old='| `ui/screens/FinalBitLutShell.kt` | All UI lives in one file: `SummaryScreen`, `SettingsScreen`, and every card/widget composable (`PersonalRecordsCard`, `StreakCard`, `LastWorkoutCard`, `MinimalMetricCard`, `SettingsConnectionCard`, etc.). `HistoryScreen`/`WorkoutTypeCard`/`DashboardWidgetGrid`/`WeeklyComparisonCard` are defined but intentionally unused (dormant, see Conventions). |',
    new='| `ui/screens/FinalBitLutShell.kt` | All UI lives in one file: `SummaryScreen`, `SettingsScreen`, and every card/widget composable (`PersonalRecordsCard`, `StreakCard`, `LastWorkoutCard`, `MinimalMetricCard`, `SettingsConnectionCard`, etc.). `DashboardWidgetGrid`/`WeeklyComparisonCard` are defined but intentionally unused (dormant, see Conventions). `HistoryScreen`/`HistoryRangeChips`/`WorkoutTypeCard` no longer exist at all (deleted 2026-07-14, not just dormant). |',
)
apply_edit(
    "CLAUDE.md",
    "Gotcha 8 rewritten: History composables are actually gone now, not dormant",
    old='8. **Several composables/functions are defined but deliberately unused** -- `HistoryScreen`, `WorkoutTypeCard`, `DashboardWidgetGrid`, `WeeklyComparisonCard`, `readStepsBars`, `readWeekOverWeekComparison` (the last one\'s *call site* was removed, the function itself may still exist). This is intentional minimal-diff precedent used throughout this project\'s patch history, not leftover cruft to "clean up" reflexively -- confirm a function is truly dead (no call sites, checked via grep across the whole non-backup tree) before touching it.',
    new='8. **Some composables/functions are defined but deliberately unused** -- currently `DashboardWidgetGrid`, `WeeklyComparisonCard`, `readWeekOverWeekComparison` (the last one\'s *call site* was removed, the function itself may still exist). This is intentional minimal-diff precedent for code that might come back (e.g. if week-over-week UI returns) -- confirm a function is truly dead (no call sites, checked via grep across the whole non-backup tree) before touching it. This is a case-by-case call, not a blanket rule, though: `HistoryScreen`/`HistoryRangeChips`/`WorkoutTypeCard`/`readStepsBars`/`readWorkoutSummariesByType`/`computeMetricBarRanges`/`MetricBar` were all fully deleted on 2026-07-14 rather than left dormant, once it was clear History itself was never coming back and they had zero remaining callers -- "leave it dormant" is the default for something that might be reconnected later, not a permanent policy for code proven to be permanently dead.',
)

log("Step 20: CHANGELOG.md -- add sprint entry")
apply_edit(
    "CHANGELOG.md",
    "insert 2026-07-14 changelog entry above the 2026-07-10 series",
    old='''# Changelog

## 2026-07-10 -- sync reliability + UI simplification sprint series''',
    new='''# Changelog

## 2026-07-14 -- full removal sprint: sleep/HR/SpO2/stress + History deleted outright

Follow-up to the 2026-07-10 series. That sprint removed History from the
bottom nav and stubbed sleep/heart-rate/SpO2/stress fields to empty/null,
but deliberately left the underlying code in place, dormant, as minimal-diff
precedent. This sprint changes that precedent for code proven to be
permanently dead (see CLAUDE.md Gotcha 8) and deletes it outright instead.

**Sleep / heart-rate / SpO2 / stress -- removed in full**
- `GoogleDashboardSnapshot`, `DashboardUiState`, and `DashboardSnapshotCache`
  no longer carry `sleepHours`, `sleepQualityScore`, `heartRateBpm`,
  `heartRateTodayBars`, `stressScore`, `spo2Percent`, `sleepBars`, or
  `heartRateBars` fields at all -- previously these existed and were just
  hardcoded to `0.0`/`null`/`emptyList()`.
- `HealthAccent.heart` deleted outright (confirmed zero real UI usage --
  only ever referenced by the also-deleted `BitPalette.heart` mapping).
  `HealthAccent.sleep` renamed to `HealthAccent.violet`: it *was* live UI
  (the Manual Sync card's accent color in Settings), just never actually
  representing sleep data, so the color stays and only the misleading name
  goes. `BitPalette.sleep`/`BitPalette.heart` fields deleted (confirmed
  zero reads anywhere, only ever assigned).
- Corrected a stale doc comment above `HealthAccent` describing a "Sleep
  progress ring on Summary" that had not existed in the UI for several
  sprints, and two similarly stale comments in `MinimalSquareTile`/
  `ProgressRingChip` referencing a "Heart/Sleep" 2x2 grid and "Sleep vs the
  8h reference" that describe a design that was never actually shipped.
- Removed 8 dead sleep/heart-rate-named string resources (`bpm`,
  `bpm_unit`, `avg_bpm_7d`, plus 5 History-only strings listed below) from
  both `values/strings.xml` and `values-ru/strings.xml`, confirmed unused
  via a full `R.string.<name>` grep first.

**History -- removed in full, not left dormant**
- Deleted `HistoryScreen`, `HistoryRangeChips`, and `WorkoutTypeCard`
  composables from `FinalBitLutShell.kt` (confirmed unreachable from the
  `MainTab` enum / nav dispatch -- History was already removed from the
  bottom nav in the 2026-07-10 sprint, this just finishes the job).
- Deleted the bar-chart infrastructure that existed solely to feed
  History's chart, once confirmed to have zero other callers: `MetricBar`
  data type, `computeMetricBarRanges`/`bucketsOfEqualSize`/
  `calendarMonthBuckets`, `readStepsBars()`, `readWorkoutSummariesByType()`,
  `MiniSparkline`, `formatBarValueShort()`, `barDateLabel()`. Deleted the
  entire `ui/components/MetricCharts.kt` file (existed only for the now-gone
  `MetricBarChartCard`) and the standalone `MetricBarReflectionTest.kt`
  scratch file (only exercised the now-gone `MetricBar` type).
- Removed the `stepsBars`/`workoutSummaries` fields from
  `GoogleDashboardSnapshot`/`DashboardUiState` and their
  `DashboardSnapshotCache` JSON (de)serialization -- these existed only to
  feed the deleted History chart and per-type workout list.
- Removed `HISTORY_RANGE_OPTIONS`, `DashboardViewModel.onHistoryRangeSelected()`,
  `DashboardUiState.selectedHistoryRangeDays`, and the
  `onHistoryRangeSelected` parameter/wiring through `FinalBitLutShell` and
  `MainActivity`.
- `HealthConnectManager.readDashboardSnapshot()` lost its `daysBack`
  parameter (in the interface, the `GoogleHealthManager` implementation,
  and the `SyncWorker` call site that had hardcoded it to `7` anyway) --
  it was only ever there to plumb History's range-chip selection through,
  and had been fully unused inside the function body since the 2026-07-10
  trim.
- Removed 6 dead History-named string resources (`tab_history`,
  `history_title`, `history_subtitle`, `history_short_title`, `tab_7days`,
  `history_title_final`) plus 3 more that were dead *and* referenced the
  removed screen in their text (`permissions_body`, `onboarding_step5`,
  `connect_google_history_body`) from both locale files, and reworded
  `widget_visibility_section_body` to drop its now-inaccurate "...and in
  history" clause.
- Updated `CLAUDE.md` to match: Gotcha 8's "deliberately unused, don't
  clean up reflexively" list no longer includes anything from History
  (only `DashboardWidgetGrid`/`WeeklyComparisonCard`/
  `readWeekOverWeekComparison` remain dormant by that precedent -- unrelated
  to today's change, still awaiting a possible future UI return).

## 2026-07-10 -- sync reliability + UI simplification sprint series''',
)
log("Step 21: README.md -- update the maintained status block")
apply_edit(
    "README.md",
    "update BITLUT_STATUS block: sleep/HR/SpO2/stress + History now fully removed from code, refresh date",
    old='''**Sleep / heart-rate / SpO2 / stress отсутствуют намеренно** — не запрашиваются у Huawei, не читаются и не пишутся в Health Connect, нет UI. Индивидуальным разработчикам Huawei не открывает advanced-уровень данных вообще, независимо от качества заявки.

**Экраны:** ровно 2 — Today (Summary) и Settings. History-экран убран из нижней навигации (код оставлен неиспользуемым, не удалён).

**Виджеты на Today (фиксированный набор, без возможности отключения):** шаги сегодня, время тренировок, личные рекорды, дней с целью подряд, последняя импортированная тренировка.

**Синхронизация:** автоматический триггер на каждом возврате в приложение (`onResume`, не только холодный старт), плюс кнопка Refresh в нижней навигации, плюс периодический воркер каждые 30 минут. Защищена debounce (5 сек между ручными триггерами) и process-wide lease против параллельных синков. Чтение сегодняшних метрик — через `readRecords()` с суммированием, не через `aggregate()` (у последнего есть задержка кэша на стороне Health Connect, что было подтверждённой причиной "синк работает только после открытия Google Fit").

_Обновлено: 2026-07-11_
<!-- BITLUT_STATUS:END -->

---''',
    new='''**Sleep / heart-rate / SpO2 / stress отсутствуют намеренно** — не запрашиваются у Huawei, не читаются и не пишутся в Health Connect, нет UI, и (с 2026-07-14) в коде не осталось даже мёртвых полей/сериализации/цветовых токенов под них — убраны полностью, а не просто отключены. Индивидуальным разработчикам Huawei не открывает advanced-уровень данных вообще, независимо от качества заявки.

**Экраны:** ровно 2 — Today (Summary) и Settings. History-экран убран из нижней навигации ещё в прошлом спринте; с 2026-07-14 его код (экран, чипы диапазона, карточка типа тренировки, вся инфраструктура bar-графика под него) удалён из репозитория полностью, а не просто оставлен неиспользуемым.

**Виджеты на Today (фиксированный набор, без возможности отключения):** шаги сегодня, время тренировок, личные рекорды, дней с целью подряд, последняя импортированная тренировка.

**Синхронизация:** автоматический триггер на каждом возврате в приложение (`onResume`, не только холодный старт), плюс кнопка Refresh в нижней навигации, плюс периодический воркер каждые 30 минут. Защищена debounce (5 сек между ручными триггерами) и process-wide lease против параллельных синков. Чтение сегодняшних метрик — через `readRecords()` с суммированием, не через `aggregate()` (у последнего есть задержка кэша на стороне Health Connect, что было подтверждённой причиной "синк работает только после открытия Google Fit").

_Обновлено: 2026-07-14_
<!-- BITLUT_STATUS:END -->

---''',
)

# ---------------------------------------------------------------------------
log(f"Done: {edits_applied} edit(s) applied, {edits_skipped} already up to date")

if edits_applied == 0:
    log("Nothing to do -- repo already matches the target state. Exiting without touching git.")
    sys.exit(0)

log(f"Backups written to {BACKUP_DIR.relative_to(ROOT)}")

gradlew = ROOT / "gradlew"
if gradlew.exists():
    log("Running best-effort Gradle compile gate (compileDebugKotlin + processDebugResources)...")
    try:
        result = subprocess.run(
            ["./gradlew", "--console=plain", ":app:compileDebugKotlin", ":app:processDebugResources"],
            cwd=ROOT,
        )
        build_ok = result.returncode == 0
    except OSError as e:
        # e.g. gradlew present but not executable, or Java not on PATH in
        # this environment -- best-effort means we report and move on
        # rather than crash with a raw traceback.
        log(f"Could not run ./gradlew ({e}) -- skipping the compile gate.")
        build_ok = None

    if build_ok is False:
        log("Gradle check FAILED. Working tree is left patched (see backups above to revert if needed).")
        log("Not committing or pushing. Fix the reported error and re-run this script -- it is idempotent.")
        sys.exit(1)
    elif build_ok is True:
        log("Gradle check passed.")
else:
    log("No ./gradlew found in this directory -- skipping the compile gate (expected in a sandbox/test run).")

log("Committing and pushing...")
subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
commit = subprocess.run(
    [
        "git", "commit", "-m",
        "Remove Sleep/HR/SpO2/stress and History code entirely (not just disabled)\n\n"
        "See CHANGELOG.md 2026-07-14 entry for the full breakdown.",
    ],
    cwd=ROOT,
)
if commit.returncode != 0:
    log("git commit reported nothing to commit or failed -- check git status manually.")
    sys.exit(1)

push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
if push.returncode != 0:
    log("git push failed -- the commit is local; push manually once resolved (e.g. auth/network).")
    sys.exit(1)

log("Pushed to origin/main. Done.")
