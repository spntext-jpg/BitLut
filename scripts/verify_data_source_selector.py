#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        raise SystemExit(f"Missing {relative}")
    return path.read_text(encoding="utf-8")

prefs = read("app/src/main/java/com/openhealth/sync/config/DataSourcePrefs.kt")
google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
cache = read("app/src/main/java/com/openhealth/sync/data/DashboardSnapshotCache.kt")
achievements = read("app/src/main/java/com/openhealth/sync/data/AchievementsStore.kt")
container = read("app/src/main/java/com/openhealth/sync/di/AppContainer.kt")
worker = read("app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt")
sync_vm = read("app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt")
dashboard_vm = read("app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
strings_en = read("app/src/main/res/values/strings.xml")
strings_ru = read("app/src/main/res/values-ru/strings.xml")

errors = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require('HUAWEI_HEALTH("huawei_health")' in prefs, "Huawei source preference missing")
require('GOOGLE_FIT("google_fit")' in prefs, "Google Fit source preference missing")
require('GOOGLE_FIT_PACKAGE = "com.google.android.apps.fitness"' in prefs, "Google Fit package missing")
require("selectedOriginPackage" in prefs, "selected origin mapping missing")

require("DataOrigin(dataSourcePrefs.selectedOriginPackage(context.packageName))" in google, "Health Connect origin filter helper missing")
require(google.count("dataOriginFilter = selectedDataOrigins()") >= 14, "not all dashboard/export reads are source-filtered")
require("Reading dashboard source=" in google, "selected-source dashboard diagnostic missing")
require("GoogleHealthManager(context, dataSourcePrefs)" in container, "Google manager does not share source prefs")
require("DashboardSnapshotCache(context, dataSourcePrefs)" in container, "cache does not share source prefs")
require("AchievementsStore(context, dataSourcePrefs)" in container, "achievements do not share source prefs")
require('"${base}_${dataSourcePrefs.selected().storageValue}"' in cache, "cache is not source scoped")
require('"${base}_${dataSourcePrefs.selected().storageValue}"' in achievements, "achievements are not source scoped")

require("selectedSource == HealthDataSource.GOOGLE_FIT" in worker, "worker has no Google Fit path")
require("Huawei import skipped" in worker, "worker does not explicitly skip Huawei in Google Fit mode")
require("huaweiBreakerBlocksSelectedSource" in worker, "Huawei circuit breaker can still block Google Fit mode")

require("selectedDataSource: HealthDataSource" in sync_vm, "SyncUiState source missing")
require("fun setDataSource(source: HealthDataSource)" in sync_vm, "source setter missing")
require("app.container.dataSourcePrefs" in main, "MainActivity source prefs injection missing")
require("dashboardViewModel.onDataSourceChanged()" in main, "Dashboard is not rebuilt on source switch")
require("onDataSourceSelected" in shell, "Settings source callback missing")
require("DataSourceToggleRow" in shell, "exclusive source switch UI missing")
require("verticalScroll(rememberScrollState())" in shell, "Settings is not scrollable after adding source controls")
require("recentWorkouts  = snapshot.recentWorkouts" in dashboard_vm, "workouts can still leak across source switches")
require("fun onDataSourceChanged()" in dashboard_vm, "Dashboard source switch reload missing")

for key in [
    "data_source_section_title",
    "data_source_section_body",
    "data_source_huawei_title",
    "data_source_huawei_body",
    "data_source_google_fit_title",
    "data_source_google_fit_body",
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

if errors:
    print("BitLut data-source selector verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut data-source selector verification passed.")
