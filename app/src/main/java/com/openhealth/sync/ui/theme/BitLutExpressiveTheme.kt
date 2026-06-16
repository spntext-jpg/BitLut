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

// Backgrounds
val BgPrimary      = Color(0xFF0F172A)   // #0F172A — main background
val BgSecondary    = Color(0xFF111827)   // #111827 — dark slate
val BgElevated     = Color(0xFF162033)   // #162033 — elevated surface
val BgCard         = Color(0x0AFFFFFF)   // rgba(255,255,255,0.04)
val BgGlass        = Color(0x0FFFFFFF)   // rgba(255,255,255,0.06)
val BgGlassHover   = Color(0x12FFFFFF)   // rgba(255,255,255,0.07)

// Brand gradient stops
val GradStart      = Color(0xFF0A1428)
val GradMid        = Color(0xFF1D2B53)
val GradEnd        = Color(0xFF4B1D8C)

// Accent Colors
val Blue           = Color(0xFF19AEF9)   // primary interactive
val BlueDim        = Color(0xFF0D8AC5)
val Orange         = Color(0xFFFF9839)   // CTA / AI button
val OrangeDark     = Color(0xFFFF6B00)
val Purple         = Color(0xFF8B5CF6)   // secondary
val PurpleDim      = Color(0xFF6D3FCE)

// Semantic
val Success        = Color(0xFF22C55E)
val Warning        = Color(0xFFF59E0B)
val Danger         = Color(0xFFEF4444)

// Text
val TextPrimary    = Color(0xFFF8F9FA)
val TextSecondary  = Color(0xFF94A3B8)
val TextTertiary   = Color(0xFF475569)

// Glass borders
val GlassBorder    = Color(0x14FFFFFF)   // rgba(255,255,255,0.08)
val GlassBorderLt  = Color(0x20FFFFFF)

// Glow colors
val GlowBlue       = Color(0x6619AEF9)   // rgba(25,174,249,0.4)
val GlowOrange     = Color(0x66FF9839)   // rgba(255,152,57,0.4)
val GlowPurple     = Color(0x668B5CF6)   // rgba(139,92,246,0.4)

// Legacy aliases for compatibility
val ElectricIndigo   = Purple
val ElectricIndigoLt = Blue
val NeonMint         = Success
val NeonAmber        = Orange
val NeonRose         = Danger
val Void             = BgPrimary
val VoidSurface      = BgSecondary
val VoidElevated     = BgElevated
val VoidBorder       = Color(0xFF1E293B)
val GlowIndigo       = GlowPurple
val GlowMint         = Color(0x4422C55E)

private val DarkScheme = darkColorScheme(
    primary              = Blue,
    onPrimary            = Color(0xFF001529),
    primaryContainer     = Color(0xFF0D2B45),
    onPrimaryContainer   = Blue,
    secondary            = Purple,
    onSecondary          = Color(0xFF1A0040),
    secondaryContainer   = Color(0xFF2D1B69),
    onSecondaryContainer = Purple,
    tertiary             = Orange,
    onTertiary           = Color(0xFF2D1500),
    tertiaryContainer    = Color(0xFF3D2000),
    onTertiaryContainer  = Orange,
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
    inversePrimary       = BlueDim,
    surfaceTint          = Blue,
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
