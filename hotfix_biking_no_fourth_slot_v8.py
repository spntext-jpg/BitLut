#!/usr/bin/env python3
"""
BitLut hotfix v8: biking workout cards drop the 4th metric slot entirely.

Context:
  Today's chain of fixes for biking's 4th workout-card metric, all on the
  same day: Steps (illogical for cycling) -> Elevation gain (logical, but
  confirmed empty in practice on real bike-ride data) -> Active Calories
  (also confirmed empty in practice). ActivitySessionData only carries four
  data fields total (distanceMeters, activeCaloriesKcal, elevationMeters,
  steps); Distance is already the card's slot 2, so Elevation and Active
  Calories were the only two remaining candidates for a biking-specific
  4th slot, and both are now confirmed to render as an em dash almost
  every time on real devices. Rather than try a metric that will likely
  fail the same way, biking cards now show three real metrics (Duration,
  Distance, Avg speed) instead of four slots where the 4th is either wrong
  (Steps) or empty (Elevation/Calories).

  WorkoutStatsGrid's chunked(2) row layout already handled variable-length
  metric lists correctly before this change -- a lone last-row item gets a
  balancing Spacer(Modifier.weight(1f)) rather than stretching full-width
  -- so no layout code needed to change for the 3-metric case, only
  workoutMetricDisplays()'s return value.

  Every other exercise type is unaffected: Steps remains the 4th slot for
  walking/running/hiking/etc, exactly as before today's whole chain of
  biking-specific fixes started.

Files touched:
  - app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt
    (workoutMetricDisplays()'s biking branch now produces a null 4th slot;
    listOf -> listOfNotNull; doc comment rewritten with full same-day
    history; WorkoutStatsGrid's comment corrected to say 3-or-4, not
    strictly 4, metrics)
  - app/src/main/res/values/strings.xml, values-ru/strings.xml
    (removes workout_stat_calories_label/workout_calories_value, now dead
    -- nothing references them after this change; workout_stat_elevation_
    label/workout_elevation_value were already removed by the previous
    hotfix and stay removed)
  - scripts/verify_workout_nav_freshness_sprint.py
    (replaces the "biking's 4th slot must be X" assertion with "biking's
    4th slot must be null"; asserts listOfNotNull is used; both
    workout_stat_calories_label and workout_stat_elevation_label are now
    retired markers, not just elevation)

Usage:
    python3 hotfix_biking_no_fourth_slot_v8.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "biking_no_fourth_slot"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    relative = path.relative_to(ROOT)
    backup_path = BACKUP_DIR / relative
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        print(f"  backed up -> {backup_path.relative_to(ROOT)}")


def read(path: Path) -> str:
    if not path.exists():
        die(f"Expected file not found: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def apply_edit(path: Path, old: str, new: str, expected_count: int = 1) -> bool:
    """Text-anchored replacement for genuine changes (old text disappears)."""
    text = read(path)
    count_old = text.count(old)
    count_new = text.count(new)

    if count_old == 0 and count_new >= expected_count:
        print(f"  already applied, skipping: {path.name} ({new[:40]!r}...)")
        return False

    if count_old != expected_count:
        die(
            f"{path}: expected {expected_count} occurrence(s) of anchor, "
            f"found {count_old}. Refusing to apply (ambiguous or stale)."
        )

    backup(path)
    write(path, text.replace(old, new, expected_count))
    print(f"  applied: {path.name}")
    return True


def main() -> None:
    shell_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
    strings_en_path = ROOT / "app/src/main/res/values/strings.xml"
    strings_ru_path = ROOT / "app/src/main/res/values-ru/strings.xml"
    verify_path = ROOT / "scripts/verify_workout_nav_freshness_sprint.py"

    for p in (shell_path, strings_en_path, strings_ru_path, verify_path):
        if not p.exists():
            die(f"Required file missing: {p}")

    print("== Step 1/5: strings.xml (en) -- remove dead calories strings ==")
    apply_edit(
        strings_en_path,
        old='    <string name="workout_stat_speed_label">Avg speed</string>\n    <string name="workout_stat_calories_label">Calories</string>\n    <string name="workout_stat_steps_label">Steps</string>',
        new='    <string name="workout_stat_speed_label">Avg speed</string>\n    <string name="workout_stat_steps_label">Steps</string>',
    )
    apply_edit(
        strings_en_path,
        old='    <string name="workout_speed_value">%1$s km/h</string>\n    <string name="workout_calories_value">%1$d kcal</string>\n    <string name="workout_swim_pace_value">%1$s /100 m</string>',
        new='    <string name="workout_speed_value">%1$s km/h</string>\n    <string name="workout_swim_pace_value">%1$s /100 m</string>',
    )

    print("== Step 2/5: strings.xml (ru) -- remove dead calories strings ==")
    apply_edit(
        strings_ru_path,
        old='    <string name="workout_stat_speed_label">Ср. скорость</string>\n    <string name="workout_stat_calories_label">Калории</string>\n    <string name="workout_stat_steps_label">Шаги</string>',
        new='    <string name="workout_stat_speed_label">Ср. скорость</string>\n    <string name="workout_stat_steps_label">Шаги</string>',
    )
    apply_edit(
        strings_ru_path,
        old='    <string name="workout_speed_value">%1$s км/ч</string>\n    <string name="workout_calories_value">%1$d ккал</string>\n    <string name="workout_swim_pace_value">%1$s /100 м</string>',
        new='    <string name="workout_speed_value">%1$s км/ч</string>\n    <string name="workout_swim_pace_value">%1$s /100 м</string>',
    )

    print("== Step 3/5: FinalBitLutShell.kt -- workoutMetricDisplays() drops biking's 4th slot ==")
    apply_edit(
        shell_path,
        old="""/**
 * Four consistent metrics on every workout card. Duration/Distance/Avg
 * speed are the same for every exercise type; the 4th slot is type-aware:
 * Steps for walking/running/hiking/etc, but Active Calories for biking,
 * since a cycling session showing "Steps: 0" read as broken rather than
 * just empty.
 *
 * Biking's 4th slot was Elevation gain for a few hours on 2026-08-22, then
 * hotfixed to Active Calories the same day after real-device testing showed
 * elevation basically never renders (the underlying elevationMeters field
 * is even more rarely populated than anticipated -- this was flagged as a
 * real risk when elevation was first chosen, and the risk materialized).
 * Active Calories is not risk-free either -- Huawei frequently scope-denies
 * it (error 50005) independent of exercise type -- but it is populated far
 * more often in practice than elevation was. Elevation is no longer shown
 * anywhere on this card for any exercise type; ActivitySessionData still
 * carries elevationMeters for CSV export and daily totals, untouched.
 *
 * Values come from real imported Health Connect data; average speed is
 * derived only from real distance and duration. Missing source values
 * remain an em dash.
 *
 * History: Active Calories and Elevation were both dropped from this card
 * entirely on 2026-08-22 (six-slot -> four-slot patch), then Elevation
 * alone came back the same day for biking only, then was swapped for
 * Active Calories a few hours later per the note above. Active Calories
 * everywhere else on this card (all non-biking exercise types) has stayed
 * dropped throughout.
 */
private data class WorkoutMetricDisplay(val label: String, val value: String)

@Composable
private fun workoutMetricDisplays(
    session: ActivitySessionData,
    durationMinutes: Long,
    exerciseType: Int?
): List<WorkoutMetricDisplay> {
    val noData = stringResource(R.string.no_data_short)
    val distanceMeters = session.distanceMeters?.takeIf { it > 0.0 }
    val distanceKm = distanceMeters?.div(1000.0)
    val steps = session.steps?.takeIf { it > 0L }
    val activeCaloriesKcal = session.activeCaloriesKcal?.takeIf { it > 0.0 }
    val durationHours =
        (session.endTimeMs - session.startTimeMs).toDouble() / 3_600_000.0
    val averageSpeedKmh = if (
        distanceKm != null &&
        durationHours > 0.0 &&
        distanceMeters >= MIN_DISTANCE_METERS_FOR_SPEED
    ) {
        distanceKm / durationHours
    } else {
        null
    }
    val isBiking = exerciseType == ExerciseSessionRecord.EXERCISE_TYPE_BIKING

    val fourthSlot = if (isBiking) {
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_calories_label),
            activeCaloriesKcal?.let {
                stringResource(R.string.workout_calories_value, it.toLong())
            } ?: noData
        )
    } else {
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_steps_label),
            steps?.let(::formatNumber) ?: noData
        )
    }

    return listOf(
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_duration_label),
            stringResource(R.string.workout_duration_value, durationMinutes)
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_distance_label),
            distanceKm?.let {
                stringResource(R.string.distance_today_value, formatOneDecimal(it))
            } ?: noData
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_speed_label),
            averageSpeedKmh?.let {
                stringResource(R.string.workout_speed_value, formatOneDecimal(it))
            } ?: noData
        ),
        fourthSlot
    )
}""",
        new="""/**
 * Duration/Distance/Avg speed on every workout card, for every exercise
 * type. The 4th slot (Steps) is shown for every type EXCEPT biking.
 *
 * Biking has no 4th slot at all as of this hotfix (2026-08-22, third
 * revision same day): Steps is semantically wrong for cycling (that's what
 * started this whole chain of fixes), but neither of the two logical
 * alternatives -- Elevation gain, then Active Calories -- actually renders
 * in practice on real devices. ActivitySessionData only carries four data
 * fields total (distanceMeters, activeCaloriesKcal, elevationMeters,
 * steps); Distance is already slot 2, so Elevation and Active Calories
 * were the only two candidates left for a biking-specific 4th slot, and
 * both came back empty on confirmed real bike-ride data. Rather than pick
 * a metric that's "logical" but shows an em dash almost every time, biking
 * cards now show three real metrics instead of four possibly-empty ones.
 * WorkoutStatsGrid's chunked(2) layout already handled odd-length lists
 * correctly before this change (a lone last-row item gets a balancing
 * Spacer(weight(1f)), not a full-width stretch) -- see WorkoutStatsGrid's
 * own logic -- so no layout change was needed for the 3-metric case.
 *
 * History, all same day (2026-08-22): six-slot -> four-slot (dropped
 * Active Calories and Elevation everywhere); biking's slot 4 became
 * Elevation gain; hotfixed to Active Calories after Elevation didn't
 * render; hotfixed again to no 4th slot at all after Active Calories
 * didn't render either. Both fields are untouched in ActivitySessionData
 * itself -- still read/synced for CSV export and daily totals; only this
 * card's biking-specific display narrowed further.
 *
 * Values come from real imported Health Connect data; average speed is
 * derived only from real distance and duration. Missing source values
 * remain an em dash.
 */
private data class WorkoutMetricDisplay(val label: String, val value: String)

@Composable
private fun workoutMetricDisplays(
    session: ActivitySessionData,
    durationMinutes: Long,
    exerciseType: Int?
): List<WorkoutMetricDisplay> {
    val noData = stringResource(R.string.no_data_short)
    val distanceMeters = session.distanceMeters?.takeIf { it > 0.0 }
    val distanceKm = distanceMeters?.div(1000.0)
    val steps = session.steps?.takeIf { it > 0L }
    val durationHours =
        (session.endTimeMs - session.startTimeMs).toDouble() / 3_600_000.0
    val averageSpeedKmh = if (
        distanceKm != null &&
        durationHours > 0.0 &&
        distanceMeters >= MIN_DISTANCE_METERS_FOR_SPEED
    ) {
        distanceKm / durationHours
    } else {
        null
    }
    val isBiking = exerciseType == ExerciseSessionRecord.EXERCISE_TYPE_BIKING

    val fourthSlot = if (isBiking) {
        null
    } else {
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_steps_label),
            steps?.let(::formatNumber) ?: noData
        )
    }

    return listOfNotNull(
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_duration_label),
            stringResource(R.string.workout_duration_value, durationMinutes)
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_distance_label),
            distanceKm?.let {
                stringResource(R.string.distance_today_value, formatOneDecimal(it))
            } ?: noData
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_speed_label),
            averageSpeedKmh?.let {
                stringResource(R.string.workout_speed_value, formatOneDecimal(it))
            } ?: noData
        ),
        fourthSlot
    )
}""",
    )

    print("== Step 4/5: FinalBitLutShell.kt -- WorkoutStatsGrid comment ==")
    apply_edit(
        shell_path,
        old="""        // Four-metric contract (2026-08-22): Duration, Distance, Avg speed,
        // Steps for every exercise type. take(4) documents that cap explicitly
        // rather than relying on workoutMetricDisplays() always returning 4.""",
        new="""        // Four-metric contract for most exercise types, three for biking
        // (2026-08-22, see workoutMetricDisplays()'s doc comment for why).
        // take(4) is a cap, not a guarantee -- workoutMetricDisplays() may
        // return 3 or 4 items depending on exercise type.""",
    )

    print("== Step 5/5: verify_workout_nav_freshness_sprint.py -- assert null 4th slot for biking ==")
    apply_edit(
        verify_path,
        old='''require("workout_stat_elevation_label" not in shell, "retired workout UI marker still present in card composable: workout_stat_elevation_label")
require(
    "workout_stat_calories_label" in shell,
    "biking's 4th metric slot (Active Calories, hotfixed 2026-08-22) is missing from the card composable"
)''',
        new='''require("workout_stat_elevation_label" not in shell, "retired workout UI marker still present in card composable: workout_stat_elevation_label")
require("workout_stat_calories_label" not in shell, "retired workout UI marker still present in card composable: workout_stat_calories_label")
require(
    "val fourthSlot = if (isBiking) {\\n        null\\n    } else {" in shell,
    "biking must have no 4th metric slot (both Elevation and Active Calories were tried and confirmed empty in practice)"
)
require("listOfNotNull(" in shell, "workoutMetricDisplays must tolerate a variable-length (3 or 4) metric list")''',
    )
    apply_edit(
        verify_path,
        old='''    "workout_swim_pace_value", "workout_stat_calories_label", "workout_calories_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

for retired in ["workout_stat_elevation_label", "workout_elevation_value"]:''',
        new='''    "workout_swim_pace_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

for retired in [
    "workout_stat_elevation_label", "workout_elevation_value",
    "workout_stat_calories_label", "workout_calories_value"
]:''',
    )

    print("\n== Compile gate: :app:assembleDebug ==")
    gradlew = ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found at repo root -- run this script from the BitLut repo root.")

    result = subprocess.run(
        [
            str(gradlew),
            ":app:assembleDebug",
            "--no-daemon",
            "--max-workers=1",
            "--no-watch-fs",
            "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        die("assembleDebug failed. No commit, no push. Fix the build and re-run this script.")

    print("\n== assembleDebug succeeded. Committing and pushing. ==")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Hotfix: biking workout cards show 3 metrics, no 4th slot (Elevation and Calories both empty in practice)",
        ],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("Nothing to commit (already applied) -- skipping push.")
        return

    push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
    if push.returncode != 0:
        die("git push failed. Commit succeeded locally; push manually once resolved.")

    print("\nDone.")


if __name__ == "__main__":
    main()
