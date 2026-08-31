#!/usr/bin/env python3
"""
patch_workout_session_scoped_metrics_v1.py

Fixes a real data-integrity gap affecting EVERY imported workout, from
EVERY source (live Huawei sync and archive/CSV import both flow through
the same write path): Health Connect had no trustworthy distance, step,
or elevation data actually linked to a workout's own time window, only
a bare ExerciseSessionRecord + TotalCaloriesBurnedRecord.

## Why this matters for "does Google Health treat it as real"

Health Connect has no explicit foreign-key link between an
ExerciseSessionRecord and its distance/steps/elevation. Per Google's own
documented pattern, a reader determines a workout's own metrics by
querying DistanceRecord/StepsRecord/etc. over the SAME TIME RANGE as the
exercise session (see the "Add exercise routes" guide's
readExerciseSessions() sample, which does exactly this). BitLut was
writing session.distanceMeters/steps/elevationMeters correctly (computed
in HuaweiHealthManager.readActivityRecordSummary() from Huawei's own
ActivityRecord summary) but only ever using them for its own dashboard's
in-memory display -- never actually writing them as Health Connect
records scoped to the session's exact interval. The only
Distance/Steps/Elevation records that existed in that time window were
the separate, coarse BACKGROUND aggregates (writeDistanceBatch /
writeStepsBatch / writeElevationBatch), whose sample windows are already
documented elsewhere in this codebase (readDistance()'s doc comment) as
not lining up cleanly with an exact workout interval. Any third-party
reader -- Google Fit, Health Connect's own "session details" UI, a
corporate wellness app, or any other app -- had nothing accurate to find
for that specific workout.

## The fix

writeActivitySessionsBatch() now bundles DistanceRecord, StepsRecord, and
ElevationGainedRecord (plus ActiveCaloriesBurnedRecord, forward-compatible
though currently always null in practice) into the SAME insertRecords
call as the ExerciseSessionRecord and TotalCaloriesBurnedRecord, scoped
to the exact session start/end -- but ONLY for exercise types that can
plausibly produce each metric. A new sessionSubMetricsFor() helper
mirrors the exact per-type grouping already established by
workoutMetricDisplays() in FinalBitLutShell.kt (the existing, agreed
source of truth for which metrics make sense per exercise type), so a
strength-training, weightlifting, HIIT, yoga, or pilates session is never
given a fabricated distance or step count it couldn't have produced on
this device -- writing that would itself be untrustworthy data in the
other direction.

Two smaller, verified-safe fixes bundled in the same patch (found while
auditing this code path, per project convention of fixing what's found
rather than only flagging it):

1. workoutFingerprint() now includes activeCaloriesKcal (previously
   missing from the hash used to decide whether a workout's Health
   Connect records need a version bump). Currently a no-op in practice
   (the field is always null today) but keeps the fingerprint correct
   for when a future data source populates it.
2. writeSnapshot()'s write order (steps -> distance -> floors ->
   elevation -> activeCalories -> activitySessions) was already correct
   by accident but undocumented: writeStepsBatch's "complete daily
   summation" branch does a StepsRecord time-range delete across the
   whole affected date range before reinserting, and would silently wipe
   out this patch's new workout-scoped StepsRecord if activitySessions
   ever ran first or concurrently. Verified safe today because these are
   sequential suspend calls in one list literal, not launched
   concurrently -- now documented explicitly so a future refactor
   (e.g. parallelizing these writes) doesn't reintroduce the collision
   silently.

No new Health Connect permissions required: BitLut already holds write
permission for DistanceRecord, StepsRecord, ElevationGainedRecord, and
ActiveCaloriesBurnedRecord (used today for the separate background
aggregate writes) -- see HealthPermissionPolicy.kt.

Mandatory workflow already completed before this script was written:
hand-edited mirror -> real diff -> this script generated from that diff
-> tested on a clean extraction with a fake gradlew -> byte-diffed
against the mirror -> re-run for idempotency. See delivery notes.
"""
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

GOOGLE_HEALTH_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Cannot back up missing file: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rel = path.relative_to(REPO_ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(path, dest)


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, expected_new_count: int, description: str) -> None:
    """Genuine replacement. Idempotent via exact old_str occurrence count."""
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == 0 and new_count >= expected_new_count:
        print(f"  [skip] {description} (already applied)")
        return

    if old_count != expected_old_count:
        die(
            f"{description}: expected {expected_old_count} occurrence(s) of anchor "
            f"in {path.name}, found {old_count}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str, description: str) -> None:
    """Pure insertion next to text that itself stays unchanged. Idempotent via unique_marker."""
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"  [skip] {description} (already applied)")
        return

    if text.count(anchor) != 1:
        die(
            f"{description}: expected exactly 1 occurrence of anchor in {path.name}, "
            f"found {text.count(anchor)}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(anchor, new_with_anchor)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def validate_kotlin_braces(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count("{") != text.count("}"):
        die(f"Brace mismatch in {path.name} after patching -- aborting before build.")
    if text.count("(") != text.count(")"):
        die(f"Parenthesis mismatch in {path.name} after patching -- aborting before build.")


def main() -> None:
    if not GOOGLE_HEALTH_FILE.exists():
        die(f"Expected file not found: {GOOGLE_HEALTH_FILE}")

    print("== Workout session-scoped metrics (GoogleHealthManager.kt) ==")

    # 1. Document the load-bearing write ordering in writeSnapshot().
    apply_insertion(
        GOOGLE_HEALTH_FILE,
        anchor=(
            '    override suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): WriteSnapshotResult {\n'
            '        val results = listOf(\n'
        ),
        new_with_anchor=(
            '    override suspend fun writeSnapshot(snapshot: HuaweiHealthSnapshot): WriteSnapshotResult {\n'
            '        // Ordering is load-bearing (2026-08-30): writeStepsBatch\'s "complete\n'
            '        // daily summation" branch does a StepsRecord time-range delete across\n'
            '        // the whole affected date range before reinserting Huawei\'s daily\n'
            '        // total (see that function\'s own comment). writeActivitySessionsBatch\n'
            '        // now also writes a workout-scoped StepsRecord for walk/run/hike\n'
            '        // sessions (same BitLut-owned record type, same day). Because these\n'
            '        // are sequential suspend calls in one list literal -- not launched\n'
            '        // concurrently -- writeStepsBatch\'s delete-then-insert always fully\n'
            '        // completes before writeActivitySessionsBatch runs, so the workout\n'
            '        // StepsRecord is never deleted by that day\'s steps reconciliation.\n'
            '        // If this list is ever parallelized, activitySessions MUST still run\n'
            '        // strictly after steps, or the daily reconciliation delete will wipe\n'
            '        // out that sync\'s freshly-written workout step records.\n'
            '        // BITLUT_SESSION_METRICS_WRITE_ORDER_2026_08_30\n'
            '        val results = listOf(\n'
        ),
        unique_marker="BITLUT_SESSION_METRICS_WRITE_ORDER_2026_08_30",
        description="document load-bearing write ordering in writeSnapshot()",
    )

    # 2. Add activeCaloriesKcal to workoutFingerprint().
    apply_edit(
        GOOGLE_HEALTH_FILE,
        old=(
            '    private fun workoutFingerprint(session: ActivitySessionData): String {\n'
            '        val source = listOf(\n'
            '            session.exerciseType.toString(),\n'
            '            session.title.trim(),\n'
            '            session.distanceMeters?.toString() ?: "x",\n'
            '            session.totalCaloriesKcal?.toString() ?: "x",\n'
            '            session.elevationMeters?.toString() ?: "x",\n'
            '            session.steps?.toString() ?: "x"\n'
            '        ).joinToString("|")\n'
        ),
        new=(
            '    private fun workoutFingerprint(session: ActivitySessionData): String {\n'
            '        val source = listOf(\n'
            '            session.exerciseType.toString(),\n'
            '            session.title.trim(),\n'
            '            session.distanceMeters?.toString() ?: "x",\n'
            '            session.totalCaloriesKcal?.toString() ?: "x",\n'
            '            session.elevationMeters?.toString() ?: "x",\n'
            '            session.steps?.toString() ?: "x",\n'
            '            // 2026-08-30: added alongside the new session-scoped\n'
            '            // ActiveCaloriesBurnedRecord write below. Currently always "x"\n'
            '            // in practice (neither HuaweiHealthManager nor\n'
            '            // HuaweiExportParser populates ActivitySessionData.\n'
            '            // activeCaloriesKcal today), included for correctness the same\n'
            '            // way the other four summary fields already are, so a future\n'
            '            // source of this value automatically triggers a version bump\n'
            '            // and re-upsert instead of silently going stale.\n'
            '            session.activeCaloriesKcal?.toString() ?: "x"\n'
            '        ).joinToString("|")\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="include activeCaloriesKcal in workoutFingerprint()",
    )

    # 3. Insert sessionSubMetricsFor() helper + SessionSubMetric enum, right
    #    before writeActivitySessionsBatch().
    apply_insertion(
        GOOGLE_HEALTH_FILE,
        anchor='    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {\n',
        new_with_anchor=(
            '    /**\n'
            '     * Which of session.distanceMeters/steps/elevationMeters plausibly\n'
            '     * belong to a given exercise type, so writeActivitySessionsBatch never\n'
            '     * fabricates a metric a workout genuinely can\'t have (e.g. distance for\n'
            '     * a strength-training or yoga session). Mirrors the exact per-type\n'
            '     * grouping already established by workoutMetricDisplays() in\n'
            '     * FinalBitLutShell.kt -- that function is the single source of truth\n'
            '     * for which metrics make sense per exercise type; this just reuses the\n'
            '     * same groupings for what gets written instead of only what gets shown.\n'
            '     */\n'
            '    // BITLUT_SESSION_SUB_METRICS_2026_08_30\n'
            '    private enum class SessionSubMetric { DISTANCE, STEPS, ELEVATION }\n'
            '\n'
            '    private fun sessionSubMetricsFor(exerciseType: Int): Set<SessionSubMetric> = when (exerciseType) {\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_WALKING,\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING,\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING_TREADMILL ->\n'
            '            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS)\n'
            '\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_HIKING ->\n'
            '            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.ELEVATION, SessionSubMetric.STEPS)\n'
            '\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_BIKING ->\n'
            '            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.ELEVATION)\n'
            '\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_BIKING_STATIONARY ->\n'
            '            setOf(SessionSubMetric.DISTANCE)\n'
            '\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER,\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL ->\n'
            '            setOf(SessionSubMetric.DISTANCE)\n'
            '\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING,\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING,\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING,\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_YOGA,\n'
            '        ExerciseSessionRecord.EXERCISE_TYPE_PILATES ->\n'
            '            emptySet()\n'
            '\n'
            '        else ->\n'
            '            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS, SessionSubMetric.ELEVATION)\n'
            '    }\n'
            '\n'
            '    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {\n'
        ),
        unique_marker="BITLUT_SESSION_SUB_METRICS_2026_08_30",
        description="insert sessionSubMetricsFor() helper + SessionSubMetric enum",
    )

    # 4. Insert the actual sub-record writes into the bundle, right after
    #    the existing TotalCaloriesBurnedRecord block and before the
    #    insertRecords try block.
    apply_insertion(
        GOOGLE_HEALTH_FILE,
        anchor=(
            '                    metadata = bitlutWorkoutMetadata(\n'
            '                        "exercise_calories_estimate",\n'
            '                        start.toEpochMilli(),\n'
            '                        end.toEpochMilli(),\n'
            '                        version = version\n'
            '                    )\n'
            '                )\n'
            '            }\n'
            '\n'
            '            try {\n'
            '                client.insertRecords(bundle)\n'
        ),
        new_with_anchor=(
            '                    metadata = bitlutWorkoutMetadata(\n'
            '                        "exercise_calories_estimate",\n'
            '                        start.toEpochMilli(),\n'
            '                        end.toEpochMilli(),\n'
            '                        version = version\n'
            '                    )\n'
            '                )\n'
            '            }\n'
            '\n'
            '            // 2026-08-30: session.distanceMeters/steps/elevationMeters were\n'
            '            // computed correctly (from Huawei\'s own ActivityRecord summary,\n'
            '            // see readActivityRecordSummary()\'s per-record fallback) but\n'
            '            // never actually written to Health Connect as records scoped to\n'
            '            // this exercise session\'s own time window -- only used for\n'
            '            // BitLut\'s own dashboard display. Per Health Connect\'s own\n'
            '            // documented pattern (a session\'s distance/steps/elevation are\n'
            '            // read back by querying those record types over the *same time\n'
            '            // range* as the exercise session -- there is no explicit\n'
            '            // foreign-key link), any third-party reader -- Google Fit,\n'
            '            // Health Connect\'s own UI, or another app -- had nothing\n'
            '            // trustworthy to find for this workout\'s own metrics: the only\n'
            '            // DistanceRecord/StepsRecord/ElevationGainedRecord in Health\n'
            '            // Connect for that time span was the coarse background\n'
            '            // aggregate written by writeDistanceBatch/writeStepsBatch/\n'
            '            // writeElevationBatch, whose sample windows are already\n'
            '            // documented (see readDistance()\'s doc comment) as not lining\n'
            '            // up cleanly with an exact workout interval. Writing these\n'
            '            // session-scoped records in the same insertRecords bundle as\n'
            '            // the exercise itself fixes that for every workout, from every\n'
            '            // import source (live sync and archive import both produce the\n'
            '            // same ActivitySessionData through this one write path).\n'
            '            //\n'
            '            // Only include a metric a given exercise type can plausibly\n'
            '            // have -- sessionSubMetricsFor() mirrors workoutMetricDisplays()\n'
            '            // exactly, so a strength/yoga/HIIT/pilates session is never\n'
            '            // given a fabricated distance or step count it couldn\'t have\n'
            '            // produced on this device, which would itself be untrustworthy\n'
            '            // data.\n'
            '            val allowedSubMetrics = sessionSubMetricsFor(session.exerciseType)\n'
            '            val sessionDistanceMeters = session.distanceMeters?.takeIf { it > 0.0 }\n'
            '            if (SessionSubMetric.DISTANCE in allowedSubMetrics && sessionDistanceMeters != null) {\n'
            '                bundle += DistanceRecord(\n'
            '                    startTime = start,\n'
            '                    endTime = end,\n'
            '                    startZoneOffset = offset(start),\n'
            '                    endZoneOffset = offset(end),\n'
            '                    distance = Length.meters(sessionDistanceMeters),\n'
            '                    metadata = bitlutWorkoutMetadata(\n'
            '                        "exercise_distance",\n'
            '                        start.toEpochMilli(),\n'
            '                        end.toEpochMilli(),\n'
            '                        version = version\n'
            '                    )\n'
            '                )\n'
            '            }\n'
            '            val sessionSteps = session.steps?.takeIf { it > 0L }\n'
            '            if (SessionSubMetric.STEPS in allowedSubMetrics && sessionSteps != null) {\n'
            '                bundle += StepsRecord(\n'
            '                    startTime = start,\n'
            '                    endTime = end,\n'
            '                    startZoneOffset = offset(start),\n'
            '                    endZoneOffset = offset(end),\n'
            '                    count = sessionSteps,\n'
            '                    metadata = bitlutWorkoutMetadata(\n'
            '                        "exercise_steps",\n'
            '                        start.toEpochMilli(),\n'
            '                        end.toEpochMilli(),\n'
            '                        version = version\n'
            '                    )\n'
            '                )\n'
            '            }\n'
            '            val sessionElevationMeters = session.elevationMeters?.takeIf { it > 0.0 }\n'
            '            if (SessionSubMetric.ELEVATION in allowedSubMetrics && sessionElevationMeters != null) {\n'
            '                bundle += ElevationGainedRecord(\n'
            '                    startTime = start,\n'
            '                    endTime = end,\n'
            '                    startZoneOffset = offset(start),\n'
            '                    endZoneOffset = offset(end),\n'
            '                    elevation = Length.meters(sessionElevationMeters),\n'
            '                    metadata = bitlutWorkoutMetadata(\n'
            '                        "exercise_elevation",\n'
            '                        start.toEpochMilli(),\n'
            '                        end.toEpochMilli(),\n'
            '                        version = version\n'
            '                    )\n'
            '                )\n'
            '            }\n'
            '            val sessionActiveCaloriesKcal = session.activeCaloriesKcal?.takeIf { it > 0.0 }\n'
            '            if (sessionActiveCaloriesKcal != null) {\n'
            '                bundle += ActiveCaloriesBurnedRecord(\n'
            '                    startTime = start,\n'
            '                    endTime = end,\n'
            '                    startZoneOffset = offset(start),\n'
            '                    endZoneOffset = offset(end),\n'
            '                    energy = Energy.kilocalories(sessionActiveCaloriesKcal),\n'
            '                    metadata = bitlutWorkoutMetadata(\n'
            '                        "exercise_active_calories",\n'
            '                        start.toEpochMilli(),\n'
            '                        end.toEpochMilli(),\n'
            '                        version = version\n'
            '                    )\n'
            '                )\n'
            '            }\n'
            '\n'
            '            try {\n'
            '                client.insertRecords(bundle)\n'
        ),
        unique_marker='"exercise_active_calories"',
        description="write session-scoped Distance/Steps/Elevation/ActiveCalories records",
    )

    validate_kotlin_braces(GOOGLE_HEALTH_FILE)

    print("== Build gate: :app:compileDebugKotlin ==")
    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found at repo root")

    result = subprocess.run(
        [
            str(gradlew), ":app:compileDebugKotlin",
            "--no-daemon", "--max-workers=1", "--no-watch-fs", "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    print(result.stdout[-4000:])
    if result.returncode != 0:
        print(result.stderr[-4000:], file=sys.stderr)
        die("compileDebugKotlin failed -- not committing/pushing. See output above.")

    print("== Compile gate passed. Checking for changes to commit. ==")
    subprocess.run(["git", "add", "-A"], cwd=str(REPO_ROOT), check=True)

    status_result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    if not status_result.stdout.strip():
        print("Nothing staged to commit (all steps already applied on a prior run). Skipping commit/push.")
        print("Done.")
        return

    commit_msg = (
        "Write session-scoped distance/steps/elevation records for every workout\n\n"
        "- GoogleHealthManager.kt: writeActivitySessionsBatch() now bundles\n"
        "  DistanceRecord, StepsRecord, and ElevationGainedRecord (plus a\n"
        "  forward-compatible ActiveCaloriesBurnedRecord) into the same\n"
        "  insertRecords call as the ExerciseSessionRecord, scoped to the\n"
        "  exact session time window. Previously these session-level metrics\n"
        "  were computed but only ever used for BitLut's own dashboard\n"
        "  display -- never written to Health Connect, so any other app\n"
        "  reading that workout's own distance/steps/elevation (per Health\n"
        "  Connect's documented time-range-overlap read pattern) found\n"
        "  nothing, or only the loosely-time-matched background aggregate.\n"
        "- A new sessionSubMetricsFor() mirrors workoutMetricDisplays()'s\n"
        "  existing per-exercise-type metric contract exactly, so types that\n"
        "  can't produce a given metric (distance/steps for strength/yoga/\n"
        "  HIIT/pilates, steps for biking/swimming) never get a fabricated\n"
        "  record.\n"
        "- Applies to every workout regardless of source: live Huawei sync\n"
        "  and archive/CSV import both flow through this one write path.\n"
        "- workoutFingerprint() now also hashes activeCaloriesKcal (currently\n"
        "  a no-op; the field is always null today, included for forward\n"
        "  correctness).\n"
        "- Documented the load-bearing write ordering in writeSnapshot() so\n"
        "  a future refactor doesn't let the daily steps reconciliation's\n"
        "  time-range delete silently wipe the new workout StepsRecord.\n"
    )
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    if commit_result.returncode != 0:
        print(commit_result.stdout)
        print(commit_result.stderr, file=sys.stderr)
        die("git commit failed")
    print(commit_result.stdout)

    push_result = subprocess.run(
        ["git", "push", "origin", "HEAD:main"], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    print(push_result.stdout)
    if push_result.returncode != 0:
        print(push_result.stderr, file=sys.stderr)
        die("git push failed")

    print("Done.")


if __name__ == "__main__":
    main()
