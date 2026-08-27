#!/usr/bin/env python3
"""
patch_walking_three_slots_v1.py

Trims the walking workout card from 4 metrics (Duration, Distance, Avg
speed, Steps) down to 3 (Duration, Distance, Avg speed), matching the
existing biking card layout.

Scope: FinalBitLutShell.kt only. workoutMetricDisplays() already special-
cases EXERCISE_TYPE_BIKING to drop the 4th (Steps) slot via a boolean
`isBiking` flag feeding a `fourthSlot` null-out. This patch generalizes
that flag to also cover EXERCISE_TYPE_WALKING, and updates the function's
doc comment to describe both cases. WorkoutStatsGrid's chunked(2) layout
already handles a 3-item list correctly (confirmed by the existing biking
case), so no layout code changes are needed.

Not touched: ActivitySessionData.steps is still read/synced for CSV
export, daily totals, and the Steps Hero card. Only this specific card's
walking display is narrowed -- same scope discipline as the original
biking fix.

Usage:
    python3 patch_walking_three_slots_v1.py

Behavior:
    1. Backs up the touched file to .bitlut_patch_backup/
    2. Applies two text-anchored edits (doc comment + logic)
    3. Runs :app:compileDebugKotlin as a compile gate
    4. On success: git add -A && git commit && git push origin HEAD:main
    5. On failure: dies with a clear message, no commit, no push
    6. Idempotent: safe to run twice; second run reports "already applied"
"""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
TARGET = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup_file(path: Path) -> None:
    if not path.exists():
        die(f"Cannot back up missing file: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]
    dest = BACKUP_DIR / f"{path.name}.{digest}.bak"
    if not dest.exists():
        shutil.copy2(path, dest)
        print(f"Backed up {path} -> {dest}")
    else:
        print(f"Backup already exists at {dest}, leaving it in place")


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, expected_new_count: int) -> bool:
    """
    Genuine replacement helper: old text is expected to disappear after the
    edit. Returns True if an edit was applied, False if already applied
    (idempotent skip). Dies if the file is in neither state.
    """
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == expected_old_count and new_count == 0:
        text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        return True

    if old_count == 0 and new_count >= expected_new_count:
        return False

    die(
        "Unexpected file state for edit.\n"
        f"  old_str occurrences: {old_count} (expected {expected_old_count} pre-patch or 0 post-patch)\n"
        f"  new_str occurrences: {new_count} (expected 0 pre-patch or >={expected_new_count} post-patch)\n"
        f"  file: {path}\n"
        "Refusing to guess; inspect the file manually."
    )


def run(cmd: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        die(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def main() -> None:
    if not TARGET.exists():
        die(f"Target file not found: {TARGET}")

    backup_file(TARGET)

    doc_old = '''/**
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
 */'''

    doc_new = '''/**
 * Duration/Distance/Avg speed on every workout card, for every exercise
 * type. The 4th slot (Steps) is shown for every type EXCEPT biking and
 * walking.
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
 * Walking drops the same Steps slot (2026-08-27) for a product reason
 * rather than a missing-data reason: on a walking session, Steps is
 * redundant with Distance/Avg speed rather than adding new information, so
 * the card was trimmed to the same three-slot layout already used for
 * biking. This is a display-only change -- ActivitySessionData.steps is
 * still read/synced for CSV export, daily totals, and the Steps Hero card;
 * only this specific card's walking display narrowed.
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
 */'''

    logic_old = """    val isBiking = exerciseType == ExerciseSessionRecord.EXERCISE_TYPE_BIKING

    val fourthSlot = if (isBiking) {
        null
    } else {"""

    logic_new = """    val isBiking = exerciseType == ExerciseSessionRecord.EXERCISE_TYPE_BIKING
    val isWalking = exerciseType == ExerciseSessionRecord.EXERCISE_TYPE_WALKING
    val dropsFourthSlot = isBiking || isWalking

    val fourthSlot = if (dropsFourthSlot) {
        null
    } else {"""

    changed_doc = apply_edit(TARGET, doc_old, doc_new, expected_old_count=1, expected_new_count=1)
    changed_logic = apply_edit(TARGET, logic_old, logic_new, expected_old_count=1, expected_new_count=1)

    if not changed_doc and not changed_logic:
        print("Already applied -- nothing to do, skipping compile/commit/push.")
        return

    print(f"Applied doc comment edit: {changed_doc}")
    print(f"Applied logic edit: {changed_logic}")

    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die(f"gradlew not found at {gradlew}; cannot run compile gate.")

    run(
        [
            str(gradlew),
            ":app:compileDebugKotlin",
            "--no-daemon",
            "--max-workers=1",
            "--no-watch-fs",
            "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=REPO_ROOT,
    )

    print("Compile gate passed. Committing and pushing.")
    run(["git", "add", "-A"], cwd=REPO_ROOT)
    run(
        [
            "git",
            "commit",
            "-m",
            "Trim walking workout card to 3 metric slots (Duration, Distance, Avg speed)",
        ],
        cwd=REPO_ROOT,
    )
    run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT)
    print("Done.")


if __name__ == "__main__":
    main()
