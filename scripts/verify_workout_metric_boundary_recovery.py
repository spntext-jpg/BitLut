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

require("Workout metrics resolved:" in google, "resolved workout metric diagnostic missing")
require("distanceSource=" in google, "distance source diagnostic missing")
require("private suspend fun recoverWorkoutDistanceFromRawRecords(" in google, "raw distance recovery missing")
require("MAX_WORKOUT_DISTANCE_SOURCE_RECORD_MS" in google, "coarse-record safety guard missing")
require("record.distance.inMeters * overlapFraction" in google, "overlap-only distance attribution missing")
require("dataOriginFilter = selectedDataOrigins()" in google, "source filtering missing")
require("prefer(distance(), stepsMetric())" in shell, "workout distance-to-steps fallback missing")
require("prefer(pace(), started())" in shell, "walking/running pace-to-start fallback missing")
require(not (ROOT / "scripts/verify_workout_metric_recovery.py").exists(), "obsolete failed verifier remains")

if errors:
    print("Workout metric boundary recovery verification FAILED:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Workout metric boundary recovery verification passed.")
