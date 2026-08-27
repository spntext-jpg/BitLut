#!/usr/bin/env python3
"""
BitLut patch: two dashboard UX fixes.

1. Stale "yesterday's data" shown on cold launch until the next sync
   completes. Root cause: DashboardViewModel.buildInitialState() applies
   whatever is in DashboardSnapshotCache unconditionally on cold launch, with
   no check for whether that cache was written on a previous calendar day.
   If the app was closed overnight, the cached daily totals (steps,
   distance, calories, workout minutes, active hours, elevation, floors)
   are yesterday's real numbers, but nothing distinguishes them from today's
   until the automatic launch sync (already existing, see MainActivity's
   triggerAutomaticSyncOnLaunch()) completes and refreshes the cache.

   Fix: compare the cache's savedAtMs (converted to a local calendar date)
   against today's date. If the cache predates today, apply the cached
   snapshot as before for recentWorkouts (a workout from yesterday is still
   real, valid history and belongs in the "previous workout" card
   regardless of what day it is now) but reset the daily-total fields to
   their zero defaults, exactly as a fresh day with no activity yet would
   look, until the already-existing auto-sync-on-launch replaces them with
   real numbers for the new day. No new sync-triggering logic was needed --
   BitLut already syncs on every cold launch (onResume() -> 
   triggerAutomaticSyncOnLaunch()) -- this only fixes what is shown in the
   gap between cold launch and that sync completing.

2. Strength-training workout cards showed Duration, Distance, Avg speed,
   Steps -- none of which are meaningful for a strength session. Fix:
   workoutMetricDisplays() now special-cases EXERCISE_TYPE_STRENGTH_TRAINING
   to show only Duration + Calories. Calories prefers Huawei's real measured
   activeCaloriesKcal when present, and falls back to a MET-formula estimate
   otherwise (which is always true today, since Huawei's activeCalories
   scope is permanently denied for this account -- error 50005).

   The MET formula/table already existed in GoogleHealthManager (added by
   patch_workout_calorie_estimate_v1.py, for the Health Connect
   TotalCaloriesBurnedRecord write). Rather than duplicate it for display,
   this patch extracts it into a new shared object,
   com.openhealth.sync.util.WorkoutCalorieEstimator, and refactors
   GoogleHealthManager to delegate to it. This means the write path and the
   dashboard display can never silently drift onto two different formulas.

Files touched:
  - app/src/main/java/com/openhealth/sync/util/WorkoutCalorieEstimator.kt
    (new file: shared MET-formula calorie estimator, extracted from
    GoogleHealthManager)
  - app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt
    (estimatedTotalCaloriesKcal now delegates to WorkoutCalorieEstimator;
    the MET table that used to live here is removed, not duplicated)
  - app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt
    (buildInitialState() zeroes daily totals when the cache predates today)
  - app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt
    (workoutMetricDisplays() special-cases strength training)
  - app/src/main/res/values/strings.xml and values-ru/strings.xml
    (new workout_stat_calories_label / workout_calories_value strings)

Sandbox limitation: this environment has no real Android SDK/Gradle/Kotlin
compiler and cannot render Compose UI, so the actual on-device appearance of
the workout card and the cold-launch zero state can only be confirmed on
your real device after this patch's assembleDebug gate passes.

Usage:
    python3 patch_stale_cache_and_strength_metrics_v1.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "stale_cache_and_strength_metrics_v1"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


_backed_up_paths: set = set()


def backup_once(path: Path) -> None:
    if path in _backed_up_paths:
        return
    if not path.exists():
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


def create_file_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        existing = read(path)
        if existing == content:
            print(f"  already applied, skipping: {path.name} (file exists, identical)")
            return False
        die(
            f"{path} already exists with different content. Refusing to "
            "overwrite -- inspect manually."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, content)
    print(f"  created: {path.relative_to(ROOT)}")
    return True


WORKOUT_CALORIE_ESTIMATOR_KT = '''package com.openhealth.sync.util

import androidx.health.connect.client.records.ExerciseSessionRecord

/**
 * MET-formula calorie ESTIMATE for a workout -- not measured data.
 *
 * Extracted (sprint 2026-08-26) from GoogleHealthManager so the exact same
 * formula and MET table back both:
 * - the TotalCaloriesBurnedRecord GoogleHealthManager writes to Health
 *   Connect so third-party readers have something to import (see
 *   GoogleHealthManager.writeActivitySessionsBatch), and
 * - the workout card's own calorie display when Huawei's real
 *   activeCaloriesKcal is unavailable (see workoutMetricDisplays in
 *   FinalBitLutShell.kt).
 *
 * Keeping one shared implementation means a future correction to the MET
 * table or the formula only has to be made once, and the two call sites can
 * never silently drift apart.
 *
 * This is NOT measured data: Huawei's real per-workout calorie figure is
 * gated behind the activeCalories scope that returns error 50005 for this
 * individual-developer account, and nothing about that is expected to
 * change. The formula itself -- kcal = MET * 3.5 * weightKg * minutes / 200
 * -- and the MET values below are drawn from the Compendium of Physical
 * Activities (Ainsworth et al.), the standard reference most fitness
 * calorie calculators cite. Reference body weight is fixed at 70 kg, the
 * conventional default used across MET calculators when no real weight is
 * available -- BitLut has no access to the user's actual weight, and adding
 * that would be a new data category, which this feature is explicitly
 * scoped to avoid.
 *
 * MET values are the "general/moderate" variant for each activity where the
 * Compendium lists multiple intensity bands, since Huawei's activity
 * records carry no intensity signal to pick a different one.
 *
 * See docs/HEALTH_DATA_PERMISSION_MATRIX.md's "Documented exception:
 * estimated workout calories" section for the full rationale and the
 * explicit exception this makes to that document's "never synthesize fake
 * health data" rule.
 */
object WorkoutCalorieEstimator {

    private const val REFERENCE_WEIGHT_KG = 70.0

    /**
     * Estimated total calories burned for a workout of the given exercise
     * type and duration. Returns null for a zero-or-negative duration, so
     * callers can fall back to a "no data" display or skip writing a record
     * for a malformed session.
     */
    fun estimateTotalCaloriesKcal(exerciseType: Int, startTimeMs: Long, endTimeMs: Long): Double? {
        val minutes = (endTimeMs - startTimeMs) / 60_000.0
        if (minutes <= 0.0) return null

        val met = metValueFor(exerciseType)
        return met * 3.5 * REFERENCE_WEIGHT_KG * minutes / 200.0
    }

    /** General/moderate MET value per Health Connect exercise type, from the
     *  Compendium of Physical Activities. See [estimateTotalCaloriesKcal]. */
    private fun metValueFor(exerciseType: Int): Double = when (exerciseType) {
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
    }
}
'''


def main() -> None:
    estimator_path = ROOT / "app/src/main/java/com/openhealth/sync/util/WorkoutCalorieEstimator.kt"
    manager_path = ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
    viewmodel_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt"
    shell_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
    strings_en_path = ROOT / "app/src/main/res/values/strings.xml"
    strings_ru_path = ROOT / "app/src/main/res/values-ru/strings.xml"

    for p in (manager_path, viewmodel_path, shell_path, strings_en_path, strings_ru_path):
        if not p.exists():
            die(f"Required file missing: {p}")

    # ---------------------------------------------------------------
    # 1. New shared calorie estimator
    # ---------------------------------------------------------------
    print("== Step 1/8: create WorkoutCalorieEstimator.kt ==")
    create_file_if_missing(estimator_path, WORKOUT_CALORIE_ESTIMATOR_KT)

    # ---------------------------------------------------------------
    # 2. GoogleHealthManager.kt: delegate to the shared estimator
    # ---------------------------------------------------------------
    print("== Step 2/8: GoogleHealthManager.kt -- delegate to WorkoutCalorieEstimator ==")
    apply_edit(
        manager_path,
        old='''    /**
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
    }

''',
        new='''    /**
     * MET-formula estimate of total calories burned for a workout, used only
     * to give third-party Health Connect readers something non-zero to
     * import (see the call site in [writeActivitySessionsBatch] for why).
     * Delegates to [com.openhealth.sync.util.WorkoutCalorieEstimator] (sprint
     * 2026-08-26 extraction) so this exact formula and MET table also back
     * the workout card's own calorie display -- see that object's own doc
     * comment for the full rationale, the formula, and why it is not
     * measured data.
     */
    private fun estimatedTotalCaloriesKcal(exerciseType: Int, startTimeMs: Long, endTimeMs: Long): Double? =
        com.openhealth.sync.util.WorkoutCalorieEstimator.estimateTotalCaloriesKcal(exerciseType, startTimeMs, endTimeMs)

''',
    )

    # ---------------------------------------------------------------
    # 3. DashboardViewModel.kt: fix stale cache across midnight
    # ---------------------------------------------------------------
    print("== Step 3/8: DashboardViewModel.kt -- import Instant/ZoneId ==")
    apply_insertion(
        viewmodel_path,
        anchor="import java.time.LocalDate",
        new_with_anchor="import java.time.Instant\nimport java.time.LocalDate\nimport java.time.ZoneId",
    )

    print("== Step 4/8: DashboardViewModel.kt -- zero daily totals when cache predates today ==")
    apply_edit(
        viewmodel_path,
        old='''        val goalsBase = readGoalsIntoState(DashboardUiState(visibleWidgets = widgetVisibilityPrefs.snapshot()))
        val base = readAchievementsIntoState(goalsBase)
        if (cached == null) return base

        return base.withSnapshot(cached.snapshot).copy(
            isLoading = true,
            // We have cached data, but we haven't actually confirmed permissions
            // are still granted in this process yet -- that happens in load().
            // hasPermissions stays true here (optimistic, last-known-good) so the
            // UI renders real numbers immediately; permissionsChecked stays false
            // so showConnectLockScreen still correctly reports "unknown" rather
            // than a hard "true" or "false".
            hasPermissions = true,
            permissionsChecked = false,
            isFromCache = true,
            lastUpdatedAtMs = cached.dataChangedAtMs
        )
    }''',
        new='''        val goalsBase = readGoalsIntoState(DashboardUiState(visibleWidgets = widgetVisibilityPrefs.snapshot()))
        val base = readAchievementsIntoState(goalsBase)
        if (cached == null) return base

        val cachedDate = Instant.ofEpochMilli(cached.savedAtMs).atZone(ZoneId.systemDefault()).toLocalDate()
        val isStaleAcrossMidnight = cachedDate.isBefore(LocalDate.now())

        val withCachedSnapshot = base.withSnapshot(cached.snapshot).copy(
            isLoading = true,
            // We have cached data, but we haven't actually confirmed permissions
            // are still granted in this process yet -- that happens in load().
            // hasPermissions stays true here (optimistic, last-known-good) so the
            // UI renders real numbers immediately; permissionsChecked stays false
            // so showConnectLockScreen still correctly reports "unknown" rather
            // than a hard "true" or "false".
            hasPermissions = true,
            permissionsChecked = false,
            isFromCache = true,
            lastUpdatedAtMs = cached.dataChangedAtMs
        )

        if (!isStaleAcrossMidnight) return withCachedSnapshot

        // Sprint 2026-08-26: the cache was last written on a previous
        // calendar day (e.g. the app was closed overnight). Showing
        // yesterday's steps/distance/calories as if they were today's is
        // misleading -- a new day has genuinely started with zero activity
        // so far. recentWorkouts is left untouched: a workout from
        // yesterday is still real, valid history and belongs in the
        // "previous workout" card regardless of what day it is now. Only
        // the daily-total fields reset to their zero defaults, and only
        // until the next live sync (already scheduled via the periodic
        // worker, or triggered by load() right after this) replaces them
        // with real numbers for the new day.
        AppLogger.i(
            TAG,
            "Cached snapshot is from $cachedDate, before today (${LocalDate.now()}) -- " +
                "showing zeroed daily totals until the next sync completes"
        )
        return withCachedSnapshot.copy(
            stepsToday = 0L,
            distanceMeters = 0.0,
            caloriesKcal = 0.0,
            workoutMinutesToday = 0L,
            activeHoursToday = 0,
            elevationMetersToday = 0.0,
            floorsToday = 0.0
        )
    }''',
    )

    # ---------------------------------------------------------------
    # 4. FinalBitLutShell.kt: strength training shows Duration + Calories only
    # ---------------------------------------------------------------
    print("== Step 5/8: FinalBitLutShell.kt -- import WorkoutCalorieEstimator ==")
    apply_insertion(
        shell_path,
        anchor="import com.openhealth.sync.util.AppLogger",
        new_with_anchor="import com.openhealth.sync.util.AppLogger\nimport com.openhealth.sync.util.WorkoutCalorieEstimator",
    )

    print("== Step 6/8: FinalBitLutShell.kt -- special-case strength training metrics ==")
    apply_edit(
        shell_path,
        old='''private data class WorkoutMetricDisplay(val label: String, val value: String)

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
}''',
        new='''private data class WorkoutMetricDisplay(val label: String, val value: String)

@Composable
private fun workoutMetricDisplays(
    session: ActivitySessionData,
    durationMinutes: Long,
    exerciseType: Int?
): List<WorkoutMetricDisplay> {
    val noData = stringResource(R.string.no_data_short)
    val durationDisplay = WorkoutMetricDisplay(
        stringResource(R.string.workout_stat_duration_label),
        stringResource(R.string.workout_duration_value, durationMinutes)
    )

    // Sprint 2026-08-26: strength training has no meaningful distance, speed,
    // or step count -- showing those fields as "--" for every strength
    // session is confusing rather than merely empty (see this function's own
    // doc comment above for the same "logical field but shows an em dash
    // almost every time" problem, previously fixed the same way for biking).
    // Duration + Calories are the two fields that are actually meaningful
    // for this exercise type. Calories prefers Huawei's real measured
    // activeCaloriesKcal when present, and falls back to the shared
    // MET-formula estimate (WorkoutCalorieEstimator, sprint 2026-08-26) only
    // when it isn't -- which is always true for this Huawei account today,
    // since the activeCalories scope is permanently denied (error 50005).
    if (exerciseType == ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING) {
        val realOrEstimatedKcal = session.activeCaloriesKcal?.takeIf { it > 0.0 }
            ?: WorkoutCalorieEstimator.estimateTotalCaloriesKcal(
                exerciseType,
                session.startTimeMs,
                session.endTimeMs
            )
        return listOf(
            durationDisplay,
            WorkoutMetricDisplay(
                stringResource(R.string.workout_stat_calories_label),
                realOrEstimatedKcal?.let {
                    stringResource(R.string.workout_calories_value, formatNumber(it.toLong()))
                } ?: noData
            )
        )
    }

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
        durationDisplay,
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
}''',
    )

    # ---------------------------------------------------------------
    # 5. String resources (EN + RU)
    # ---------------------------------------------------------------
    print("== Step 7/8: values/strings.xml -- add calorie label/value strings ==")
    apply_insertion(
        strings_en_path,
        anchor='    <string name="workout_stat_steps_label">Steps</string>',
        new_with_anchor=(
            '    <string name="workout_stat_steps_label">Steps</string>\n'
            '    <string name="workout_stat_calories_label">Calories</string>\n'
            '    <string name="workout_calories_value">%1$s kcal</string>'
        ),
    )

    print("== Step 8/8: values-ru/strings.xml -- add calorie label/value strings ==")
    apply_insertion(
        strings_ru_path,
        anchor='    <string name="workout_stat_steps_label">Шаги</string>',
        new_with_anchor=(
            '    <string name="workout_stat_steps_label">Шаги</string>\n'
            '    <string name="workout_stat_calories_label">Калории</string>\n'
            '    <string name="workout_calories_value">%1$s ккал</string>'
        ),
    )

    # ---------------------------------------------------------------
    # Verification (symptom-based, not anchor-based)
    # ---------------------------------------------------------------
    print("\n== Verification ==")
    import xml.etree.ElementTree as ET

    for xml_path in (strings_en_path, strings_ru_path):
        try:
            ET.parse(xml_path)
        except ET.ParseError as e:
            die(f"{xml_path.name} is not well-formed XML after patch: {e}")
    print("  verified: both strings.xml files are well-formed XML")

    if not estimator_path.exists():
        die(f"Expected new file not found: {estimator_path}")
    estimator_text = read(estimator_path)
    if "fun estimateTotalCaloriesKcal(" not in estimator_text:
        die(f"Expected estimateTotalCaloriesKcal() not found in {estimator_path.name}.")
    print(f"  verified: {estimator_path.name} exists with estimateTotalCaloriesKcal()")

    manager_text = read(manager_path)
    if "WorkoutCalorieEstimator.estimateTotalCaloriesKcal" not in manager_text:
        die(f"Expected delegation to WorkoutCalorieEstimator not found in {manager_path.name}.")
    if "exerciseTypeMetValue" in manager_text:
        die(
            f"{manager_path.name} still contains the old exerciseTypeMetValue "
            "function -- the MET table should have been removed, not duplicated."
        )
    print(f"  verified: {manager_path.name} delegates to WorkoutCalorieEstimator, no duplicate MET table")

    viewmodel_text = read(viewmodel_path)
    if "isStaleAcrossMidnight" not in viewmodel_text:
        die(f"Expected isStaleAcrossMidnight check not found in {viewmodel_path.name}.")
    print(f"  verified: {viewmodel_path.name} checks for a stale-across-midnight cache")

    shell_text = read(shell_path)
    if "EXERCISE_TYPE_STRENGTH_TRAINING" not in shell_text:
        die(f"Expected strength-training special case not found in {shell_path.name}.")
    if "WorkoutCalorieEstimator.estimateTotalCaloriesKcal" not in shell_text:
        die(f"Expected WorkoutCalorieEstimator call not found in {shell_path.name}.")
    print(f"  verified: {shell_path.name} special-cases strength training with a calorie fallback")

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
            "Fix stale daily totals shown across midnight on cold launch; "
            "show only Duration + Calories for strength-training workout "
            "cards (extract shared MET calorie estimator)",
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
