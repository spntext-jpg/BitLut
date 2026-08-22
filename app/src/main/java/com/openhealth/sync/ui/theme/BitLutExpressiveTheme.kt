package com.openhealth.sync.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * Material bridge for August v3.
 *
 * Most BitLut screens still consume BitPalette for incremental migration,
 * while ImportScreen consumes MaterialTheme directly. Both are sourced from
 * the same AugustColor tokens so primary/secondary semantics cannot drift.
 */
private val LightScheme = lightColorScheme(
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

private val DarkScheme = darkColorScheme(
    primary              = AugustColor.Lime,
    onPrimary            = AugustColor.LimeInk,
    primaryContainer     = AugustColor.NavySoft,
    onPrimaryContainer   = AugustColor.Lime,
    secondary            = AugustColor.AccentLight,
    onSecondary          = AugustColor.Navy,
    secondaryContainer   = AugustColor.DarkSecondaryContainer,
    onSecondaryContainer = AugustColor.AccentLight,
    tertiary             = AugustColor.Surface,
    onTertiary           = AugustColor.Navy,
    tertiaryContainer    = AugustColor.NavySoft,
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
    inverseOnSurface     = AugustColor.Navy,
    inversePrimary       = AugustColor.Lime,
    surfaceTint          = Color.Transparent,
    scrim                = AugustColor.Navy.copy(alpha = 0.80f),
)

@Composable
fun BitLutExpressiveTheme(content: @Composable () -> Unit) {
    val isDark = isSystemInDarkTheme()
    val scheme = remember(isDark) { if (isDark) DarkScheme else LightScheme }
    val statusBarColor = remember(isDark) {
        if (isDark) AugustColor.Navy else AugustColor.Canvas
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = statusBarColor.toArgb()
            window.navigationBarColor = statusBarColor.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = !isDark
                isAppearanceLightNavigationBars = !isDark
            }
        }
    }

    MaterialTheme(
        colorScheme = scheme,
        typography = AugustTypography,
        content = content
    )
}
