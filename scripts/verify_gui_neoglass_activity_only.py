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

def read_optional(path):
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")

shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
prefs = read("app/src/main/java/com/openhealth/sync/config/WidgetVisibilityPrefs.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")

component_dir = Path("app/src/main/java/com/openhealth/sync/ui/components")
components = ""
if component_dir.exists():
    for path in sorted(component_dir.glob("*.kt")):
        components += "\n// FILE: " + str(path) + "\n"
        components += path.read_text(encoding="utf-8") + "\n"

ui_sources = shell + "\n" + components

def require(condition, message):
    if not condition:
        errors.append(message)

def function_count(name):
    return len(
        re.findall(
            r"(?m)^\s*(?:@[A-Za-z0-9_.]+(?:\([^)]*\))?\s*\n\s*)*(?:private|internal|public)?\s*fun\s+"
            + re.escape(name)
            + r"\s*(?:<[^>]+>)?\s*\(",
            ui_sources,
        )
    )

def function_exists(name):
    return function_count(name) > 0

require("Glass20BottomNavigation(" in shell, "Shell must call Glass20BottomNavigation")
require(function_exists("Glass20BottomNavigation"), "Missing Glass20BottomNavigation")
require(function_exists("Glass20NavButton"), "Missing Glass20NavButton")
require(function_exists("SoftCard"), "Missing SoftCard")
require(function_exists("MetricBarChartCard"), "Missing MetricBarChartCard")

require("NavigationBarItem(" not in ui_sources, "Material NavigationBarItem must not remain")
require("NavigationBar(" not in ui_sources, "Material NavigationBar must not remain")
require("contentDescription = null" in ui_sources, "Bottom navigation must be icon-only")
require("Brush.linearGradient" in ui_sources and "Brush.radialGradient" in ui_sources, "Glass gradients are missing")
require("drawLine(" in ui_sources, "Glass highlight line is missing")
require("defaultMinSize(minHeight = 6.dp)" in ui_sources, "Metric bars need bounded minimum visible height")
require(".height(84.dp)" in ui_sources, "Metric bar drawing area must be bounded")
require(".height(132.dp)" in ui_sources, "Metric chart row must reserve stable vertical space")
require("TextOverflow.Ellipsis" in ui_sources, "Large chart labels must be clipped safely")
require("val targetCardColor = if (palette.dark)" in ui_sources, "Global SoftCard glass system missing")

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

for fn in [
    "SummaryScreen",
    "HistoryScreen",
    "SettingsScreen",
]:
    if f"private fun {fn}(" in shell:
        require(
            re.search(r"@Composable\s*\nprivate fun " + re.escape(fn) + r"\(", shell) is not None,
            f"{fn} must be @Composable"
        )

for fn in [
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
]:
    require(function_count(fn) == 1, f"{fn} must exist exactly once")

require("@Composable\n@Composable" not in shell, "Duplicate @Composable annotation found in shell")
require("refreshUiStatusOnLaunch()" in main, "MainActivity must refresh status on launch")

if errors:
    print("Glass 2.0 GUI verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Glass 2.0 GUI verification passed.")
