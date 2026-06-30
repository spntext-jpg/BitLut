#!/usr/bin/env python3
from pathlib import Path
import re
import sys

errors = []

def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
prefs = read("app/src/main/java/com/openhealth/sync/config/WidgetVisibilityPrefs.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("NeoGlassBottomBar(" in shell, "Bottom navigation must use NeoGlassBottomBar")
require("NeoGlassNavButton(" in shell, "Bottom navigation must use NeoGlassNavButton")
require("NavigationBarItem(" not in shell, "Material NavigationBarItem must be removed")
require("NavigationBar(" not in shell, "Material NavigationBar must be removed")
require("contentDescription = null" in shell, "Icon-only nav should avoid visible labels")
require("label =" not in shell[shell.find("NeoGlassBottomBar"):shell.find("private fun NeoGlassNavButton")], "Bottom bar must be icon-only")

for forbidden in [
    "DashboardWidget.HEART_RATE",
    "DashboardWidget.SLEEP",
    "DashboardWidget.STRESS",
    "DashboardWidget.SPO2",
    "HeartRateWidgetCard(",
    "SleepWidgetCard(",
    "widget_toggle_heart",
    "widget_toggle_sleep",
    "widget_toggle_stress",
    "widget_toggle_spo2",
    "readSleepLastNight",
    "readLatestSpo2Percent",
    "readStressScoreToday",
    "optionalDashboardRead(",
]:
    require(forbidden not in shell, f"Unsupported UI term remains in shell: {forbidden}")
    require(forbidden not in prefs, f"Unsupported widget term remains in prefs: {forbidden}")

for forbidden_widget in ["HEART_RATE", "SLEEP", "STRESS", "SPO2"]:
    require(forbidden_widget not in prefs, f"Unsupported DashboardWidget remains: {forbidden_widget}")

summary_start = shell.find("private fun SummaryScreen")
history_start = shell.find("private fun HistoryScreen")
summary = shell[summary_start:history_start if history_start != -1 else len(shell)]
require("refresh_status" not in summary, "Dashboard Summary must not contain refresh status button")
require("refreshUiStatusOnLaunch()" in main, "MainActivity must refresh status on launch")
require("setupPeriodicSync()\n        refreshUiStatusOnLaunch()" in main, "Launch refresh must run after periodic sync setup")
require("val showMeshGradient = true" in shell, "SoftCard must apply neo-glass glow mesh globally")

if errors:
    print("GUI neo-glass activity-only verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("GUI neo-glass activity-only verification passed.")
