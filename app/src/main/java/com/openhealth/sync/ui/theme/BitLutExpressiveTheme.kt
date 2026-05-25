package com.openhealth.sync.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val BrandBlue = Color(0xFF00A2E8)
private val BrandBlueSoft = Color(0xFF2FC6F6)
private val CoPilotViolet = Color(0xFF6F4DFF)
private val TaskOrange = Color(0xFFFF8A3D)
private val CrmGreen = Color(0xFF2ECC71)
private val CollaborationCyan = Color(0xFF17D5C3)
private val AppLime = Color(0xFFD7F632)
private val Ink = Color(0xFF142033)
private val SoftBackground = Color(0xFFF5F8FB)
private val SoftSurface = Color(0xFFFFFFFF)
private val SoftContainer = Color(0xFFEAF6FD)

private val LightExpressiveScheme = lightColorScheme(
    primary = BrandBlue,
    onPrimary = Color.White,
    primaryContainer = SoftContainer,
    onPrimaryContainer = Color(0xFF00354D),
    secondary = CoPilotViolet,
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFEDE8FF),
    onSecondaryContainer = Color(0xFF241052),
    tertiary = CollaborationCyan,
    onTertiary = Color(0xFF00201D),
    tertiaryContainer = Color(0xFFD7FAF6),
    onTertiaryContainer = Color(0xFF003D37),
    background = SoftBackground,
    onBackground = Ink,
    surface = SoftSurface,
    onSurface = Ink,
    surfaceVariant = Color(0xFFE9EEF5),
    onSurfaceVariant = Color(0xFF4F5B6A),
    surfaceContainerLowest = Color.White,
    surfaceContainerLow = Color(0xFFF9FBFD),
    surfaceContainer = Color(0xFFF1F6FA),
    surfaceContainerHigh = Color(0xFFEAF2F8),
    surfaceContainerHighest = Color(0xFFE1ECF5),
    error = Color(0xFFE5484D),
    onError = Color.White,
    outline = Color(0xFFB6C7D6),
    outlineVariant = Color(0xFFD5E1EA)
)

private val DarkExpressiveScheme = darkColorScheme(
    primary = BrandBlueSoft,
    onPrimary = Color(0xFF001F2E),
    primaryContainer = Color(0xFF004C6D),
    onPrimaryContainer = Color(0xFFBDEEFF),
    secondary = Color(0xFFCFC2FF),
    onSecondary = Color(0xFF26185A),
    secondaryContainer = Color(0xFF49358E),
    onSecondaryContainer = Color(0xFFEDE8FF),
    tertiary = Color(0xFF8EF2E7),
    onTertiary = Color(0xFF003733),
    tertiaryContainer = Color(0xFF00504A),
    onTertiaryContainer = Color(0xFFB8FFF7),
    background = Color(0xFF0E141B),
    onBackground = Color(0xFFE7EEF7),
    surface = Color(0xFF121B24),
    onSurface = Color(0xFFE7EEF7),
    surfaceVariant = Color(0xFF263441),
    onSurfaceVariant = Color(0xFFC1CED9),
    surfaceContainerLowest = Color(0xFF0A1016),
    surfaceContainerLow = Color(0xFF101922),
    surfaceContainer = Color(0xFF17222D),
    surfaceContainerHigh = Color(0xFF1E2B37),
    surfaceContainerHighest = Color(0xFF263543),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    outline = Color(0xFF8FA4B5),
    outlineVariant = Color(0xFF405464)
)

@Composable
fun BitLutExpressiveTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val colorScheme: ColorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && darkTheme -> dynamicDarkColorScheme(context)
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> dynamicLightColorScheme(context)
        darkTheme -> DarkExpressiveScheme
        else -> LightExpressiveScheme
    }.harmonizedWithBitLut()

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.background.toArgb()
            window.navigationBarColor = colorScheme.surfaceContainer.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
            WindowCompat.getInsetsController(window, view).isAppearanceLightNavigationBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography(),
        content = content
    )
}

/**
 * Keeps Android dynamic colors, but restores BitLut's product identity:
 * blue reliability, violet assistant accent, lime mascot energy.
 */
private fun ColorScheme.harmonizedWithBitLut(): ColorScheme = copy(
    primary = BrandBlue,
    secondary = CoPilotViolet,
    tertiary = CollaborationCyan,
    inversePrimary = AppLime
)

object BitLutExpressiveTokens {
    val brandBlue = BrandBlue
    val brandBlueSoft = BrandBlueSoft
    val coPilotViolet = CoPilotViolet
    val taskOrange = TaskOrange
    val crmGreen = CrmGreen
    val collaborationCyan = CollaborationCyan
    val mascotLime = AppLime
}
