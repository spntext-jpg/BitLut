#!/usr/bin/env python3
"""
BitLut workout metrics aggregation fix.

The dashboard previously tried to reconstruct workout metrics by matching a
bounded 30-day page of raw activity records to exercise sessions. Once the
newest-first page no longer covered the session interval, workout cards showed
an em dash even though Health Connect still contained historical distance.

This patch keeps the quota-safe bounded dashboard reads and adds exactly one
Health Connect aggregate request for each of the two displayed workouts.
Health Connect performs the interval aggregation for distance, active calories,
elevation and steps, avoiding raw-record pagination and manual overlap math as
the primary source for workout cards.

Run from the BitLut repository root:
    python3 bitlut_workout_metrics_aggregate_fix.py --apply
    python3 bitlut_workout_metrics_aggregate_fix.py --verify
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GOOGLE = ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"
VERIFIER = ROOT / "scripts/verify_workout_metrics_aggregate_fix.py"


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def ensure_repo() -> None:
    required = [GOOGLE, ROOT / "gradlew", ROOT / "app/build.gradle.kts"]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        fail("Run from the BitLut repository root. Missing: " + ", ".join(missing))


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    if new in text:
        return text, False
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected exactly one source anchor, found {count}")
    return text.replace(old, new, 1), True


def apply() -> None:
    ensure_repo()
    text = GOOGLE.read_text(encoding="utf-8")
    changed = False

    old_snapshot = '''            val recentWorkouts = readRecentWorkouts(200)
            val activityWindow = readDailyActivitySummaries(
                client = client,
                daysBack = DASHBOARD_HISTORY_DAYS,
                workouts = recentWorkouts
            )
            val today = LocalDate.now()
            val todayActivity = activityWindow.dailyActivity.firstOrNull { it.date == today }

            GoogleDashboardSnapshot(
                stepsToday = todayActivity?.steps ?: 0L,
                distanceMeters = todayActivity?.distanceMeters ?: 0.0,
                caloriesKcal = todayActivity?.caloriesKcal ?: 0.0,
                workoutMinutesToday = todayActivity?.workoutMinutes ?: 0L,
                activeHoursToday = 0,
                recentWorkouts = activityWindow.workouts.take(2),
                dailyActivity = activityWindow.dailyActivity
            )'''

    new_snapshot = '''            val recentWorkouts = readRecentWorkouts(200)
            val activityWindow = readDailyActivitySummaries(
                client = client,
                daysBack = DASHBOARD_HISTORY_DAYS,
                workouts = recentWorkouts
            )
            val displayedWorkouts = enrichDisplayedWorkoutMetrics(
                client = client,
                workouts = activityWindow.workouts.take(2)
            )
            val today = LocalDate.now()
            val todayActivity = activityWindow.dailyActivity.firstOrNull { it.date == today }

            GoogleDashboardSnapshot(
                stepsToday = todayActivity?.steps ?: 0L,
                distanceMeters = todayActivity?.distanceMeters ?: 0.0,
                caloriesKcal = todayActivity?.caloriesKcal ?: 0.0,
                workoutMinutesToday = todayActivity?.workoutMinutes ?: 0L,
                activeHoursToday = 0,
                recentWorkouts = displayedWorkouts,
                dailyActivity = activityWindow.dailyActivity
            )'''

    text, did = replace_once(
        text,
        old_snapshot,
        new_snapshot,
        "wire exact workout aggregation into dashboard snapshot",
    )
    changed |= did

    helper = '''    /**
     * Enriches only the workout cards that are actually displayed.
     *
     * Raw activity records are still used for the 30-day dashboard ledger, but
     * they are not a reliable primary source for per-session metrics: a bounded
     * newest-first page can legitimately omit records from an older workout.
     * Health Connect's aggregate API is designed for this exact case and
     * computes totals inside the exercise interval without paging raw records.
     *
     * The dashboard shows two workouts, so this adds at most two provider calls
     * per dashboard snapshot and keeps the quota-storm fix intact.
     */
    private suspend fun enrichDisplayedWorkoutMetrics(
        client: HealthConnectClient,
        workouts: List<ActivitySessionData>
    ): List<ActivitySessionData> = workouts.take(2).map { workout ->
        if (workout.endTimeMs <= workout.startTimeMs) return@map workout

        val start = Instant.ofEpochMilli(workout.startTimeMs)
        val end = Instant.ofEpochMilli(workout.endTimeMs)

        try {
            val aggregate = client.aggregate(
                AggregateRequest(
                    metrics = setOf(
                        StepsRecord.COUNT_TOTAL,
                        DistanceRecord.DISTANCE_TOTAL,
                        ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL,
                        ElevationGainedRecord.ELEVATION_GAINED_TOTAL
                    ),
                    timeRangeFilter = TimeRangeFilter.between(start, end),
                    dataOriginFilter = selectedDataOrigins()
                )
            )

            val distanceMeters = aggregate[DistanceRecord.DISTANCE_TOTAL]
                ?.inMeters
                ?.takeIf { it > 0.0 }
            val activeCaloriesKcal = aggregate[ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL]
                ?.inKilocalories
                ?.takeIf { it > 0.0 }
            val elevationMeters = aggregate[ElevationGainedRecord.ELEVATION_GAINED_TOTAL]
                ?.inMeters
                ?.takeIf { it > 0.0 }
            val steps = aggregate[StepsRecord.COUNT_TOTAL]
                ?.takeIf { it > 0L }

            AppLogger.i(
                TAG,
                "Workout metrics aggregated: type=${workout.exerciseType} " +
                    "start=${workout.startTimeMs} end=${workout.endTimeMs} " +
                    "distanceMeters=${distanceMeters ?: 0.0} " +
                    "activeCaloriesKcal=${activeCaloriesKcal ?: 0.0} " +
                    "elevationMeters=${elevationMeters ?: 0.0} steps=${steps ?: 0L}"
            )

            workout.copy(
                distanceMeters = distanceMeters ?: workout.distanceMeters,
                activeCaloriesKcal = activeCaloriesKcal ?: workout.activeCaloriesKcal,
                elevationMeters = elevationMeters ?: workout.elevationMeters,
                steps = steps ?: workout.steps
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLogger.w(
                TAG,
                "Workout metric aggregation failed for ${workout.startTimeMs}..${workout.endTimeMs}: ${e.message}"
            )
            workout
        }
    }

'''

    helper_anchor = '''    /**
     * Dashboard reads must stay quota-bounded.'''
    if helper not in text:
        count = text.count(helper_anchor)
        if count != 1:
            fail(f"insert workout aggregation helper: expected one anchor, found {count}")
        text = text.replace(helper_anchor, helper + helper_anchor, 1)
        changed = True

    old_precedence = '''                workout.copy(
                    distanceMeters = metrics.distanceMeters.takeIf { it > 0.0 } ?: workout.distanceMeters,
                    activeCaloriesKcal = metrics.activeCaloriesKcal.takeIf { it > 0.0 } ?: workout.activeCaloriesKcal,
                    elevationMeters = metrics.elevationMeters.takeIf { it > 0.0 } ?: workout.elevationMeters,
                    steps = metrics.steps.toLong().takeIf { it > 0L } ?: workout.steps
                )'''

    new_precedence = '''                workout.copy(
                    distanceMeters = workout.distanceMeters ?: metrics.distanceMeters.takeIf { it > 0.0 },
                    activeCaloriesKcal = workout.activeCaloriesKcal ?: metrics.activeCaloriesKcal.takeIf { it > 0.0 },
                    elevationMeters = workout.elevationMeters ?: metrics.elevationMeters.takeIf { it > 0.0 },
                    steps = workout.steps ?: metrics.steps.toLong().takeIf { it > 0L }
                )'''

    text, did = replace_once(
        text,
        old_precedence,
        new_precedence,
        "prefer exact aggregate workout metrics over raw-page overlap fallback",
    )
    changed |= did

    if changed:
        GOOGLE.write_text(text, encoding="utf-8")
        print(f"Updated: {GOOGLE.relative_to(ROOT)}")
    else:
        print("Already applied: source is unchanged.")

    write_verifier()
    verify_static()


def write_verifier() -> None:
    VERIFIER.parent.mkdir(parents=True, exist_ok=True)
    content = r'''#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GOOGLE = ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt"

if not GOOGLE.exists():
    raise SystemExit("Missing GoogleHealthManager.kt")

text = GOOGLE.read_text(encoding="utf-8")
errors = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


require("private suspend fun enrichDisplayedWorkoutMetrics(" in text, "workout aggregate helper missing")
require("DistanceRecord.DISTANCE_TOTAL" in text, "distance aggregate metric missing")
require("ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL" in text, "active-calorie aggregate metric missing")
require("ElevationGainedRecord.ELEVATION_GAINED_TOTAL" in text, "elevation aggregate metric missing")
require("StepsRecord.COUNT_TOTAL" in text, "steps aggregate metric missing")
require("TimeRangeFilter.between(start, end)" in text, "workout aggregate does not use exact session interval")
require("dataOriginFilter = selectedDataOrigins()" in text, "workout aggregate lost selected-origin filter")
require("workouts = activityWindow.workouts.take(2)" in text, "dashboard must aggregate only two displayed workouts")
require("recentWorkouts = displayedWorkouts" in text, "dashboard does not expose aggregated workouts")
require("Workout metrics aggregated:" in text, "diagnostic metric log missing")
require("private suspend fun <T : Record> readBoundedRecentRecords(" in text, "quota-safe bounded reader was removed")
require("readAllRecords(" not in text, "unbounded pagination must not return to dashboard hot path")
require("distanceMeters = workout.distanceMeters ?: metrics.distanceMeters" in text, "raw overlap fallback can overwrite exact aggregate distance")
require("activeCaloriesKcal = workout.activeCaloriesKcal ?: metrics.activeCaloriesKcal" in text, "raw overlap fallback can overwrite exact aggregate calories")
require("elevationMeters = workout.elevationMeters ?: metrics.elevationMeters" in text, "raw overlap fallback can overwrite exact aggregate elevation")

for forbidden in ["HeartRateRecord", "SleepSessionRecord", "OxygenSaturationRecord"]:
    require(forbidden not in text, f"out-of-scope health category introduced: {forbidden}")

if errors:
    print("Workout metric aggregation verification FAILED:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Workout metric aggregation verification passed.")
'''
    VERIFIER.write_text(content, encoding="utf-8")
    VERIFIER.chmod(0o755)
    print(f"Updated: {VERIFIER.relative_to(ROOT)}")


def verify_static() -> None:
    ensure_repo()
    write_verifier_if_missing = not VERIFIER.exists()
    if write_verifier_if_missing:
        write_verifier()
    result = subprocess.run(["python3", str(VERIFIER)], cwd=ROOT)
    if result.returncode != 0:
        fail("Static verification failed")


def run_build() -> None:
    command = [
        "./gradlew",
        ":app:assembleDebug",
        "--no-daemon",
        "--max-workers=1",
        "--no-watch-fs",
        "--console=plain",
        "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
        "-Pkotlin.compiler.execution.strategy=in-process",
    ]
    print("==> " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        fail(f"Build failed with exit code {result.returncode}")
    print("Android build passed.")


def verify() -> None:
    verify_static()
    run_build()


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--verify-static", action="store_true")
    args = parser.parse_args()

    if args.apply:
        apply()
    elif args.verify_static:
        verify_static()
    else:
        verify()


if __name__ == "__main__":
    main()
