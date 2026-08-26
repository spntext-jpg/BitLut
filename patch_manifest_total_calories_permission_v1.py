#!/usr/bin/env python3
"""
BitLut patch: declare the TotalCaloriesBurnedRecord Health Connect permission
in AndroidManifest.xml, fixing the permission dialog not appearing at all.

Context (2026-08-26, follow-up to patch_workout_calorie_estimate_v1.py):
  After that patch shipped, the app could not obtain the new Health Connect
  permission at all. Diagnostic logs showed the permission launcher firing
  but Health Connect returning an empty grant set every time:

      W/SyncOrchestrator: Manual sync blocked by missing Health Connect
          permissions: [android.permission.health.READ_TOTAL_CALORIES_BURNED,
          android.permission.health.WRITE_TOTAL_CALORIES_BURNED]
      I/MainActivity: Health Connect permissions returned: []

  Revoking all Health Connect access and retrying did not bring the dialog
  back either -- at that point ALL permissions (not just the new one) showed
  as missing, confirming Health Connect was treating the whole grant as void
  rather than just declining the one new permission.

Root cause:
  patch_workout_calorie_estimate_v1.py added TotalCaloriesBurnedRecord to
  HealthPermissionPolicy.kt's runtime permission request set, but never
  added the corresponding <uses-permission> declarations to
  AndroidManifest.xml. Per Android's own Health Connect documentation
  ("Get started with Health Connect"): "Make sure that the permissions in
  the set are declared in your Android manifest first." Requesting a
  permission that is not declared in the manifest is documented to prevent
  Health Connect from offering it at all -- consistent with the observed
  symptom of the whole batched request silently returning empty instead of
  prompting for anything, including the six permissions that previously
  worked fine.

Fix:
  Add <uses-permission android:name="android.permission.health.
  READ_TOTAL_CALORIES_BURNED" /> and the WRITE_ counterpart to
  AndroidManifest.xml, immediately after the existing READ_EXERCISE /
  WRITE_EXERCISE declarations. No other manifest changes. This does not add
  any new Huawei scope -- it only declares the Health-Connect-side
  permission that HealthPermissionPolicy.kt already requests at runtime.

Also updates docs/HEALTH_DATA_PERMISSION_MATRIX.md to record the calorie
estimate as an explicit, user-approved exception to that document's
"never synthesize fake health data" rule. This was raised with the user
directly before this patch was written; the user chose to keep the
estimate and record it as a documented exception rather than revert it.

Files touched:
  - app/src/main/AndroidManifest.xml
    (adds READ_TOTAL_CALORIES_BURNED / WRITE_TOTAL_CALORIES_BURNED
    uses-permission declarations)
  - docs/HEALTH_DATA_PERMISSION_MATRIX.md
    (adds a "Documented exception: estimated workout calories" section)

After this patch, the user must reopen BitLut and tap "Connect Google
Health" again -- Health Connect should now show a real permission dialog
including Total calories burned, since the permission is finally declared
in the manifest.

Sandbox limitation: this environment has no real Android SDK/Gradle/Kotlin
compiler and cannot launch the actual Health Connect permission dialog to
confirm it appears -- that can only be verified on the user's real device
after installing a build from this patch.

Usage:
    python3 patch_manifest_total_calories_permission_v1.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "manifest_total_calories_permission_v1"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


_backed_up_paths: set = set()


def backup_once(path: Path) -> None:
    if path in _backed_up_paths:
        return
    relative = path.relative_to(ROOT)
    backup_path = BACKUP_DIR / relative
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        print(f"  backed up -> {backup_path.relative_to(ROOT)}")
    _backed_up_paths.add(path)


def read(path: Path) -> str:
    if not path.exists():
        die(f"Expected file not found: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def apply_insertion(path: Path, anchor: str, new_with_anchor: str) -> bool:
    """Pure insertion: anchor text itself is unchanged, something new sits
    next to it. apply_edit is wrong here because the anchor survives as a
    substring of new_with_anchor -- a second run's exact-count check would
    still find it and re-insert, duplicating the insertion.
    """
    text = read(path)
    if new_with_anchor in text:
        print(f"  already applied, skipping: {path.name} (insertion at anchor)")
        return False

    count_anchor = text.count(anchor)
    if count_anchor != 1:
        die(
            f"{path}: expected 1 occurrence of insertion anchor in {path.name}, "
            f"found {count_anchor}. Refusing to apply (ambiguous or stale)."
        )

    backup_once(path)
    write(path, text.replace(anchor, new_with_anchor, 1))
    print(f"  applied: {path.name}")
    return True


def main() -> None:
    manifest_path = ROOT / "app/src/main/AndroidManifest.xml"
    matrix_doc_path = ROOT / "docs/HEALTH_DATA_PERMISSION_MATRIX.md"

    if not manifest_path.exists():
        die(f"Required file missing: {manifest_path}")
    if not matrix_doc_path.exists():
        die(f"Required file missing: {matrix_doc_path}")

    print("== Step 1/2: AndroidManifest.xml -- declare TotalCaloriesBurnedRecord permission ==")
    apply_insertion(
        manifest_path,
        anchor=(
            '    <uses-permission android:name="android.permission.health.READ_EXERCISE" />\n'
            '    <uses-permission android:name="android.permission.health.WRITE_EXERCISE" />'
        ),
        new_with_anchor=(
            '    <uses-permission android:name="android.permission.health.READ_EXERCISE" />\n'
            '    <uses-permission android:name="android.permission.health.WRITE_EXERCISE" />\n'
            '\n'
            '    <!-- Sprint 2026-08-25 exception, not part of the Huawei-approved\n'
            '         activity/basic sport scope above: an estimated (not measured)\n'
            '         MET-formula total-calories figure, attached to workout sessions so\n'
            '         third-party Health Connect readers have something to import. See\n'
            '         GoogleHealthManager.estimatedTotalCaloriesKcal and\n'
            '         docs/HEALTH_DATA_PERMISSION_MATRIX.md for the full rationale and the\n'
            '         explicit exception this makes to this file\'s "never synthesize fake\n'
            '         health data" rule. Declaring this permission here is required before\n'
            '         Health Connect will show ANY permission dialog for it -- omitting it\n'
            '         causes the whole runtime permission request to silently return an\n'
            '         empty grant set instead of prompting. -->\n'
            '    <uses-permission android:name="android.permission.health.READ_TOTAL_CALORIES_BURNED" />\n'
            '    <uses-permission android:name="android.permission.health.WRITE_TOTAL_CALORIES_BURNED" />'
        ),
    )

    print("== Step 2/2: docs/HEALTH_DATA_PERMISSION_MATRIX.md -- document the exception ==")
    apply_insertion(
        matrix_doc_path,
        anchor=(
            "- The app must never synthesize fake health data to satisfy a visual KPI.\n"
            "\n"
            "## Health Connect Activity Intensity"
        ),
        new_with_anchor=(
            "- The app must never synthesize fake health data to satisfy a visual KPI.\n"
            "\n"
            "## Documented exception: estimated workout calories (2026-08-25)\n"
            "\n"
            "Huawei's real per-workout `activeCalories` figure is permanently unavailable\n"
            "for this individual-developer account (error 50005). Without it, every\n"
            "`ExerciseSessionRecord` BitLut wrote carried no calorie data at all, which is\n"
            "a documented reason several real third-party Health Connect readers (e.g. a\n"
            "corporate fitness app) silently decline to import a workout.\n"
            "\n"
            "As an explicit, user-approved exception to the \"never synthesize fake health\n"
            "data\" rule above, BitLut attaches a MET-formula calorie **estimate** (not\n"
            "measured data) to each workout as a `TotalCaloriesBurnedRecord` -- see\n"
            "`GoogleHealthManager.estimatedTotalCaloriesKcal`. This exception is scoped\n"
            "narrowly:\n"
            "\n"
            "- Only `TotalCaloriesBurnedRecord` is estimated. No other record type in\n"
            "  this matrix is or should be synthesized.\n"
            "- `ActivitySessionData.activeCaloriesKcal`, which powers BitLut's own\n"
            "  dashboard, is untouched -- BitLut's own UI continues to honestly show no\n"
            "  calorie figure. The estimate exists solely so external Health Connect\n"
            "  readers have something non-zero to import.\n"
            "- `TotalCaloriesBurnedRecord` is used specifically because it is a distinct\n"
            "  Health Connect data type from `ActiveCaloriesBurnedRecord` (Huawei's\n"
            "  permanently-blocked, sensor-measured category) -- this avoids conflating\n"
            "  an estimate with the exact record type users and other apps already\n"
            "  expect to mean \"measured by a real sensor.\"\n"
            "- Requires `android.permission.health.READ_TOTAL_CALORIES_BURNED` /\n"
            "  `WRITE_TOTAL_CALORIES_BURNED`, declared in `AndroidManifest.xml` and\n"
            "  requested via `HealthPermissionPolicy` -- itself a deliberate, one-off\n"
            "  exception to this project's general \"no new Health Connect/Huawei\n"
            "  permissions\" rule.\n"
            "\n"
            "## Health Connect Activity Intensity"
        ),
    )

    # ---------------------------------------------------------------
    # Verification (symptom-based, not anchor-based)
    # ---------------------------------------------------------------
    print("\n== Verification ==")
    manifest_text = read(manifest_path)
    if manifest_text.count('android.permission.health.READ_TOTAL_CALORIES_BURNED') != 1:
        die(f"Expected exactly one READ_TOTAL_CALORIES_BURNED declaration in {manifest_path.name}.")
    if manifest_text.count('android.permission.health.WRITE_TOTAL_CALORIES_BURNED') != 1:
        die(f"Expected exactly one WRITE_TOTAL_CALORIES_BURNED declaration in {manifest_path.name}.")
    print(f"  verified: {manifest_path.name} declares TotalCaloriesBurnedRecord read+write")

    matrix_text = read(matrix_doc_path)
    if "Documented exception: estimated workout calories" not in matrix_text:
        die(f"Expected exception section not found in {matrix_doc_path.name} after patch.")
    print(f"  verified: {matrix_doc_path.name} records the estimate as a documented exception")

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
            "Declare TotalCaloriesBurnedRecord Health Connect permission in "
            "manifest (was blocking the permission dialog entirely); "
            "document the calorie-estimate exception in the sprint contract",
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
    print(
        "\nNext step: reopen BitLut and tap \"Connect Google Health\" again. "
        "The system dialog should now include Total calories burned, since "
        "the permission is finally declared in the manifest."
    )


if __name__ == "__main__":
    main()
