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

build = read("app/build.gradle.kts")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
logger = read("app/src/main/java/com/openhealth/sync/util/AppLogger.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("androidx.lifecycle:lifecycle-runtime-compose" in build, "Missing lifecycle-runtime-compose dependency")
require("collectAsStateWithLifecycle" in main, "MainActivity must use collectAsStateWithLifecycle")
require("collectAsState().value" not in main, "MainActivity still uses collectAsState().value")
require("import androidx.lifecycle.compose.collectAsStateWithLifecycle" in main, "Missing lifecycle compose import")

for fn in [
    "SummaryScreen",
    "HistoryScreen",
    "SettingsScreen",
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
]:
    if f"private fun {fn}(" in shell:
        require(
            re.search(r"@Composable\s*\nprivate fun " + re.escape(fn) + r"\(", shell) is not None,
            f"{fn} must be @Composable"
        )

require("@Composable\n@Composable" not in shell, "Duplicate @Composable annotation found")
require("NavigationBarItem(" not in shell, "Material NavigationBarItem must not remain")
require("NavigationBar(" not in shell, "Material NavigationBar must not remain")

for token in [
    "val shellShape = remember",
    "val selectedBrush = remember",
    "val backgroundBrush = remember",
    "val accentGlowColors = remember",
    "val maxValue = remember(bars)",
    "defaultMinSize(minHeight = 6.dp)",
    ".height(84.dp)",
    ".height(132.dp)",
    "TextOverflow.Ellipsis",
]:
    require(token in shell, f"Missing Compose performance/bounded chart token: {token}")

if "object AppLogger" in logger:
    require("MAX_LOG_ENTRIES" in logger, "AppLogger should define MAX_LOG_ENTRIES")
    require("MAX_LOG_MESSAGE_LENGTH" in logger, "AppLogger should define MAX_LOG_MESSAGE_LENGTH")

if errors:
    print("Lifecycle and Glass performance verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Lifecycle and Glass performance verification passed.")
