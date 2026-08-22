#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
google = (ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt").read_text(encoding="utf-8")
shell = (ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt").read_text(encoding="utf-8")

errors = []

def require(condition, message):
    if not condition:
        errors.append(message)

require(
    "private const val WORKOUT_DISTANCE_QUERY_PADDING_SECONDS" in google,
    "top-level workout distance recovery constants missing",
)
require(
    "private suspend fun recoverWorkoutDistanceFromRawRecords(" in google,
    "raw workout distance fallback missing",
)
require(
    "recordDurationMs > MAX_WORKOUT_DISTANCE_SOURCE_RECORD_MS" in google,
    "long/coarse distance record guard missing",
)
require(
    "record.distance.inMeters * overlapFraction" in google,
    "exact overlap attribution missing",
)
require(
    "key in displayedWorkoutKeys" in google,
    "fallback is not limited to displayed workouts",
)
require(
    "if (distanceMeters != null) distance() else stepsMetric()" in shell,
    "walking/running real-steps fallback missing",
)
require(
    "if (paceMinutesPerKm != null) pace() else started()" in shell,
    "walking/running time fallback missing",
)
require(
    not (ROOT / "scripts/verify_workout_metric_boundary_fix.py").exists(),
    "failed verifier from previous attempt still exists",
)

if errors:
    print("Workout metric recovery verification FAILED:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Workout metric recovery verification passed.")
