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

require("internal enum class MainTab" in shell or "enum class MainTab" in shell, "MainTab must be visible")
require("internal fun Modifier.pressScale" in shell or "fun Modifier.pressScale" in shell, "pressScale must be visible")
require("internal fun formatBarValueShort(" in shell or "fun formatBarValueShort(" in shell, "formatBarValueShort must be visible")
require("internal fun barDateLabel(" in shell or "fun barDateLabel(" in shell, "barDateLabel must be visible")

for text_name, text in [
    ("GlassNavigation.kt", nav),
    ("GlassCards.kt", cards),
    ("MetricCharts.kt", charts),
]:
    require("package com.openhealth.sync" in text, f"{text_name} must stay in root package")
    require("@Composable" in text, f"{text_name} must contain composables")

require("## v1.9.6 UI File Split Sprint 1" in readme, "README missing UI split note")
require("## v1.9.6 UI File Split Sprint 1" in context, "CONTEXT missing UI split note")

if errors:
    print("UI File Split Sprint 1 verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("UI File Split Sprint 1 verification passed.")
