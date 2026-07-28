#!/usr/bin/env python3
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
huawei = (ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt").read_text(encoding="utf-8")
google = (ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt").read_text(encoding="utf-8")
store = (ROOT / "app/src/main/java/com/openhealth/sync/data/WorkoutDetailsStore.kt").read_text(encoding="utf-8")
cache = (ROOT / "app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt").read_text(encoding="utf-8")
shell = (ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt").read_text(encoding="utf-8")
errors = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require("getActivitySummary" in huawei, "Huawei ActivityRecord summary is not read")
require("getDataSummary" in huawei, "Huawei activity dataSummary is not read")
require("getPaceSummary" in huawei, "Huawei pace summary is not read")
require("heart_rate" in huawei and "continue" in huawei, "heart-rate exclusion guard missing")
require("activityKey = canonicalType" in huawei, "Huawei activity key not preserved")
require("metrics = metrics" in huawei, "Huawei workout metrics not attached")
require("data class WorkoutMetric" in google, "WorkoutMetric model missing")
require("WorkoutDetailsStore(context)" in google, "Workout details store not wired")
require("workoutDetailsStore.saveAll(records)" in google, "Workout details not persisted")
require("workoutDetailsStore.enrich(session)" in google, "Recent workouts not enriched")
require("activityKey" in cache and "metrics" in cache, "Dashboard cache does not persist workout details")
require("activityKey = session?.activityKey" in shell, "Dynamic workout icon missing")
require("WorkoutMetricsGrid" in shell, "Workout metric grid missing")
require("Icons.Rounded.DirectionsBike" in shell, "Cycling icon missing")
require("Icons.Rounded.Pool" in shell, "Swimming icon missing")
require("Icons.Rounded.FitnessCenter" in shell, "Strength icon missing")
require("Icon(\n                    Icons.Rounded.DirectionsRun," not in shell, "Fixed running icon still hard-coded in workout card")
require(shell.count("private fun workoutIcon(") == 1, "workoutIcon helper duplicated")
require(google.count("object WorkoutMetricKey") == 1, "WorkoutMetricKey duplicated")
require(huawei.count("private fun extractWorkoutMetrics(") == 1, "metric extractor duplicated")

for path in [
    ROOT / "app/src/main/res/values/strings.xml",
    ROOT / "app/src/main/res/values-ru/strings.xml",
]:
    try:
        ET.parse(path)
    except Exception as exc:
        errors.append(f"invalid XML {path}: {exc}")

if errors:
    print("BitLut rich workout cards verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut rich workout cards verification passed.")
