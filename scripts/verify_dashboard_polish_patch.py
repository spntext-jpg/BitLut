#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        errors.append(f"Missing {relative}")
        return ""
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
strings_en = read("app/src/main/res/values/strings.xml")
strings_ru = read("app/src/main/res/values-ru/strings.xml")
huawei = read("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
policy = read("app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt")

personal_start = shell.find("private fun PersonalRecordsCard(")
personal_end = shell.find("private fun RecordStat(", personal_start)
personal = shell[personal_start:personal_end] if personal_start >= 0 and personal_end > personal_start else ""
require(bool(personal), "PersonalRecordsCard block missing")
require("R.string.record_steps_per_day" in personal, "Personal record still lacks Steps per day label")
require("label = stringResource(R.string.steps_today)" not in personal, "Personal record still says Steps today")
require('name="record_steps_per_day"' in strings_en and "Steps per day" in strings_en, "English record label missing")
require('name="record_steps_per_day"' in strings_ru and "Шаги за день" in strings_ru, "Russian record label missing")

metric_start = shell.find("private fun MinimalMetricCard(")
metric_end = shell.find("private fun DashboardLoadingCard(", metric_start)
metric = shell[metric_start:metric_end] if metric_start >= 0 and metric_end > metric_start else ""
require(bool(metric), "MinimalMetricCard block missing")
require("else if (icon != null)" in metric, "Icon chip is not conditional on an actual icon")
require('Text("●"' not in metric, "Empty dot-in-circle fallback still exists")

scope_text = (huawei + "\n" + policy).upper()
for token in ["HEALTHKIT_SLEEP", "SLEEPSESSIONRECORD", "READ_SLEEP", "WRITE_SLEEP"]:
    require(token not in scope_text, f"Sleep token unexpectedly present: {token}")

cadence_hits = []
for path in (ROOT / "app/src/main").rglob("*"):
    if path.is_file() and path.suffix.lower() in {".kt", ".xml"}:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if any(token in text for token in ("cadence", "каденс", "max_cadence", "maxcadence")):
            cadence_hits.append(str(path.relative_to(ROOT)))
require(not cadence_hits, "Cadence UI/data token still present: " + ", ".join(cadence_hits))

if errors:
    print("BitLut dashboard polish verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut dashboard polish verification passed.")
