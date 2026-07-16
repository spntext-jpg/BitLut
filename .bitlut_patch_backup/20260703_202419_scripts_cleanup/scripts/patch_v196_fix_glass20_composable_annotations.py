#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")

SHELL = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
VERIFY_OLD = ROOT / "scripts/verify_gui_neoglass_activity_only.py"
VERIFY_GLASS = ROOT / "scripts/verify_glass20_gui_self_heal.py"

COMPOSABLE_FUNCTIONS = [
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
]

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def ensure_function_is_composable(text: str, function_name: str) -> str:
    # Collapse duplicate annotations directly above this function.
    text = re.sub(
        rf"(?m)(?:^@Composable\s*\n)+(?=private fun {re.escape(function_name)}\()",
        "@Composable\n",
        text,
    )

    # Add @Composable when missing.
    text = re.sub(
        rf"(?m)^(private fun {re.escape(function_name)}\()",
        r"@Composable\n\1",
        text,
    )

    return text

def normalize_annotations(text: str) -> str:
    # Remove only true adjacent duplicate @Composable annotations.
    text = re.sub(r"(?m)(^@Composable\s*\n){2,}", "@Composable\n", text)
    return text

def patch_shell() -> None:
    shell = read(SHELL)

    # Remove old Material nav import if it survived.
    shell = shell.replace("import androidx.compose.material3.NavigationBar\n", "")
    shell = shell.replace("import androidx.compose.material3.NavigationBarItem\n", "")

    # Make sure every generated helper is composable.
    for fn in COMPOSABLE_FUNCTIONS:
        shell = ensure_function_is_composable(shell, fn)

    shell = normalize_annotations(shell)

    # Defensive: if a previous patch accidentally inserted comments around NavigationBarItem,
    # remove them instead of leaving a verifier false-positive.
    shell = shell.replace("/* removed NavigationBarItem(", "")
    shell = shell.replace("/* removed NavigationBar(", "")

    write(SHELL, shell)

def patch_old_verifier() -> None:
    if not VERIFY_OLD.exists():
        return

    write(VERIFY_OLD, r'''#!/usr/bin/env python3
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

require("Glass20BottomNavigation(" in shell, "Bottom navigation must use Glass20BottomNavigation")
require("Glass20NavButton(" in shell, "Bottom navigation must use Glass20NavButton")
require("NavigationBarItem(" not in shell, "Material NavigationBarItem must be removed")
require("NavigationBar(" not in shell, "Material NavigationBar must be removed")
require("contentDescription = null" in shell, "Bottom bar must be icon-only")
require("val targetCardColor = if (palette.dark)" in shell, "SoftCard must use Glass 2.0 color system")
require("Brush.radialGradient" in shell, "Glass radial glow is missing")
require("Brush.linearGradient" in shell, "Glass linear surface is missing")
require("drawLine(" in shell, "Thin glass highlight border is missing")
require("defaultMinSize(minHeight = 6.dp)" in shell, "Charts must be bounded")
require(".height(84.dp)" in shell, "Chart bar drawing area must be bounded")
require(".height(132.dp)" in shell, "Chart row height must be bounded")

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

duplicate_annotations = re.findall(r"@Composable\s*\n@Composable", shell)
require(not duplicate_annotations, "Duplicate @Composable annotation found")

for fn in [
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
]:
    require(shell.count(f"private fun {fn}(") == 1, f"{fn} must exist exactly once")
    require(
        re.search(r"@Composable\s*\nprivate fun " + re.escape(fn) + r"\(", shell) is not None,
        f"{fn} must be @Composable"
    )

if errors:
    print("GUI Glass 2.0 activity-only verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("GUI Glass 2.0 activity-only verification passed.")
''')
    VERIFY_OLD.chmod(0o755)

def patch_glass_verifier() -> None:
    if not VERIFY_GLASS.exists():
        return

    text = read(VERIFY_GLASS)
    text = text.replace(
        'require("val showMeshGradient = true" in shell, "SoftCard must apply neo-glass glow mesh globally")',
        'require("val targetCardColor = if (palette.dark)" in shell, "SoftCard must use Glass 2.0 color system")'
    )
    write(VERIFY_GLASS, text)
    VERIFY_GLASS.chmod(0o755)

def self_check() -> None:
    shell = read(SHELL)
    errors = []

    if "@Composable\n@Composable" in shell:
        errors.append("Duplicate @Composable annotation remains")

    for fn in COMPOSABLE_FUNCTIONS:
        if shell.count(f"private fun {fn}(") != 1:
            errors.append(f"{fn} must exist exactly once")
        if re.search(r"@Composable\s*\nprivate fun " + re.escape(fn) + r"\(", shell) is None:
            errors.append(f"{fn} is missing @Composable")

    for forbidden in [
        "NavigationBarItem(",
        "NavigationBar(",
    ]:
        if forbidden in shell:
            errors.append(f"Forbidden Material nav term remains: {forbidden}")

    if errors:
        print("Glass 2.0 composable annotation fix failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

def main() -> None:
    patch_shell()
    patch_old_verifier()
    patch_glass_verifier()
    self_check()
    print("Fixed Glass 2.0 composable annotations and verifiers.")

if __name__ == "__main__":
    main()
