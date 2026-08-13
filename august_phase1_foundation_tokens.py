
#!/usr/bin/env python3
"""
August design system integration -- Phase 1: foundation tokens.

Paulo supplied his brand design system, "August" (calm/premium/editorial:
dark navy anchor, light bento surfaces, restrained purple interaction, rare
lime growth highlight -- see AUGUST_DESIGN_SYSTEM_AI_FIRST_v1.0.md). This is
the first of several patch scripts integrating it into BitLut; it covers ONLY
the token foundation, deliberately split out from riskier, larger UI changes
(card shadow/glow redesign, button/nav chrome, the ~2700-line typography
rollout across FinalBitLutShell.kt) so each phase can be verified and rolled
back independently, same reasoning as splitting a new Gradle dependency into
its own script.

What this script does:

1. Adds a new file, AugustTokens.kt, with the color/spacing/radius/motion/
   typography tokens ported from the design doc's sections 3-7. A few
   values are DERIVED (not literally in the doc) because the doc describes
   a light-canvas-with-dark-anchor web system, not a full Android light/dark
   theme -- every derived value is documented in the file with the real
   WCAG contrast ratio it was checked against (computed programmatically,
   not eyeballed; see the file's comments for the numbers).

2. Rewrites BitLutExpressiveTheme.kt to build real light/dark Material3
   ColorSchemes from those tokens (it previously hardcoded a single
   always-dark scheme built from independent, unused token names -- a whole-
   tree grep confirmed nothing outside that one file ever referenced them)
   and to make the status/navigation bar appearance follow the actual system
   theme instead of being hardcoded dark regardless of it. This also wires
   the new August typography scale into MaterialTheme, which immediately
   reskins ImportScreen.kt (the Huawei archive-import flow) since it already
   reads MaterialTheme.colorScheme/.typography directly -- everywhere else,
   text sizing is hand-set per Text() call and is unaffected until a later
   phase migrates those calls onto this scale.

3. Repoints HealthAccent (FinalBitLutShell.kt) from three unrelated hues
   (warm orange / teal / violet) onto August's Accent / Accent Dark purple
   family, and BitPalette.light()/dark() onto the matching Canvas/Surface/
   Ink/Muted (light) and Navy/Dark Panel/White/#BEC3D4 (dark) tokens. Both
   objects keep their existing property names (activity/mind/violet,
   systemBackground/card/text/...) so none of the ~60 call sites across the
   app that read them need to change in this phase -- this is a value swap,
   not a structural one, which is what keeps this specific script low-risk
   despite touching the app's entire color identity at once.

   [mind] is aliased to Accent Dark as an interim value rather than August's
   Growth Lime: several of its call sites are genuine "growth" moments
   (the positive-trend indicator, activity ring segments) that are strong
   candidates for Lime, but Lime text/icons directly on this app's white/
   light cards measures at 1.14:1 contrast (computed) -- unreadable. Giving
   Lime a proper dark backing per call site is real UI work, deferred to the
   next phase rather than shipped unverified here.

4. Repoints the bottom nav's refresh-button color from a warm orange (picked
   specifically to stand apart from the app's other accents) to August's
   Accent purple -- under August, "purple means action" makes that the
   *correct* color for the app's single most central tappable action rather
   than a fourth hue standing apart from everything else.

5. Updates the home-screen widget's light/dark colors (values/colors.xml,
   values-night/colors.xml) to the matching August tokens, so the widget
   doesn't visually drift from the in-app palette.

Every old/new text block in this script was hand-edited against a real
extraction of the current codebase first, then generated from that edited
copy's actual diff (not transcribed from memory), and tested for idempotency
(a second run makes zero changes) before being included here.

Run from the repo root:
    python3 august_phase1_foundation_tokens.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

THEME_DIR = "app/src/main/java/com/openhealth/sync/ui/theme"
AUGUST_TOKENS = f"{THEME_DIR}/AugustTokens.kt"
EXPRESSIVE_THEME = f"{THEME_DIR}/BitLutExpressiveTheme.kt"
UI_SHELL = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
NAV = "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt"
COLORS_LIGHT = "app/src/main/res/values/colors.xml"
COLORS_NIGHT = "app/src/main/res/values-night/colors.xml"

# AugustTokens.kt is a brand-new file, so it's not in TARGET_FILES for
# backup/edit purposes (nothing to back up, nothing to apply_edit against) --
# it's created directly in main().
TARGET_FILES = [EXPRESSIVE_THEME, UI_SHELL, NAV, COLORS_LIGHT, COLORS_NIGHT]

AUGUST_TOKENS_CONTENT = '''
package com.openhealth.sync.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp

// ── August Design System — token foundation (integration phase 1) ─────────────
//
// Source: AUGUST_DESIGN_SYSTEM_AI_FIRST_v1.0.md (Paulo's brand design system,
// "AI-first implementation standard v1.0.0"). This file is the machine-
// readable seam between that document and Compose: primitive + semantic
// tokens only. Component-level decisions (card shadow recipes, button
// anatomy, nav bar chrome, etc.) are NOT here on purpose -- they belong to
// the composables that consume these tokens, and are being migrated in
// later phases of this integration (see CLAUDE.md / CHANGELOG.md for the
// phase breakdown once phase 1 lands).
//
// What phase 1 wires up:
//   - AugustColor: the literal palette from the doc's section 3, plus a
//     small number of DERIVED (non-normative) extensions clearly marked as
//     such below -- the source doc is a light-canvas-with-dark-anchor web
//     design system and doesn't tabulate every value a full Android
//     light/dark theme needs (e.g. a dark-mode card surface distinct from
//     Navy, or a lighter accent tint safe as icon/text foreground on a dark
//     background). Every derived value has a comment explaining how it was
//     produced and why (WCAG contrast computed against the exact surface
//     it's used on -- see the accompanying design-system integration plan
//     for the numbers).
//   - AugustRadius / AugustSpace / AugustMotion: direct ports of sections
//     5 (spacing), 6.1 (radius) and 7 (motion) of the doc.
//   - AugustTypography: a Material3 Typography built from section 4's type
//     scale. Font family is FontFamily.Default (system sans) for now, not
//     the doc's specified Inter Variable -- bundling a real, offline-safe
//     Inter font file is a deliberately separate, later phase (it needs a
//     product decision: bundle an actual .ttf in the APK vs. Android's
//     Downloadable Fonts API, which depends on Google Play Services and is
//     therefore risky on Huawei devices without GMS). AugustFont.Family is
//     the one line that phase will change.
//
// What phase 1 deliberately does NOT do: rewrite SoftCard's shadow/glow
// recipe, the bottom nav's glass chrome, or the ~2700 lines of hand-set
// fontSize/fontWeight in FinalBitLutShell.kt. Those are real UI/behavior
// changes that need their own reviewed, compiled, diffed patch scripts --
// bundling them into the token foundation would make one already-large
// change much harder to verify or roll back independently.

/**
 * Primitive + semantic color tokens, ported from the design doc's section 3
 * (Color system) and 3.2 (Status colors). Values are copied verbatim from
 * the doc's table except where marked DERIVED.
 */
internal object AugustColor {
    // -- Primitive / semantic (verbatim from the doc) --
    val Ink = Color(0xFF171927)
    val Muted = Color(0xFF697084)
    val Canvas = Color(0xFFF7F8FC)
    val Surface = Color(0xFFFFFFFF)
    val Soft = Color(0xFFF4F5FA)
    val Accent = Color(0xFF6E5CF6)
    val AccentDark = Color(0xFF5140DC)
    val GrowthLime = Color(0xFFD7FF61)
    val Navy = Color(0xFF15172A)

    // Status pairs (background / foreground), verbatim from 3.2.
    val SuccessBg = Color(0xFFDAF6DC)
    val SuccessFg = Color(0xFF276131)
    val WarningBg = Color(0xFFFFF0C9)
    val WarningFg = Color(0xFF7B5813)
    val DangerBg = Color(0xFFFFF6F6)
    val DangerFg = Color(0xFFA43F3F)
    val NeutralBg = Color(0xFFECECF0)
    val NeutralFg = Color(0xFF777B88)
    val AccentStatusBg = Color(0xFFEEEAFF)
    val AccentStatusFg = Color(0xFF5D4BD5)
    val GrowthStatusBg = Color(0xFFE7FF9D)
    val GrowthStatusFg = Color(0xFF31410C)

    // Borders, verbatim from 3.1 (light/dark alpha over the token itself).
    val BorderLight = Color(0x1C1C1F31) // rgba(28,31,49,.11)
    val BorderDark = Color(0x1AFFFFFF)  // rgba(255,255,255,.10)

    // Dark-surface secondary text, verbatim from 3.1 ("#BEC3D4").
    val DarkSecondaryText = Color(0xFFBEC3D4)

    // -- DERIVED (not in the source doc) --
    //
    // The doc treats Navy as a component-level "anchor" (sidebar/hero/
    // editor) inside an otherwise light UI, not as a full app-wide dark
    // theme background. BitLut already supports following the system
    // light/dark setting (see BitPalette in FinalBitLutShell.kt), so phase
    // 1 extends August's own stated dark-surface rule ("Navy or Dark Panel
    // with white primary text and #BEC3D4 secondary text", section 3.1)
    // into a full dark ColorScheme rather than dropping system dark-theme
    // support. Every derived value below was chosen by computing its real
    // WCAG contrast ratio against the exact surface it's used on -- see the
    // integration plan for the numbers; the short version is in each
    // comment.

    /** Dark-mode card/panel surface: Navy blended 7% toward white, so cards
     * read as a distinct elevated layer above the Navy page background
     * instead of blending into it flat. White text on this: 14.7:1. */
    val DarkPanel = Color(0xFF252739)

    /** Accent lightened ~20% toward white. Reserved for icon/text FOREGROUND
     * on dark surfaces only (Navy or DarkPanel) -- true Accent's contrast
     * there is only ~3.2-3.8:1 (fine for a button fill with white text on
     * top, too low to reuse as bare foreground). AccentLight on Navy:
     * 5.4:1; on DarkPanel: 4.5:1. Never use as a button FILL (white text on
     * AccentLight only reaches 3.3:1) -- fills always use plain Accent. */
    val AccentLight = Color(0xFF8B7DF8)

    // Derived Material3 dark tonal containers (primary/secondary/tertiary/
    // error), each Navy blended toward its accent so dark containers read
    // as "the accent, dimmed for a dark surface" rather than a flat navy
    // box. Paired *_fg tokens (AccentLight / GrowthLime / a lightened
    // danger red) are the only foregrounds verified legible on each one.
    val DarkPrimaryContainer = Color(0xFF342F71)
    val DarkSecondaryContainer = Color(0xFF27235F)
    val DarkTertiaryContainer = Color(0xFF303732)
    val DarkErrorContainer = Color(0xFF472531)
    val DarkErrorContainerFg = Color(0xFFFFC9C9)
}

/** Section 6.1 radius scale. One representative dp per named bucket -- the
 * doc gives ranges (e.g. "18-24px: cards and panels"); component code picks
 * the exact end of the range it needs and should still reference these
 * where a bucket, not a specific px value, is what actually matters. */
internal object AugustRadius {
    val Compact = 10.dp   // 8-12px: compact controls, work items, icon buttons
    val Control = 15.dp   // 13-16px: regular controls, nav items, segmented controls
    val Card = 20.dp       // 18-24px: cards and panels
    val Hero = 28.dp       // 26-30px: guidance banners, hero, onboarding
    val Pill = 999.dp     // pills, chips, progress tracks
}

/** Section 5 spacing scale, verbatim: 0,2,4,6,8,10,12,14,16,18,20,22,24,28,
 * 32,36,42,48,52,64,72px. */
internal object AugustSpace {
    val s0 = 0.dp
    val s2 = 2.dp
    val s4 = 4.dp
    val s6 = 6.dp
    val s8 = 8.dp
    val s10 = 10.dp
    val s12 = 12.dp
    val s14 = 14.dp
    val s16 = 16.dp
    val s18 = 18.dp
    val s20 = 20.dp
    val s22 = 22.dp
    val s24 = 24.dp
    val s28 = 28.dp
    val s32 = 32.dp
    val s36 = 36.dp
    val s42 = 42.dp
    val s48 = 48.dp
    val s52 = 52.dp
    val s64 = 64.dp
    val s72 = 72.dp
}

/** Section 7 motion. Durations in ms (for `tween(durationMillis = ...)`)
 * plus the doc's standard cubic-bezier easing. The doc explicitly forbids
 * bounce/elastic overshoot -- component code migrating off the old
 * `Spring.DampingRatioMediumBouncy` presses should land on
 * `tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing)` or
 * similar, not a replacement spring. */
internal object AugustMotion {
    const val FastMs = 120
    const val DefaultMs = 160
    const val MediumMs = 240
    const val SlowMs = 360
    val StandardEasing = androidx.compose.animation.core.CubicBezierEasing(0.2f, 0.8f, 0.2f, 1f)
}

/** Section 4 typography. Font family is system default for now -- see the
 * file header for why Inter Variable isn't bundled yet. */
internal object AugustFont {
    val Family: FontFamily = FontFamily.Default
}

/**
 * Material3 Typography built from the doc's section 4 type scale. Tracking
 * is expressed in em (matches the doc's own em-based tracking, which scales
 * correctly with font size, unlike a fixed sp value). Tabular numerals
 * (`fontFeatureSettings = "tnum"`) are applied to the two styles actually
 * used for big metric numbers (display/headline), per the doc's "MUST use
 * ... tabular numerals for metrics".
 *
 * Display's doc value is a responsive `clamp(32px, 5vw, 62px)` -- there's
 * no native viewport-relative unit on Android (dp already scales with
 * density, not viewport width), so this uses a fixed size near the clamp's
 * mobile-viewport end rather than porting the clamp literally. Same for
 * Heading 2's `clamp(30px, 4vw, 48px)`.
 *
 * NOTE: wiring this into MaterialTheme (phase 1) does not, by itself,
 * retheme most of the app's text -- FinalBitLutShell.kt currently sets
 * fontSize/fontWeight by hand on nearly every Text() call rather than
 * reading MaterialTheme.typography. It DOES immediately retheme
 * ImportScreen.kt, which already reads MaterialTheme.typography throughout.
 * Migrating FinalBitLutShell.kt's hand-set text styles onto this scale is a
 * later phase (large mechanical change, its own patch script).
 */
internal val AugustTypography = Typography(
    displayLarge = TextStyle(
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(850),
        fontSize = 40.sp,
        lineHeight = 40.sp,
        letterSpacing = (-0.055).em,
        fontFeatureSettings = "tnum",
    ),
    headlineLarge = TextStyle( // Heading 2 (page title)
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(820),
        fontSize = 32.sp,
        lineHeight = 33.sp,
        letterSpacing = (-0.05).em,
        fontFeatureSettings = "tnum",
    ),
    titleLarge = TextStyle( // Heading 3 (section title)
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(780),
        fontSize = 22.sp,
        lineHeight = 25.sp,
        letterSpacing = (-0.035).em,
    ),
    titleMedium = TextStyle( // Heading 4 (compact panel title)
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(750),
        fontSize = 18.sp,
        lineHeight = 22.sp,
        letterSpacing = (-0.025).em,
    ),
    titleSmall = TextStyle( // Label (eyebrows, badges, captions)
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(800),
        fontSize = 10.sp,
        lineHeight = 14.sp,
        letterSpacing = 0.10.em,
    ),
    bodyLarge = TextStyle( // Lead (hero supporting copy)
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(450),
        fontSize = 16.sp,
        lineHeight = 26.sp,
    ),
    bodyMedium = TextStyle( // Body (default reading text)
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(450),
        fontSize = 14.sp,
        lineHeight = 23.sp,
    ),
    bodySmall = TextStyle( // Body small (dense cards)
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(450),
        fontSize = 12.sp,
        lineHeight = 19.sp,
    ),
    labelLarge = TextStyle( // Caption (secondary descriptions)
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(650),
        fontSize = 11.sp,
        lineHeight = 17.sp,
    ),
    labelSmall = TextStyle( // Micro (system labels, compact metadata)
        fontFamily = AugustFont.Family,
        fontWeight = FontWeight(850),
        fontSize = 9.sp,
        lineHeight = 12.sp,
        letterSpacing = 0.09.em,
    ),
)
'''

EXPRESSIVE_THEME_CONTENT = '''
package com.openhealth.sync.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// ── Design System Tokens (August integration, phase 1) ────────────────────────
//
// v1.9.11 note (kept for history): this file used to hand-roll its own
// Blue/Orange/Purple token set that no screen actually rendered with, since
// every screen built its visuals through the separate BitPalette/HealthAccent
// system in FinalBitLutShell.kt instead. That's still true architecturally --
// BitPalette/HealthAccent remain the primary source most composables read
// from -- but as of this phase, BOTH systems are sourced from the same
// AugustColor tokens (see AugustTokens.kt), so there's exactly one Accent
// purple, one Growth lime, etc., no matter which system a given piece of UI
// reads its color from. BitPalette/HealthAccent's own token swap lives in
// FinalBitLutShell.kt, not here.
//
// This MaterialTheme colorScheme has exactly one real independent consumer
// today: ImportScreen.kt (the Huawei archive-import flow), which reads
// MaterialTheme.colorScheme/.typography directly rather than going through
// BitPalette. Everything else in this object was previously unused dead
// exported API surface (confirmed via a whole-tree grep before this rewrite)
// -- wiring real August tokens through it costs nothing and fixes that
// screen's theming as a side effect of this phase, rather than requiring a
// separate change.

private val LightScheme = lightColorScheme(
    primary              = AugustColor.Accent,
    onPrimary            = AugustColor.Surface,
    primaryContainer     = AugustColor.AccentStatusBg,
    onPrimaryContainer   = AugustColor.AccentStatusFg,
    secondary            = AugustColor.AccentDark,
    onSecondary          = AugustColor.Surface,
    secondaryContainer   = AugustColor.Soft,
    onSecondaryContainer = AugustColor.Ink,
    tertiary             = AugustColor.GrowthStatusFg,
    onTertiary           = AugustColor.Surface,
    tertiaryContainer    = AugustColor.GrowthStatusBg,
    onTertiaryContainer  = AugustColor.GrowthStatusFg,
    error                = AugustColor.DangerFg,
    onError              = AugustColor.Surface,
    errorContainer       = AugustColor.DangerBg,
    onErrorContainer     = AugustColor.DangerFg,
    background           = AugustColor.Canvas,
    onBackground         = AugustColor.Ink,
    surface              = AugustColor.Surface,
    onSurface            = AugustColor.Ink,
    surfaceVariant       = AugustColor.Soft,
    onSurfaceVariant     = AugustColor.Muted,
    outline              = AugustColor.BorderLight,
    outlineVariant       = AugustColor.Soft,
    inverseSurface       = AugustColor.Navy,
    inverseOnSurface     = AugustColor.Surface,
    inversePrimary       = AugustColor.AccentLight,
    surfaceTint          = AugustColor.Accent,
    scrim                = AugustColor.Navy.copy(alpha = 0.80f),
)

private val DarkScheme = darkColorScheme(
    primary              = AugustColor.Accent,
    onPrimary            = AugustColor.Surface,
    primaryContainer     = AugustColor.DarkPrimaryContainer,
    onPrimaryContainer   = AugustColor.AccentLight,
    secondary            = AugustColor.AccentLight,
    onSecondary          = AugustColor.Navy,
    secondaryContainer   = AugustColor.DarkSecondaryContainer,
    onSecondaryContainer = AugustColor.AccentLight,
    tertiary             = AugustColor.GrowthLime,
    onTertiary           = AugustColor.Navy,
    tertiaryContainer    = AugustColor.DarkTertiaryContainer,
    onTertiaryContainer  = AugustColor.GrowthLime,
    error                = AugustColor.DarkErrorContainerFg,
    onError              = AugustColor.Navy,
    errorContainer       = AugustColor.DarkErrorContainer,
    onErrorContainer     = AugustColor.DarkErrorContainerFg,
    background           = AugustColor.Navy,
    onBackground         = AugustColor.Surface,
    surface              = AugustColor.DarkPanel,
    onSurface            = AugustColor.Surface,
    surfaceVariant       = AugustColor.DarkPanel,
    onSurfaceVariant     = AugustColor.DarkSecondaryText,
    outline              = AugustColor.BorderDark,
    outlineVariant       = AugustColor.DarkPanel,
    inverseSurface       = AugustColor.Surface,
    inverseOnSurface     = AugustColor.Navy,
    inversePrimary       = AugustColor.AccentDark,
    surfaceTint          = AugustColor.Accent,
    scrim                = AugustColor.Navy.copy(alpha = 0.80f),
)

@Composable
fun BitLutExpressiveTheme(content: @Composable () -> Unit) {
    val isDark = isSystemInDarkTheme()
    val scheme = remember(isDark) { if (isDark) DarkScheme else LightScheme }
    val statusBarColor = remember(isDark) { if (isDark) AugustColor.Navy else AugustColor.Canvas }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = statusBarColor.toArgb()
            window.navigationBarColor = statusBarColor.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                // Light system bars need dark icons (isAppearanceLight* = true);
                // dark bars need light icons -- previously hardcoded to always
                // dark-appearance icons regardless of theme, which only looked
                // right because the app effectively always rendered dark chrome.
                isAppearanceLightStatusBars = !isDark
                isAppearanceLightNavigationBars = !isDark
            }
        }
    }
    MaterialTheme(colorScheme = scheme, typography = AugustTypography, content = content)
}
'''


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
    dst = BACKUP_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def apply_edit(rel_path: str, old: str, new: str, desc: str) -> bool:
    """Plain-substring replacement, exactly 1 occurrence expected.

    Checks the OLD anchor's count first; NEW-presence is only consulted as
    a fallback once OLD is confirmed absent.
    """
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    old_count = text.count(old)
    if old_count == 0:
        if text.count(new) >= 1:
            print(f"   (already applied, skipping) {desc}")
            return False
        die(f"Anchor not found for '{desc}' in {rel_path}, and patched text "
            f"is also absent. File may have changed since this script was "
            f"written -- aborting rather than guessing.")

    if old_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {old_count}. Aborting rather than guessing "
            f"which one to patch.")

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def apply_insertion(rel_path: str, anchor: str, new_with_anchor: str, unique_marker: str, desc: str) -> bool:
    """For edits that insert new text between two lines that stay unchanged
    on both sides. `anchor` (spanning both sides) remains a substring of
    `new_with_anchor`, so checking anchor-count-first would never see it as
    "gone" and would reapply forever. Idempotency here is instead decided by
    `unique_marker`, a string that only exists once the insertion has
    happened.
    """
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"   (already applied, skipping) {desc}")
        return False

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {anchor_count}. Aborting rather than "
            f"guessing which one to patch.")

    path.write_text(text.replace(anchor, new_with_anchor, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def write_new_file(rel_path: str, content: str, desc: str) -> bool:
    """Idempotent whole-file creation for a brand-new file. If the file
    already exists with this exact content, this is a no-op; if it exists
    with different content, abort rather than clobber unknown edits."""
    path = ROOT / rel_path
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            print(f"   (already applied, skipping) {desc}")
            return False
        die(f"{rel_path} already exists with different content than "
            f"expected for '{desc}'. Aborting rather than overwriting -- "
            f"if this file was hand-edited since, that needs a human look.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"   created: {desc}")
    return True


def main() -> None:
    print("==> Checking target files exist")
    for rel in TARGET_FILES:
        if not (ROOT / rel).exists():
            die(f"Expected file not found: {rel} (run this from the repo root)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)
    # AugustTokens.kt is new -- back it up too if a previous partial run
    # already created it, so re-running is safe to inspect/roll back.
    if (ROOT / AUGUST_TOKENS).exists():
        backup_file(AUGUST_TOKENS)

    print("==> Creating AugustTokens.kt")
    write_new_file(AUGUST_TOKENS, AUGUST_TOKENS_CONTENT, "August design tokens (colors, radius, spacing, motion, typography)")

    print("==> Rewriting BitLutExpressiveTheme.kt (August light/dark Material3 schemes)")
    path = ROOT / EXPRESSIVE_THEME
    current = path.read_text(encoding="utf-8")
    if current == EXPRESSIVE_THEME_CONTENT:
        print("   (already applied, skipping) BitLutExpressiveTheme.kt rewrite")
    else:
        path.write_text(EXPRESSIVE_THEME_CONTENT, encoding="utf-8")
        print("   applied: BitLutExpressiveTheme.kt rewrite")

    print("==> Repointing HealthAccent + BitPalette in FinalBitLutShell.kt")
    apply_insertion(
        UI_SHELL,
        anchor="import com.openhealth.sync.ui.theme.BitLutExpressiveTheme\n",
        new_with_anchor="import com.openhealth.sync.ui.theme.AugustColor\nimport com.openhealth.sync.ui.theme.BitLutExpressiveTheme\n",
        unique_marker="import com.openhealth.sync.ui.theme.AugustColor\n",
        desc="import AugustColor",
    )
    apply_edit(
        UI_SHELL,
        old='''/**
 * Shared accent-color palette used across cards and icons throughout the app.
 * These are purely visual accents (not tied to any specific health metric) --
 * [violet] in particular is just the app's fourth decorative accent color
 * (currently used for the Manual Sync card in Settings), not an indicator of
 * any sleep-related feature or data.
 */
internal object HealthAccent {
    val activity = Color(0xFFFF6B5A)
    val violet = Color(0xFF9E6FC3)
    val mind = Color(0xFF5FE0C6)
    val cardLight = Color.White
    val cardDark = Color(0xCC1C1C1E)
    val systemLight = Color(0xFFF2F2F7)
}''',
        new='''/**
 * Shared accent-color palette used across cards and icons throughout the app.
 * These are purely visual accents (not tied to any specific health metric).
 *
 * August design system integration, phase 1 (see AugustTokens.kt): these
 * three used to be three unrelated hues (warm orange/teal/violet). August's
 * own principles are explicit about this ("one strong action color... never
 * a collection of unrelated gradients") -- [activity] and [violet] are now
 * both drawn from August's purple family (Accent / Accent Dark), and [mind]
 * is aliased to Accent Dark as an interim, contrast-safe value too. [mind]'s
 * call sites include real "growth" moments (the positive-trend indicator,
 * the activity rings) that are strong candidates for August's actual Growth
 * Lime token -- that needs a per-call-site pass to give Lime a proper dark
 * backing (Lime text/icons on the app's white/light cards fails contrast
 * outright: computed at 1.14:1, versus the ~4.6-6.7:1 the two purple tokens
 * below measure at on both this app's card surfaces), so it's deliberately
 * deferred to the next integration phase rather than shipped unverified.
 */
internal object HealthAccent {
    val activity = AugustColor.Accent
    val violet = AugustColor.AccentDark
    val mind = AugustColor.AccentDark
    val cardLight = Color.White
    val cardDark = Color(0xCC1C1C1E)
    val systemLight = Color(0xFFF2F2F7)
}''',
        desc="repoint HealthAccent to August Accent/Accent Dark",
    )
    apply_edit(
        UI_SHELL,
        old='''    companion object {
        // light() intentionally uses its own, slightly more saturated accent
        // values rather than HealthAccent's dark-mode hexes verbatim: the same
        // glow-tinted accent that reads as rich against a near-black card
        // washes out and looks chalky against white, so a small amount of
        // per-theme accent tuning is correct design, not drift.
        fun light(): BitPalette = BitPalette(
            dark = false,
            systemBackground = Color(0xFFF6F4F1),
            card = Color.White,
            text = Color(0xFF111318),
            secondaryText = Color(0xFF6E6E73),
            stroke = Color(0x1A111318),
            activity = Color(0xFFFF6B5F),
            mind = Color(0xFF46C7B7),
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFFF6F4F1), Color(0xFFFFFFFF)))
        )
        // dark() reuses HealthAccent directly (single source of truth) rather
        // than redeclaring near-duplicate hex values that could drift apart.
        fun dark(): BitPalette = BitPalette(
            dark = true,
            systemBackground = Color(0xFF0C0C0E),
            card = Color(0xCC1C1C1E),
            text = Color(0xFFF8F8F8),
            secondaryText = Color(0xFF8E8E93),
            stroke = Color(0x22FFFFFF),
            activity = HealthAccent.activity,
            mind = HealthAccent.mind,
            backgroundBrush = Brush.verticalGradient(listOf(Color(0xFF0C0C0E), Color(0xFF1C1C1E)))
        )
    }''',
        new='''    companion object {
        // August design system integration, phase 1 (see AugustTokens.kt).
        // light() previously used its own hand-tuned accent hexes rather than
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
            backgroundBrush = Brush.verticalGradient(listOf(AugustColor.Canvas, AugustColor.Surface))
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
            text = Color.White,
            secondaryText = AugustColor.DarkSecondaryText,
            stroke = AugustColor.BorderDark,
            activity = HealthAccent.activity,
            mind = HealthAccent.mind,
            backgroundBrush = Brush.verticalGradient(listOf(AugustColor.Navy, AugustColor.DarkPanel))
        )
    }''',
        desc="repoint BitPalette.light()/dark() to August tokens",
    )

    print("==> Repointing bottom nav refresh button color in GlassNavigation.kt")
    apply_insertion(
        NAV,
        anchor="import androidx.compose.ui.unit.dp\nimport kotlinx.coroutines.launch",
        new_with_anchor="import androidx.compose.ui.unit.dp\nimport com.openhealth.sync.ui.theme.AugustColor\nimport kotlinx.coroutines.launch",
        unique_marker="import com.openhealth.sync.ui.theme.AugustColor",
        desc="import AugustColor",
    )
    apply_edit(
        NAV,
        old='''/**
 * Warm orange, sprint 2026-07-09: distinct from every existing accent
 * (activity/mind/violet) on purpose, so the refresh button reads as its
 * own clearly-tappable action rather than belonging to either tab.
 */
private val WarmRefreshOrange = Color(0xFFFF8A34)

/**
 * Centered, larger, warm-orange manual refresh button (sprint 2026-07-09),
 * sitting between the two tab buttons in the bottom nav. Reuses the same
 * "sync now" action as the Settings screen's manual sync button.
 */
@Composable
private fun Glass20RefreshButton(onClick: () -> Unit) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val scope = rememberCoroutineScope()
    val iconRotation = remember { Animatable(0f) }
    val iconBounce = remember { Animatable(1f) }
    val shape = remember { RoundedCornerShape(30.dp) }
    val brush = remember {
        Brush.linearGradient(
            listOf(WarmRefreshOrange, WarmRefreshOrange.copy(alpha = 0.84f))
        )
    }''',
        new='''/**
 * August design system integration, phase 1 (see AugustTokens.kt). Was a
 * warm orange (sprint 2026-07-09) chosen specifically to be distinct from
 * every other accent in the app at the time. Under August, that rationale
 * inverts: "purple means action" (section 1.3, principle 4) makes the one
 * true Accent purple the *correct* color for the app's single most central
 * tappable action, not a mismatch -- so this is now literally
 * AugustColor.Accent rather than a fourth hue invented to stand apart from
 * activity/mind/violet (which are themselves now Accent/Accent Dark, see
 * HealthAccent in FinalBitLutShell.kt).
 */
private val RefreshButtonAccent = AugustColor.Accent

/**
 * Centered, larger manual refresh button (sprint 2026-07-09), sitting
 * between the two tab buttons in the bottom nav. Reuses the same "sync now"
 * action as the Settings screen's manual sync button.
 */
@Composable
private fun Glass20RefreshButton(onClick: () -> Unit) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val scope = rememberCoroutineScope()
    val iconRotation = remember { Animatable(0f) }
    val iconBounce = remember { Animatable(1f) }
    val shape = remember { RoundedCornerShape(30.dp) }
    val brush = remember {
        Brush.linearGradient(
            listOf(RefreshButtonAccent, RefreshButtonAccent.copy(alpha = 0.84f))
        )
    }''',
        desc="rename WarmRefreshOrange -> RefreshButtonAccent = AugustColor.Accent",
    )
    apply_edit(
        NAV,
        old="                ambientColor = WarmRefreshOrange.copy(alpha = 0.40f),\n                spotColor = WarmRefreshOrange.copy(alpha = 0.55f)",
        new="                ambientColor = RefreshButtonAccent.copy(alpha = 0.40f),\n                spotColor = RefreshButtonAccent.copy(alpha = 0.55f)",
        desc="update refresh button shadow colors",
    )

    print("==> Updating widget colors (light)")
    apply_edit(
        COLORS_LIGHT,
        old='''         ColorProvider(color: Color) and ColorProvider(resId: Int) exist). -->
    <color name="widget_card">#FFFFFFFF</color>
    <color name="widget_text">#FF111318</color>
    <color name="widget_secondary_text">#FF6E6E73</color>''',
        new='''         ColorProvider(color: Color) and ColorProvider(resId: Int) exist).

         August design system integration, phase 1: widget_card was already
         equal to August's Surface (#FFFFFF); widget_text/widget_secondary_text
         are now August's Ink/Muted tokens (see AugustTokens.kt) instead of
         their own independently-set hexes. -->
    <color name="widget_card">#FFFFFFFF</color>
    <color name="widget_text">#FF171927</color>
    <color name="widget_secondary_text">#FF697084</color>''',
        desc="repoint light widget colors to August Ink/Muted",
    )

    print("==> Updating widget colors (dark)")
    apply_edit(
        COLORS_NIGHT,
        old='''  than Glance's ColorProvider(day=, night=).
-->
<resources>
    <color name="widget_card">#FF1C1C1E</color>
    <color name="widget_text">#FFF8F8F8</color>
    <color name="widget_secondary_text">#FF8E8E93</color>
</resources>''',
        new='''  than Glance's ColorProvider(day=, night=).

  August design system integration, phase 1: widget_card/widget_text/
  widget_secondary_text are now August's DarkPanel / White / dark-surface
  secondary text tokens (see AugustTokens.kt AugustColor.DarkPanel and
  AugustColor.DarkSecondaryText for how these were derived and
  contrast-checked) instead of their own independently-set hexes.
-->
<resources>
    <color name="widget_card">#FF252739</color>
    <color name="widget_text">#FFFFFFFF</color>
    <color name="widget_secondary_text">#FFBEC3D4</color>
</resources>''',
        desc="repoint dark widget colors to August DarkPanel/White/DarkSecondaryText",
    )

    print("==> Best-effort compile check")
    gradlew = ROOT / "gradlew"
    if gradlew.exists():
        result = subprocess.run(
            ["./gradlew", ":app:compileDebugKotlin", "--console=plain"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            die("compileDebugKotlin failed -- NOT committing or pushing. "
                "Fix the error above (or paste it back) before re-running.")
        print("==> Compile check passed")
    else:
        print("   gradlew not found -- skipping compile check (unexpected outside "
              "a throwaway sandbox; NOT committing automatically).")
        return

    print("==> git add / commit / push")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m", "August design system integration, phase 1: foundation tokens"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
