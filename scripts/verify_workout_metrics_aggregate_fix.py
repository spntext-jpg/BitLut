#!/usr/bin/env python3
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
