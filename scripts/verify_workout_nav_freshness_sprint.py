#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        errors.append(f"Missing {rel}")
        return ""
    return path.read_text(encoding="utf-8")

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
cache = read("app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt")
vm = read("app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
nav = read("app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt")
strings_en = read("app/src/main/res/values/strings.xml")
strings_ru = read("app/src/main/res/values-ru/strings.xml")
app_gradle = read("app/build.gradle.kts")

for field in ["activeCaloriesKcal: Double?", "elevationMeters: Double?", "steps: Long?"]:
    require(field in google, f"Workout metric field missing: {field}")
require("SessionMetricAccumulator" in google, "bulk workout metric accumulator missing")
require("displayedWorkouts = workouts.take(2)" in google, "metric attribution is not bounded to displayed workouts")
require("overlapFraction" in google, "time-overlap attribution helper missing")
require("DashboardActivityWindow" in google, "dashboard activity result wrapper missing")
require("activeCaloriesKcal = metrics.activeCaloriesKcal" in google, "calories are not attributed to workouts")
require("elevationMeters = metrics.elevationMeters" in google, "elevation is not attributed to workouts")
require("steps = metrics.steps.toLong()" in google, "steps are not attributed to workouts")

for field in ["activeCaloriesKcal", "elevationMeters", 'w.steps?.let { put("steps", it) }']:
    require(field in cache, f"cached workout metric missing: {field}")
require("private const val KEY_SNAPSHOT_DATA_CHANGED_AT_MS" in cache, "data-changed timestamp key missing")
require("val dataChangedAtMs" in cache, "CachedSnapshot dataChangedAtMs missing")
require("previous?.snapshot == snapshot" in cache, "cache does not preserve timestamp for identical data")
require("KEY_SNAPSHOT_SAVED_AT_MS" in cache, "cache freshness timestamp must remain intact")
require("lastUpdatedAtMs = cached.dataChangedAtMs" in vm, "cold start does not use data-change time")
require("val dataChangedAtMs = snapshotCache.save(snapshot)" in vm, "live load does not get data-change time")
require("lastUpdatedAtMs = dataChangedAtMs" in vm, "UI freshness still uses app-open wall clock")
require("lastUpdatedAtMs = System.currentTimeMillis()" not in vm, "app-open timestamp bug remains")

require("workoutMetricDisplays" in shell, "type-aware workout metrics missing")
for marker in [
    "EXERCISE_TYPE_RUNNING", "EXERCISE_TYPE_WALKING", "EXERCISE_TYPE_BIKING",
    "EXERCISE_TYPE_HIKING", "EXERCISE_TYPE_SWIMMING_POOL", "EXERCISE_TYPE_STRENGTH_TRAINING",
    "workout_stat_speed_label"
]:
    require(marker in shell, f"workout UI marker missing: {marker}")
require("metrics.take(4).chunked(2)" in shell, "workout cards are not capped to four metrics")
require("workout_stat_elevation_label" not in shell, "retired workout UI marker still present in card composable: workout_stat_elevation_label")
require(
    "workout_stat_calories_label" in shell,
    "biking's 4th metric slot (Active Calories, hotfixed 2026-08-22) is missing from the card composable"
)
require("state.lastUpdatedAtMs" in shell, "header does not use displayed-data freshness")
require("syncState.lastSyncTime" not in shell, "header still depends on sync-completion clock")

require("Compact August v3 navigation dock" in nav, "new navigation dock missing")
require("text = label" in nav, "destination labels are not persistently rendered")
require("destinationPressScale" in nav, "destination press motion missing")
require("syncPressRotation" in nav, "sync press rotation missing")
require("AugustColor.TangerineActive" in nav, "sync active state missing")
require("Role.Tab" in nav and "Role.Button" in nav, "navigation semantics missing")
require("navigationBarsPadding()" in nav, "gesture-navigation inset handling missing")
require("dev.chrisbanes.haze" not in nav and "dev.chrisbanes.haze" not in app_gradle, "Haze was reintroduced")

for key in [
    "workout_stat_speed_label", "workout_stat_steps_label", "workout_stat_started_label",
    "workout_stat_ended_label", "workout_stat_swim_pace_label", "workout_speed_value",
    "workout_swim_pace_value", "workout_stat_calories_label", "workout_calories_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

for retired in ["workout_stat_elevation_label", "workout_elevation_value"]:
    require(f'name="{retired}"' not in strings_en, f"retired English string still present: {retired}")
    require(f'name="{retired}"' not in strings_ru, f"retired Russian string still present: {retired}")

for forbidden in ["HeartRateRecord", "SleepSessionRecord", "OxygenSaturationRecord"]:
    require(forbidden not in google, f"new out-of-scope health category leaked in: {forbidden}")

if errors:
    print("BitLut workout/nav/freshness verification FAILED:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut workout/nav/freshness static verification passed.")
