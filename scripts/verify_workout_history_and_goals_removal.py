#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        raise SystemExit(f"Missing {relative}")
    return path.read_text(encoding="utf-8")

huawei = read("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
scheduler = read("app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")

errors = []
def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require("ACTIVITY_HISTORY_WINDOW_DAYS = 7L" in huawei, "seven-day workout history constant missing")
require("readActivitySessions(activityStartTimeMs, endTimeMs)" in huawei, "workouts still use incremental cursor window")
require("Huawei workout query window:" in huawei, "workout-window diagnostics missing")
require(".read(DataType.DT_CONTINUOUS_STEPS_DELTA)" in huawei, "activity request carries no Huawei DataType")
require("Querying Huawei activity records with steps-delta detail" in huawei, "activity request diagnostics missing")

require('UNIQUE_SYNC_NOW = "bitlut_sync_now_v2"' in scheduler, "manual work queue was not versioned")
require("ExistingWorkPolicy.KEEP" in scheduler, "manual work is not single-flight KEEP")
require("ExistingWorkPolicy.APPEND_OR_REPLACE" not in scheduler, "legacy append chain policy remains")
require("cancelUniqueWork(LEGACY_UNIQUE_SYNC_NOW)" in scheduler, "legacy queued work migration missing")

settings_start = shell.find("private fun SettingsScreen(")
settings_end = shell.find("private fun DataSourceToggleRow(", settings_start)
settings = shell[settings_start:settings_end]
summary_start = shell.find("private fun SummaryScreen(")
summary_end = shell.find("private fun WorkoutRecencyCard(", summary_start)
summary = shell[summary_start:summary_end]
require(settings_start >= 0 and settings_end > settings_start, "SettingsScreen block missing")
require("goals_section_title" not in settings, "Daily Goals card is still visible")
require("GoalStepperRow" not in shell, "Daily Goals stepper implementation remains")
require("onStepsGoalChanged" not in shell, "Daily Goals callbacks remain in shell")
require("onStepsGoalChanged" not in main, "Daily Goals callbacks remain in MainActivity")
require("dashboard_pct_goal" not in summary, "Today card still displays goal percentage")
require("progress = state.stepsProgress" not in summary, "Today card still renders goal progress")
require("data_source_section_title" in settings, "data source selector was accidentally removed")

if errors:
    print("BitLut workout-history/goals-removal verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut workout-history/goals-removal verification passed.")
