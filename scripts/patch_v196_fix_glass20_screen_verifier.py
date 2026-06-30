#!/usr/bin/env python3
from pathlib import Path
import re

SHELL = Path("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
VERIFY_GLASS = Path("scripts/verify_glass20_gui_self_heal.py")
VERIFY_GUI = Path("scripts/verify_gui_neoglass_activity_only.py")

CORE_COMPOSABLES = [
    "SummaryScreen",
    "HistoryScreen",
    "SettingsScreen",
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
]

OPTIONAL_SCREEN_CANDIDATES = [
    "ImportScreen",
    "ImportDataScreen",
    "SourcesScreen",
    "SyncScreen",
    "ConnectionsScreen",
]

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

def function_exists(text: str, fn: str) -> bool:
    return re.search(rf"(?m)^(?:@Composable\s*\n)?private fun {re.escape(fn)}\(", text) is not None

def ensure_composable(text: str, fn: str) -> str:
    if not function_exists(text, fn):
        return text

    text = re.sub(
        rf"(?m)(?:^@Composable\s*\n)+(?=private fun {re.escape(fn)}\()",
        "@Composable\n",
        text,
    )

    text = re.sub(
        rf"(?m)^(private fun {re.escape(fn)}\()",
        r"@Composable\n\1",
        text,
    )

    return text

shell = read(SHELL)

required = CORE_COMPOSABLES[:]
required += [fn for fn in OPTIONAL_SCREEN_CANDIDATES if function_exists(shell, fn)]

for fn in required:
    shell = ensure_composable(shell, fn)

shell = re.sub(r"(?m)(^@Composable\s*\n){2,}", "@Composable\n", shell)
write(SHELL, shell)

verifier = r'''#!/usr/bin/env python3
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
'''

for path in [VERIFY_GLASS, VERIFY_GUI]:
    if path.exists():
        write(path, verifier)
        path.chmod(0o755)

# Self-check only for functions that actually exist.
shell = read(SHELL)
failed = []
for fn in required:
    if re.search(r"@Composable\s*\nprivate fun " + re.escape(fn) + r"\(", shell) is None:
        failed.append(fn)

if failed:
    print("Failed to mark existing functions as @Composable:")
    for fn in failed:
        print(" -", fn)
    raise SystemExit(1)

print("Fixed Glass 2.0 verifier to respect actual screen names.")
