package com.openhealth.sync.ui.theme

import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// ── Design System Tokens ──────────────────────────────────────────────────────
//
// Single source of truth (v1.9.11): these are now the SAME values used by
// BitPalette.dark() and HealthAccent in FinalBitLutShell.kt, instead of an
// independent blue/orange/purple palette that no screen actually rendered
// with. Previously, MaterialTheme(colorScheme = DarkScheme) carried tokens
// (Blue #19AEF9, Orange #FF9839, Purple #8B5CF6) that never appeared
// anywhere in the actual UI -- every screen built its visuals through the
// separate BitPalette/HealthAccent system instead. That meant any future
// code accidentally referencing MaterialTheme.colorScheme.primary would get
// a blue that doesn't exist anywhere else in the product. Aligning them
// means there is exactly one health-accent orange, one "mind" teal, etc.,
// no matter which system a given piece of UI reads its color from.

// Backgrounds (mirrors BitPalette.dark())
val BgPrimary      = Color(0xFF0C0C0E)   // BitPalette.dark().systemBackground
val BgSecondary    = Color(0xFF0C0C0E)
val BgElevated     = Color(0xCC1C1C1E)   // BitPalette.dark().card

// Accent Colors (mirrors HealthAccent / BitPalette.dark())
val Orange         = Color(0xFFFF6B5A)   // HealthAccent.activity -- the one true "activity" accent
val OrangeDim      = Color(0xFFE25A4B)
val Purple         = Color(0xFF9E6FC3)   // BitPalette.dark().sleep -- the one true "sleep" accent
val Mind           = Color(0xFF5FE0C6)   // BitPalette.dark().mind / HealthAccent.mind

// Semantic
val Success        = Color(0xFF22C55E)
val Warning        = Color(0xFFF59E0B)
val Danger         = Color(0xFFFF453A)   // BitPalette.dark().heart

// Text (mirrors BitPalette.dark())
val TextPrimary    = Color(0xFFF8F8F8)
val TextSecondary  = Color(0xFF8E8E93)

// Glass borders (mirrors BitPalette.dark().stroke)
val GlassBorder    = Color(0x22FFFFFF)

private val DarkScheme = darkColorScheme(
    primary              = Orange,
    onPrimary            = Color(0xFF2D1500),
    primaryContainer     = Color(0xFF3D2000),
    onPrimaryContainer   = Orange,
    secondary            = Purple,
    onSecondary          = Color(0xFF1A0040),
    secondaryContainer   = Color(0xFF2D1B69),
    onSecondaryContainer = Purple,
    tertiary             = Mind,
    onTertiary           = Color(0xFF00261F),
    tertiaryContainer    = Color(0xFF003D32),
    onTertiaryContainer  = Mind,
    error                = Danger,
    onError              = Color(0xFF1A0000),
    errorContainer       = Color(0xFF4C0000),
    onErrorContainer     = Color(0xFFFFB3B3),
    background           = BgPrimary,
    onBackground         = TextPrimary,
    surface              = BgSecondary,
    onSurface            = TextPrimary,
    surfaceVariant       = BgElevated,
    onSurfaceVariant     = TextSecondary,
    outline              = GlassBorder,
    outlineVariant       = Color(0xFF1E293B),
    inverseSurface       = TextPrimary,
    inverseOnSurface     = BgPrimary,
    inversePrimary       = OrangeDim,
    surfaceTint          = Orange,
    scrim                = Color(0xCC0A1428),
)

@Composable
fun BitLutExpressiveTheme(content: @Composable () -> Unit) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = BgPrimary.toArgb()
            window.navigationBarColor = BgPrimary.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = false
                isAppearanceLightNavigationBars = false
            }
        }
    }
    MaterialTheme(colorScheme = DarkScheme, content = content)
}
