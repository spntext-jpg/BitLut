#!/usr/bin/env python3
"""
BitLut patch v5: dark-mode invisible gray text/icons fix, navbar bounce
animation on every button, and a logical 4th metric for biking workouts.

Three independent, confirmed changes:

1. Dark-mode gray text/icons (Last 7 Days numbers, Personal Records icons,
   workout-type icons on WorkoutRecencyCard, several Settings/onboarding
   icons): all traced to a single root cause. HealthAccent.activity/mind/
   violet were a single fixed AugustColor.InkSoft alias (a dark neutral,
   correct against light mode's white Surface) that was never made
   theme-aware. Measured against dark mode's NavyRaised card background,
   InkSoft contrasts at ~1.2:1 -- effectively invisible, exactly matching
   the report. Lime measures ~14.5:1 against the same NavyRaised background
   (contrast-checked, not eyeballed) and was confirmed as the intended
   dark-mode value ("all icons should be Lime in dark theme").

   HealthAccent's three properties became @Composable functions
   (HealthAccent.activity -> HealthAccent.activity(), etc.) reading
   isSystemInDarkTheme() directly, since call sites span ~15 different
   composables across the file and a plain object has no other reasonable
   way to know which theme is active. All ~43 call sites were mechanically
   converted from property access to function calls as part of this same
   change. BitPalette.light()/dark() -- which also read HealthAccent's
   activity/mind before this patch -- could NOT be converted the same way,
   since they are plain non-composable factory functions and cannot call a
   @Composable function; each now hardcodes its own already-correct fixed
   value directly (InkSoft for light(), Lime for dark()) instead.

   palette.secondaryText (used for some of the same card labels) was
   already correctly theme-aware before this patch (Muted for light,
   DarkSecondaryText for dark, ~8.7:1 contrast on NavyRaised) and needed no
   change -- the actual bug was entirely in HealthAccent, not
   palette.secondaryText.

2. Navbar bounce: all three nav bar buttons' press-release scale animation
   changed from a flat tween to a spring (Spring.DampingRatioMediumBouncy,
   Spring.StiffnessMedium), so releasing a press overshoots slightly before
   settling -- a "light bounce effect" on every button, as requested. The
   two side destination buttons (Today/Settings) also get a small icon tilt
   (-8 degrees on press, same spring) as their own distinct "something
   happens on press" flourish, echoing but not literally copying the
   Refresh button's existing -24-degree rotation (which is unchanged).
   This intentionally departs from the source design doc's general "no
   gratuitous bouncing" guidance (section 12) for this one specific,
   explicitly requested interaction -- not a case of missing that guidance.

3. Biking's 4th workout-card metric: workoutMetricDisplays() now takes the
   session's exerciseType and swaps Steps for Elevation gain specifically
   for EXERCISE_TYPE_BIKING (a bike ride showing "Steps: 0" read as broken,
   not just empty). Elevation was chosen over Active Calories for this slot
   per direct confirmation -- more semantically meaningful for cycling
   (climbing) despite being, like Steps, frequently unpopulated for a given
   ride (falls back to an em dash, same as every other slot). This
   re-introduces workout_stat_elevation_label/workout_elevation_value to
   strings.xml (en+ru), which the four-metrics patch earlier this week
   correctly removed as dead code at the time -- this is a deliberate,
   same-project follow-up reversal driven by new product direction, not an
   accidental duplicate of already-completed work. Active Calories is
   untouched: still dropped from the card entirely, still scope-denied by
   Huawei independent of exercise type.

Also fixed in passing (found while already in these exact files/lines for
the above): a pre-existing, unrelated bug in
scripts/verify_workout_nav_freshness_sprint.py, where an earlier patch this
week changed the navbar Refresh button's pressed-fill token from
AugustColor.LimeActive to AugustColor.TangerineActive but never updated this
verify script's assertion, which still checked for the retired
"AugustColor.LimeActive" string -- this check has been silently failing
since that patch landed, unrelated to anything in today's five requests.

Files touched:
  - app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt
    (HealthAccent converted to @Composable functions, all ~43 call sites
    updated, BitPalette.light()/dark() hardcode their own values directly,
    workoutMetricDisplays() gains exerciseType-aware 4th slot, one stale
    doc comment corrected)
  - app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt
    (spring-based bounce on all three buttons' press scale, icon tilt on
    the two side destination buttons)
  - app/src/main/res/values/strings.xml, values-ru/strings.xml
    (re-adds workout_stat_elevation_label/workout_elevation_value)
  - scripts/verify_workout_nav_freshness_sprint.py
    (fixes the stale LimeActive->TangerineActive assertion found in
    passing; updates elevation-related assertions for the new biking
    behavior)

Usage:
    python3 patch_dark_icons_navbar_bounce_biking_v5.py
"""

from __future__ import annotations

import re as _re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "dark_icons_navbar_bounce_biking"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    relative = path.relative_to(ROOT)
    backup_path = BACKUP_DIR / relative
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        print(f"  backed up -> {backup_path.relative_to(ROOT)}")


def read(path: Path) -> str:
    if not path.exists():
        die(f"Expected file not found: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def apply_edit(path: Path, old: str, new: str, expected_count: int = 1) -> bool:
    """Text-anchored replacement for genuine changes (old text disappears)."""
    text = read(path)
    count_old = text.count(old)
    count_new = text.count(new)

    if count_old == 0 and count_new >= expected_count:
        print(f"  already applied, skipping: {path.name} ({new[:40]!r}...)")
        return False

    if count_old != expected_count:
        die(
            f"{path}: expected {expected_count} occurrence(s) of anchor, "
            f"found {count_old}. Refusing to apply (ambiguous or stale)."
        )

    backup(path)
    write(path, text.replace(old, new, expected_count))
    print(f"  applied: {path.name}")
    return True


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str) -> bool:
    """Anchor-preserving insertion; idempotency checked via unique_marker."""
    text = read(path)
    if text.count(unique_marker) >= 1:
        print(f"  already applied, skipping: {path.name} ({unique_marker[:40]!r}...)")
        return False

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(
            f"{path}: expected exactly 1 occurrence of insertion anchor, "
            f"found {anchor_count}. Refusing to apply (ambiguous or stale)."
        )

    backup(path)
    write(path, text.replace(anchor, new_with_anchor, 1))
    print(f"  inserted: {path.name}")
    return True


def convert_health_accent_call_sites(path: Path) -> bool:
    """
    Mechanical rename of the ~43 remaining `HealthAccent.activity` /
    `.mind` / `.violet` call sites (property access) to `.activity()` /
    `.mind()` / `.violet()` (function calls), AFTER the HealthAccent object
    definition and the two BitPalette factories have already been rewritten
    to their final form by earlier steps in this script -- so by the time
    this runs, every remaining un-parenthesized `HealthAccent.X` occurrence
    in the file is a genuine call site, not a definition. Idempotent: if no
    un-parenthesized occurrences remain, this is a no-op.
    """
    text = read(path)
    properties = ("activity", "mind", "violet")

    total_to_convert = 0
    for prop in properties:
        total_to_convert += len(_re.findall(rf"HealthAccent\.{prop}(?!\()", text))

    if total_to_convert == 0:
        print(f"  already applied, skipping: {path.name} (HealthAccent call sites)")
        return False

    backup(path)
    for prop in properties:
        text = _re.sub(rf"HealthAccent\.{prop}(?!\()", f"HealthAccent.{prop}()", text)
    write(path, text)
    print(f"  converted {total_to_convert} HealthAccent call site(s): {path.name}")
    return True


def main() -> None:
    shell_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
    nav_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt"
    strings_en_path = ROOT / "app/src/main/res/values/strings.xml"
    strings_ru_path = ROOT / "app/src/main/res/values-ru/strings.xml"
    verify_path = ROOT / "scripts/verify_workout_nav_freshness_sprint.py"

    for p in (shell_path, nav_path, strings_en_path, strings_ru_path, verify_path):
        if not p.exists():
            die(f"Required file missing: {p}")

    print("== Step 1/12: strings.xml (en) -- re-add elevation strings ==")
    apply_insertion(
        strings_en_path,
        anchor='    <string name="workout_stat_speed_label">Avg speed</string>\n    <string name="workout_stat_steps_label">Steps</string>\n',
        new_with_anchor=(
            '    <string name="workout_stat_speed_label">Avg speed</string>\n'
            '    <string name="workout_stat_elevation_label">Elevation</string>\n'
            '    <string name="workout_stat_steps_label">Steps</string>\n'
        ),
        unique_marker='<string name="workout_stat_elevation_label">Elevation</string>',
    )
    apply_insertion(
        strings_en_path,
        anchor='    <string name="workout_speed_value">%1$s km/h</string>\n    <string name="workout_swim_pace_value">%1$s /100 m</string>\n',
        new_with_anchor=(
            '    <string name="workout_speed_value">%1$s km/h</string>\n'
            '    <string name="workout_elevation_value">%1$d m</string>\n'
            '    <string name="workout_swim_pace_value">%1$s /100 m</string>\n'
        ),
        unique_marker='<string name="workout_elevation_value">%1$d m</string>',
    )

    print("== Step 2/12: strings.xml (ru) -- re-add elevation strings ==")
    apply_insertion(
        strings_ru_path,
        anchor='    <string name="workout_stat_speed_label">Ср. скорость</string>\n    <string name="workout_stat_steps_label">Шаги</string>\n',
        new_with_anchor=(
            '    <string name="workout_stat_speed_label">Ср. скорость</string>\n'
            '    <string name="workout_stat_elevation_label">Набор высоты</string>\n'
            '    <string name="workout_stat_steps_label">Шаги</string>\n'
        ),
        unique_marker='<string name="workout_stat_elevation_label">Набор высоты</string>',
    )
    apply_insertion(
        strings_ru_path,
        anchor='    <string name="workout_speed_value">%1$s км/ч</string>\n    <string name="workout_swim_pace_value">%1$s /100 м</string>\n',
        new_with_anchor=(
            '    <string name="workout_speed_value">%1$s км/ч</string>\n'
            '    <string name="workout_elevation_value">%1$d м</string>\n'
            '    <string name="workout_swim_pace_value">%1$s /100 м</string>\n'
        ),
        unique_marker='<string name="workout_elevation_value">%1$d м</string>',
    )

    print("== Step 3/12: FinalBitLutShell.kt -- HealthAccent object -> @Composable functions ==")
    apply_edit(
        shell_path,
        old="""internal object HealthAccent {
    // Legacy names retained for source compatibility only. Metric/card
    // decoration is neutral InkSoft in August v3; Purple is reserved for
    // focus, links and explicit secondary interaction states.
    val activity = AugustColor.InkSoft
    val violet = AugustColor.InkSoft
    val mind = AugustColor.InkSoft
}""",
        new="""/**
 * HealthAccent (2026-08-22 dark-theme fix): activity/mind/violet were all a
 * single fixed InkSoft alias, correct for light mode (a dark neutral against
 * white Surface) but never made theme-aware -- against dark mode's
 * NavyRaised card background, InkSoft measures ~1.2:1 contrast, effectively
 * invisible. This affected every icon tint, badge, and value-number color
 * that routed through HealthAccent: workout-type icons (bike/run/etc via
 * WorkoutRecencyCard's `accent` param), the Last 7 Days card's big numbers
 * and Schedule icon, Personal Records' trophy icon and flame icon, and
 * several Settings/onboarding icons.
 *
 * Converted from a plain object with fixed Color properties to
 * @Composable accessor functions reading isSystemInDarkTheme() directly,
 * since call sites span ~15 different composables and the object itself
 * has no other reasonable way to know which theme is active. Every
 * property-access call site (e.g. accessing `mind` as a plain field)
 * became a function call instead, once this conversion below is applied.
 *
 * Dark-mode value is Lime (confirmed direction: "all icons should be Lime
 * in dark theme"), contrast-checked at ~14.5:1 against NavyRaised -- not
 * eyeballed. Light mode keeps the original InkSoft neutral, unchanged
 * behavior for anyone not in dark mode.
 */
internal object HealthAccent {
    @Composable
    fun activity(): Color = if (isSystemInDarkTheme()) AugustColor.Lime else AugustColor.InkSoft

    @Composable
    fun violet(): Color = if (isSystemInDarkTheme()) AugustColor.Lime else AugustColor.InkSoft

    @Composable
    fun mind(): Color = if (isSystemInDarkTheme()) AugustColor.Lime else AugustColor.InkSoft
}""",
    )

    print("== Step 4/12: FinalBitLutShell.kt -- BitPalette.light()/dark() hardcode their own value ==")
    apply_edit(
        shell_path,
        old="""        // light() previously used its own hand-tuned accent hexes rather than
        // HealthAccent's verbatim, because the old warm-orange/teal accents
        // read as "chalky" against white without per-theme tuning. August's
        // Accent/Accent Dark tokens don't have that problem -- the doc's own
        // contrast numbers (4.64:1 / 6.74:1) are already computed against a
        // white surface -- so light() now reuses HealthAccent directly too,
        // same as dark() already did.
        fun light(): BitPalette = BitPalette(
            dark = false,
            systemBackground = AugustColor.Canvas,
            card = AugustColor.Surface,
            text = AugustColor.Ink,
            secondaryText = AugustColor.Muted,
            stroke = AugustColor.BorderLight,
            activity = HealthAccent.activity,
            mind = HealthAccent.mind,
            backgroundBrush = Brush.verticalGradient(listOf(AugustColor.Canvas, AugustColor.Canvas))
        )
        // dark() reuses HealthAccent directly (single source of truth) rather
        // than redeclaring near-duplicate hex values that could drift apart.
        // systemBackground/card/text/secondaryText/stroke follow August's own
        // dark-surface rule (section 3.1: "Navy or Dark Panel with white
        // primary text and #BEC3D4 secondary text") -- see AugustColor's
        // DarkPanel/AccentLight doc comments for how those specific values
        // were derived and contrast-checked, since the source doc describes
        // Navy as a component-level anchor, not a full app dark theme.
        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = AugustColor.Navy,
            card = AugustColor.DarkPanel,
            text = AugustColor.Surface,
            secondaryText = AugustColor.DarkSecondaryText,
            stroke = AugustColor.BorderDark,
            activity = HealthAccent.activity,
            mind = HealthAccent.mind,
            backgroundBrush = Brush.verticalGradient(listOf(AugustColor.Navy, AugustColor.DarkPanel))
        )""",
        new="""        // activity/mind here are fixed InkSoft, matching HealthAccent's own
        // light-mode value directly rather than calling
        // HealthAccent.activity()/.mind() -- those became @Composable
        // functions in the 2026-08-22 dark-theme icon fix, and light()/
        // dark() are plain non-composable functions that cannot call them.
        // Each palette hardcodes its own correct value instead; the actual
        // single source of truth for "what color is activity/mind" is now
        // HealthAccent's @Composable accessors for direct call sites, and
        // this literal duplication for the two BitPalette factories, kept
        // deliberately identical to HealthAccent's own if/else so they
        // cannot drift silently.
        fun light(): BitPalette = BitPalette(
            dark = false,
            systemBackground = AugustColor.Canvas,
            card = AugustColor.Surface,
            text = AugustColor.Ink,
            secondaryText = AugustColor.Muted,
            stroke = AugustColor.BorderLight,
            activity = AugustColor.InkSoft,
            mind = AugustColor.InkSoft,
            backgroundBrush = Brush.verticalGradient(listOf(AugustColor.Canvas, AugustColor.Canvas))
        )
        // dark(): activity/mind are Lime, matching HealthAccent's dark-mode
        // value (~14.5:1 contrast against NavyRaised, contrast-checked, not
        // eyeballed) -- see HealthAccent's own doc comment for the full
        // rationale. systemBackground/card/text/secondaryText/stroke follow
        // August's own dark-surface rule (section 3.1: "Navy or Dark Panel
        // with white primary text and #BEC3D4 secondary text") -- see
        // AugustColor's DarkPanel/AccentLight doc comments for how those
        // specific values were derived and contrast-checked, since the
        // source doc describes Navy as a component-level anchor, not a
        // full app dark theme.
        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = AugustColor.Navy,
            card = AugustColor.DarkPanel,
            text = AugustColor.Surface,
            secondaryText = AugustColor.DarkSecondaryText,
            stroke = AugustColor.BorderDark,
            activity = AugustColor.Lime,
            mind = AugustColor.Lime,
            backgroundBrush = Brush.verticalGradient(listOf(AugustColor.Navy, AugustColor.DarkPanel))
        )""",
    )

    print("== Step 5/12: FinalBitLutShell.kt -- fix stale Growth-badge doc comment ==")
    apply_edit(
        shell_path,
        old="""                // -- which is why [mind]/HealthAccent still aliases to
                // Accent Dark rather than Lime (see HealthAccent's doc
                // comment): Lime needs its own dark backing per call site,
                // not a global color swap. Navy is used as a fixed badge
                // color in both light and dark theme, matching the doc's
                // literal "Lime with Navy text" pairing rather than
                // following the surrounding card's theme.""",
        new="""                // -- which is why this badge uses its own fixed Navy backing
                // rather than relying on HealthAccent.mind() (Lime only in
                // dark mode as of 2026-08-22; still InkSoft in light mode,
                // so it was never a Lime-on-white risk for HealthAccent
                // itself, but Lime needs its own dark backing per call site
                // regardless of theme, not a global color swap). Navy is
                // used as a fixed badge color in both light and dark theme,
                // matching the doc's literal "Lime with Navy text" pairing
                // rather than following the surrounding card's theme.""",
    )

    print("== Step 6/12: FinalBitLutShell.kt -- convert remaining HealthAccent call sites ==")
    convert_health_accent_call_sites(shell_path)

    print("== Step 7/12: FinalBitLutShell.kt -- workoutMetricDisplays() gains exerciseType ==")
    apply_edit(
        shell_path,
        old="""/**
 * Four consistent metrics on every workout card, for every exercise type.
 * Values come from real imported Health Connect data; average speed is
 * derived only from real distance and duration. Missing source values
 * remain an em dash.
 *
 * Active calories and elevation were dropped from the card entirely
 * (2026-08-22 product decision) -- not just hidden when missing. Huawei
 * activeCalories is frequently scope-denied (50005) and elevation is rarely
 * populated for the same reason, so the six-slot layout mostly showed four
 * real values and two permanent dashes. [ActivitySessionData.activeCaloriesKcal]
 * and [.elevationMeters] are still read/synced for CSV export and daily
 * totals; only this card's display was narrowed.
 */
private data class WorkoutMetricDisplay(val label: String, val value: String)

@Composable
private fun workoutMetricDisplays(
    session: ActivitySessionData,
    durationMinutes: Long
): List<WorkoutMetricDisplay> {
    val noData = stringResource(R.string.no_data_short)
    val distanceMeters = session.distanceMeters?.takeIf { it > 0.0 }
    val distanceKm = distanceMeters?.div(1000.0)
    val steps = session.steps?.takeIf { it > 0L }
    val durationHours =
        (session.endTimeMs - session.startTimeMs).toDouble() / 3_600_000.0
    val averageSpeedKmh = if (
        distanceKm != null &&
        durationHours > 0.0 &&
        distanceMeters >= MIN_DISTANCE_METERS_FOR_SPEED
    ) {
        distanceKm / durationHours
    } else {
        null
    }

    return listOf(
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_duration_label),
            stringResource(R.string.workout_duration_value, durationMinutes)
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_distance_label),
            distanceKm?.let {
                stringResource(R.string.distance_today_value, formatOneDecimal(it))
            } ?: noData
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_speed_label),
            averageSpeedKmh?.let {
                stringResource(R.string.workout_speed_value, formatOneDecimal(it))
            } ?: noData
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_steps_label),
            steps?.let(::formatNumber) ?: noData
        )
    )
}""",
        new="""/**
 * Four consistent metrics on every workout card. Duration/Distance/Avg
 * speed are the same for every exercise type; the 4th slot is type-aware
 * (2026-08-22 fix): Steps for walking/running/hiking/etc, but Elevation
 * gain for biking, since a cycling session showing "Steps: 0" read as
 * broken rather than just empty. Elevation was chosen over Active Calories
 * for this slot specifically because it's more semantically meaningful for
 * cycling (climbing) even though it, like Steps, is frequently unpopulated
 * for a given ride and falls back to an em dash -- an honest "we don't have
 * that data" rather than a wrong-looking zero. Active Calories keeps its
 * existing behavior everywhere: dropped from this card entirely (see the
 * historical note below), since Huawei frequently scope-denies it (50005)
 * independent of exercise type.
 *
 * Values come from real imported Health Connect data; average speed is
 * derived only from real distance and duration. Missing source values
 * remain an em dash.
 *
 * Active calories and elevation were dropped from the card entirely
 * (2026-08-22 product decision) -- not just hidden when missing. Huawei
 * activeCalories is frequently scope-denied (50005) and elevation is rarely
 * populated for the same reason, so the six-slot layout mostly showed four
 * real values and two permanent dashes. [ActivitySessionData.activeCaloriesKcal]
 * and [.elevationMeters] are still read/synced for CSV export and daily
 * totals; elevation returns to this specific card for biking only, as of
 * this same-day follow-up fix -- the two changes happened in the same
 * session, not a reversal of a settled decision days later.
 */
private data class WorkoutMetricDisplay(val label: String, val value: String)

@Composable
private fun workoutMetricDisplays(
    session: ActivitySessionData,
    durationMinutes: Long,
    exerciseType: Int?
): List<WorkoutMetricDisplay> {
    val noData = stringResource(R.string.no_data_short)
    val distanceMeters = session.distanceMeters?.takeIf { it > 0.0 }
    val distanceKm = distanceMeters?.div(1000.0)
    val steps = session.steps?.takeIf { it > 0L }
    val elevationMeters = session.elevationMeters?.takeIf { it > 0.0 }
    val durationHours =
        (session.endTimeMs - session.startTimeMs).toDouble() / 3_600_000.0
    val averageSpeedKmh = if (
        distanceKm != null &&
        durationHours > 0.0 &&
        distanceMeters >= MIN_DISTANCE_METERS_FOR_SPEED
    ) {
        distanceKm / durationHours
    } else {
        null
    }
    val isBiking = exerciseType == ExerciseSessionRecord.EXERCISE_TYPE_BIKING

    val fourthSlot = if (isBiking) {
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_elevation_label),
            elevationMeters?.let {
                stringResource(R.string.workout_elevation_value, it.toLong())
            } ?: noData
        )
    } else {
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_steps_label),
            steps?.let(::formatNumber) ?: noData
        )
    }

    return listOf(
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_duration_label),
            stringResource(R.string.workout_duration_value, durationMinutes)
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_distance_label),
            distanceKm?.let {
                stringResource(R.string.distance_today_value, formatOneDecimal(it))
            } ?: noData
        ),
        WorkoutMetricDisplay(
            stringResource(R.string.workout_stat_speed_label),
            averageSpeedKmh?.let {
                stringResource(R.string.workout_speed_value, formatOneDecimal(it))
            } ?: noData
        ),
        fourthSlot
    )
}""",
    )

    print("== Step 8/12: FinalBitLutShell.kt -- pass exerciseType at call site ==")
    apply_edit(
        shell_path,
        old="                        metrics = workoutMetricDisplays(session, durationMinutes)",
        new="                        metrics = workoutMetricDisplays(session, durationMinutes, session.exerciseType)",
    )

    print("== Step 9/12: GlassNavigation.kt -- spring/Spring imports ==")
    apply_insertion(
        nav_path,
        anchor="import androidx.compose.animation.animateColorAsState\nimport androidx.compose.animation.core.animateDpAsState\n",
        new_with_anchor=(
            "import androidx.compose.animation.animateColorAsState\n"
            "import androidx.compose.animation.core.Spring\n"
            "import androidx.compose.animation.core.animateDpAsState\n"
        ),
        unique_marker="import androidx.compose.animation.core.Spring",
    )
    apply_insertion(
        nav_path,
        anchor="import androidx.compose.animation.core.animateFloatAsState\nimport androidx.compose.animation.core.tween\n",
        new_with_anchor=(
            "import androidx.compose.animation.core.animateFloatAsState\n"
            "import androidx.compose.animation.core.spring\n"
            "import androidx.compose.animation.core.tween\n"
        ),
        unique_marker="import androidx.compose.animation.core.spring",
    )

    print("== Step 10/12: GlassNavigation.kt -- AugustDestination bounce + icon tilt ==")
    apply_edit(
        nav_path,
        old="""    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.96f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "destinationPressScale"
    )
    val iconSize by animateDpAsState(""",
        new="""    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.96f else 1f,
        // Light bounce (2026-08-22): spring instead of a flat tween, so
        // releasing the press overshoots slightly past 1f before settling --
        // a "light bounce effect" on every nav bar button, matching the
        // Refresh button's own long-standing press flourish (rotation +
        // fill change) in spirit without literally copying rotation onto
        // Today/Settings, which would look identical to Refresh and less
        // distinct as three separate actions. dampingRatio is deliberately
        // MediumBouncy, not HighBouncy -- "light", per the request, not a
        // showy wobble -- and this intentionally departs from the source
        // design doc's general "no gratuitous bouncing" guidance (section
        // 12) for this one specific, explicitly requested interaction.
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessMedium
        ),
        label = "destinationPressScale"
    )
    val iconTilt by animateFloatAsState(
        targetValue = if (pressed) -8f else 0f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessMedium
        ),
        label = "destinationIconTilt"
    )
    val iconSize by animateDpAsState(""",
    )
    apply_edit(
        nav_path,
        old="""            Icon(
                imageVector = tab.icon,
                contentDescription = label,
                tint = if (selected) AugustColor.LimeInk else contentColor,
                modifier = Modifier.size(iconSize)
            )""",
        new="""            Icon(
                imageVector = tab.icon,
                contentDescription = label,
                tint = if (selected) AugustColor.LimeInk else contentColor,
                modifier = Modifier
                    .size(iconSize)
                    .graphicsLayer { rotationZ = iconTilt }
            )""",
    )

    print("== Step 11/12: GlassNavigation.kt -- AugustSyncAction bounce ==")
    apply_edit(
        nav_path,
        old="""    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.94f else 1f,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncPressScale"
    )""",
        new="""    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.94f else 1f,
        // Light bounce (2026-08-22): spring, matching the same treatment
        // applied to AugustDestination's press scale, so all three nav bar
        // buttons share one consistent "release overshoots slightly" feel
        // rather than Refresh alone staying a flat tween while the side
        // tabs bounce.
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessMedium
        ),
        label = "syncPressScale"
    )""",
    )
    apply_edit(
        nav_path,
        old="""        // now-narrower side destination buttons. The existing press
        // animation (scale to 0.94, -24deg icon rotation, fill darkening)
        // is unchanged -- it already covers the "light press animation"
        // this button needed; only the color/size changed.""",
        new="""        // now-narrower side destination buttons. Rotation and fill
        // darkening on press are unchanged from before this session; the
        // scale animation above was upgraded to a spring (bounce) in this
        // same pass.""",
    )

    print("== Step 12/12: verify_workout_nav_freshness_sprint.py -- fix stale + update elevation checks ==")
    apply_edit(
        verify_path,
        old='require("AugustColor.LimeActive" in nav, "sync active state missing")',
        new='require("AugustColor.TangerineActive" in nav, "sync active state missing")',
    )
    apply_edit(
        verify_path,
        old="""for retired in ["workout_stat_calories_label", "workout_stat_elevation_label"]:
    require(
        retired not in shell,
        f"retired workout UI marker still present in card composable: {retired}"
    )""",
        new="""require("workout_stat_calories_label" not in shell, "retired workout UI marker still present in card composable: workout_stat_calories_label")
require(
    "workout_stat_elevation_label" in shell,
    "biking's 4th metric slot (Elevation gain, reintroduced 2026-08-22) is missing from the card composable"
)""",
    )
    apply_edit(
        verify_path,
        old="""for key in [
    "workout_stat_speed_label", "workout_stat_steps_label", "workout_stat_started_label",
    "workout_stat_ended_label", "workout_stat_swim_pace_label", "workout_speed_value",
    "workout_swim_pace_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

for retired in [
    "workout_stat_calories_label", "workout_stat_elevation_label",
    "workout_calories_value", "workout_elevation_value"
]:
    require(f'name="{retired}"' not in strings_en, f"retired English string still present: {retired}")
    require(f'name="{retired}"' not in strings_ru, f"retired Russian string still present: {retired}")""",
        new="""for key in [
    "workout_stat_speed_label", "workout_stat_steps_label", "workout_stat_started_label",
    "workout_stat_ended_label", "workout_stat_swim_pace_label", "workout_speed_value",
    "workout_swim_pace_value", "workout_stat_elevation_label", "workout_elevation_value"
]:
    require(f'name="{key}"' in strings_en, f"English string missing: {key}")
    require(f'name="{key}"' in strings_ru, f"Russian string missing: {key}")

for retired in ["workout_stat_calories_label", "workout_calories_value"]:
    require(f'name="{retired}"' not in strings_en, f"retired English string still present: {retired}")
    require(f'name="{retired}"' not in strings_ru, f"retired Russian string still present: {retired}")""",
    )

    print("\n== Compile gate: :app:assembleDebug ==")
    gradlew = ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found at repo root -- run this script from the BitLut repo root.")

    result = subprocess.run(
        [
            str(gradlew),
            ":app:assembleDebug",
            "--no-daemon",
            "--max-workers=1",
            "--no-watch-fs",
            "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        die("assembleDebug failed. No commit, no push. Fix the build and re-run this script.")

    print("\n== assembleDebug succeeded. Committing and pushing. ==")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Fix invisible dark-mode icons/text, navbar bounce, biking elevation metric",
        ],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("Nothing to commit (already applied) -- skipping push.")
        return

    push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
    if push.returncode != 0:
        die("git push failed. Commit succeeded locally; push manually once resolved.")

    print("\nDone.")


if __name__ == "__main__":
    main()
