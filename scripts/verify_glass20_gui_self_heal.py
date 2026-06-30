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

def function_exists(fn):
    return re.search(r"(?m)^(?:@Composable\s*\n)?private fun " + re.escape(fn) + r"\(", shell) is not None

def require_composable_if_exists(fn):
    if function_exists(fn):
        require(
            re.search(r"@Composable\s*\nprivate fun " + re.escape(fn) + r"\(", shell) is not None,
            f"{fn} must be @Composable"
        )

require("Glass20BottomNavigation(" in shell, "Missing Glass20BottomNavigation")
require("Glass20NavButton(" in shell, "Missing Glass20NavButton")
require("NavigationBarItem(" not in shell, "Material NavigationBarItem must not remain")
require("NavigationBar(" not in shell, "Material NavigationBar must not remain")
require("contentDescription = null" in shell, "Bottom navigation must be icon-only")
require("Brush.linearGradient" in shell and "Brush.radialGradient" in shell, "Glass gradients are missing")
require("drawLine(" in shell, "Glass highlight line is missing")
require("defaultMinSize(minHeight = 6.dp)" in shell, "Metric bars need bounded minimum visible height")
require(".height(84.dp)" in shell, "Metric bar drawing area must be bounded")
require(".height(132.dp)" in shell, "Metric chart row must reserve stable vertical space")
require("TextOverflow.Ellipsis" in shell, "Large chart labels must be clipped safely")
require("val targetCardColor = if (palette.dark)" in shell, "Global SoftCard glass system missing")

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
    "ImportScreen",
    "ImportDataScreen",
    "SourcesScreen",
    "SyncScreen",
    "ConnectionsScreen",
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
]:
    require_composable_if_exists(fn)

for fn in [
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
]:
    require(shell.count(f"private fun {fn}(") == 1, f"{fn} must exist exactly once")

require("@Composable\n@Composable" not in shell, "Duplicate @Composable annotation found")
require("refreshUiStatusOnLaunch()" in main, "MainActivity must refresh status on launch")

if errors:
    print("Glass 2.0 GUI verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Glass 2.0 GUI verification passed.")
