#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        errors.append(f"Missing {relative}")
        return ""
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
cache = read("app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt")
achievements = read("app/src/main/java/com/openhealth/sync/data/AchievementsStore.kt")
vm = read("app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt")
worker = read("app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
strings_en = read("app/src/main/res/values/strings.xml")
strings_ru = read("app/src/main/res/values-ru/strings.xml")
policy = read("app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt")
huawei = read("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")

require("data class DailyActivitySummary(" in google, "Daily activity model missing")
require("readDailyActivitySummaries(" in google, "30-day dashboard history reader missing")
for token in ["ElevationGainedRecord::class", "FloorsClimbedRecord::class", "longestWorkoutMinutes"]:
    require(token in google, f"GoogleHealthManager missing {token}")
require("dailyActivityToJson" in cache and "dailyActivityFromJson" in cache, "Dashboard cache does not persist insight history")
require("fun mergeDailyActivity(" in achievements, "AchievementsStore daily merge missing")
require("fun achievementSummary()" in achievements, "AchievementsStore cumulative summary missing")
for token in ["bestCaloriesDay", "bestElevationMetersDay", "bestWorkoutDurationMinutes"]:
    require(token in achievements and token in vm, f"Expanded record missing: {token}")
require("achievementsStore.mergeDailyActivity(snapshot.dailyActivity)" in vm, "DashboardViewModel does not merge daily history")
require("achievementsStore.mergeDailyActivity(freshSnapshot.dailyActivity)" in worker, "SyncWorker does not merge daily history")
for token in ["ElevationSummaryCard", "LastSevenDaysCard", "AchievementsCard", "formatDashboardSourceStatus"]:
    require(token in shell, f"Dashboard UI missing {token}")
require("syncState.lastSyncTime" in shell, "Dashboard header does not use the persisted sync time")
require('getSharedPreferences("sync_prefs"' in worker and '"last_sync_time"' in worker, "Background sync does not publish its completion time")
require("cleanWorkoutCardTitle(it.title)" in shell, "Workout card still renders unsanitized cadence metadata")
require("Text(\"●\"" not in shell, "Empty dot-in-circle fallback returned")
for name in [
    "dashboard_elevation_title",
    "dashboard_last_7_days_title",
    "dashboard_record_calories",
    "dashboard_achievements_title",
    "achievement_steps_million",
]:
    require(f'name="{name}"' in strings_en, f"English string missing: {name}")
    require(f'name="{name}"' in strings_ru, f"Russian string missing: {name}")

scope_text = (policy + "\n" + huawei).upper()
for token in ["HEALTHKIT_SLEEP", "SLEEPSESSIONRECORD", "READ_SLEEP", "WRITE_SLEEP"]:
    require(token not in scope_text, f"Sleep scope unexpectedly introduced: {token}")

if errors:
    print("BitLut dashboard insights verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut dashboard insights verification passed.")
