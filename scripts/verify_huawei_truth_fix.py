#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
huawei = (ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt").read_text(encoding="utf-8")
google = (ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt").read_text(encoding="utf-8")
errors = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require("readDailySummation(DataType.DT_CONTINUOUS_STEPS_DELTA" in huawei, "Huawei daily step summation missing")
require("readSteps(startTimeMs" not in huawei, "legacy raw-delta step reader still reachable")
require("canonicalHuaweiActivityName" in huawei, "Huawei numeric activity mapping missing")
require("SYNTHETIC_HUAWEI_ACTIVITY_NAME" in huawei, "synthetic sportHealth title filter missing")
require("56 -> \"running\"" in huawei, "Huawei running activity ID mapping missing")
require("90 -> \"walking\"" in huawei, "Huawei walking activity ID mapping missing")
require("sourceId: String? = null" in google, "daily step source identity missing")
require("client.deleteRecords(\n                StepsRecord::class" in google, "owned time-range step reconciliation missing")
require("bitlut_steps_daily_" in google, "stable daily step clientRecordId missing")
require("version = System.currentTimeMillis()" in google, "monotonic Health Connect upsert version missing")
require("workoutDisplayName(it.title, it.exerciseType)" in google, "workout title sanitization missing")
require("SYNTHETIC_WORKOUT_TITLE" in google, "Health Connect sportHealth title fallback missing")
require(huawei.count("import java.time.Instant") == 1, "Huawei time imports duplicated")
require(google.count("private fun workoutDisplayName") == 1, "workout title sanitizer duplicated")

if errors:
    print("BitLut Huawei truth fix verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut Huawei truth fix verification passed.")
