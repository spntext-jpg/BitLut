package com.openhealth.sync.ui.theme

import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * August v3 is intentionally a light-canvas product system, not an OS-driven
 * dark theme. Dark is reserved for architectural anchors: the top hero,
 * navigation dock and explicit work surfaces. Regular controls/cards remain
 * White Surface on Canvas in both OS appearance modes.
 */
private val AugustScheme = lightColorScheme(
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

@Composable
fun BitLutExpressiveTheme(content: @Composable () -> Unit) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = AugustColor.Canvas.toArgb()
            window.navigationBarColor = AugustColor.Navy.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = true
                isAppearanceLightNavigationBars = false
            }
        }
    }

    MaterialTheme(
        colorScheme = AugustScheme,
        typography = AugustTypography,
        content = content
    )
}
