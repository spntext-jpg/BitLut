#!/usr/bin/env python3
from pathlib import Path

CHARTS = Path("app/src/main/java/com/openhealth/sync/ui/components/MetricCharts.kt")
VERIFY_UI_SPLIT = Path("scripts/verify_ui_file_split_sprint1.py")
README = Path("README.md")
CONTEXT = Path("CONTEXT.md")

def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def patch_charts() -> None:
    text = read(CHARTS)
    if not text:
        raise SystemExit("MetricCharts.kt not found")

    text = text.replace("package com.openhealth.sync.ui.components", "package com.openhealth.sync")
    text = text.replace("bars: List<MetricBar>", "bars: List<Any?>")
    text = text.replace("formatBarValueShort(bar.value)", "valueFormatter(rawValue)")
    text = text.replace("barDateLabel(bar)", "metricBarDateLabel(bar)")

    write(CHARTS, text)

def write_verifier() -> None:
    write(VERIFY_UI_SPLIT, r'''#!/usr/bin/env python3
from pathlib import Path
import sys

errors = []

def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
nav = read("app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt")
cards = read("app/src/main/java/com/openhealth/sync/ui/components/GlassCards.kt")
charts = read("app/src/main/java/com/openhealth/sync/ui/components/MetricCharts.kt")
readme = read("README.md")
context = read("CONTEXT.md")

def require(condition, message):
    if not condition:
        errors.append(message)

require("Glass20BottomNavigation(" in shell, "Shell must still call Glass20BottomNavigation")
require("SoftCard(" in shell, "Shell must still call SoftCard")
require("MetricBarChartCard(" in shell, "Shell must still call MetricBarChartCard")

require("internal fun Glass20BottomNavigation(" in nav, "GlassNavigation.kt must define Glass20BottomNavigation")
require("private fun Glass20NavButton(" in nav, "GlassNavigation.kt must define private Glass20NavButton")
require("internal fun SoftCard(" in cards, "GlassCards.kt must define SoftCard")
require("internal fun MetricBarChartCard(" in charts, "MetricCharts.kt must define MetricBarChartCard")

require("bars: List<Any?>" in charts, "MetricCharts must not depend on missing MetricBar type")
require("List<MetricBar>" not in charts, "MetricCharts must not reference missing List<MetricBar>")
require("private fun metricBarValue(bar: Any?)" in charts, "MetricCharts must provide metricBarValue accessor")
require("private fun metricBarDateLabel(bar: Any?)" in charts, "MetricCharts must provide metricBarDateLabel accessor")
require("valueFormatter(rawValue)" in charts, "MetricCharts must use caller valueFormatter")
require("defaultMinSize(minHeight = 6.dp)" in charts, "Metric bars must keep bounded minimum visible height")
require(".height(84.dp)" in charts, "Metric bar drawing area must stay bounded")
require(".height(132.dp)" in charts, "Metric chart row must reserve stable vertical space")

for text_name, text in [
    ("GlassNavigation.kt", nav),
    ("GlassCards.kt", cards),
    ("MetricCharts.kt", charts),
]:
    require("package com.openhealth.sync" in text, f"{text_name} must stay in root package")

require("## v1.9.6 UI File Split Sprint 1" in readme, "README missing UI split note")
require("## v1.9.6 UI File Split Sprint 1" in context, "CONTEXT missing UI split note")

if errors:
    print("UI File Split Sprint 1 verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("UI File Split Sprint 1 verification passed.")
''')
    VERIFY_UI_SPLIT.chmod(0o755)

def patch_docs() -> None:
    note = """
## v1.9.6 MetricCharts self-check fix

Fixed the UI split verifier/self-check so it allows `MetricBarChartCard` as a function name while preventing dependency on the missing `List<MetricBar>` type.
""".strip()

    for doc in [README, CONTEXT]:
        content = read(doc)
        if content and "## v1.9.6 MetricCharts self-check fix" not in content:
            write(doc, content.rstrip() + "\n\n" + note + "\n")

def self_check() -> None:
    charts = read(CHARTS)
    errors = []

    for token in [
        "internal fun MetricBarChartCard(",
        "bars: List<Any?>",
        "private fun metricBarValue(bar: Any?)",
        "private fun metricBarDateLabel(bar: Any?)",
        "valueFormatter(rawValue)",
        "defaultMinSize(minHeight = 6.dp)",
        ".height(84.dp)",
        ".height(132.dp)",
    ]:
        if token not in charts:
            errors.append(f"Missing MetricCharts token: {token}")

    forbidden = [
        "List<MetricBar>",
        "formatBarValueShort(bar.value)",
        "barDateLabel(bar)",
    ]
    for token in forbidden:
        if token in charts:
            errors.append(f"Forbidden stale MetricCharts token: {token}")

    if errors:
        print("MetricCharts self-check patch failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

def main() -> None:
    patch_charts()
    write_verifier()
    patch_docs()
    self_check()
    print("MetricCharts self-check fixed.")

if __name__ == "__main__":
    main()
