package com.openhealth.sync.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.openhealth.sync.R

// ── August v3 — Dark Workbench / BitLut adaptation ───────────────────────────
//
// Canonical roles for the Android app:
//   Canvas/Surface = content and controls
//   Navy = persistent architectural anchor (bottom navigation / dark chrome)
//   Lime = primary action surface with Ink foreground
//   Purple = focus, selection detail, and secondary interaction
//
// This file is the single token source of truth for Compose. Existing
// Accent/GrowthLime names remain only as compatibility aliases so the
// migration can stay surgical and avoid rewriting unrelated health-data UI.

internal object AugustColor {
    // August v3 core neutrals.
    val Ink = Color(0xFF151728)
    val InkSoft = Color(0xFF292C3E)
    val Muted = Color(0xFF6F7385)
    val Canvas = Color(0xFFF7F8FC)
    val Surface = Color(0xFFFFFFFF)
    val Soft = Color(0xFFF2F3F7)

    // Brand/action: Lime is a filled surface with Ink foreground.
    val Lime = Color(0xFFDFFF6A)
    val LimeHover = Color(0xFFD2F650)
    val LimeActive = Color(0xFFC3E93E)
    val LimeInk = Ink

    // Interaction/focus: Purple is secondary, never the primary CTA.
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

    // Dark architectural anchor.
    val Navy = Color(0xFF151728)
    val NavyRaised = Color(0xFF1C1E33)
    val NavySoft = Color(0xFF24263D)
    val DarkSecondaryText = Color(0xFFB8BDCE)

    // Compatibility aliases for incremental migration of existing call sites.
    // New UI code should prefer the semantic v3 names above.
    val Accent = Purple
    val AccentDark = PurpleDark
    val GrowthLime = Lime
    val DarkPanel = NavyRaised
    val AccentLight = Color(0xFF8B7DF8)

    // Semantic status colors remain independent from brand/action colors.
    val SuccessBg = Color(0xFFDAF6DC)
    val SuccessFg = Color(0xFF276131)
    val WarningBg = Color(0xFFFFF0C9)
    val WarningFg = Color(0xFF7B5813)
    val DangerBg = Color(0xFFFFF6F6)
    val DangerFg = Color(0xFFA43F3F)
    val NeutralBg = Color(0xFFECECF0)
    val NeutralFg = Color(0xFF777B88)
    val AccentStatusBg = PurpleSoft
    val AccentStatusFg = PurpleDark
    val GrowthStatusBg = Color(0xFFE7FF9D)
    val GrowthStatusFg = Color(0xFF31410C)

    val BorderLight = Color(0x1C151728)
    val BorderDark = Color(0x1AFFFFFF)

    // Derived dark containers used by the existing Material bridge.
    val DarkPrimaryContainer = NavySoft
    val DarkSecondaryContainer = Color(0xFF27235F)
    val DarkTertiaryContainer = Color(0xFF303732)
    val DarkErrorContainer = Color(0xFF472531)
    val DarkErrorContainerFg = Color(0xFFFFC9C9)
}

/** August v3 radius scale: controls 10-14, cards 14-18, work surfaces 20-24. */
internal object AugustRadius {
    val Compact = 14.dp
    val Control = 16.dp
    val Pill = 999.dp
    val Button = Pill
    val Card = 22.dp
    val WorkSurface = 26.dp
    val Hero = 30.dp
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

/** August v3 motion: 140-200 ms standard, navigation up to 280 ms, no bounce. */
internal object AugustMotion {
    const val FastMs = 140
    const val DefaultMs = 180
    const val MediumMs = 240
    const val NavigationMs = 280
    val StandardEasing = androidx.compose.animation.core.CubicBezierEasing(0.2f, 0.8f, 0.2f, 1f)
}

/** August v3 restrained neutral depth + weak Lime primary-action glow. */
internal object AugustElevation {
    val CardShadowColor = Color(0xFF151728)
    const val CardShadowAlpha = 0.0f
    val CardShadowElevation = 0.dp

    val HeroShadowColor = Color(0xFF151728)
    const val HeroShadowAlpha = 0.10f
    val HeroShadowElevation = 8.dp

    // Buttons stay flat; hierarchy comes from fill, shape and typography.
    val ButtonShadowColor = AugustColor.Lime
    const val ButtonShadowAlpha = 0.0f
    val ButtonShadowElevation = 0.dp
}


/**
 * Section 4 typography, font family (integration phase 5). Bundled real
 * Inter -- specifically the OFL variable instance from Google's own font
 * repository (github.com/google/fonts, ofl/inter/Inter[opsz,wght].ttf),
 * subsetted to Latin + Cyrillic (this app is EN/RU only) with fonttools'
 * pyftsubset, which cut it from 876KB to 481KB while keeping every
 * character actually used anywhere in strings.xml (both locales) --
 * verified by diffing the subset font's cmap against every distinct
 * character in both string tables; the only 2 characters not covered were
 * emoji (🎉/🎯), which Inter never covers regardless of subsetting -- no
 * text typeface ships emoji glyphs, Android's font-fallback chain renders
 * those from the system emoji font automatically no matter what
 * AugustFont.Family is set to, so this isn't a real gap.
 *
 * This was deliberately deferred out of phase 1 pending a product decision
 * between Android's Downloadable Fonts API (depends on Google Play
 * Services' Fonts Provider -- risky on Huawei devices without GMS, which
 * is this app's whole target audience) and bundling a real font file
 * (works fully offline, no GMS dependency, at the cost of real APK size).
 * Bundling won on that trade-off given the GMS constraint.
 *
 * Every FontWeight value used ANYWHERE in the app (not just
 * AugustTypography's own 9 styles) is registered here with its own
 * FontVariation.weight setting, verified by grepping every FontWeight.*
 * and TextStyle fontWeight literal across FinalBitLutShell.kt, GlassCards.kt,
 * GlassNavigation.kt and ImportScreen.kt: 450/500/600/650/700/750/780/800/
 * 820/850/900. None of those call sites set their own `fontFamily` (the
 * app's one exception, a monospace id/hash display, explicitly opts out
 * with FontFamily.Monospace already) -- Compose's Text() merges an
 * unspecified fontFamily from the ambient LocalTextStyle, which
 * MaterialTheme sets to AugustTypography's own text styles, so bundling
 * the real typeface here retheme the entire app's text without editing any
 * of those individual Text() calls. The optical-size axis (opsz, 14-32) is
 * intentionally left unset on every entry: this app's real weight range
 * (450-900 across mostly small-to-medium text) sits at or near the font's
 * own default opsz of 14, so an explicit value would be redundant with
 * the font's default rather than a deliberate choice -- see this file's
 * top-level header for why per-role opsz was considered and dropped (a
 * single FontWeight can't carry two different opsz values through
 * Compose's family-matching, so a uniform value was the only option that
 * didn't need per-TextStyle fontFamily overrides).
 *
 * @OptIn(ExperimentalTextApi::class): the `Font(resId, weight, style,
 * variationSettings)` overload -- the one that actually lets a resource
 * font be rendered at a specific point on its variable axes instead of
 * just its default instance -- is marked experimental by Compose UI
 * itself, and unlike most `@Experimental*` warnings, Kotlin treats an
 * unacknowledged use of it as a hard compile error, not a warning (caught
 * by this integration's own compile gate on the very first real build --
 * this file had never actually been compiled by a real Kotlin toolchain
 * before that, only diffed against a hand-edited copy, which can verify
 * the text is exactly what was intended but can't catch a real compiler
 * error). The opt-in is scoped to this one object rather than a broader
 * file- or module-level suppression, since it's the only place in the
 * app that touches this API.
 */
@OptIn(ExperimentalTextApi::class)
internal object AugustFont {
    val Family: FontFamily = FontFamily(
        Font(R.font.inter_variable, weight = FontWeight(450), variationSettings = FontVariation.Settings(FontVariation.weight(450))),
        Font(R.font.inter_variable, weight = FontWeight(500), variationSettings = FontVariation.Settings(FontVariation.weight(500))),
        Font(R.font.inter_variable, weight = FontWeight(600), variationSettings = FontVariation.Settings(FontVariation.weight(600))),
        Font(R.font.inter_variable, weight = FontWeight(650), variationSettings = FontVariation.Settings(FontVariation.weight(650))),
        Font(R.font.inter_variable, weight = FontWeight(700), variationSettings = FontVariation.Settings(FontVariation.weight(700))),
        Font(R.font.inter_variable, weight = FontWeight(750), variationSettings = FontVariation.Settings(FontVariation.weight(750))),
        Font(R.font.inter_variable, weight = FontWeight(780), variationSettings = FontVariation.Settings(FontVariation.weight(780))),
        Font(R.font.inter_variable, weight = FontWeight(800), variationSettings = FontVariation.Settings(FontVariation.weight(800))),
        Font(R.font.inter_variable, weight = FontWeight(820), variationSettings = FontVariation.Settings(FontVariation.weight(820))),
        Font(R.font.inter_variable, weight = FontWeight(850), variationSettings = FontVariation.Settings(FontVariation.weight(850))),
        Font(R.font.inter_variable, weight = FontWeight(900), variationSettings = FontVariation.Settings(FontVariation.weight(900))),
    )
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