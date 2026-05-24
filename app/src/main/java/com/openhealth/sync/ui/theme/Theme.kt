package com.openhealth.sync.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary              = DarkPrimary,
    onPrimary            = DarkOnPrimary,
    secondary            = DarkSecondary,
    onSecondary          = DarkOnSecondary,
    background           = DarkBackground,
    surface              = DarkSurface,
    surfaceVariant       = DarkSurfaceVariant,
    surfaceContainer     = DarkSurfaceContainer,
    surfaceContainerHigh = DarkSurfaceContainerHigh,
    onSurface            = DarkOnSurface,
    onSurfaceVariant     = DarkOnSurfaceVariant,
    error                = DarkError,
    onError              = DarkOnError
)

private val LightColorScheme = lightColorScheme(
    primary              = LightPrimary,
    onPrimary            = LightOnPrimary,
    secondary            = LightSecondary,
    onSecondary          = LightOnSecondary,
    background           = LightBackground,
    surface              = LightSurface,
    surfaceVariant       = LightSurfaceVariant,
    surfaceContainer     = LightSurfaceContainer,
    surfaceContainerHigh = LightSurfaceContainerHigh,
    onSurface            = LightOnSurface,
    onSurfaceVariant     = LightOnSurfaceVariant,
    error                = LightError,
    onError              = LightOnError
)

@Composable
fun OpenHealthSyncTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color (Monet) — Android 12+ takes user wallpaper colors
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context)
            else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else      -> LightColorScheme
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            @Suppress("DEPRECATION")
            window.statusBarColor = colorScheme.background.toArgb()
            WindowCompat.getInsetsController(window, view)
                .isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
