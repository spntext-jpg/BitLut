package com.openhealth.sync.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/**
 * August v3's own doc (section 1: "Dark Workbench, Light Controls") only
 * specifies Navy as a permanent architectural anchor -- sidebar, hero,
 * navigation -- inside an otherwise light-canvas product. It does not define
 * a full OS-driven dark theme: there is no "what does a white Surface card
 * become at night" answer in the source doc, because the doc's own product
 * (a media tool) never asked that question.
 *
 * BitLut's dark theme (2026-08-22) answers it by extending Navy's existing
 * role rather than inventing a second, unrelated dark palette: Navy takes
 * over Canvas's role, NavyRaised takes over Surface's role, NavySoft takes
 * over Soft's role -- the same relative-elevation relationship the light
 * scheme already has (Canvas -> Surface -> Soft, each one step lighter),
 * just inverted. This was a deliberate content decision confirmed directly
 * (not inferred): Lime stays a filled surface with Ink text in both modes,
 * and the Steps Hero card stays NavyRaised unchanged (SoftCard's `hero`
 * branch already hardcodes NavyRaised independent of `palette`, so it never
 * needed a dark-mode-specific change).
 *
 * Every reused token was checked against WCAG contrast math before reuse,
 * not assumed: Surface/DarkSecondaryText/Lime/Ink all clear 7:1+ against
 * Navy/NavyRaised/NavySoft. Purple only clears AA-large (3:1) against dark
 * backgrounds, not full AA text contrast (4.5:1) -- consistent with the
 * source doc's own contract that Purple is for focus rings/links/selection
 * detail, never body text, so this doesn't block reuse for that role.
 * DangerFg (tuned for white) drops to 2.62:1 on NavyRaised and does NOT get
 * reused for dark error text; AugustColor's pre-existing but previously
 * unused DarkErrorContainerFg (#FFC9C9) is used for both the dark `error`
 * role and dark `onErrorContainer`, since it already clears 11:1+ against
 * both Navy and NavyRaised and reusing one token for both matches the
 * doc's own "don't add a new color literal if a role already exists" rule
 * (section 16.5) instead of inventing a fourth red.
 */
private val AugustLightScheme = lightColorScheme(
    primary              = AugustColor.Lime,
    onPrimary            = AugustColor.LimeInk,
    primaryContainer     = AugustColor.GrowthStatusBg,
    onPrimaryContainer   = AugustColor.Ink,
    secondary            = AugustColor.Purple,
    onSecondary          = AugustColor.Surface,
    secondaryContainer   = AugustColor.PurpleSoft,
    onSecondaryContainer = AugustColor.PurpleDark,
    tertiary             = AugustColor.Navy,
    onTertiary           = AugustColor.Surface,
    tertiaryContainer    = AugustColor.Soft,
    onTertiaryContainer  = AugustColor.Ink,
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
    inversePrimary       = AugustColor.Lime,
    surfaceTint          = Color.Transparent,
    scrim                = AugustColor.Navy.copy(alpha = 0.80f),
)

private val AugustDarkScheme = darkColorScheme(
    primary              = AugustColor.Lime,
    onPrimary            = AugustColor.LimeInk,
    primaryContainer     = AugustColor.DarkPrimaryContainer,
    onPrimaryContainer   = AugustColor.Surface,
    secondary            = AugustColor.Purple,
    onSecondary          = AugustColor.Surface,
    secondaryContainer   = AugustColor.DarkSecondaryContainer,
    onSecondaryContainer = AugustColor.Surface,
    tertiary             = AugustColor.Surface,
    onTertiary           = AugustColor.Navy,
    tertiaryContainer    = AugustColor.DarkTertiaryContainer,
    onTertiaryContainer  = AugustColor.Surface,
    error                = AugustColor.DarkErrorContainerFg,
    onError              = AugustColor.Navy,
    errorContainer       = AugustColor.DarkErrorContainer,
    onErrorContainer     = AugustColor.DarkErrorContainerFg,
    background           = AugustColor.Navy,
    onBackground         = AugustColor.Surface,
    surface              = AugustColor.NavyRaised,
    onSurface            = AugustColor.Surface,
    surfaceVariant       = AugustColor.NavySoft,
    onSurfaceVariant     = AugustColor.DarkSecondaryText,
    outline              = AugustColor.BorderDark,
    outlineVariant       = AugustColor.NavySoft,
    inverseSurface       = AugustColor.Surface,
    inverseOnSurface     = AugustColor.Ink,
    inversePrimary       = AugustColor.Lime,
    surfaceTint          = Color.Transparent,
    scrim                = AugustColor.Navy.copy(alpha = 0.80f),
)

@Composable
fun BitLutExpressiveTheme(content: @Composable () -> Unit) {
    val isDark = isSystemInDarkTheme()

    // System bars are owned by ComponentActivity.enableEdgeToEdge(). Activity 1.13
    // re-applies edge-to-edge on configuration changes and handles light/dark icon
    // contrast itself. Keeping deprecated Window.statusBarColor/navigationBarColor
    // writes here would be both redundant and ineffective on Android 15+ gesture nav.
    // BITLUT_LINT_CLEANUP_2026_09_11
    MaterialTheme(
        colorScheme = if (isDark) AugustDarkScheme else AugustLightScheme,
        typography = AugustTypography,
        content = content
    )
}
