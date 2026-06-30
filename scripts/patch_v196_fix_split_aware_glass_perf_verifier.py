#!/usr/bin/env python3
from pathlib import Path

VERIFY = Path("scripts/verify_lifecycle_glass_perf_hardening.py")
README = Path("README.md")
CONTEXT = Path("CONTEXT.md")

def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

write(VERIFY, r'''#!/usr/bin/env python3
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

build = read("app/build.gradle.kts")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
logger = read_optional("app/src/main/java/com/openhealth/sync/util/AppLogger.kt")

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

require("androidx.lifecycle:lifecycle-runtime-compose" in build, "Missing lifecycle-runtime-compose dependency")
require("collectAsStateWithLifecycle" in main, "MainActivity must use collectAsStateWithLifecycle")
require("collectAsState().value" not in main, "MainActivity still uses collectAsState().value")
require("import androidx.lifecycle.compose.collectAsStateWithLifecycle" in main, "Missing lifecycle compose import")

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
    "SoftCard",
    "MetricBarChartCard",
]:
    require(f"fun {fn}(" in ui_sources, f"{fn} must exist in shell or extracted components")

require("@Composable\n@Composable" not in shell, "Duplicate @Composable annotation found in shell")
require("NavigationBarItem(" not in ui_sources, "Material NavigationBarItem must not remain")
require("NavigationBar(" not in ui_sources, "Material NavigationBar must not remain")

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
    require(token in ui_sources, f"Missing Compose performance/bounded chart token: {token}")

if "object AppLogger" in logger:
    require("MAX_LOG_ENTRIES" in logger, "AppLogger should define MAX_LOG_ENTRIES")
    require("MAX_LOG_MESSAGE_LENGTH" in logger, "AppLogger should define MAX_LOG_MESSAGE_LENGTH")

if errors:
    print("Lifecycle and Glass performance verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Lifecycle and Glass performance verification passed.")
''')

VERIFY.chmod(0o755)

note = """
## v1.9.6 split-aware Glass performance verification

`verify_lifecycle_glass_perf_hardening.py` now validates Glass 2.0 performance tokens across both `FinalBitLutShell.kt` and extracted `ui/components/*.kt` files.
""".strip()

for doc in [README, CONTEXT]:
    if doc.exists():
        content = read(doc)
        if "## v1.9.6 split-aware Glass performance verification" not in content:
            content = content.rstrip() + "\n\n" + note + "\n"
        write(doc, content)

print("Updated lifecycle Glass performance verifier for split UI components.")
