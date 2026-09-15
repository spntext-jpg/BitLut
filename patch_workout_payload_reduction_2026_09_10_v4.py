#!/usr/bin/env python3
"""
patch_workout_payload_reduction_2026_09_10_v4.py

Reduces the per-workout Health Connect payload in response to corporate
wellness-app sync failures ("binder died" / rate-limit errors after
roughly two minutes) reported for late August/early September 2026, and
brings project documentation in line with the change. Also removes the
prior delivery-artifact patch script from the repo root (already applied
and confirmed working per its own terminal output).

Code change (GoogleHealthManager.kt)
-------------------------------------
`writeActivitySessionsBatch()` no longer bundles `ElevationGainedRecord`
or `TotalCaloriesBurnedRecord` with a workout. Only `ExerciseSessionRecord`
(duration via its own start/end time), `DistanceRecord`, and `StepsRecord`
remain. `sessionSubMetricsFor()`'s per-exercise-type table and the
`SessionSubMetric` enum were updated to match (the ELEVATION case is
removed entirely, not just unused). The now-orphaned
`estimatedTotalCaloriesKcal()` wrapper was removed after verifying zero
remaining callers -- the underlying `WorkoutCalorieEstimator` utility is
untouched and still backs BitLut's own dashboard calorie display via its
own, separate call site in FinalBitLutShell.kt.

This is a targeted volume reduction, not a confirmed fix: no
corporate-app-side timestamped log has yet confirmed correlation with
BitLut's own sync times. Two other plausible mechanisms were checked and
ruled out before landing on this change: `replaceRecords()` already
upserts via stable `clientRecordId`s rather than Google's documented
delete-and-reinsert anti-pattern, and both the session-scoped and
continuous-metric write paths already use fingerprint/version-stable
`clientRecordVersion`s that shouldn't generate Health Connect changelog
noise on unchanged data. The payload-size angle (large `insertRecords`
transactions, consistent with a "binder died"
`TransactionTooLargeException`-style failure) was judged the more
actionable lever pending real correlated evidence.

Neither removal affects BitLut's own dashboard: `workoutMetricDisplays()`
in FinalBitLutShell.kt still shows hiking/biking elevation and workout
calories, computed from the live Huawei snapshot each sync -- this was
verified to be independent of what gets written to Health Connect before
making this change. Only third-party readers (the corporate app, or any
other Health Connect client) lose access to these two fields per workout
going forward.

Write ordering in writeSnapshot() (writeStepsBatch before
writeActivitySessionsBatch, load-bearing per the 2026-08-30 fix) is
unaffected -- verified unchanged before writing this patch.

Documentation changes
----------------------
sync.md sections 4.7, 4.8, and 4.11; docs/HEALTH_DATA_PERMISSION_MATRIX.md;
docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md; docs/PRIVACY_POLICY.md (a
user-facing document -- corrected its claim that the calorie estimate is
written to Health Connect, and removed an inaccurate "local profile
inputs" claim, verified against WorkoutCalorieEstimator.kt, which uses a
fixed 70kg reference weight and no profile data at all); README.md;
CONTEXT.md; CLAUDE.md; SESSION_HANDOFF.md; docs/BACKLOG.md (new open
investigation item); CHANGELOG.md (new entry for this change, plus a
retroactive entry for the 2026-09-10 battery-sync-reliability patch, which
never got its own changelog entry since it was code/strings-only).

Mandatory workflow already completed before this script was written:
hand-edited a mirror -> real diffs (diff -u against the current canonical
tree, itself reflecting patch_battery_sync_reliability_2026_09_10_v1.py
already applied) -> this script generated from those diffs -> tested on a
clean extraction with a fake gradlew -> byte-diffed against the mirror ->
re-run for idempotency.
"""
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

GOOGLE_HEALTH_MANAGER_FILE = REPO_ROOT / "app" / "src" / "main" / "java" / "com" / "openhealth" / "sync" / "data" / "GoogleHealthManager.kt"
SYNC_FILE = REPO_ROOT / "sync.md"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"
CLAUDE_FILE = REPO_ROOT / "CLAUDE.md"
CONTEXT_FILE = REPO_ROOT / "CONTEXT.md"
README_FILE = REPO_ROOT / "README.md"
HANDOFF_FILE = REPO_ROOT / "SESSION_HANDOFF.md"
BACKLOG_FILE = REPO_ROOT / "docs" / "BACKLOG.md"
PERMISSION_MATRIX_FILE = REPO_ROOT / "docs" / "HEALTH_DATA_PERMISSION_MATRIX.md"
HUAWEI_REVIEW_FILE = REPO_ROOT / "docs" / "HUAWEI_PRODUCTION_REVIEW_PACKAGE.md"
PRIVACY_POLICY_FILE = REPO_ROOT / "docs" / "PRIVACY_POLICY.md"

STALE_PATCH_SCRIPTS = [
    REPO_ROOT / "patch_battery_sync_reliability_2026_09_10_v1.py",
    REPO_ROOT / "patch_workout_payload_reduction_2026_09_10_v2.py",
    REPO_ROOT / "patch_workout_payload_reduction_2026_09_10_v3.py",
]


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
    """Pure insertion: anchor text itself is unchanged and still present after
    the edit, so idempotency cannot key on the anchor's occurrence count (it
    would still be found, as a substring of new_with_anchor, on every re-run).
    Keys instead on unique_marker, a string that only exists after this
    insertion has been applied.
    """
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"  [skip] {description} (already applied)")
        return

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(
            f"{description}: expected exactly 1 occurrence of anchor in {path.name}, "
            f"found {anchor_count}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(anchor, new_with_anchor)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def remove_stale_patch_scripts() -> None:
    for script in STALE_PATCH_SCRIPTS:
        if not script.exists():
            print(f"  [skip] {script.name} already removed")
            continue
        backup(script)
        script.unlink()
        print(f"  [applied] removed stale patch script {script.name}")


def validate_markdown_untouched_by_xml_parser() -> None:
    """This patch doesn't touch strings.xml, but keep the same real-parser
    discipline used in prior patches for any XML-adjacent files it does
    touch. No XML files are edited by this patch; this is a deliberate
    no-op placeholder documenting that this check was considered."""
    pass


def apply_ghm_fix_with_recovery() -> None:
    """GoogleHealthManager.kt's fix needs a three-way check, not the plain
    two-state apply_edit(): a prior patch (v3, 2026-09-10) applied a broken
    replacement on top of this same anchor -- it dropped three real helper
    functions (workoutInteropScore/preferWorkoutSession/
    normalizeWorkoutSessionsForHealthConnect) that happened to sit between
    the doc comment and writeActivitySessionsBatch(), because that patch's
    replacement text was reconstructed from memory instead of surgically
    edited from the real content. That patch's compile gate caught the
    resulting "Unresolved reference" and aborted before committing, but its
    file edits (this script runs after backup, before the compile gate) were
    already written to disk. This function detects and recovers from
    exactly that state, in addition to the normal pristine/already-fixed
    cases, so this script is safe to run regardless of which of the three
    states GoogleHealthManager.kt is currently in.
    """
    path = GOOGLE_HEALTH_MANAGER_FILE
    text = path.read_text(encoding="utf-8")
    description = "GoogleHealthManager.kt: drop ElevationGainedRecord/TotalCaloriesBurnedRecord from writeActivitySessionsBatch, update sessionSubMetricsFor()/SessionSubMetric, remove orphaned estimatedTotalCaloriesKcal()"

    if NEW_GHM_BLOCK in text:
        print(f"  [skip] {description} (already applied)")
        return

    if OLD_GHM_BLOCK in text:
        count = text.count(OLD_GHM_BLOCK)
        if count != 1:
            die(f"{description}: expected 1 occurrence of pristine anchor, found {count}.")
        backup(path)
        text = text.replace(OLD_GHM_BLOCK, NEW_GHM_BLOCK)
        path.write_text(text, encoding="utf-8")
        print(f"  [applied] {description}")
        return

    if BROKEN_GHM_BLOCK in text:
        count = text.count(BROKEN_GHM_BLOCK)
        if count != 1:
            die(f"{description}: expected 1 occurrence of broken (v3) block, found {count}.")
        backup(path)
        text = text.replace(BROKEN_GHM_BLOCK, NEW_GHM_BLOCK)
        path.write_text(text, encoding="utf-8")
        print(f"  [recovered] {description} (repaired a broken partial apply left by patch_workout_payload_reduction_2026_09_10_v3.py, which dropped workoutInteropScore/preferWorkoutSession/normalizeWorkoutSessionsForHealthConnect)")
        return

    die(
        f"{description}: GoogleHealthManager.kt matches none of the three known states "
        "(pristine / already-fixed / v3-broken). Aborting -- source has diverged further "
        "than this script can safely reconcile."
    )


def run_compile_gate() -> None:
    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found; cannot run compile gate")

    cmd = [
        str(gradlew),
        ":app:assembleDebug",
        ":app:lintDebug",
        "--no-daemon",
        "--max-workers=1",
        "--no-watch-fs",
        "--console=plain",
        "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
        "-Pkotlin.compiler.execution.strategy=in-process",
    ]
    print("Running compile gate: " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        die("Compile gate failed. No commit/push performed. See Gradle output above.")


def git_commit_and_push() -> None:
    subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT, check=True)
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    if not status.stdout.strip():
        print("Nothing to commit (already applied and clean).")
        return

    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Reduce workout Health Connect payload (drop elevation/calories), "
            "update docs for corporate-app investigation",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT, check=True)



OLD_GHM_BLOCK = '    private enum class SessionSubMetric { DISTANCE, STEPS, ELEVATION }\n\n    private fun sessionSubMetricsFor(exerciseType: Int): Set<SessionSubMetric> = when (exerciseType) {\n        ExerciseSessionRecord.EXERCISE_TYPE_WALKING,\n        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING,\n        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING_TREADMILL ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_HIKING ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.ELEVATION, SessionSubMetric.STEPS)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_BIKING ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.ELEVATION)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_BIKING_STATIONARY ->\n            setOf(SessionSubMetric.DISTANCE)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER,\n        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL ->\n            setOf(SessionSubMetric.DISTANCE)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING,\n        ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING,\n        ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING,\n        ExerciseSessionRecord.EXERCISE_TYPE_YOGA,\n        ExerciseSessionRecord.EXERCISE_TYPE_PILATES ->\n            emptySet()\n\n        else ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS, SessionSubMetric.ELEVATION)\n    }\n\n\n    /**\n     * Health Connect\'s current workout guidance explicitly rejects overlapping\n     * sessions from the same app. Huawei can occasionally return an explicit\n     * workout together with a lower-information auto-detected session that\n     * overlaps it. Keep the richer source session instead of clipping times\n     * (which would fabricate source data) or letting one malformed overlap\n     * poison the activitySessions category and retry cursor indefinitely.\n     */\n    private fun workoutInteropScore(session: ActivitySessionData): Int {\n        var score = 0\n        if (session.exerciseType != ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT) score += 8\n        if (session.title.isNotBlank() && !SYNTHETIC_WORKOUT_TITLE.matches(session.title)) score += 4\n        if ((session.distanceMeters ?: 0.0) > 0.0) score += 2\n        if ((session.steps ?: 0L) > 0L) score += 2\n        if ((session.totalCaloriesKcal ?: 0.0) > 0.0) score += 2\n        if ((session.activeCaloriesKcal ?: 0.0) > 0.0) score += 1\n        if ((session.elevationMeters ?: 0.0) > 0.0) score += 1\n        return score\n    }\n\n    private fun preferWorkoutSession(\n        current: ActivitySessionData,\n        candidate: ActivitySessionData\n    ): ActivitySessionData {\n        val currentScore = workoutInteropScore(current)\n        val candidateScore = workoutInteropScore(candidate)\n        if (candidateScore != currentScore) return if (candidateScore > currentScore) candidate else current\n\n        val currentDuration = current.endTimeMs - current.startTimeMs\n        val candidateDuration = candidate.endTimeMs - candidate.startTimeMs\n        if (candidateDuration != currentDuration) return if (candidateDuration > currentDuration) candidate else current\n\n        // Stable final tie-break: earlier source session wins.\n        return if (candidate.startTimeMs < current.startTimeMs) candidate else current\n    }\n\n    private fun normalizeWorkoutSessionsForHealthConnect(\n        records: List<ActivitySessionData>\n    ): List<ActivitySessionData> {\n        val exactDeduplicated = records\n            .asSequence()\n            .filter { it.startTimeMs < it.endTimeMs }\n            .groupBy { Pair(it.startTimeMs, it.endTimeMs) }\n            .values\n            .map { duplicates -> duplicates.reduce(::preferWorkoutSession) }\n            .sortedBy { it.startTimeMs }\n\n        if (exactDeduplicated.size < 2) return exactDeduplicated\n\n        val normalized = mutableListOf<ActivitySessionData>()\n        for (session in exactDeduplicated) {\n            val previous = normalized.lastOrNull()\n            if (previous == null || session.startTimeMs >= previous.endTimeMs) {\n                normalized += session\n                continue\n            }\n\n            val preferred = preferWorkoutSession(previous, session)\n            val dropped = if (preferred === previous) session else previous\n            if (preferred !== previous) normalized[normalized.lastIndex] = preferred\n\n            AppLogger.w(\n                TAG,\n                "Dropped overlapping workout before Health Connect write: " +\n                    "kept=${preferred.startTimeMs}..${preferred.endTimeMs}/type=${preferred.exerciseType} " +\n                    "dropped=${dropped.startTimeMs}..${dropped.endTimeMs}/type=${dropped.exerciseType}"\n            )\n        }\n        return normalized\n    }\n\n    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {\n        // BITLUT_WORKOUT_HARDENING_V4\n        val validSessions = normalizeWorkoutSessionsForHealthConnect(records)\n\n        if (validSessions.isEmpty()) {\n            AppLogger.i(TAG, "No activitySessions records to write")\n            return true\n        }\n\n        val client = resolveClient() ?: run {\n            AppLogger.e(TAG, "write activitySessions: no Health Connect client")\n            return false\n        }\n\n        var allSucceeded = true\n        var written = 0\n\n        for (session in validSessions) {\n            persistWorkoutSummary(session)\n            val version = workoutRecordVersion(session)\n            val start = Instant.ofEpochMilli(session.startTimeMs)\n            val end = Instant.ofEpochMilli(session.endTimeMs)\n\n            val exercise = ExerciseSessionRecord(\n                startTime = start,\n                endTime = end,\n                startZoneOffset = offset(start),\n                endZoneOffset = offset(end),\n                exerciseType = session.exerciseType,\n                title = session.title,\n                metadata = bitlutWorkoutMetadata(\n                    "exercise",\n                    start.toEpochMilli(),\n                    end.toEpochMilli(),\n                    version = version\n                )\n            )\n\n            // Health Connect models workout summaries as records sharing the\n            // exercise interval. Insert the session and its calorie summary in\n            // one request so readers never observe a newly-written bare session\n            // before the associated summary arrives.\n            val bundle = mutableListOf<Record>(exercise)\n            val kcal = session.totalCaloriesKcal?.takeIf { it > 0.0 }\n                ?: estimatedTotalCaloriesKcal(session.exerciseType, session.startTimeMs, session.endTimeMs)\n            if (kcal != null && kcal > 0.0) {\n                bundle += TotalCaloriesBurnedRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    energy = Energy.kilocalories(kcal),\n                    // Keep the historical ID so old estimated calorie records\n                    // are upgraded in place instead of duplicated.\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_calories_estimate",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n\n            // 2026-08-30: session.distanceMeters/steps/elevationMeters were\n            // computed correctly (from Huawei\'s own ActivityRecord summary,\n            // see readActivityRecordSummary()\'s per-record fallback) but\n            // never actually written to Health Connect as records scoped to\n            // this exercise session\'s own time window -- only used for\n            // BitLut\'s own dashboard display. Per Health Connect\'s own\n            // documented pattern (a session\'s distance/steps/elevation are\n            // read back by querying those record types over the *same time\n            // range* as the exercise session -- there is no explicit\n            // foreign-key link), any third-party reader -- Google Fit,\n            // Health Connect\'s own UI, or another app -- had nothing\n            // trustworthy to find for this workout\'s own metrics: the only\n            // DistanceRecord/StepsRecord/ElevationGainedRecord in Health\n            // Connect for that time span was the coarse background\n            // aggregate written by writeDistanceBatch/writeStepsBatch/\n            // writeElevationBatch, whose sample windows are already\n            // documented (see readDistance()\'s doc comment) as not lining\n            // up cleanly with an exact workout interval. Writing these\n            // session-scoped records in the same insertRecords bundle as\n            // the exercise itself fixes that for every workout, from every\n            // import source (live sync and archive import both produce the\n            // same ActivitySessionData through this one write path).\n            //\n            // Only include a metric a given exercise type can plausibly\n            // have -- sessionSubMetricsFor() mirrors workoutMetricDisplays()\n            // exactly, so a strength/yoga/HIIT/pilates session is never\n            // given a fabricated distance or step count it couldn\'t have\n            // produced on this device, which would itself be untrustworthy\n            // data.\n            val allowedSubMetrics = sessionSubMetricsFor(session.exerciseType)\n            val sessionDistanceMeters = session.distanceMeters?.takeIf { it > 0.0 }\n            if (SessionSubMetric.DISTANCE in allowedSubMetrics && sessionDistanceMeters != null) {\n                bundle += DistanceRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    distance = Length.meters(sessionDistanceMeters),\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_distance",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n            val sessionSteps = session.steps?.takeIf { it > 0L }\n            if (SessionSubMetric.STEPS in allowedSubMetrics && sessionSteps != null) {\n                bundle += StepsRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    count = sessionSteps,\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_steps",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n            val sessionElevationMeters = session.elevationMeters?.takeIf { it > 0.0 }\n            if (SessionSubMetric.ELEVATION in allowedSubMetrics && sessionElevationMeters != null) {\n                bundle += ElevationGainedRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    elevation = Length.meters(sessionElevationMeters),\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_elevation",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n            val sessionActiveCaloriesKcal = session.activeCaloriesKcal?.takeIf { it > 0.0 }\n            if (sessionActiveCaloriesKcal != null) {\n                bundle += ActiveCaloriesBurnedRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    energy = Energy.kilocalories(sessionActiveCaloriesKcal),\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_active_calories",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n\n            try {\n                client.insertRecords(bundle)\n                written += 1\n            } catch (e: CancellationException) {\n                throw e\n            } catch (e: SecurityException) {\n                AppLogger.e(TAG, "write activitySessions denied by Health Connect: ${e.message}", e)\n                invalidateClientCache()\n                throw e\n            } catch (e: Exception) {\n                // One malformed/overlapping Huawei session must not prevent\n                // unrelated valid workouts in the same sync from being written.\n                allSucceeded = false\n                AppLogger.e(\n                    TAG,\n                    "Workout bundle write failed: start=${session.startTimeMs} end=${session.endTimeMs} " +\n                        "type=${session.exerciseType} error=${e.message}",\n                    e\n                )\n            }\n        }\n\n        AppLogger.i(TAG, "Workout bundles written: $written/${validSessions.size}")\n        return allSucceeded\n    }\n\n\n    /**\n     * MET-formula estimate of total calories burned for a workout, used only\n     * to give third-party Health Connect readers something non-zero to\n     * import (see the call site in [writeActivitySessionsBatch] for why).\n     * Delegates to [com.openhealth.sync.util.WorkoutCalorieEstimator] (sprint\n     * 2026-08-26 extraction) so this exact formula and MET table also back\n     * the workout card\'s own calorie display -- see that object\'s own doc\n     * comment for the full rationale, the formula, and why it is not\n     * measured data.\n     */\n    private fun estimatedTotalCaloriesKcal(exerciseType: Int, startTimeMs: Long, endTimeMs: Long): Double? =\n        com.openhealth.sync.util.WorkoutCalorieEstimator.estimateTotalCaloriesKcal(exerciseType, startTimeMs, endTimeMs)\n'
NEW_GHM_BLOCK = '    private enum class SessionSubMetric { DISTANCE, STEPS }\n\n    private fun sessionSubMetricsFor(exerciseType: Int): Set<SessionSubMetric> = when (exerciseType) {\n        ExerciseSessionRecord.EXERCISE_TYPE_WALKING,\n        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING,\n        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING_TREADMILL ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_HIKING ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_BIKING ->\n            setOf(SessionSubMetric.DISTANCE)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_BIKING_STATIONARY ->\n            setOf(SessionSubMetric.DISTANCE)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER,\n        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL ->\n            setOf(SessionSubMetric.DISTANCE)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING,\n        ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING,\n        ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING,\n        ExerciseSessionRecord.EXERCISE_TYPE_YOGA,\n        ExerciseSessionRecord.EXERCISE_TYPE_PILATES ->\n            emptySet()\n\n        else ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS)\n    }\n\n\n    /**\n     * Health Connect\'s current workout guidance explicitly rejects overlapping\n     * sessions from the same app. Huawei can occasionally return an explicit\n     * workout together with a lower-information auto-detected session that\n     * overlaps it. Keep the richer source session instead of clipping times\n     * (which would fabricate source data) or letting one malformed overlap\n     * poison the activitySessions category and retry cursor indefinitely.\n     */\n    private fun workoutInteropScore(session: ActivitySessionData): Int {\n        var score = 0\n        if (session.exerciseType != ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT) score += 8\n        if (session.title.isNotBlank() && !SYNTHETIC_WORKOUT_TITLE.matches(session.title)) score += 4\n        if ((session.distanceMeters ?: 0.0) > 0.0) score += 2\n        if ((session.steps ?: 0L) > 0L) score += 2\n        if ((session.totalCaloriesKcal ?: 0.0) > 0.0) score += 2\n        if ((session.activeCaloriesKcal ?: 0.0) > 0.0) score += 1\n        if ((session.elevationMeters ?: 0.0) > 0.0) score += 1\n        return score\n    }\n\n    private fun preferWorkoutSession(\n        current: ActivitySessionData,\n        candidate: ActivitySessionData\n    ): ActivitySessionData {\n        val currentScore = workoutInteropScore(current)\n        val candidateScore = workoutInteropScore(candidate)\n        if (candidateScore != currentScore) return if (candidateScore > currentScore) candidate else current\n\n        val currentDuration = current.endTimeMs - current.startTimeMs\n        val candidateDuration = candidate.endTimeMs - candidate.startTimeMs\n        if (candidateDuration != currentDuration) return if (candidateDuration > currentDuration) candidate else current\n\n        // Stable final tie-break: earlier source session wins.\n        return if (candidate.startTimeMs < current.startTimeMs) candidate else current\n    }\n\n    private fun normalizeWorkoutSessionsForHealthConnect(\n        records: List<ActivitySessionData>\n    ): List<ActivitySessionData> {\n        val exactDeduplicated = records\n            .asSequence()\n            .filter { it.startTimeMs < it.endTimeMs }\n            .groupBy { Pair(it.startTimeMs, it.endTimeMs) }\n            .values\n            .map { duplicates -> duplicates.reduce(::preferWorkoutSession) }\n            .sortedBy { it.startTimeMs }\n\n        if (exactDeduplicated.size < 2) return exactDeduplicated\n\n        val normalized = mutableListOf<ActivitySessionData>()\n        for (session in exactDeduplicated) {\n            val previous = normalized.lastOrNull()\n            if (previous == null || session.startTimeMs >= previous.endTimeMs) {\n                normalized += session\n                continue\n            }\n\n            val preferred = preferWorkoutSession(previous, session)\n            val dropped = if (preferred === previous) session else previous\n            if (preferred !== previous) normalized[normalized.lastIndex] = preferred\n\n            AppLogger.w(\n                TAG,\n                "Dropped overlapping workout before Health Connect write: " +\n                    "kept=${preferred.startTimeMs}..${preferred.endTimeMs}/type=${preferred.exerciseType} " +\n                    "dropped=${dropped.startTimeMs}..${dropped.endTimeMs}/type=${dropped.exerciseType}"\n            )\n        }\n        return normalized\n    }\n\n    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {\n        // BITLUT_WORKOUT_HARDENING_V4\n        val validSessions = normalizeWorkoutSessionsForHealthConnect(records)\n\n        if (validSessions.isEmpty()) {\n            AppLogger.i(TAG, "No activitySessions records to write")\n            return true\n        }\n\n        val client = resolveClient() ?: run {\n            AppLogger.e(TAG, "write activitySessions: no Health Connect client")\n            return false\n        }\n\n        var allSucceeded = true\n        var written = 0\n\n        for (session in validSessions) {\n            persistWorkoutSummary(session)\n            val version = workoutRecordVersion(session)\n            val start = Instant.ofEpochMilli(session.startTimeMs)\n            val end = Instant.ofEpochMilli(session.endTimeMs)\n\n            val exercise = ExerciseSessionRecord(\n                startTime = start,\n                endTime = end,\n                startZoneOffset = offset(start),\n                endZoneOffset = offset(end),\n                exerciseType = session.exerciseType,\n                title = session.title,\n                metadata = bitlutWorkoutMetadata(\n                    "exercise",\n                    start.toEpochMilli(),\n                    end.toEpochMilli(),\n                    version = version\n                )\n            )\n\n            // Health Connect models workout summaries as records sharing the\n            // exercise interval.\n            //\n            // 2026-09-10: this bundle previously also included a\n            // TotalCaloriesBurnedRecord (a real Huawei value when available,\n            // else WorkoutCalorieEstimator\'s MET-formula fallback) and, for\n            // hiking/biking, an ElevationGainedRecord. Both removed -- per\n            // Paulo\'s explicit request -- to shrink the per-workout Health\n            // Connect payload after a corporate wellness-app reader started\n            // failing to sync ("binder died" / rate-limit errors after\n            // roughly two minutes) starting in the same window this bundle\n            // was introduced. This is a targeted volume reduction, not a\n            // confirmed fix: no corporate-app-side timestamped log has yet\n            // confirmed the correlation (see sync.md section 4.7 and\n            // docs/BACKLOG.md\'s open investigation item). Neither removal\n            // affects BitLut\'s own dashboard: hiking/biking elevation and\n            // workout calories are displayed there from the live Huawei\n            // snapshot each sync (FinalBitLutShell.kt\'s workoutMetricDisplays()\n            // and WorkoutCalorieEstimator), never read back from what was\n            // previously written to Health Connect.\n            val bundle = mutableListOf<Record>(exercise)\n\n            // 2026-08-30: session.distanceMeters/steps were computed\n            // correctly (from Huawei\'s own ActivityRecord summary, see\n            // readActivityRecordSummary()\'s per-record fallback) but never\n            // actually written to Health Connect as records scoped to this\n            // exercise session\'s own time window -- only used for BitLut\'s\n            // own dashboard display. Per Health Connect\'s own documented\n            // pattern (a session\'s distance/steps are read back by querying\n            // those record types over the *same time range* as the exercise\n            // session -- there is no explicit foreign-key link), any\n            // third-party reader -- Google Fit, Health Connect\'s own UI, or\n            // another app -- had nothing trustworthy to find for this\n            // workout\'s own metrics: the only DistanceRecord/StepsRecord in\n            // Health Connect for that time span was the coarse background\n            // aggregate written by writeDistanceBatch/writeStepsBatch,\n            // whose sample windows are already documented (see\n            // readDistance()\'s doc comment) as not lining up cleanly with\n            // an exact workout interval. Writing these session-scoped\n            // records in the same insertRecords bundle as the exercise\n            // itself fixes that for every workout, from every import\n            // source (live sync and archive import both produce the same\n            // ActivitySessionData through this one write path).\n            //\n            // Only include a metric a given exercise type can plausibly\n            // have and that this bundle still writes -- sessionSubMetricsFor()\n            // previously mirrored workoutMetricDisplays() (BitLut\'s own\n            // dashboard metric selection) exactly, but no longer does after\n            // 2026-09-10\'s elevation removal: workoutMetricDisplays() still\n            // shows elevation for hiking/biking cards, sourced from the live\n            // Huawei snapshot each sync, independent of what this bundle\n            // writes to Health Connect. sessionSubMetricsFor() now only\n            // decides what\'s written for third-party readers, not what\n            // BitLut itself displays. Strength/yoga/HIIT/pilates still never\n            // get a fabricated distance or step count they couldn\'t have\n            // produced on this device, which would itself be untrustworthy\n            // data.\n            val allowedSubMetrics = sessionSubMetricsFor(session.exerciseType)\n            val sessionDistanceMeters = session.distanceMeters?.takeIf { it > 0.0 }\n            if (SessionSubMetric.DISTANCE in allowedSubMetrics && sessionDistanceMeters != null) {\n                bundle += DistanceRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    distance = Length.meters(sessionDistanceMeters),\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_distance",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n            val sessionSteps = session.steps?.takeIf { it > 0L }\n            if (SessionSubMetric.STEPS in allowedSubMetrics && sessionSteps != null) {\n                bundle += StepsRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    count = sessionSteps,\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_steps",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n            val sessionActiveCaloriesKcal = session.activeCaloriesKcal?.takeIf { it > 0.0 }\n            if (sessionActiveCaloriesKcal != null) {\n                bundle += ActiveCaloriesBurnedRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    energy = Energy.kilocalories(sessionActiveCaloriesKcal),\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_active_calories",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n\n            try {\n                client.insertRecords(bundle)\n                written += 1\n            } catch (e: CancellationException) {\n                throw e\n            } catch (e: SecurityException) {\n                AppLogger.e(TAG, "write activitySessions denied by Health Connect: ${e.message}", e)\n                invalidateClientCache()\n                throw e\n            } catch (e: Exception) {\n                // One malformed/overlapping Huawei session must not prevent\n                // unrelated valid workouts in the same sync from being written.\n                allSucceeded = false\n                AppLogger.e(\n                    TAG,\n                    "Workout bundle write failed: start=${session.startTimeMs} end=${session.endTimeMs} " +\n                        "type=${session.exerciseType} error=${e.message}",\n                    e\n                )\n            }\n        }\n\n        AppLogger.i(TAG, "Workout bundles written: $written/${validSessions.size}")\n        return allSucceeded\n    }\n'
BROKEN_GHM_BLOCK = '    private enum class SessionSubMetric { DISTANCE, STEPS }\n\n    // 2026-09-10: elevation removed from this set entirely (previously\n    // ELEVATION for hiking/biking) -- per Paulo\'s explicit request to\n    // reduce the per-workout Health Connect payload after a corporate\n    // wellness-app reader started failing to sync ("binder died" / rate\n    // limit errors after ~2 minutes). See writeActivitySessionsBatch()\'s\n    // doc comment for the full rationale and what this does/doesn\'t fix.\n    private fun sessionSubMetricsFor(exerciseType: Int): Set<SessionSubMetric> = when (exerciseType) {\n        ExerciseSessionRecord.EXERCISE_TYPE_WALKING,\n        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING,\n        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING_TREADMILL ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_HIKING ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_BIKING ->\n            setOf(SessionSubMetric.DISTANCE)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_BIKING_STATIONARY ->\n            setOf(SessionSubMetric.DISTANCE)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER,\n        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL ->\n            setOf(SessionSubMetric.DISTANCE)\n\n        ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING,\n        ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING,\n        ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING,\n        ExerciseSessionRecord.EXERCISE_TYPE_YOGA,\n        ExerciseSessionRecord.EXERCISE_TYPE_PILATES ->\n            emptySet()\n\n        else ->\n            setOf(SessionSubMetric.DISTANCE, SessionSubMetric.STEPS)\n    }\n\n\n    /**\n     * Health Connect\'s current workout guidance explicitly rejects overlapping\n     * sessions from the same app. Huawei can occasionally return an explicit\n     * workout together with a lower-information auto-detected session that\n     * overlaps it. Keep the richer source session instead of clipping times\n     * or dropping both -- see normalizeWorkoutSessionsForHealthConnect() for\n     * the exact overlap-resolution rule.\n     */\n    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {\n        // BITLUT_WORKOUT_HARDENING_V4\n        val validSessions = normalizeWorkoutSessionsForHealthConnect(records)\n\n        if (validSessions.isEmpty()) {\n            AppLogger.i(TAG, "No activitySessions records to write")\n            return true\n        }\n\n        val client = resolveClient() ?: run {\n            AppLogger.e(TAG, "write activitySessions: no Health Connect client")\n            return false\n        }\n\n        var allSucceeded = true\n        var written = 0\n\n        for (session in validSessions) {\n            persistWorkoutSummary(session)\n            val version = workoutRecordVersion(session)\n            val start = Instant.ofEpochMilli(session.startTimeMs)\n            val end = Instant.ofEpochMilli(session.endTimeMs)\n\n            val exercise = ExerciseSessionRecord(\n                startTime = start,\n                endTime = end,\n                startZoneOffset = offset(start),\n                endZoneOffset = offset(end),\n                exerciseType = session.exerciseType,\n                title = session.title,\n                metadata = bitlutWorkoutMetadata(\n                    "exercise",\n                    start.toEpochMilli(),\n                    end.toEpochMilli(),\n                    version = version\n                )\n            )\n\n            // Health Connect models workout summaries as records sharing the\n            // exercise interval.\n            //\n            // 2026-09-10: this bundle previously also included a\n            // TotalCaloriesBurnedRecord (a real Huawei value when available,\n            // else WorkoutCalorieEstimator\'s MET-formula fallback) and, for\n            // hiking/biking, an ElevationGainedRecord. Both removed -- per\n            // Paulo\'s explicit request -- to shrink the per-workout Health\n            // Connect payload after a corporate wellness-app reader started\n            // failing to sync ("binder died" / rate-limit errors after\n            // roughly two minutes) starting in the same window this bundle\n            // was introduced. This is a targeted volume reduction, not a\n            // confirmed fix: no corporate-app-side timestamped log has yet\n            // confirmed the correlation (see sync.md section 4.6 and\n            // docs/BACKLOG.md\'s open investigation item). Neither removal\n            // affects BitLut\'s own dashboard: hiking/biking elevation and\n            // workout calories are displayed there from the live Huawei\n            // snapshot each sync (FinalBitLutShell.kt\'s workoutMetricDisplays()\n            // and WorkoutCalorieEstimator), never read back from what was\n            // previously written to Health Connect.\n            val bundle = mutableListOf<Record>(exercise)\n\n            // 2026-08-30: session.distanceMeters/steps were computed\n            // correctly (from Huawei\'s own ActivityRecord summary, see\n            // readActivityRecordSummary()\'s per-record fallback) but never\n            // actually written to Health Connect as records scoped to this\n            // exercise session\'s own time window -- only used for BitLut\'s\n            // own dashboard display. Per Health Connect\'s own documented\n            // pattern (a session\'s distance/steps are read back by querying\n            // those record types over the *same time range* as the exercise\n            // session -- there is no explicit foreign-key link), any\n            // third-party reader -- Google Fit, Health Connect\'s own UI, or\n            // another app -- had nothing trustworthy to find for this\n            // workout\'s own metrics: the only DistanceRecord/StepsRecord in\n            // Health Connect for that time span was the coarse background\n            // aggregate written by writeDistanceBatch/writeStepsBatch,\n            // whose sample windows are already documented (see\n            // readDistance()\'s doc comment) as not lining up cleanly with\n            // an exact workout interval. Writing these session-scoped\n            // records in the same insertRecords bundle as the exercise\n            // itself fixes that for every workout, from every import\n            // source (live sync and archive import both produce the same\n            // ActivitySessionData through this one write path).\n            //\n            // Only include a metric a given exercise type can plausibly\n            // have and that this bundle still writes -- sessionSubMetricsFor()\n            // previously mirrored workoutMetricDisplays() (BitLut\'s own\n            // dashboard metric selection) exactly, but no longer does after\n            // 2026-09-10\'s elevation removal: workoutMetricDisplays() still\n            // shows elevation for hiking/biking cards, sourced from the live\n            // Huawei snapshot each sync, independent of what this bundle\n            // writes to Health Connect. sessionSubMetricsFor() now only\n            // decides what\'s written for third-party readers, not what\n            // BitLut itself displays. Strength/yoga/HIIT/pilates still never\n            // get a fabricated distance or step count they couldn\'t have\n            // produced on this device, which would itself be untrustworthy\n            // data.\n            val allowedSubMetrics = sessionSubMetricsFor(session.exerciseType)\n            val sessionDistanceMeters = session.distanceMeters?.takeIf { it > 0.0 }\n            if (SessionSubMetric.DISTANCE in allowedSubMetrics && sessionDistanceMeters != null) {\n                bundle += DistanceRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    distance = Length.meters(sessionDistanceMeters),\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_distance",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n            val sessionSteps = session.steps?.takeIf { it > 0L }\n            if (SessionSubMetric.STEPS in allowedSubMetrics && sessionSteps != null) {\n                bundle += StepsRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    count = sessionSteps,\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_steps",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n            val sessionActiveCaloriesKcal = session.activeCaloriesKcal?.takeIf { it > 0.0 }\n            if (sessionActiveCaloriesKcal != null) {\n                bundle += ActiveCaloriesBurnedRecord(\n                    startTime = start,\n                    endTime = end,\n                    startZoneOffset = offset(start),\n                    endZoneOffset = offset(end),\n                    energy = Energy.kilocalories(sessionActiveCaloriesKcal),\n                    metadata = bitlutWorkoutMetadata(\n                        "exercise_active_calories",\n                        start.toEpochMilli(),\n                        end.toEpochMilli(),\n                        version = version\n                    )\n                )\n            }\n\n            try {\n                client.insertRecords(bundle)\n                written += 1\n            } catch (e: CancellationException) {\n                throw e\n            } catch (e: SecurityException) {\n                AppLogger.e(TAG, "write activitySessions denied by Health Connect: ${e.message}", e)\n                invalidateClientCache()\n                throw e\n            } catch (e: Exception) {\n                // One malformed/overlapping Huawei session must not prevent\n                // unrelated valid workouts in the same sync from being written.\n                allSucceeded = false\n                AppLogger.e(\n                    TAG,\n                    "Workout bundle write failed: start=${session.startTimeMs} end=${session.endTimeMs} " +\n                        "type=${session.exerciseType} error=${e.message}",\n                    e\n                )\n            }\n        }\n\n        AppLogger.i(TAG, "Workout bundles written: $written/${validSessions.size}")\n        return allSucceeded\n    }\n\n'
OLD_SYNC_47 = '**The fix.** `writeActivitySessionsBatch()` now bundles\n`DistanceRecord`/`StepsRecord`/`ElevationGainedRecord`/\n`ActiveCaloriesBurnedRecord` into the **same `insertRecords` call** as the\n`ExerciseSessionRecord`, scoped to the session\'s **exact** `startTime`/\n`endTime` — so a time-range-overlap query from any reader now finds real,\naccurately-scoped data for that specific workout, not a coarse background\nguess.\n\n**Per-exercise-type gating (`sessionSubMetricsFor`).** Not every exercise\ntype can plausibly produce every metric — writing a fabricated `DistanceRecord`\nfor a strength-training or yoga session would itself be untrustworthy data,\nin the opposite direction from the original bug. `sessionSubMetricsFor()`\nmirrors, metric-for-metric, the exact per-type contract already established\nby the dashboard\'s own `workoutMetricDisplays()` in `FinalBitLutShell.kt`\n(so there is exactly one place that decides "what metrics make sense for\nthis exercise type," reused for both what gets *shown* and what gets\n*written*):\n\n| Exercise type(s) | Distance | Steps | Elevation |\n|---|---|---|---|\n| Walking, Running, Running (treadmill) | ✓ | ✓ | |\n| Hiking | ✓ | ✓ | ✓ |\n| Biking (outdoor) | ✓ | | ✓ |\n| Biking (stationary) | ✓ | | |\n| Swimming (open water, pool) | ✓ | | |\n| Strength training, Weightlifting, HIIT, Yoga, Pilates | | | |\n| Everything else (fallback) | ✓ | ✓ | ✓ |\n\n`ActiveCaloriesBurnedRecord` is written whenever\n`session.activeCaloriesKcal` is non-null and positive, with no per-type\ngate — it is currently always `null` in practice, since neither\n`HuaweiHealthManager` nor the archive/CSV import parser populates that field\ntoday (Huawei\'s activeCalories category is itself scope-gated behind 50005\nfor this individual-developer account, per `WorkoutCalorieEstimator`\'s own\ndoc comment). The write path handles it correctly regardless, so a future\ndata source populating it needs no further plumbing change here.\n\n**Applies to every workout, from every import source.** Live sync\n(`HuaweiHealthManager.readActivitySessions`) and archive/CSV import\n(`HuaweiExportParser`) both produce the same `ActivitySessionData` shape and\nflow through this one `writeActivitySessionsBatch()` write path — the fix\ncovers both without any source-specific code.\n\n**No new Health Connect permissions required.** BitLut already held write\npermission for all four record types (`HealthPermissionPolicy`, 4.13),\nsince they were already being written as background aggregates.\n\n'
NEW_SYNC_47 = '**The fix (2026-08-30/31).** `writeActivitySessionsBatch()` started bundling\n`DistanceRecord`/`StepsRecord`/`ElevationGainedRecord`/\n`ActiveCaloriesBurnedRecord`, plus a `TotalCaloriesBurnedRecord` (4.11),\ninto the **same `insertRecords` call** as the `ExerciseSessionRecord`,\nscoped to the session\'s **exact** `startTime`/`endTime` — so a\ntime-range-overlap query from any reader now finds real, accurately-scoped\ndata for that specific workout, not a coarse background guess.\n\n**Reduced scope (2026-09-10).** `ElevationGainedRecord` and\n`TotalCaloriesBurnedRecord` were removed from this bundle — Distance and\nSteps are the only sub-metrics still written. Trigger: the corporate\nwellness app started failing to sync from Health Connect ("binder died" /\nrate-limit errors after roughly two minutes) in the same late-August/\nearly-September window this bundle was introduced. Paulo asked to shrink\nthe per-workout payload as a direct response; distance, duration (from the\nsession\'s own `startTime`/`endTime`), and steps were kept as the minimum\nthe corporate app actually needs, elevation and calories were judged\nnon-essential for that reader and cut. **This is a targeted reduction, not\na confirmed fix** — no corporate-app-side timestamped log has yet\nconfirmed correlation with BitLut\'s own sync times; see `docs/BACKLOG.md`\'s\nopen investigation item. If a future correlated log rules this out, both\nrecords can be reintroduced from this same section\'s pre-2026-09-10\nhistory without re-deriving the design. Neither removal affects BitLut\'s\nown dashboard: `workoutMetricDisplays()` in `FinalBitLutShell.kt` still\nshows hiking/biking elevation and workout calories, computed from the live\nHuawei snapshot each sync — never read back from what was previously\nwritten to Health Connect.\n\n**Per-exercise-type gating (`sessionSubMetricsFor`).** Not every exercise\ntype can plausibly produce every metric — writing a fabricated `DistanceRecord`\nfor a strength-training or yoga session would itself be untrustworthy data,\nin the opposite direction from the original bug. As of 2026-09-10,\n`sessionSubMetricsFor()` no longer mirrors `workoutMetricDisplays()`\nexactly (that dashboard function still selects elevation for hiking/biking\ncards; this write-path function no longer has an elevation case at all) —\nit now only decides what\'s written to Health Connect for third-party\nreaders, independent of what BitLut itself displays:\n\n| Exercise type(s) | Distance | Steps |\n|---|---|---|\n| Walking, Running, Running (treadmill) | ✓ | ✓ |\n| Hiking | ✓ | ✓ |\n| Biking (outdoor) | ✓ | |\n| Biking (stationary) | ✓ | |\n| Swimming (open water, pool) | ✓ | |\n| Strength training, Weightlifting, HIIT, Yoga, Pilates | | |\n| Everything else (fallback) | ✓ | ✓ |\n\n`ActiveCaloriesBurnedRecord` is written whenever\n`session.activeCaloriesKcal` is non-null and positive, with no per-type\ngate — it is currently always `null` in practice, since neither\n`HuaweiHealthManager` nor the archive/CSV import parser populates that field\ntoday (Huawei\'s activeCalories category is itself scope-gated behind 50005\nfor this individual-developer account, per `WorkoutCalorieEstimator`\'s own\ndoc comment). The write path handles it correctly regardless, so a future\ndata source populating it needs no further plumbing change here. This\nrecord was left in place (unlike the calorie *estimate*, 4.11) because it\nalready contributes nothing to the payload today.\n\n**Applies to every workout, from every import source.** Live sync\n(`HuaweiHealthManager.readActivitySessions`) and archive/CSV import\n(`HuaweiExportParser`) both produce the same `ActivitySessionData` shape and\nflow through this one `writeActivitySessionsBatch()` write path — the fix\ncovers both without any source-specific code.\n\n**No new Health Connect permissions required.** BitLut already held write\npermission for all record types discussed here (`HealthPermissionPolicy`,\n4.13), since they were already being written as background aggregates.\n\n'
OLD_SYNC_411 = '### 4.11 Calorie estimation (`WorkoutCalorieEstimator`) — the one explicit exception to "never fabricate data"\n\nReal per-workout active-calorie data from Huawei requires the\n`HEALTHKIT_CALORIES_READ` scope, which BitLut has never requested (its\ncurrent scope array is Step/Distance/Activity/ActivityRecord/HistoryWeek\nonly — see `docs/SCALING_ROADMAP.md` section 3). This is why\n`activeCalories` reads return 50005: an unrequested scope, not a denied\none. It is **not** part of the permanently-closed Advanced tier (3.2\ncorrectly lists active calories as part of the individual-developer-\nreachable activity tier) and is understood, per Huawei\'s own developer\ndocumentation, to be unrestricted, quickly-approved Basic-tier data — see\n`docs/SCALING_ROADMAP.md` for the request plan. Until that scope is\nrequested and approved, to give third-party readers *something* non-zero\nto import for a workout\'s total calories,\n`WorkoutCalorieEstimator.estimateTotalCaloriesKcal(exerciseType,\nstartTimeMs, endTimeMs)` computes a standard MET-formula estimate:\n\n```\nkcal = MET * 3.5 * 70.0(kg reference weight) * durationMinutes / 200.0\n```\n\nMET values are the "general/moderate" variant per exercise type, drawn from\nthe Compendium of Physical Activities (Ainsworth et al.) — the standard\nreference most fitness calorie calculators cite — since Huawei\'s activity\nrecords carry no separate intensity signal that would justify picking a\ndifferent band. The 70&nbsp;kg reference weight is the conventional default\nused across MET calculators when no real body weight is available; BitLut\nhas no access to the user\'s actual weight, and adding that would introduce\na new data category, which this feature is explicitly scoped to avoid.\n\nThis is documented, in the code itself and in\n`docs/HEALTH_DATA_PERMISSION_MATRIX.md`, as the **one explicit, deliberate\nexception** to this project\'s otherwise-absolute "never synthesize fake\nhealth data" rule — made only because a plausible-but-labeled estimate\nserves interoperability better than a hard zero, and only for total\ncalories specifically, never for distance, steps, or elevation, which are\nalways either real Huawei data or omitted. The same formula and MET table\nback both the Health Connect write (`estimatedTotalCaloriesKcal`, called\nfrom `writeActivitySessionsBatch`) and the workout card\'s own calorie\ndisplay fallback (`workoutMetricDisplays` in `FinalBitLutShell.kt`) — a\nsingle shared implementation (extracted 2026-08-26) so the two call sites\ncan never silently drift apart.\n\n'
NEW_SYNC_411 = '### 4.11 Calorie estimation (`WorkoutCalorieEstimator`) — dashboard-only since 2026-09-10\n\nReal per-workout active-calorie data from Huawei requires the\n`HEALTHKIT_CALORIES_READ` scope, which BitLut has never requested (its\ncurrent scope array is Step/Distance/Activity/ActivityRecord/HistoryWeek\nonly — see `docs/SCALING_ROADMAP.md` section 3). This is why\n`activeCalories` reads return 50005: an unrequested scope, not a denied\none. It is **not** part of the permanently-closed Advanced tier (3.2\ncorrectly lists active calories as part of the individual-developer-\nreachable activity tier) and is understood, per Huawei\'s own developer\ndocumentation, to be unrestricted, quickly-approved Basic-tier data — see\n`docs/SCALING_ROADMAP.md` for the request plan.\n\n`WorkoutCalorieEstimator.estimateTotalCaloriesKcal(exerciseType,\nstartTimeMs, endTimeMs)` computes a standard MET-formula estimate:\n\n```\nkcal = MET * 3.5 * 70.0(kg reference weight) * durationMinutes / 200.0\n```\n\nMET values are the "general/moderate" variant per exercise type, drawn from\nthe Compendium of Physical Activities (Ainsworth et al.) — the standard\nreference most fitness calorie calculators cite — since Huawei\'s activity\nrecords carry no separate intensity signal that would justify picking a\ndifferent band. The 70&nbsp;kg reference weight is the conventional default\nused across MET calculators when no real body weight is available; BitLut\nhas no access to the user\'s actual weight, and adding that would introduce\na new data category, which this feature is explicitly scoped to avoid.\n\n**Until 2026-09-10, this estimate was also written to Health Connect** as\na `TotalCaloriesBurnedRecord` bundled with every workout\n(`writeActivitySessionsBatch`, 4.7) — documented, in the code itself and in\n`docs/HEALTH_DATA_PERMISSION_MATRIX.md`, as the **one explicit, deliberate\nexception** to this project\'s otherwise-absolute "never synthesize fake\nhealth data" rule, made only because a plausible-but-labeled estimate\nserved interoperability better than a hard zero. **That Health Connect\nwrite was removed in 4.7\'s 2026-09-10 payload-reduction change** — the\nestimate is no longer sent to third-party readers at all, calorie data or\nnone. The exception itself, and the formula, are unchanged: `\nWorkoutCalorieEstimator` is still the single shared implementation\n(extracted 2026-08-26) behind BitLut\'s own workout card calorie display\nfallback (`workoutMetricDisplays` in `FinalBitLutShell.kt`), which is\nunaffected by the Health Connect write\'s removal since it always read the\nlive Huawei snapshot directly, never Health Connect\'s stored record. If\n`HEALTHKIT_CALORIES_READ` is ever approved (`docs/SCALING_ROADMAP.md`),\nthis estimate stops mattering for real Huawei-provided workouts either\nway, via the existing `?:` fallback pattern in both call sites.\n\n'
OLD_HDPM_BLOCK = '## Documented exception: estimated workout calories (2026-08-25)\n\nWhen Huawei does not provide workout calories for a session, BitLut may use the\nexisting user-approved MET-formula **estimate** as a `TotalCaloriesBurnedRecord`.\nMeasured Huawei workout calories always win when present. This exception is\nscoped narrowly:\n\n- Only `TotalCaloriesBurnedRecord` is estimated. No other record type in\n  this matrix is or should be synthesized.\n- Dashboard strength calories may use the same documented estimator only as a clearly bounded fallback when a measured workout calorie value is absent. Other workout metrics are never synthesized.\n- `TotalCaloriesBurnedRecord` is used specifically because it is a distinct\n  Health Connect data type from `ActiveCaloriesBurnedRecord` (Huawei\'s\n  active-calorie category, currently returning 50005 because BitLut has\n  never requested the `HEALTHKIT_CALORIES_READ` scope for it -- see\n  `docs/SCALING_ROADMAP.md` -- not because it is permanently blocked) --\n  this avoids conflating\n  an estimate with the exact record type users and other apps already\n  expect to mean "measured by a real sensor."\n- Requires `android.permission.health.READ_TOTAL_CALORIES_BURNED` /\n  `WRITE_TOTAL_CALORIES_BURNED`, declared in `AndroidManifest.xml` and\n  requested via `HealthPermissionPolicy` -- itself a deliberate, one-off\n  exception to this project\'s general "no new Health Connect/Huawei\n  permissions" rule.\n\n'
NEW_HDPM_BLOCK = '## Documented exception: estimated workout calories (2026-08-25) — dashboard display only since 2026-09-10\n\nWhen Huawei does not provide workout calories for a session, BitLut may use the\nexisting user-approved MET-formula **estimate** for the workout card\'s own\ncalorie display (`workoutMetricDisplays` in `FinalBitLutShell.kt`).\nMeasured Huawei workout calories always win when present. This exception is\nscoped narrowly:\n\n- Only the workout card\'s own calorie display is estimated. No record type\n  in this matrix is or should be synthesized and written to Health Connect.\n- Dashboard strength calories may use the same documented estimator only as a clearly bounded fallback when a measured workout calorie value is absent. Other workout metrics are never synthesized.\n- **Until 2026-09-10, this estimate was also written to Health Connect** as\n  a `TotalCaloriesBurnedRecord` bundled with every workout. That write was\n  removed to shrink the per-workout Health Connect payload after a\n  corporate wellness-app reader started failing to sync ("binder died" /\n  rate-limit errors) — see `sync.md` sections 4.7 and 4.11 for the full\n  detail, and `docs/BACKLOG.md` for the open question of whether this\n  actually explains the reader\'s failure. The MET estimate itself, and its\n  use for BitLut\'s own dashboard, are unchanged.\n- `ActiveCaloriesBurnedRecord` (Huawei\'s active-calorie category, currently\n  returning 50005 because BitLut has never requested the\n  `HEALTHKIT_CALORIES_READ` scope for it -- see `docs/SCALING_ROADMAP.md`\n  -- not because it is permanently blocked) is a separate, distinct record\n  type from the estimate discussed here and was never itself estimated;\n  it is only ever written with a real Huawei-provided value, which is\n  currently always absent.\n- Requires `android.permission.health.READ_TOTAL_CALORIES_BURNED` /\n  `WRITE_TOTAL_CALORIES_BURNED`, declared in `AndroidManifest.xml` and\n  requested via `HealthPermissionPolicy` -- itself a deliberate, one-off\n  exception to this project\'s general "no new Health Connect/Huawei\n  permissions" rule. This permission is left in place even though the\n  write no longer happens, since the underlying Health Connect record\n  type may be written again if a correlated log rules out this cause.\n\n## Session-scoped workout sub-records (2026-08-30, reduced 2026-09-10)\n\n`writeActivitySessionsBatch()` bundles Distance and Steps records scoped to\neach workout\'s own exact time window, for exercise types where that metric\nis plausible (`sessionSubMetricsFor()` in `GoogleHealthManager.kt`; see\n`sync.md` section 4.7 for the full per-type table). Elevation and total\ncalories were removed from this bundle on 2026-09-10 -- both metrics\nremain unaffected in the **continuous, non-workout-scoped** background\nelevation/calorie streams covered by the main scope table above, and in\nBitLut\'s own dashboard display, which reads the live Huawei snapshot\ndirectly rather than what was written to Health Connect.\n\n'
CHANGELOG_INSERTION = '## 2026-09-10 (b) -- workout Health Connect payload reduced (elevation, calories removed)\n\n- **Corporate wellness app sync failures reported** (late August/early\n  September 2026): "binder died" and rate-limit errors after roughly two\n  minutes when the corporate app tries to sync from Health Connect. No\n  corporate-app-side timestamped log exists yet to confirm correlation\n  with BitLut\'s own sync activity -- tracked as an open investigation in\n  `docs/BACKLOG.md`.\n- **As a direct, requested response, reduced the per-workout Health\n  Connect payload.** `writeActivitySessionsBatch()` (`GoogleHealthManager.kt`)\n  no longer bundles `ElevationGainedRecord` or `TotalCaloriesBurnedRecord`\n  with a workout -- only `ExerciseSessionRecord` (which carries duration\n  via its own start/end time), `DistanceRecord`, and `StepsRecord` remain.\n  `sessionSubMetricsFor()`\'s per-exercise-type table and the\n  `SessionSubMetric` enum were updated to match (ELEVATION case removed\n  entirely). The now-orphaned `estimatedTotalCaloriesKcal()` wrapper in\n  `GoogleHealthManager.kt` was removed (verified zero remaining callers);\n  the underlying `WorkoutCalorieEstimator` utility is untouched and still\n  backs BitLut\'s own dashboard calorie display directly.\n- **This is a targeted volume reduction, not a confirmed fix** for the\n  corporate app\'s errors -- documented as such in `sync.md` sections 4.7\n  and 4.11, and `docs/HEALTH_DATA_PERMISSION_MATRIX.md`. Both database\n  investigation avenues were checked before landing on this change:\n  `replaceRecords()` already uses `insertRecords` as a stable-ID upsert,\n  not Google\'s documented delete-and-reinsert anti-pattern, and both the\n  session-scoped and continuous-metric write paths already use\n  fingerprint/version-stable `clientRecordVersion`s that shouldn\'t\n  generate Health Connect changelog noise on unchanged data -- so the\n  payload-size angle (large `insertRecords` transactions, consistent with\n  a "binder died" `TransactionTooLargeException`-style failure) was judged\n  the more actionable lever pending real correlated evidence.\n- **Neither BitLut\'s own dashboard is affected.** Hiking/biking elevation\n  and workout calories are still shown on BitLut\'s workout cards\n  (`workoutMetricDisplays()` in `FinalBitLutShell.kt`), computed from the\n  live Huawei snapshot each sync -- this was already independent of what\n  gets written to Health Connect, confirmed before making this change.\n  Only third-party readers (the corporate app, or any other Health\n  Connect client) lose access to these two fields per workout going\n  forward.\n- `docs/HEALTH_DATA_PERMISSION_MATRIX.md` corrected to reflect the\n  Health-Connect-write removal for the calorie estimate; `sync.md`\n  sections 4.7 and 4.11 rewritten with the full before/after and the\n  explicit "not a confirmed fix" caveat; `docs/BACKLOG.md` updated with\n  the open investigation item.\n\n## 2026-09-10 -- Android 12+ battery-optimization hint, periodic-sync reliability, DRY/YAGNI pass\n\n- **Root-caused a "sync got worse" report as NOT a code regression.**\n  Diffed two repomix exports taken before and after Paulo\'s own manual\n  code changes: `app/` source was byte-identical across both, and the\n  2026-09-02/03 documentation patches that predated this report only ever\n  touched `.md` files (confirmed against their own file lists) -- neither\n  could have caused a behavior change. Real cause, from a real-device\n  diagnostic log (Xiaomi M2102K1G, Android 13/MIUI): a ~5.2 hour gap where\n  the 30-minute periodic background sync never ran, only catching up once\n  the app was opened manually -- MIUI/HyperOS force-stopping the app\n  process, the same class of issue as Huawei EMUI\'s "Protected Apps"\n  behavior.\n- **`SyncApplication.onCreate()` now schedules the periodic sync and\n  evening reminder**, moved from `MainActivity.onCreate()`, so\n  BitLut\'s own idempotent scheduling call (`ExistingPeriodicWorkPolicy.KEEP`\n  plus a one-time migration flag, both already idempotent) runs on every\n  process start, not only when a person opens the app. Deliberately does\n  **not** add a custom `BOOT_COMPLETED` receiver -- verified WorkManager\'s\n  own `RescheduleReceiver`/`ForceStopRunnable` already handle reboot and\n  force-stop recovery internally; a custom receiver would be redundant\n  (YAGNI).\n- **New Android 12+ (API 31) `BatteryOptimizationCard` in Settings**\n  (`BatteryOptimizationHelper.kt`), shown when the OS reports BitLut is\n  not exempt from battery optimization. Opens the general "ignore battery\n  optimizations" settings list (`ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS`)\n  rather than the direct one-tap exemption dialog, which needs an extra\n  manifest permission meant for apps whose core function requires it\n  (VPNs, alarm clocks) -- not best-effort background sync like BitLut\'s.\n  No new manifest permission added. Re-evaluated on every `onResume()` so\n  the card disappears immediately once the person grants the exemption.\n- **Code-quality pass (DRY/SOLID/KISS/YAGNI), requested in the same\n  sprint.** Consolidated `GoogleHealthManager`\'s four near-identical\n  `write*Batch` functions into a single `writeContinuousMetricBatch()`\n  helper. Consolidated `FinalBitLutShell.kt`\'s `PrimaryButton`/\n  `SecondaryButton` around a shared `PillActionButton` core (both keep\n  their existing call signatures). Removed `WorkoutFilterPrefs`\'\n  `setMinDurationMinutes()`/`setExcludedExerciseTypes()`/\n  `MIN_DURATION_PRESETS_MINUTES` -- zero callers anywhere in the codebase\n  (verified by exact-name grep, not a heuristic), leftover from a Settings\n  UI that was removed; Paulo\'s explicit call to delete rather than keep\n  for later. `FinalBitLutShell.kt`\'s size (~2500 lines, 41 composables)\n  was noted as a Single-Responsibility observation but deliberately not\n  acted on -- a real refactor without a real compiler available to verify\n  it was judged not worth the regression risk. A first-pass automated\n  unused-import regex sweep was run and discarded as unreliable (it\n  flagged obviously-used symbols like `ComponentActivity`); none of its\n  findings were acted on.\n- Delivered as `patch_battery_sync_reliability_2026_09_10_v1.py`. This\n  changelog entry was added retroactively (2026-09-10, same day, later\n  patch) -- the original patch was code/strings-only and didn\'t touch any\n  `.md` doc.\n\n'

def main() -> None:
    print("=== 1/11: GoogleHealthManager.kt -- remove Elevation/Calories from workout bundle ===")
    apply_ghm_fix_with_recovery()

    print("=== 2/11: sync.md sections 4.7 and 4.8 ===")
    apply_edit(
        SYNC_FILE,
        old=OLD_SYNC_47,
        new=NEW_SYNC_47,
        expected_old_count=1,
        expected_new_count=1,
        description="sync.md: rewrite section 4.7 (workout sub-record bundle, reduced scope)",
    )
    apply_edit(
        SYNC_FILE,
        old=(
            "- **`bitlutWorkoutMetadata(...)`** → `Metadata.activelyRecorded(...)`. Used\n"
            "  for exercise sessions and their calorie/distance/steps/elevation\n"
            "  sub-records — Huawei documents this data as produced only after the user\n"
        ),
        new=(
            "- **`bitlutWorkoutMetadata(...)`** → `Metadata.activelyRecorded(...)`. Used\n"
            "  for exercise sessions and their bundled Distance/Steps sub-records\n"
            "  — Huawei documents this data as produced only after the user\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="sync.md: correct bitlutWorkoutMetadata() bullet in section 4.8",
    )

    print("=== 3/11: sync.md section 4.11 ===")
    apply_edit(
        SYNC_FILE,
        old=OLD_SYNC_411,
        new=NEW_SYNC_411,
        expected_old_count=1,
        expected_new_count=1,
        description="sync.md: rewrite section 4.11 (calorie estimate now dashboard-only)",
    )

    print("=== 4/11: docs/HEALTH_DATA_PERMISSION_MATRIX.md ===")
    apply_edit(
        PERMISSION_MATRIX_FILE,
        old=OLD_HDPM_BLOCK,
        new=NEW_HDPM_BLOCK,
        expected_old_count=1,
        expected_new_count=1,
        description="docs/HEALTH_DATA_PERMISSION_MATRIX.md: correct calorie-estimate write status, add session-scoped sub-records section",
    )

    print("=== 5/11: docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md ===")
    apply_edit(
        HUAWEI_REVIEW_FILE,
        old="When Huawei omits calories for a real workout, BitLut may attach the documented MET-based `TotalCaloriesBurnedRecord` estimate as a bounded fallback; measured Huawei workout calories always take priority.",
        new="BitLut may use a documented MET-based calorie estimate for its own dashboard's workout calorie display when Huawei omits calories for a real workout; measured Huawei workout calories always take priority. This estimate is not written to Health Connect.",
        expected_old_count=1,
        expected_new_count=1,
        description="docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md: correct calorie-estimate write status",
    )

    print("=== 6/11: docs/PRIVACY_POLICY.md (user-facing) ===")
    apply_edit(
        PRIVACY_POLICY_FILE,
        old="If Huawei Health does not provide calories for a real workout, BitLut may calculate an estimated total calorie value from the real workout type/duration and local profile inputs and write it to Health Connect as `TotalCaloriesBurnedRecord`. This estimate is local, bounded to the real workout, and is never used to invent another health metric.",
        new="If Huawei Health does not provide calories for a real workout, BitLut may calculate an estimated total calorie value from the real workout type and duration for its own app display only. This estimate is local, bounded to the real workout, is not written to Android Health Connect, and is never used to invent another health metric.",
        expected_old_count=1,
        expected_new_count=1,
        description="docs/PRIVACY_POLICY.md: correct calorie-estimate write status, remove inaccurate 'local profile inputs' claim (verified: estimator uses a fixed 70kg reference weight, no profile data)",
    )

    print("=== 7/11: README.md ===")
    apply_edit(
        README_FILE,
        old=(
            "The only approved derived metric is a documented fallback for total workout calories when Huawei does not provide calories for a real workout. The fallback does not extend to distance, steps, elevation, or other metrics.\n"
            "\n"
            "## Corporate wellness compatibility\n"
            "\n"
            "The current interoperability path has been validated with a downstream corporate wellness application reading BitLut-synced workouts through Health Connect.\n"
            "\n"
            "The important compatibility contract is that real per-workout distance, steps, elevation, and calories are written inside the workout's actual time window rather than exposed only as daily aggregates. See [`sync.md`](sync.md) for the full data contract and reliability notes.\n"
        ),
        new=(
            "The only approved derived metric is a documented fallback for total workout calories when Huawei does not provide calories for a real workout, used only for BitLut's own dashboard display and not written to Health Connect. The fallback does not extend to distance, steps, elevation, or other metrics.\n"
            "\n"
            "## Corporate wellness compatibility\n"
            "\n"
            "The current interoperability path has been validated with a downstream corporate wellness application reading BitLut-synced workouts through Health Connect. Sync failures were reported again in late August/early September 2026; as a targeted response the per-workout payload was reduced on 2026-09-10 (elevation and total-calories removed) -- not yet a confirmed fix.\n"
            "\n"
            "The important compatibility contract is that real per-workout distance and steps are written inside the workout's actual time window rather than exposed only as daily aggregates. See [`sync.md`](sync.md) for the full data contract and reliability notes.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="README.md: correct workout-records/corporate-compatibility sections",
    )

    print("=== 8/11: CONTEXT.md, CLAUDE.md ===")
    apply_edit(
        CONTEXT_FILE,
        old="Activity/workout data only. No backend/account. Real data first. The only approved estimate is workout `TotalCaloriesBurnedRecord` fallback documented in project docs.",
        new="Activity/workout data only. No backend/account. Real data first. The only approved estimate is a workout total-calories fallback used for BitLut's own dashboard display only (not written to Health Connect since 2026-09-10), documented in project docs.",
        expected_old_count=1,
        expected_new_count=1,
        description="CONTEXT.md: correct calorie-estimate write status",
    )
    apply_edit(
        CONTEXT_FILE,
        old="- Session + related calories written as a bundle; distance/steps/elevation (when the exercise type plausibly has them) are also written as their own Health Connect records scoped to the exact session interval, so third-party readers see real per-workout metrics rather than only a bare session plus an unrelated background aggregate.",
        new="- Distance/Steps (when the exercise type plausibly has them) are written as their own Health Connect records scoped to the exact session interval, so third-party readers see real per-workout metrics rather than only a bare session plus an unrelated background aggregate. Elevation and total-calories were removed from this bundle 2026-09-10.",
        expected_old_count=1,
        expected_new_count=1,
        description="CONTEXT.md: correct workout bundle description",
    )
    apply_edit(
        CONTEXT_FILE,
        old=(
            "- The 2026-08-31 corporate-reader failure mode remains fixed by session-scoped workout sub-metrics. A separate intermittent downstream import symptom appeared after the late-August/early-September Google Health update cycle; 2026-09-11 hardening keeps the bundle/IDs intact, rejects overlapping source sessions deterministically, uses stable Health Connect `1.1.0` on the Android 16 production toolchain, and documents connection/data-source-priority checks before changing serialization again."
        ),
        new=(
            "- The 2026-08-31 corporate-reader failure mode remains fixed by session-scoped workout sub-metrics. A separate intermittent downstream import symptom (\"binder died\"/rate-limit errors) appeared after the late-August/early-September Google Health update cycle; 2026-09-11 hardening keeps the bundle/IDs intact, rejects overlapping source sessions deterministically, uses stable Health Connect `1.1.0` on the Android 16 production toolchain, and documents connection/data-source-priority checks before changing serialization again. As a further, direct response, the 2026-09-10 workout bundle was also reduced (elevation/total-calories removed, Distance/Steps retained) to shrink payload size -- targeted, not a confirmed fix; see `docs/BACKLOG.md`."
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CONTEXT.md: note 2026-09-10 payload reduction alongside 2026-09-11 hardening",
    )
    apply_edit(
        CLAUDE_FILE,
        old="## Current baseline — 2026-08-31\n",
        new="## Current baseline — 2026-09-10\n",
        expected_old_count=1,
        expected_new_count=1,
        description="CLAUDE.md: bump baseline date",
    )
    apply_edit(
        CLAUDE_FILE,
        old=(
            "- Health Connect workouts are `ACTIVELY_RECORDED`, use Huawei device manufacturer metadata, deterministic client record IDs and stable versions, and write session + related calories as one bundle.\n"
            "- Workout distance/steps/elevation are also written as their own Health Connect records scoped to the exact session interval (gated per exercise type), so third-party readers see real per-workout metrics instead of only a coarser background aggregate. See `sync.md` section 4.6-4.7 for the full mechanism.\n"
        ),
        new=(
            "- Health Connect workouts are `ACTIVELY_RECORDED`, use Huawei device manufacturer metadata, deterministic client record IDs and stable versions, and write session + Distance/Steps as one bundle (elevation and total-calories removed 2026-09-10).\n"
            "- Workout distance/steps are also written as their own Health Connect records scoped to the exact session interval (gated per exercise type), so third-party readers see real per-workout metrics instead of only a coarser background aggregate. Elevation and total-calories were removed from this bundle on 2026-09-10 to shrink the payload after a corporate reader started failing to sync -- targeted reduction, not a confirmed fix (see `docs/BACKLOG.md`). See `sync.md` section 4.7.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CLAUDE.md: correct workout baseline bullets",
    )
    apply_edit(
        CLAUDE_FILE,
        old="The corporate wellness app now reliably imports BitLut-origin workouts, confirmed on a real device after the 2026-08-31 session-scoped Distance/Steps/Elevation sub-metric write (see `sync.md` section 4.6). Do not mutate workout write metadata further on this front without new evidence of a different problem.",
        new="The corporate wellness app started reliably importing BitLut-origin workouts after the 2026-08-31 session-scoped Distance/Steps/Elevation sub-metric write, but sync failures (\"binder died\" / rate-limit errors) were reported again in late August/early September 2026. Elevation and total-calories were removed from the workout bundle 2026-09-10 as a targeted payload-reduction response -- not a confirmed fix. Do not mutate workout write metadata further without new evidence (a corporate-app-side timestamped log correlated with BitLut's own sync times).",
        expected_old_count=1,
        expected_new_count=1,
        description="CLAUDE.md: correct corporate wellness app status",
    )

    print("=== 9/11: SESSION_HANDOFF.md ===")
    apply_insertion(
        HANDOFF_FILE,
        anchor="- Session-scoped workout metrics remain the interoperability-critical contract for downstream readers.\n",
        new_with_anchor=(
            "- Session-scoped workout metrics remain the interoperability-critical contract for downstream readers.\n"
            "- 2026-09-10: workout bundle no longer includes elevation/total-calories (`ElevationGainedRecord`/`TotalCaloriesBurnedRecord`) -- only session, Distance, Steps -- reducing per-workout Health Connect payload after a corporate reader reported \"binder died\"/rate-limit sync failures. Targeted reduction, not a confirmed fix; see `docs/BACKLOG.md`.\n"
        ),
        unique_marker="workout bundle no longer includes elevation/total-calories",
        description="SESSION_HANDOFF.md: document 2026-09-10 payload reduction under Sync hardening",
    )
    apply_insertion(
        HANDOFF_FILE,
        anchor=(
            "There is no known migration blocker left from this session. Start from the current `main` branch and the latest successful GitHub Actions run.\n"
        ),
        new_with_anchor=(
            "There is no known migration blocker left from this session. Start from the current `main` branch and the latest successful GitHub Actions run.\n"
            "\n"
            "If the corporate wellness app's sync failures recur after the 2026-09-10 payload reduction, capture the exact error time and a BitLut diagnostic log for the same window before making any further write-path change.\n"
        ),
        unique_marker="capture the exact error time and a BitLut diagnostic log",
        description="SESSION_HANDOFF.md: add next-session correlation note",
    )

    print("=== 10/11: docs/BACKLOG.md, CHANGELOG.md ===")
    apply_edit(
        BACKLOG_FILE,
        old=(
            "Updated: 2026-09-03\n"
            "\n"
            "## Highest priority\n"
            "\n"
            "- **Scaling: submit Huawei Health Kit Verification** to lift the 100-user test-phase cap -- the top current goal. See `docs/SCALING_ROADMAP.md` section 2 for the concrete action items (~15 working day review, no code changes required).\n"
        ),
        new=(
            "Updated: 2026-09-10\n"
            "\n"
            "## Highest priority\n"
            "\n"
            "- **Open investigation: corporate wellness app sync failures (\"binder died\" / rate-limit errors after ~2 minutes), reported late August/early September 2026.** No corporate-app-side timestamped log exists yet to correlate against BitLut's own sync times. As a direct response, the per-workout Health Connect payload was reduced on 2026-09-10 (elevation and total-calories removed from the session bundle, see `sync.md` section 4.7) -- this is a targeted volume reduction, not a confirmed fix. Next step: capture the exact time of the next corporate-app error alongside a BitLut diagnostic log for the same window, to confirm or rule out correlation with BitLut's own sync activity.\n"
            "- **Scaling: submit Huawei Health Kit Verification** to lift the 100-user test-phase cap -- the top current scaling goal. See `docs/SCALING_ROADMAP.md` section 2 for the concrete action items (~15 working day review, no code changes required).\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="docs/BACKLOG.md: bump date, add open investigation item",
    )
    apply_edit(
        BACKLOG_FILE,
        old="- Workout session-scoped Distance/Steps/Elevation Health Connect records; corporate wellness app now reliably imports BitLut-synced workouts (confirmed on a real device, `sync.md` section 4.6).",
        new="- Workout session-scoped Distance/Steps Health Connect records (Elevation and total-calories removed 2026-09-10, see Highest Priority); corporate wellness app started reliably importing BitLut-synced workouts once this began (confirmed on a real device, `sync.md` section 4.7).",
        expected_old_count=1,
        expected_new_count=1,
        description="docs/BACKLOG.md: correct Completed section entry",
    )
    apply_insertion(
        CHANGELOG_FILE,
        anchor="## 2026-09-11 -- lint/compiler cleanup after Android 16 migration\n",
        new_with_anchor=CHANGELOG_INSERTION + "## 2026-09-11 -- lint/compiler cleanup after Android 16 migration\n",
        unique_marker="workout Health Connect payload reduced (elevation, calories removed)",
        description="CHANGELOG.md: add 2026-09-10 (b) entry and retroactive 2026-09-10 battery-patch entry, positioned before the 2026-09-11 entry",
    )

    print("=== 11/11: repo hygiene + compile gate ===")
    remove_stale_patch_scripts()

    run_compile_gate()

    print("=== Compile gate passed. Committing and pushing. ===")
    git_commit_and_push()

    print("Done.")


if __name__ == "__main__":
    main()
