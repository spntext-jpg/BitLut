#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        raise SystemExit(f"Missing {relative}")
    return path.read_text(encoding="utf-8")

glass = read("app/src/main/java/com/openhealth/sync/GlassCards.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
strings_en = read("app/src/main/res/values/strings.xml")
strings_ru = read("app/src/main/res/values-ru/strings.xml")

errors = []
def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require("pressLift: Boolean = false" in glass, "SoftCard pressLift option missing")
require("awaitFirstDown(requireUnconsumed = false)" in glass, "card motion must not steal child taps")
require("translationY = -lift.toPx()" in glass, "card lift translation missing")
require("shadowElevation" in glass and "scaleX = scale" in glass, "premium shadow/scale motion missing")

summary_start = shell.find("private fun SummaryScreen(")
summary_end = shell.find("private fun WorkoutRecencyCard(", summary_start)
summary = shell[summary_start:summary_end]
require(summary_start >= 0 and summary_end > summary_start, "Summary block missing")
require("LazyColumn(" in summary, "Dashboard is not accessibility-safe and scrollable")
require("workout_minutes_title" not in summary, "Workout time card is still reachable")
require("StreakCard(" not in summary, "Days-in-a-row card is still reachable")
require("pressLift = true" in summary, "Steps card lift effect missing")

order_tokens = [
    "R.string.steps_today",
    "R.string.dashboard_latest_workout",
    "R.string.dashboard_previous_workout",
    "PersonalRecordsCard(",
]
positions = [summary.find(token) for token in order_tokens]
require(all(position >= 0 for position in positions), "One or more required Dashboard cards are missing")
require(positions == sorted(positions), "Dashboard card order is incorrect")
require("state.recentWorkouts.getOrNull(0)" in summary, "latest workout slot missing")
require("state.recentWorkouts.getOrNull(1)" in summary, "previous workout slot missing")
require("private fun WorkoutRecencyCard(" in shell, "premium workout card missing")
require(shell.count("pressLift = true") >= 3, "not all Dashboard data cards lift on press")
require("R.string.dashboard_records_empty" in shell, "stable personal-record empty state missing")

require("workoutMinutesToday = 0L" in google, "invisible workout total still triggers a read")
require("activeHoursToday = 0" in google, "invisible active-hours total still triggers a read")
require("recentWorkouts = readRecentWorkouts(2)" in google, "Dashboard does not load exactly two workouts")

for key in [
    "dashboard_latest_workout",
    "dashboard_previous_workout",
    "dashboard_workout_empty_latest",
    "dashboard_workout_empty_previous",
    "dashboard_records_empty",
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

if errors:
    print("BitLut premium Dashboard verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut premium Dashboard verification passed.")
