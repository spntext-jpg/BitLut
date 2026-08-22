#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def read(rel):
    path = ROOT / rel
    if not path.exists():
        errors.append(f"Missing {rel}")
        return ""
    return path.read_text(encoding="utf-8")

def require(condition, message):
    if not condition:
        errors.append(message)

ghm = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
cards = read("app/src/main/java/com/openhealth/sync/GlassCards.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
import_ui = read("app/src/main/java/com/openhealth/sync/ui/ImportScreen.kt")
colors = read("app/src/main/res/values/colors.xml")
colors_night = read("app/src/main/res/values-night/colors.xml")
launcher_bg = read("app/src/main/res/drawable/ic_launcher_background.xml")

require("private suspend fun <T : Record> readAllRecords(" in ghm, "paginated Health Connect reader missing")
require("pageToken = response.pageToken" in ghm, "Health Connect pagination token is not drained")
require(ghm.count("readAllRecords(") >= 7, "not all dashboard/workout record reads use pagination")
require("private suspend fun readDistanceForSessions(" not in ghm, "duplicate distance-only workout reader still exists")
require("activeCaloriesKcal = metrics.activeCaloriesKcal.takeIf { it > 0.0 } ?: workout.activeCaloriesKcal" in ghm, "workout metric fallback missing")
require("ascendingOrder = false" in ghm, "recent workouts are not requested newest-first")

require("targetValue = if (hero) AugustColor.NavyRaised else palette.card" in cards, "SoftCard hero is not NavyRaised")
require("val borderColor = if (hero) AugustColor.BorderDark else palette.stroke" in cards, "card borders are still decorative/accent tinted")
require("lerp(palette.stroke" not in cards, "old accent-tinted card border remains")

require("accent = AugustColor.Lime" in shell, "Summary hero does not use Lime brand accent")
require("val valueColor = if (hero) AugustColor.Surface else palette.text" in shell, "hero value text is not white")
require("val titleColor = if (hero) AugustColor.DarkSecondaryText else palette.secondaryText" in shell, "hero supporting text is not dark-surface secondary")
require("valueColor = palette.text" in shell, "workout metric values are still colored decoratively")
require("accent.copy(alpha = 0.14f)" in shell, "progress-ring glow is not restrained")
require("formatWorkoutDateTime(session.startTimeMs)" in shell, "workout date/time metadata line missing")
require("fun prefer(primary: WorkoutMetricDisplay" in shell, "workout metric fallback selection missing")
require("checkedTrackColor = AugustColor.Purple" in shell, "form switch interaction color is not Purple")
require("listOf(AugustColor.Canvas, AugustColor.Canvas)" in shell, "light app canvas still fades into Surface")
require(".background(AugustColor.Lime)" in shell and "color = AugustColor.LimeInk" in shell, "hand-built primary action is not Lime + Ink")

require("containerColor = AugustColor.NavyRaised" in import_ui, "Import hero is not fixed to August NavyRaised")
require("color = AugustColor.DarkSecondaryText" in import_ui, "Import hero supporting text is not DarkSecondaryText")
require("color = MaterialTheme.colorScheme.onSurface" in import_ui, "Import counters still use Lime as light-surface foreground")
require("RoundedCornerShape(AugustRadius.Hero)" in import_ui, "Import hero radius is not tokenized")
require("RoundedCornerShape(AugustRadius.Card)" in import_ui, "Import card radius is not tokenized")
require("shape = RoundedCornerShape(AugustRadius.Button)" in import_ui, "Import button radius is not tokenized")

require("#FF151728" in colors, "widget/light Ink token is stale")
require("#FF6F7385" in colors, "widget/light Muted token is stale")
require("#FF1C1E33" in colors_night, "widget/dark NavyRaised token is stale")
require("#FFB8BDCE" in colors_night, "widget/dark secondary text token is stale")
require("#151728" in launcher_bg, "launcher background is not August Navy")

require("dev.chrisbanes.haze" not in ghm + cards + shell + import_ui, "Haze reference reintroduced")

if errors:
    print("Workout data + August v3 product sprint verification FAILED:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Workout data + August v3 product sprint static verification passed.")
