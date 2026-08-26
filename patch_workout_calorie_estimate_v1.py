#!/usr/bin/env python3
"""
BitLut patch: attach an estimated TotalCaloriesBurnedRecord to every workout,
so third-party Health Connect readers (e.g. a corporate fitness app) import
BitLut-synced exercise sessions instead of silently ignoring them.

Context (2026-08-25 sprint, follow-up to patch_hc_recording_method_v11.py):
  After the recording-method fix, a strength-training workout correctly
  passed Huawei -> BitLut -> Google Fit (visible there), but a separate
  corporate fitness app reading the same Health Connect data still would not
  import it. Diagnostic logs showed the written ExerciseSessionRecord had:

      distanceMeters=0.0 distanceSource=missing activeCaloriesKcal=0.0

  i.e. a bare session with literally nothing attached to it. This matches a
  documented, real pattern across multiple third-party Health Connect
  consumers: MyFitnessPal's own support docs state cardio synced through
  Health Connect only imports "as long as they have a duration and calorie
  burn"; a filed bug against another consumer app (SparkyFitness #955)
  independently confirms apps commonly fail to import Health Connect
  exercise sessions with no attached TotalCaloriesBurnedRecord /
  ActiveCaloriesBurnedRecord. Some third-party integrations separately
  require distance for the same reason.

Root cause:
  BitLut writes ExerciseSessionRecord with only start/end time, exercise
  type, and title -- no attached calorie or distance data. Huawei's real
  per-workout activeCalories figure is permanently unavailable for this
  individual-developer account (error 50005, confirmed unfixable -- see
  writeActiveCaloriesBatch and HuaweiHealthManager's activeCalories read
  path), so there has never been a real calorie number for BitLut to attach.

Fix (explicitly scoped and user-approved -- see below):
  Write a MET-formula calorie ESTIMATE (not measured data) as a
  TotalCaloriesBurnedRecord alongside every ExerciseSessionRecord, using
  only data BitLut already has: exercise type and duration. The formula
  (kcal = MET * 3.5 * weightKg * minutes / 200) and the MET table are drawn
  from the Compendium of Physical Activities (Ainsworth et al.), the
  standard reference nearly all fitness calorie calculators cite. Reference
  body weight is fixed at 70 kg -- the conventional default used across MET
  calculators when real weight is unavailable, which it is here: BitLut has
  no access to the user's actual weight, and adding that would itself be a
  new data category, which this fix is explicitly scoped to avoid.

  TotalCaloriesBurnedRecord is used deliberately instead of the
  already-integrated ActiveCaloriesBurnedRecord: the latter is Huawei's
  permanently-blocked category, and continuing to write to it would
  conflate an estimate with the exact record type users and other apps
  already expect to mean "measured by a real sensor." This does NOT change
  BitLut's own dashboard: ActivitySessionData.activeCaloriesKcal, which
  powers BitLut's own UI, is untouched, so BitLut's own display continues
  to honestly show no calorie figure for this account. The estimate exists
  solely to give external Health Connect readers something to import.

Deliberate exception to the "no new Health Connect/Huawei permissions" rule:
  Writing TotalCaloriesBurnedRecord requires a Health Connect permission
  BitLut has never requested before (read+write). This is a genuine new
  permission grant, explicitly discussed with and approved by the user
  before writing this script -- not a default assumption. No new Huawei
  scope of any kind is requested; this is Health-Connect-side only.

  Verified safe rollout path: SyncWorker.runSingleAttempt() already gates
  every sync attempt (both HUAWEI_HEALTH and GOOGLE_FIT source branches) on
  googleManager.hasAllPermissions(), returning SyncAttemptOutcome.GracefulNoop
  before writeSnapshot() is ever reached if any required permission --
  including this new one -- is missing. This means: after this patch ships,
  sync will safely no-op (not crash) until the user re-taps "Connect Google
  Health" and grants the new permission in the resulting system dialog. No
  additional defensive code was needed in the new write path itself because
  this existing preflight gate already covers it.

Files touched:
  - app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt
    (adds TotalCaloriesBurnedRecord read+write permission, documented as a
    deliberate one-off exception in the file's own doc comment)
  - app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt
    (adds TotalCaloriesBurnedRecord import; writeActivitySessionsBatch() now
    also writes an estimated TotalCaloriesBurnedRecord per session; adds
    estimatedTotalCaloriesKcal() and exerciseTypeMetValue() helper functions)

Sandbox limitation: this environment has no real Android SDK/Gradle/Kotlin
compiler, so this cannot be proven to compile before your machine's real
assembleDebug runs it (which this script gates on, same as prior patches).

Usage:
    python3 patch_workout_calorie_estimate_v1.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "workout_calorie_estimate_v1"


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
            f"{path}: expected {expected_count} occurrence(s) of anchor in "
            f"{path.name}, found {count_old}. Refusing to apply (ambiguous or stale)."
        )

    backup_once(path)
    write(path, text.replace(old, new, expected_count))
    print(f"  applied: {path.name}")
    return True


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
    policy_path = ROOT / "app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt"
    manager_path = ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"

    if not policy_path.exists():
        die(f"Required file missing: {policy_path}")
    if not manager_path.exists():
        die(f"Required file missing: {manager_path}")

    # ---------------------------------------------------------------
    # HealthPermissionPolicy.kt
    # ---------------------------------------------------------------
    print("== Step 1/6: HealthPermissionPolicy.kt -- import TotalCaloriesBurnedRecord ==")
    apply_insertion(
        policy_path,
        anchor="import androidx.health.connect.client.records.StepsRecord",
        new_with_anchor=(
            "import androidx.health.connect.client.records.StepsRecord\n"
            "import androidx.health.connect.client.records.TotalCaloriesBurnedRecord"
        ),
    )

    print("== Step 2/6: HealthPermissionPolicy.kt -- document the permission exception ==")
    apply_insertion(
        policy_path,
        anchor=(
            " * Sleep, pulse, SpO2, HRV, stress and Activity Intensity are intentionally not\n"
            " * requested, not read and not written in this release.\n"
            " */"
        ),
        new_with_anchor=(
            " * Sleep, pulse, SpO2, HRV, stress and Activity Intensity are intentionally not\n"
            " * requested, not read and not written in this release.\n"
            " *\n"
            " * Sprint 2026-08-25 exception: TotalCaloriesBurnedRecord read+write was added\n"
            " * as a deliberate, user-approved one-off exception to this project's general\n"
            " * \"no new Health Connect/Huawei permissions\" rule. Huawei's activeCalories\n"
            " * category is permanently denied (error 50005) for this individual-developer\n"
            " * account, so BitLut's ExerciseSessionRecord writes previously carried no\n"
            " * calorie data at all. Several real third-party Health Connect readers\n"
            " * (documented pattern: MyFitnessPal requires calories, other apps require\n"
            " * distance) silently decline to import an exercise session with nothing\n"
            " * attached to it. TotalCaloriesBurnedRecord -- not the still-unavailable\n"
            " * ActiveCaloriesBurnedRecord -- lets BitLut attach a MET-formula estimate\n"
            " * (see GoogleHealthManager.estimatedTotalCaloriesKcal) so those readers have\n"
            " * something to import, without requesting any new Huawei scope.\n"
            " */"
        ),
    )

    print("== Step 3/6: HealthPermissionPolicy.kt -- add read permission ==")
    apply_insertion(
        policy_path,
        anchor="        HealthPermission.getReadPermission(ExerciseSessionRecord::class),\n    )",
        new_with_anchor=(
            "        HealthPermission.getReadPermission(ExerciseSessionRecord::class),\n"
            "        HealthPermission.getReadPermission(TotalCaloriesBurnedRecord::class),\n"
            "    )"
        ),
    )

    print("== Step 4/6: HealthPermissionPolicy.kt -- add write permission ==")
    apply_insertion(
        policy_path,
        anchor="        HealthPermission.getWritePermission(ExerciseSessionRecord::class),\n    )",
        new_with_anchor=(
            "        HealthPermission.getWritePermission(ExerciseSessionRecord::class),\n"
            "        HealthPermission.getWritePermission(TotalCaloriesBurnedRecord::class),\n"
            "    )"
        ),
    )

    # ---------------------------------------------------------------
    # GoogleHealthManager.kt
    # ---------------------------------------------------------------
    print("== Step 5/6: GoogleHealthManager.kt -- import TotalCaloriesBurnedRecord ==")
    apply_insertion(
        manager_path,
        anchor="import androidx.health.connect.client.records.StepsRecord",
        new_with_anchor=(
            "import androidx.health.connect.client.records.StepsRecord\n"
            "import androidx.health.connect.client.records.TotalCaloriesBurnedRecord"
        ),
    )

    print("== Step 6/6: GoogleHealthManager.kt -- write estimated calories alongside each session ==")
    apply_edit(
        manager_path,
        old='''    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {
        // Huawei may revise workout metadata after the initial sync. A
        // timestamp version ensures the same stable clientRecordId upserts the
        // real type/title over records written by older BitLut builds.
        val version = System.currentTimeMillis()
        val valid = records
            .filter { it.startTimeMs < it.endTimeMs }
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                ExerciseSessionRecord(
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    exerciseType = it.exerciseType,
                    title = it.title,
                    metadata = bitlutMetadata(
                        "exercise",
                        start.toEpochMilli(),
                        end.toEpochMilli(),
                        version = version
                    )
                )
            }

        return replaceRecords("activitySessions", valid, ExerciseSessionRecord::class)
    }''',
        new='''    private suspend fun writeActivitySessionsBatch(records: List<ActivitySessionData>): Boolean {
        // Huawei may revise workout metadata after the initial sync. A
        // timestamp version ensures the same stable clientRecordId upserts the
        // real type/title over records written by older BitLut builds.
        val version = System.currentTimeMillis()
        val validSessions = records.filter { it.startTimeMs < it.endTimeMs }
        val valid = validSessions
            .map {
                val start = Instant.ofEpochMilli(it.startTimeMs)
                val end = Instant.ofEpochMilli(it.endTimeMs)
                ExerciseSessionRecord(
                    startTime = start,
                    endTime = end,
                    startZoneOffset = offset(start),
                    endZoneOffset = offset(end),
                    exerciseType = it.exerciseType,
                    title = it.title,
                    metadata = bitlutMetadata(
                        "exercise",
                        start.toEpochMilli(),
                        end.toEpochMilli(),
                        version = version
                    )
                )
            }

        val sessionsWritten = replaceRecords("activitySessions", valid, ExerciseSessionRecord::class)

        // Sprint 2026-08-25: attach an estimated TotalCaloriesBurnedRecord to
        // every session. Huawei's real activeCalories category is
        // permanently denied for this individual-developer account (error
        // 50005 -- see writeActiveCaloriesBatch), so before this, every
        // ExerciseSessionRecord BitLut wrote carried no calorie data
        // whatsoever. A bare session with nothing attached to it is a
        // documented reason real third-party Health Connect readers silently
        // decline to import a workout (e.g. MyFitnessPal requires calories
        // before importing cardio sessions synced through Health Connect).
        // estimatedTotalCaloriesKcal() is a MET-formula estimate, not
        // measured data -- see its own doc comment for the caveats and why
        // TotalCaloriesBurnedRecord (not the still-unavailable
        // ActiveCaloriesBurnedRecord) is used. This does not touch
        // ActivitySessionData.activeCaloriesKcal or BitLut's own dashboard,
        // which continue to show "--" for calories exactly as before, since
        // BitLut still has no real measured figure for its own display.
        val caloriesValid = validSessions.mapNotNull {
            val kcal = estimatedTotalCaloriesKcal(it.exerciseType, it.startTimeMs, it.endTimeMs)
                ?: return@mapNotNull null
            val start = Instant.ofEpochMilli(it.startTimeMs)
            val end = Instant.ofEpochMilli(it.endTimeMs)
            TotalCaloriesBurnedRecord(
                startTime = start,
                endTime = end,
                startZoneOffset = offset(start),
                endZoneOffset = offset(end),
                energy = Energy.kilocalories(kcal),
                metadata = bitlutMetadata(
                    "exercise_calories_estimate",
                    start.toEpochMilli(),
                    end.toEpochMilli(),
                    version = version
                )
            )
        }
        replaceRecords("activitySessionEstimatedCalories", caloriesValid, TotalCaloriesBurnedRecord::class)

        return sessionsWritten
    }

    /**
     * MET-formula estimate of total calories burned for a workout, used only
     * to give third-party Health Connect readers something non-zero to
     * import (see the call site in [writeActivitySessionsBatch] for why).
     * This is NOT measured data: Huawei's real per-workout calorie figure is
     * gated behind the same activeCalories scope that returns error 50005
     * for this account (see [writeActiveCaloriesBatch] above, and
     * HuaweiHealthManager's activeCalories read path), and nothing
     * about that is expected to change. The formula itself --
     * kcal = MET * 3.5 * weightKg * minutes / 200 -- and the MET values below
     * are drawn from the Compendium of Physical Activities (Ainsworth et al.),
     * the standard reference most fitness calorie calculators cite. Reference
     * body weight is fixed at 70 kg, the conventional default used across MET
     * calculators when no real weight is available -- BitLut has no access to
     * the user's actual weight and adding that would be a new data category,
     * which this sprint's fix is explicitly scoped to avoid.
     *
     * MET values are the "general/moderate" variant for each activity where
     * the Compendium lists multiple intensity bands, since Huawei's activity
     * records carry no intensity signal to pick a different one. Returns null
     * for a zero-or-negative duration, so no record is written for a
     * malformed session.
     */
    private fun estimatedTotalCaloriesKcal(exerciseType: Int, startTimeMs: Long, endTimeMs: Long): Double? {
        val minutes = (endTimeMs - startTimeMs) / 60_000.0
        if (minutes <= 0.0) return null

        val met = exerciseTypeMetValue(exerciseType)
        val referenceWeightKg = 70.0
        return met * 3.5 * referenceWeightKg * minutes / 200.0
    }

    /** General/moderate MET value per Health Connect exercise type, from the
     *  Compendium of Physical Activities. See [estimatedTotalCaloriesKcal]. */
    private fun exerciseTypeMetValue(exerciseType: Int): Double = when (exerciseType) {
        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING -> 8.0
        ExerciseSessionRecord.EXERCISE_TYPE_BIKING -> 7.5
        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL,
        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER -> 6.0
        ExerciseSessionRecord.EXERCISE_TYPE_HIKING -> 6.0
        ExerciseSessionRecord.EXERCISE_TYPE_ROWING,
        ExerciseSessionRecord.EXERCISE_TYPE_ROWING_MACHINE -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_ELLIPTICAL -> 5.0
        ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING -> 3.5
        ExerciseSessionRecord.EXERCISE_TYPE_YOGA -> 2.5
        ExerciseSessionRecord.EXERCISE_TYPE_WALKING -> 3.5
        ExerciseSessionRecord.EXERCISE_TYPE_SKIING -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_SNOWBOARDING -> 5.3
        ExerciseSessionRecord.EXERCISE_TYPE_SKATING -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_TENNIS -> 7.3
        ExerciseSessionRecord.EXERCISE_TYPE_TABLE_TENNIS -> 4.0
        ExerciseSessionRecord.EXERCISE_TYPE_BASKETBALL -> 6.5
        ExerciseSessionRecord.EXERCISE_TYPE_VOLLEYBALL -> 4.0
        ExerciseSessionRecord.EXERCISE_TYPE_BADMINTON -> 5.5
        ExerciseSessionRecord.EXERCISE_TYPE_BASEBALL -> 5.0
        ExerciseSessionRecord.EXERCISE_TYPE_BOXING -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_DANCING -> 4.5
        ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING -> 8.0
        ExerciseSessionRecord.EXERCISE_TYPE_PILATES -> 3.0
        ExerciseSessionRecord.EXERCISE_TYPE_GOLF -> 4.8
        ExerciseSessionRecord.EXERCISE_TYPE_SOCCER -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AMERICAN,
        ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AUSTRALIAN -> 8.0
        else -> 4.0 // EXERCISE_TYPE_OTHER_WORKOUT and anything unmapped: conservative moderate-activity default.
    }''',
    )

    # ---------------------------------------------------------------
    # Verification (symptom-based, not anchor-based)
    # ---------------------------------------------------------------
    print("\n== Verification ==")
    policy_text = read(policy_path)
    if "TotalCaloriesBurnedRecord::class" not in policy_text:
        die(f"Expected TotalCaloriesBurnedRecord permission not found in {policy_path.name} after patch.")
    if policy_text.count("HealthPermission.getReadPermission(TotalCaloriesBurnedRecord::class)") != 1:
        die(f"Expected exactly one read-permission entry in {policy_path.name} after patch.")
    if policy_text.count("HealthPermission.getWritePermission(TotalCaloriesBurnedRecord::class)") != 1:
        die(f"Expected exactly one write-permission entry in {policy_path.name} after patch.")
    print(f"  verified: {policy_path.name} requests TotalCaloriesBurnedRecord read+write")

    manager_text = read(manager_path)
    if "estimatedTotalCaloriesKcal(" not in manager_text:
        die(f"Expected estimatedTotalCaloriesKcal() not found in {manager_path.name} after patch.")
    if "exerciseTypeMetValue(" not in manager_text:
        die(f"Expected exerciseTypeMetValue() not found in {manager_path.name} after patch.")
    if "TotalCaloriesBurnedRecord(" not in manager_text:
        die(f"Expected TotalCaloriesBurnedRecord(...) construction not found in {manager_path.name} after patch.")
    if "activitySessionEstimatedCalories" not in manager_text:
        die(f"Expected activitySessionEstimatedCalories write label not found in {manager_path.name} after patch.")
    # ActivitySessionData.activeCaloriesKcal (BitLut's own real-data dashboard
    # field) must remain untouched by this patch -- verify the estimate path
    # never assigns into it.
    if re.search(r"activeCaloriesKcal\s*=\s*(estimatedTotalCaloriesKcal|kcal)\b", manager_text):
        die(
            "The calorie estimate appears to be assigned into "
            "ActivitySessionData.activeCaloriesKcal, which must stay reserved "
            "for real measured data -- investigate before building."
        )
    print(f"  verified: {manager_path.name} writes an estimated TotalCaloriesBurnedRecord per session")
    print("  verified: ActivitySessionData.activeCaloriesKcal is not touched by the estimate")

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
            "Attach estimated TotalCaloriesBurnedRecord to workouts so "
            "third-party Health Connect readers import them (new HC "
            "permission, user-approved exception)",
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
        "\nIMPORTANT: this adds a new Health Connect permission. Sync will "
        "safely no-op (see SyncWorker's hasAllPermissions() preflight) until "
        "you re-open BitLut and tap \"Connect Google Health\" again to grant "
        "the new TotalCaloriesBurnedRecord permission in the system dialog."
    )


if __name__ == "__main__":
    main()
