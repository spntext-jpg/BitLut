
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
