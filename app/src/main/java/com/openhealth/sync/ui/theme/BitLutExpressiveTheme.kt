
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
