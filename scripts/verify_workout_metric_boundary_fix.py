#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
google = (ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt").read_text(encoding="utf-8")
shell = (ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt").read_text(encoding="utf-8")

errors = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


require(
    "private suspend fun recoverWorkoutDistanceFromRawRecords(" in google,
    "raw workout-distance boundary fallback is missing",
)
require(
    "distanceSource=" in google and '"raw_overlap"' in google,
    "workout distance source diagnostic is missing",
)
require(
    "MAX_WORKOUT_DISTANCE_SOURCE_RECORD_MS" in google,
    "daily/long distance record safety guard is missing",
)
require(
    "overlapFraction = overlapMs.toDouble() / recordDurationMs.toDouble()" in google,
    "raw fallback does not attribute only exact temporal overlap",
)
require(
    "dataOriginFilter = selectedDataOrigins()" in google,
    "selected source/origin filter was lost",
)
require(
    "pageSize = WORKOUT_DISTANCE_FALLBACK_PAGE_SIZE" in google,
    "raw fallback is not quota bounded",
)
require(
    "readAllRecords(" not in google,
    "unbounded Health Connect pagination returned to the hot path",
)
require(
    "if (distanceMeters != null) distance() else stepsMetric()" in shell,
    "walking/running cards do not fall back to real steps",
)
require(
    "if (paceMinutesPerKm != null) pace() else started()" in shell,
    "walking/running cards still show an avoidable empty pace slot",
)
require(
    "if (calories != null) caloriesMetric()" in shell,
    "workout cards lost real calorie selection",
)

if errors:
    print("Workout metric boundary verification FAILED:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Workout metric boundary verification passed.")
