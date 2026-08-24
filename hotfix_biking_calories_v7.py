#!/usr/bin/env python3
"""
BitLut hotfix v7: swap biking's 4th workout-card metric from Elevation gain
to Active Calories.

Context:
  Elevation gain was added as biking's 4th metric slot earlier today
  (patch v5), chosen deliberately over Active Calories because it seemed
  more semantically meaningful for cycling despite an acknowledged risk
  that it's frequently unpopulated. Real-device testing today showed that
  risk materialized more severely than expected: elevation basically never
  renders. This hotfix swaps the same slot to Active Calories instead,
  which -- while also subject to Huawei's known scope-denial issue
  (error 50005) -- is populated far more often in practice.

  Elevation is now shown nowhere on this card for any exercise type.
  ActivitySessionData.elevationMeters is untouched and still used for CSV
  export and daily totals; only this one card display slot changed, same
  scope as every other change to this function today.

Files touched:
  - app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt
    (workoutMetricDisplays()'s biking branch: elevationMeters ->
    activeCaloriesKcal, workout_stat_elevation_label ->
    workout_stat_calories_label, workout_elevation_value ->
    workout_calories_value; doc comment rewritten to record the full
    same-day history: six-slot -> four-slot, then +elevation for biking,
    then elevation -> calories for biking, all on 2026-08-22)
  - app/src/main/res/values/strings.xml, values-ru/strings.xml
    (workout_stat_elevation_label/workout_elevation_value replaced with
    workout_stat_calories_label/workout_calories_value -- re-adding the
    exact strings the four-metrics patch removed as dead code earlier
    today, now needed again for the same reason elevation was)
  - scripts/verify_workout_nav_freshness_sprint.py
    (flips the elevation-required/calories-retired assertions added by the
    previous patch to calories-required/elevation-retired)

Usage:
    python3 hotfix_biking_calories_v7.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "biking_calories_hotfix"


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

    print("== Step 1/7: strings.xml (en) -- elevation strings -> calories strings ==")
    apply_edit(
        strings_en_path,
        old='    <string name="workout_stat_speed_label">Avg speed</string>\n    <string name="workout_stat_elevation_label">Elevation</string>\n    <string name="workout_stat_steps_label">Steps</string>',
        new='    <string name="workout_stat_speed_label">Avg speed</string>\n    <string name="workout_stat_calories_label">Calories</string>\n    <string name="workout_stat_steps_label">Steps</string>',
    )
    apply_edit(
        strings_en_path,
        old='    <string name="workout_speed_value">%1$s km/h</string>\n    <string name="workout_elevation_value">%1$d m</string>\n    <string name="workout_swim_pace_value">%1$s /100 m</string>',
        new='    <string name="workout_speed_value">%1$s km/h</string>\n    <string name="workout_calories_value">%1$d kcal</string>\n    <string name="workout_swim_pace_value">%1$s /100 m</string>',
    )

    print("== Step 2/7: strings.xml (ru) -- elevation strings -> calories strings ==")
    apply_edit(
        strings_ru_path,
        old='    <string name="workout_stat_speed_label">Ср. скорость</string>\n    <string name="workout_stat_elevation_label">Набор высоты</string>\n    <string name="workout_stat_steps_label">Шаги</string>',
        new='    <string name="workout_stat_speed_label">Ср. скорость</string>\n    <string name="workout_stat_calories_label">Калории</string>\n    <string name="workout_stat_steps_label">Шаги</string>',
    )
    apply_edit(
        strings_ru_path,
        old='    <string name="workout_speed_value">%1$s км/ч</string>\n    <string name="workout_elevation_value">%1$d м</string>\n    <string name="workout_swim_pace_value">%1$s /100 м</string>',
        new='    <string name="workout_speed_value">%1$s км/ч</string>\n    <string name="workout_calories_value">%1$d ккал</string>\n    <string name="workout_swim_pace_value">%1$s /100 м</string>',
    )

    print("== Step 3/7: FinalBitLutShell.kt -- doc comment rewrite ==")
    apply_edit(
        shell_path,
        old="""/**
 * Four consistent metrics on every workout card. Duration/Distance/Avg
 * speed are the same for every exercise type; the 4th slot is type-aware
 * (2026-08-22 fix): Steps for walking/running/hiking/etc, but Elevation
 * gain for biking, since a cycling session showing "Steps: 0" read as
 * broken rather than just empty. Elevation was chosen over Active Calories
 * for this slot specifically because it's more semantically meaningful for
 * cycling (climbing) even though it, like Steps, is frequently unpopulated
 * for a given ride and falls back to an em dash -- an honest "we don't have
 * that data" rather than a wrong-looking zero. Active Calories keeps its
 * existing behavior everywhere: dropped from this card entirely (see the
 * historical note below), since Huawei frequently scope-denies it (50005)
 * independent of exercise type.
 *
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
 * totals; elevation returns to this specific card for biking only, as of
 * this same-day follow-up fix -- the two changes happened in the same
 * session, not a reversal of a settled decision days later.
 */
private data class WorkoutMetricDisplay(val label: String, val value: String)""",
        new="""/**
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
private data class WorkoutMetricDisplay(val label: String, val value: String)""",
    )

    print("== Step 4/7: FinalBitLutShell.kt -- read activeCaloriesKcal instead of elevationMeters ==")
    apply_edit(
        shell_path,
        old="    val elevationMeters = session.elevationMeters?.takeIf { it > 0.0 }",
        new="    val activeCaloriesKcal = session.activeCaloriesKcal?.takeIf { it > 0.0 }",
    )

    print("== Step 5/7: FinalBitLutShell.kt -- biking's 4th slot uses calories ==")
    apply_edit(
        shell_path,
        old="""            stringResource(R.string.workout_stat_elevation_label),
            elevationMeters?.let {
                stringResource(R.string.workout_elevation_value, it.toLong())""",
        new="""            stringResource(R.string.workout_stat_calories_label),
            activeCaloriesKcal?.let {
                stringResource(R.string.workout_calories_value, it.toLong())""",
    )

    print("== Step 6/7: verify_workout_nav_freshness_sprint.py -- flip elevation/calories assertions ==")
    apply_edit(
        verify_path,
        old='require("workout_stat_calories_label" not in shell, "retired workout UI marker still present in card composable: workout_stat_calories_label")',
        new='require("workout_stat_elevation_label" not in shell, "retired workout UI marker still present in card composable: workout_stat_elevation_label")',
    )
    apply_edit(
        verify_path,
        old='''require(
    "workout_stat_elevation_label" in shell,
    "biking's 4th metric slot (Elevation gain, reintroduced 2026-08-22) is missing from the card composable"
)''',
        new='''require(
    "workout_stat_calories_label" in shell,
    "biking's 4th metric slot (Active Calories, hotfixed 2026-08-22) is missing from the card composable"
)''',
    )
    apply_edit(
        verify_path,
        old='''    "workout_swim_pace_value", "workout_stat_elevation_label", "workout_elevation_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

for retired in ["workout_stat_calories_label", "workout_calories_value"]:''',
        new='''    "workout_swim_pace_value", "workout_stat_calories_label", "workout_calories_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

for retired in ["workout_stat_elevation_label", "workout_elevation_value"]:''',
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
            "Hotfix: biking's 4th workout metric is Active Calories, not Elevation gain",
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
