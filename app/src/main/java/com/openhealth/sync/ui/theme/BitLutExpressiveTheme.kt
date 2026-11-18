package com.openhealth.sync.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/** August brand palette mapped once to Material roles; screens derive their surfaces here. */
private val AugustLightScheme = lightColorScheme(
    primary              = AugustColor.PurpleDark,
    onPrimary            = AugustColor.Surface,
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
    onSurfaceVariant     = AugustColor.InkSoft,
    outline              = AugustColor.Muted,
    outlineVariant       = AugustColor.BorderLight,
    inverseSurface       = AugustColor.Navy,
    inverseOnSurface     = AugustColor.Surface,
    inversePrimary       = AugustColor.Lime,
    surfaceContainerLowest = AugustColor.Canvas,
    surfaceContainerLow    = AugustColor.Surface,
    surfaceContainer       = AugustColor.Soft,
    surfaceContainerHigh   = AugustColor.Soft,
    surfaceContainerHighest = AugustColor.Soft,
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
    outline              = AugustColor.DarkSecondaryText,
    outlineVariant       = AugustColor.BorderDark,
    inverseSurface       = AugustColor.Surface,
    inverseOnSurface     = AugustColor.Ink,
    inversePrimary       = AugustColor.Lime,
    surfaceContainerLowest = AugustColor.Navy,
    surfaceContainerLow    = AugustColor.NavyRaised,
    surfaceContainer       = AugustColor.NavySoft,
    surfaceContainerHigh   = AugustColor.NavySoft,
    surfaceContainerHighest = AugustColor.NavySoft,
    surfaceTint          = Color.Transparent,
    scrim                = AugustColor.Navy.copy(alpha = 0.80f),
)

@Composable
fun BitLutExpressiveTheme(content: @Composable () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val mode = rememberThemeMode(context)
    val isDark = when (mode) {
        ThemeMode.SYSTEM -> isSystemInDarkTheme()
        ThemeMode.LIGHT -> false
        ThemeMode.DARK -> true
    }
    androidx.compose.runtime.LaunchedEffect(isDark) {
        val activity = context as? androidx.activity.ComponentActivity
        activity?.enableEdgeToEdge(
            statusBarStyle = androidx.activity.SystemBarStyle.auto(
                android.graphics.Color.TRANSPARENT, android.graphics.Color.TRANSPARENT
            ) { isDark },
            navigationBarStyle = androidx.activity.SystemBarStyle.auto(
                android.graphics.Color.TRANSPARENT, android.graphics.Color.TRANSPARENT
            ) { isDark }
        )
    }

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
