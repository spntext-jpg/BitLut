#!/usr/bin/env python3
"""
BitLut patch: narrow workout cards to four metrics for every exercise type.

Context (2026-08-22 diagnostic log review):
  The six-slot workout card contract (Duration, Distance, Avg speed, Steps,
  Active calories, Elevation gain) was locked in an earlier sprint. Product
  decision now trims this to four slots for ALL exercise types (walking,
  running, biking, and everything else): Duration, Distance, Avg speed, Steps.
  Active calories and Elevation gain are removed from the card entirely --
  not conditionally hidden when missing, removed as a display contract.

  Rationale surfaced by the log review: Huawei activeCalories is frequently
  scope-denied (error 50005, per-category incremental approval) and elevation
  is rarely populated for the same underlying reason, so in practice the old
  six-slot layout showed four real values and two permanent dashes on most
  cards. This change does not touch data collection: ActivitySessionData
  still carries activeCaloriesKcal/elevationMeters for CSV export and daily
  totals. Only the workout card's *display* contract is narrowed.

  This is NOT a fix for the "wrong steps on last workout" question raised in
  the same conversation. That is confirmed-expected data staleness: the
  affected workout (2026-08-07) is now more than 7 days old, so BitLut's
  continuous per-minute Huawei sync window no longer covers it, and the
  Health Connect workout-distance/steps aggregate for that historical window
  has genuinely sparse source data. No code path is misbehaving; see
  SESSION_HANDOFF.md's explicit note that the distance fallback logic must
  not be reopened, and docs/HUAWEI_DAILY_CHUNKING_166.md confirming the
  7-day continuous-data policy.

Files touched:
  - app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt
  - app/src/main/res/values/strings.xml
  - app/src/main/res/values-ru/strings.xml
  - scripts/verify_workout_nav_freshness_sprint.py
    (this script encodes the *previous* six-slot contract as a regression
    gate; it is updated in lockstep so it asserts the new four-slot contract
    instead of permanently failing after this legitimate change)

Usage:
    python3 patch_workout_card_four_metrics.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Reuses the repo's existing .bitlut_patch_backup/ convention (already
# present in .gitignore) rather than inventing a new ignored directory.
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "workout_four_metrics"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    # Backups must never live inside app/src/main/res/** (or any other
    # AGP-scanned source set): AGP's resource merger treats every file
    # under res/ as a candidate resource and fails the build on anything
    # not ending in .xml (or a recognized resource extension). A prior
    # version of this script suffixed backups in-place next to the
    # original file, which broke mergeDebugResources for res/values/*.xml.
    # Keeping backups in a separate .patch_backups/ tree outside any
    # Android source set avoids this class of problem entirely, for this
    # and any future patch script touching res/.
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
    """
    Text-anchored replacement for genuine changes (old text disappears).
    Returns True if applied, False if already applied (idempotent skip).
    Dies if the anchor count doesn't match what's expected, since that
    signals either an already-diverged file or an ambiguous anchor.
    """
    text = read(path)
    count_old = text.count(old)
    count_new = text.count(new)

    if count_old == 0 and count_new >= 1:
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

    print("== Step 1/6: FinalBitLutShell.kt -- workoutMetricDisplays() ==")
    apply_edit(
        shell_path,
        old="""/**
 * Six consistent metrics on every workout card. Values come from real imported
 * Health Connect data; average speed is derived only from real distance and
 * duration. Missing source values remain an em dash.
 */
private data class WorkoutMetricDisplay(val label: String, val value: String)

@Composable
private fun workoutMetricDisplays(
    session: ActivitySessionData,
    durationMinutes: Long
): List<WorkoutMetricDisplay> {
    val noData = stringResource(R.string.no_data_short)
    val distanceMeters = session.distanceMeters?.takeIf { it > 0.0 }
    val distanceKm = distanceMeters?.div(1000.0)
    val calories = session.activeCaloriesKcal?.takeIf { it > 0.0 }
    val elevation = session.elevationMeters?.takeIf { it > 0.0 }
    val steps = session.steps?.takeIf { it > 0L }""",
        new="""/**
 * Four consistent metrics on every workout card, for every exercise type.
 * Values come from real imported Health Connect data; average speed is
 * derived only from real distance and duration. Missing source values
 * remain an em dash.
 *
 * Active calories and elevation were dropped from the card entirely
 * (2026-08-22 product decision) -- not just hidden when missing. Huawei
 * activeCalories is frequently scope-denied (50005) and elevation is rarely
 * populated for the same reason, so the six-slot layout mostly showed four
 * real values and two permanent dashes. [ActivitySessionData.activeCaloriesKcal]
 * and [.elevationMeters] are still read/synced for CSV export and daily
 * totals; only this card's display was narrowed.
 */
private data class WorkoutMetricDisplay(val label: String, val value: String)

@Composable
private fun workoutMetricDisplays(
    session: ActivitySessionData,
    durationMinutes: Long
): List<WorkoutMetricDisplay> {
    val noData = stringResource(R.string.no_data_short)
    val distanceMeters = session.distanceMeters?.takeIf { it > 0.0 }
    val distanceKm = distanceMeters?.div(1000.0)
    val steps = session.steps?.takeIf { it > 0L }""",
    )

    print("== Step 2/6: FinalBitLutShell.kt -- drop calories/elevation list entries ==")
    apply_edit(
        shell_path,
        old="""        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_steps_label),
            steps?.let(::formatNumber) ?: noData
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_calories_label),
            calories?.let {
                stringResource(R.string.workout_calories_value, it.toLong())
            } ?: noData
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_elevation_label),
            elevation?.let {
                stringResource(R.string.workout_elevation_value, it.toLong())
            } ?: noData
        )
    )
}""",
        new="""        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_steps_label),
            steps?.let(::formatNumber) ?: noData
        )
    )
}""",
    )

    print("== Step 3/6: FinalBitLutShell.kt -- WorkoutStatsGrid cap take(6) -> take(4) ==")
    apply_edit(
        shell_path,
        old="""    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        metrics.take(6).chunked(2).forEach { rowMetrics ->""",
        new="""    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        // Four-metric contract (2026-08-22): Duration, Distance, Avg speed,
        // Steps for every exercise type. take(4) documents that cap explicitly
        // rather than relying on workoutMetricDisplays() always returning 4.
        metrics.take(4).chunked(2).forEach { rowMetrics ->""",
    )

    print("== Step 4/6: strings.xml (en) -- remove dead calories/elevation strings ==")
    apply_edit(
        strings_en_path,
        old="""    <string name="workout_stat_speed_label">Avg speed</string>
    <string name="workout_stat_calories_label">Calories</string>
    <string name="workout_stat_elevation_label">Elevation</string>
    <string name="workout_stat_steps_label">Steps</string>""",
        new="""    <string name="workout_stat_speed_label">Avg speed</string>
    <string name="workout_stat_steps_label">Steps</string>""",
    )
    apply_edit(
        strings_en_path,
        old="""    <string name="workout_speed_value">%1$s km/h</string>
    <string name="workout_calories_value">%1$d kcal</string>
    <string name="workout_elevation_value">%1$d m</string>
    <string name="workout_swim_pace_value">%1$s /100 m</string>""",
        new="""    <string name="workout_speed_value">%1$s km/h</string>
    <string name="workout_swim_pace_value">%1$s /100 m</string>""",
    )

    print("== Step 5/6: strings.xml (ru) -- remove dead calories/elevation strings ==")
    apply_edit(
        strings_ru_path,
        old="""    <string name="workout_stat_speed_label">Ср. скорость</string>
    <string name="workout_stat_calories_label">Калории</string>
    <string name="workout_stat_elevation_label">Набор</string>
    <string name="workout_stat_steps_label">Шаги</string>""",
        new="""    <string name="workout_stat_speed_label">Ср. скорость</string>
    <string name="workout_stat_steps_label">Шаги</string>""",
    )
    apply_edit(
        strings_ru_path,
        old="""    <string name="workout_speed_value">%1$s км/ч</string>
    <string name="workout_calories_value">%1$d ккал</string>
    <string name="workout_elevation_value">%1$d м</string>
    <string name="workout_swim_pace_value">%1$s /100 м</string>""",
        new="""    <string name="workout_speed_value">%1$s км/ч</string>
    <string name="workout_swim_pace_value">%1$s /100 м</string>""",
    )

    print("== Step 6/6: scripts/verify_workout_nav_freshness_sprint.py -- update contract ==")
    apply_edit(
        verify_path,
        old="""require("workoutMetricDisplays" in shell, "type-aware workout metrics missing")
for marker in [
    "EXERCISE_TYPE_RUNNING", "EXERCISE_TYPE_WALKING", "EXERCISE_TYPE_BIKING",
    "EXERCISE_TYPE_HIKING", "EXERCISE_TYPE_SWIMMING_POOL", "EXERCISE_TYPE_STRENGTH_TRAINING",
    "workout_stat_speed_label", "workout_stat_calories_label", "workout_stat_elevation_label"
]:
    require(marker in shell, f"workout UI marker missing: {marker}")
require("metrics.take(4).chunked(2)" in shell, "workout cards are not capped to four metrics")""",
        new="""require("workoutMetricDisplays" in shell, "type-aware workout metrics missing")
for marker in [
    "EXERCISE_TYPE_RUNNING", "EXERCISE_TYPE_WALKING", "EXERCISE_TYPE_BIKING",
    "EXERCISE_TYPE_HIKING", "EXERCISE_TYPE_SWIMMING_POOL", "EXERCISE_TYPE_STRENGTH_TRAINING",
    "workout_stat_speed_label"
]:
    require(marker in shell, f"workout UI marker missing: {marker}")
require("metrics.take(4).chunked(2)" in shell, "workout cards are not capped to four metrics")
for retired in ["workout_stat_calories_label", "workout_stat_elevation_label"]:
    require(
        retired not in shell,
        f"retired workout UI marker still present in card composable: {retired}"
    )""",
    )
    apply_edit(
        verify_path,
        old="""for key in [
    "workout_stat_speed_label", "workout_stat_calories_label", "workout_stat_elevation_label",
    "workout_stat_steps_label", "workout_stat_started_label", "workout_stat_ended_label",
    "workout_stat_swim_pace_label", "workout_speed_value", "workout_calories_value",
    "workout_elevation_value", "workout_swim_pace_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")""",
        new="""for key in [
    "workout_stat_speed_label", "workout_stat_steps_label", "workout_stat_started_label",
    "workout_stat_ended_label", "workout_stat_swim_pace_label", "workout_speed_value",
    "workout_swim_pace_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

for retired in [
    "workout_stat_calories_label", "workout_stat_elevation_label",
    "workout_calories_value", "workout_elevation_value"
]:
    require(f'name="{retired}"' not in strings_en, f"retired English string still present: {retired}")
    require(f'name="{retired}"' not in strings_ru, f"retired Russian string still present: {retired}")""",
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
            "Narrow workout cards to 4 metrics (Duration, Distance, Avg speed, Steps) for all exercise types",
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
