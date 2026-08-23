#!/usr/bin/env python3
"""
BitLut patch v4: Hero card two-value layout, Tangerine accent for Settings
toggles and the navbar Refresh action, narrower navbar via side-button margin.

Three independent, confirmed changes:

1. Steps Hero card (dashboard top card): Distance now renders as its own
   big-number + small-unit block, matching Steps, instead of being folded
   into Steps' small trailing unit string ("steps · 0.1 km"). A new
   StepsHeroCard/HeroMetricBlock composable pair handles this -- it is NOT a
   generalization of MinimalMetricCard, which stays exactly as-is and in use
   everywhere else (Connect Google lock screen, the Distance card inside
   DashboardOrderedCard, etc.), since no other card needs two equal-weight
   big numbers side by side. The steps-goal progress ring moves below both
   numbers instead of sitting beside them (confirmed layout decision) --
   two big-number blocks plus a ring competing for one row was too tight
   once Distance became first-class instead of trailing text.

2. Tangerine (new AugustColor token): replaces Purple as the "on/active"
   signal in exactly two places -- the two Settings toggle tracks
   (DataSourceToggleRow, WidgetVisibilityRow) and the navbar's center
   Refresh button fill (was Lime). Purple keeps every other existing role
   (focus rings, links, selection detail) untouched, including the navbar's
   own focus-visible ring. #F28500 is the commonly documented "Tangerine"
   named color (ColorHexa/Wikipedia's canonical value), not any single
   company's brand orange. TangerineActive (#DD7A00, the Refresh button's
   pressed-state fill) is derived by applying the same relative HSV
   saturation/value shift that produces LimeActive from Lime, not eyeballed.
   Ink-on-Tangerine clears ~6.9:1 WCAG AA; white-on-Tangerine fails at
   ~2.6:1, so the Refresh icon moves from LimeInk to the equivalent Ink,
   and the Refresh button keeps Ink content on both its fill states, same
   contract Lime already had.

3. Navbar width + Refresh button size: outer horizontal margin increased
   16.dp -> 24.dp so the two side destination buttons (each weight(1f))
   shrink and the pill reads narrower. This is a deliberately conservative
   first pass, not the ~44.dp a literal "20% narrower" derivation would
   produce on a typical ~400.dp-wide screen -- that number cannot be
   visually verified in this environment, so a smaller, safer bump was
   used instead, isolated into one named constant
   (NAV_BAR_OUTER_HORIZONTAL_MARGIN) for easy on-device tuning afterward.
   The Refresh button itself grows 15% (58.dp -> 67.dp, icon 27.dp -> 31.dp)
   to read as the dominant middle action against the now-narrower side
   buttons. Its existing press animation (scale to 0.94, -24deg icon
   rotation, fill darkening on press) already covered the "light press
   animation" ask and is left unchanged -- only color and size changed.
   The two side destination buttons already had their own press-scale
   animation (1.0 -> 0.96) prior to this patch; also left unchanged for
   the same reason.

Files touched:
  - app/src/main/java/com/openhealth/sync/ui/theme/AugustTokens.kt
    (new Tangerine/TangerineActive tokens)
  - app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt
    (StepsHeroCard/HeroMetricBlock added; call site swapped from
    MinimalMetricCard; two toggle track colors changed to Tangerine)
  - app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt
    (navbar outer margin, Refresh button color/size; also removes one
    pre-existing unused import, AugustRadius, found while already editing
    this file for the sync-action changes -- every shape in this file uses
    a raw RoundedCornerShape(N.dp) literal, never AugustRadius.*, verified
    by grep before removal, not assumed from a first-pass import sweep)
  - app/src/main/res/values/strings.xml, values-ru/strings.xml
    (new distance_unit_km string -- a bare unit label was needed since
    distance_today_value bundles the number and "km" into one template
    string, which is exactly why Distance couldn't be split into a big
    number + small unit before this patch)

Usage:
    python3 patch_hero_tangerine_navbar_v4.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "hero_tangerine_navbar"


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
    """
    Anchor-preserving insertion for adding content next to text that itself
    stays unchanged. The anchor survives as a substring of the result, so
    idempotency is checked via `unique_marker` -- text that only exists
    after the insertion -- not via the anchor's absence.
    """
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


def main() -> None:
    tokens_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/theme/AugustTokens.kt"
    shell_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
    nav_path = ROOT / "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt"
    strings_en_path = ROOT / "app/src/main/res/values/strings.xml"
    strings_ru_path = ROOT / "app/src/main/res/values-ru/strings.xml"

    for p in (tokens_path, shell_path, nav_path, strings_en_path, strings_ru_path):
        if not p.exists():
            die(f"Required file missing: {p}")

    print("== Step 1/11: AugustTokens.kt -- insert Tangerine/TangerineActive ==")
    apply_insertion(
        tokens_path,
        anchor="""    // Interaction/focus: Purple is secondary, never the primary CTA.
    val Purple = Color(0xFF6E5CF6)
    val PurpleDark = Color(0xFF5140DC)
    val PurpleSoft = Color(0xFFEEEAFF)

""",
        new_with_anchor="""    // Interaction/focus: Purple is secondary, never the primary CTA.
    val Purple = Color(0xFF6E5CF6)
    val PurpleDark = Color(0xFF5140DC)
    val PurpleSoft = Color(0xFFEEEAFF)

    // Tangerine (2026-08-22): trending warm-orange "on/active" signal for two
    // specific spots -- Settings toggle "on" track and the bottom nav's
    // Refresh action fill -- replacing Purple in those two roles only.
    // Purple keeps its existing focus-ring/link/selection-detail role
    // everywhere else (including the nav bar's own focus-visible ring,
    // deliberately left untouched here); Tangerine is not a second primary
    // CTA color competing with Lime, just a distinct accent for these two
    // toggle-like "this is currently on/active" cases.
    //
    // #F28500 is the commonly documented "Tangerine" named color (matches
    // ColorHexa/Wikipedia's canonical value) rather than any single
    // company's specific brand orange, since a design-system token named
    // after a generic color word shouldn't quietly be someone else's logo
    // color. TangerineActive is derived, not eyeballed: same relative
    // HSV saturation/value shift that produces LimeActive from Lime,
    // applied to Tangerine (source Lime->LimeActive ratios: s x1.256,
    // v x0.914), landing on #DD7A00. Ink-on-Tangerine clears ~6.9:1 and
    // Ink-on-TangerineActive ~5.8:1 (WCAG AA); white-on-Tangerine fails
    // (~2.6:1), so anything filled Tangerine keeps Ink content, matching
    // Lime's own existing contract -- no separate "TangerineInk" alias is
    // introduced since Ink already is that color.
    val Tangerine = Color(0xFFF28500)
    val TangerineActive = Color(0xFFDD7A00)

""",
        unique_marker="val Tangerine = Color(0xFFF28500)",
    )

    print("== Step 2/11: strings.xml (en) -- distance_unit_km ==")
    apply_insertion(
        strings_en_path,
        anchor='    <string name="distance_today_value">%1$s km</string>\n',
        new_with_anchor='    <string name="distance_today_value">%1$s km</string>\n    <string name="distance_unit_km">km</string>\n',
        unique_marker='<string name="distance_unit_km">km</string>',
    )

    print("== Step 3/11: strings.xml (ru) -- distance_unit_km ==")
    apply_insertion(
        strings_ru_path,
        anchor='    <string name="distance_today_value">%1$s км</string>\n',
        new_with_anchor='    <string name="distance_today_value">%1$s км</string>\n    <string name="distance_unit_km">км</string>\n',
        unique_marker='<string name="distance_unit_km">км</string>',
    )

    print("== Step 4/11: FinalBitLutShell.kt -- Hero call site swap ==")
    apply_edit(
        shell_path,
        old="""                item {
                    MinimalMetricCard(
                        palette = palette,
                        title = stringResource(R.string.steps_today),
                        value = formatNumber(state.stepsToday),
                        unit = "${stringResource(R.string.steps_unit)} \u00b7 ${stringResource(R.string.distance_today_value, formatOneDecimal(state.distanceMeters / 1000.0))}",
                        accent = AugustColor.Lime,
                        progress = state.stepsProgress,
                        progressText = stepsGoalProgressText(state.stepsToday, state.stepsGoal),
                        hero = true,
                        pressLift = true
                    )
                }""",
        new="""                item {
                    StepsHeroCard(
                        palette = palette,
                        title = stringResource(R.string.steps_today),
                        stepsValue = formatNumber(state.stepsToday),
                        stepsUnit = stringResource(R.string.steps_unit),
                        distanceValue = formatOneDecimal(state.distanceMeters / 1000.0),
                        distanceUnit = stringResource(R.string.distance_unit_km),
                        progress = state.stepsProgress,
                        progressText = stepsGoalProgressText(state.stepsToday, state.stepsGoal),
                        pressLift = true
                    )
                }""",
    )

    print("== Step 5/11: FinalBitLutShell.kt -- insert StepsHeroCard + HeroMetricBlock ==")
    apply_edit(
        shell_path,
        old="""        if (onClick != null) {
            Spacer(Modifier.height(10.dp))
            PrimaryButton(text = unit, onClick = onClick)
        }
    }
}

/**
 * Neutral loading placeholder shown only on a brand-new install (no cached""",
        new="""        if (onClick != null) {
            Spacer(Modifier.height(10.dp))
            PrimaryButton(text = unit, onClick = onClick)
        }
    }
}

/**
 * Two-metric Steps Hero card (2026-08-22): Steps and Distance are each
 * rendered as their own big-number + small-unit pair, side by side, instead
 * of Distance being folded into Steps' small unit string
 * ("steps \u00b7 0.1 km") the way MinimalMetricCard's generic hero mode did
 * before this. Distance now gets equal visual weight to Steps rather than
 * reading as an afterthought.
 *
 * The steps-goal progress ring moves below both numbers instead of sitting
 * beside them in the same row (confirmed layout decision, 2026-08-22) --
 * two big-number blocks plus a ring all competing for one row was too tight
 * once Distance became a first-class value instead of trailing text.
 *
 * MinimalMetricCard itself is untouched and stays in use for every other
 * single-value card (the Connect Google lock screen, the Distance card at
 * DashboardOrderedCard, etc.) -- this is a dedicated Hero-only composable,
 * not a generalization of the existing one, since no other card needs two
 * equal-weight big numbers side by side.
 */
@Composable
private fun StepsHeroCard(
    palette: BitPalette,
    title: String,
    stepsValue: String,
    stepsUnit: String,
    distanceValue: String,
    distanceUnit: String,
    progress: Float?,
    progressText: String?,
    pressLift: Boolean = false
) {
    val interactionSource = remember { MutableInteractionSource() }
    SoftCard(
        palette = palette,
        modifier = Modifier
            .fillMaxWidth()
            .pressScale(interactionSource),
        accent = AugustColor.Lime,
        hero = true,
        tintWithAccent = true,
        pressLift = pressLift
    ) {
        Text(
            text = title.uppercase(Locale.getDefault()),
            color = AugustColor.DarkSecondaryText,
            fontWeight = FontWeight.Black,
            fontSize = 12.sp
        )
        Spacer(Modifier.height(4.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            HeroMetricBlock(
                value = stepsValue,
                unit = stepsUnit,
                modifier = Modifier.weight(1f)
            )
            HeroMetricBlock(
                value = distanceValue,
                unit = distanceUnit,
                modifier = Modifier.weight(1f)
            )
        }
        if (progress != null || progressText != null) {
            Spacer(Modifier.height(14.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (progress != null) {
                    ProgressRingChip(progress = progress, accent = AugustColor.Lime, size = 40.dp)
                    Spacer(Modifier.width(12.dp))
                }
                if (progressText != null) {
                    Text(
                        text = progressText,
                        color = AugustColor.DarkSecondaryText,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 12.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}

/**
 * One big-number + small-unit pair inside [StepsHeroCard]. Font size steps
 * down for longer formatted values -- same overflow-safety rule
 * MinimalMetricCard already used (sprint 2026-07-09), reused here rather
 * than re-derived, since two narrower half-width columns are actually more
 * overflow-prone than MinimalMetricCard's single full-width value ever was.
 */
@Composable
private fun HeroMetricBlock(
    value: String,
    unit: String,
    modifier: Modifier = Modifier
) {
    val valueFontSize = when {
        value.length > 7 -> 28.sp
        value.length > 5 -> 34.sp
        else -> 40.sp
    }
    Column(modifier = modifier) {
        Row(verticalAlignment = Alignment.Bottom) {
            Text(
                text = value,
                color = AugustColor.Surface,
                fontWeight = FontWeight.Black,
                fontSize = valueFontSize,
                lineHeight = valueFontSize,
                letterSpacing = (-1).sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f, fill = false)
            )
            Spacer(Modifier.width(4.dp))
            Text(
                text = unit,
                color = AugustColor.Lime,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 13.sp,
                maxLines = 1,
                modifier = Modifier.padding(bottom = 4.dp)
            )
        }
    }
}

/**
 * Neutral loading placeholder shown only on a brand-new install (no cached""",
    )

    print("== Step 6/11: FinalBitLutShell.kt -- Settings toggle colors (both) ==")
    apply_edit(
        shell_path,
        old="""                checkedThumbColor = AugustColor.Surface,
                checkedTrackColor = AugustColor.Purple,
                uncheckedThumbColor = Color.White,
                uncheckedTrackColor = palette.stroke""",
        new="""                checkedThumbColor = AugustColor.Surface,
                checkedTrackColor = AugustColor.Tangerine,
                uncheckedThumbColor = Color.White,
                uncheckedTrackColor = palette.stroke""",
        expected_count=2,
    )

    print("== Step 7/11: GlassNavigation.kt -- remove unused AugustRadius import ==")
    apply_edit(
        nav_path,
        old="""import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustMotion
import com.openhealth.sync.ui.theme.AugustRadius""",
        new="""import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustMotion""",
    )

    print("== Step 8/11: GlassNavigation.kt -- narrower outer margin constant ==")
    apply_edit(
        nav_path,
        old="""private const val SECRET_TAP_COUNT = 5
private const val SECRET_TAP_WINDOW_MS = 2000L

/**
 * Compact August v3 navigation dock inspired by the 2026 Material 3 Expressive""",
        new="""private const val SECRET_TAP_COUNT = 5
private const val SECRET_TAP_WINDOW_MS = 2000L

// Nav bar outer margin (2026-08-22): was a flat 16.dp on both axes. Bumped
// horizontally only, to 24.dp, so the two side destination buttons (each
// weight(1f) inside the Row) shrink and the whole pill reads narrower --
// a deliberately conservative first pass rather than the ~44.dp a literal
// "20% narrower" derivation would produce on a typical ~400.dp-wide screen,
// since that number can't be visually verified in this environment. Tune
// this single constant after checking on-device; nothing else needs to
// change to adjust the width further in either direction.
private val NAV_BAR_OUTER_HORIZONTAL_MARGIN = 24.dp
private val NAV_BAR_OUTER_VERTICAL_MARGIN = 8.dp

/**
 * Compact August v3 navigation dock inspired by the 2026 Material 3 Expressive""",
    )

    print("== Step 9/11: GlassNavigation.kt -- apply the margin constants ==")
    apply_edit(
        nav_path,
        old="            .padding(horizontal = 16.dp, vertical = 8.dp),",
        new="            .padding(horizontal = NAV_BAR_OUTER_HORIZONTAL_MARGIN, vertical = NAV_BAR_OUTER_VERTICAL_MARGIN),",
    )

    print("== Step 10/11: GlassNavigation.kt -- Refresh button color/size ==")
    apply_edit(
        nav_path,
        old="""    val fill by animateColorAsState(
        targetValue = if (pressed) AugustColor.LimeActive else AugustColor.Lime,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncFill"
    )

    Box(
        modifier = Modifier
            .size(58.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                translationY = -2.dp.toPx()
            }
            .shadow(
                elevation = AugustElevation.ButtonShadowElevation,
                shape = shape,
                ambientColor = AugustColor.Lime.copy(alpha = 0.18f),
                spotColor = AugustColor.Lime.copy(alpha = 0.18f)
            )""",
        new="""    val fill by animateColorAsState(
        // Tangerine (2026-08-22), was Lime/LimeActive. Size bumped 15%
        // (58.dp -> 67.dp, icon 27.dp -> 31.dp: 58*1.15=66.7 rounded to
        // 67.dp) to read as the visually dominant middle action against the
        // now-narrower side destination buttons. The existing press
        // animation (scale to 0.94, -24deg icon rotation, fill darkening)
        // is unchanged -- it already covers the "light press animation"
        // this button needed; only the color/size changed.
        targetValue = if (pressed) AugustColor.TangerineActive else AugustColor.Tangerine,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncFill"
    )

    Box(
        modifier = Modifier
            .size(67.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                translationY = -2.dp.toPx()
            }
            .shadow(
                elevation = AugustElevation.ButtonShadowElevation,
                shape = shape,
                ambientColor = AugustColor.Tangerine.copy(alpha = 0.18f),
                spotColor = AugustColor.Tangerine.copy(alpha = 0.18f)
            )""",
    )

    print("== Step 11/11: GlassNavigation.kt -- Refresh icon tint/size ==")
    apply_edit(
        nav_path,
        old="""        Icon(
            imageVector = Icons.Rounded.Refresh,
            contentDescription = stringResource(R.string.sync_now),
            tint = AugustColor.LimeInk,
            modifier = Modifier
                .size(27.dp)
                .graphicsLayer { rotationZ = rotation }
        )""",
        new="""        Icon(
            imageVector = Icons.Rounded.Refresh,
            contentDescription = stringResource(R.string.sync_now),
            tint = AugustColor.Ink,
            modifier = Modifier
                .size(31.dp)
                .graphicsLayer { rotationZ = rotation }
        )""",
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
            "Hero two-value layout, Tangerine accent for toggles/navbar, narrower navbar",
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
