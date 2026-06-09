package com.openhealth.sync.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// ── Palette ───────────────────────────────────────────────────────────────────

val Void          = Color(0xFF050510)   // deepest background
val VoidSurface   = Color(0xFF0C0C1E)   // card base
val VoidElevated  = Color(0xFF13132B)   // elevated surface
val VoidBorder    = Color(0xFF1E1E3F)   // subtle borders

val ElectricIndigo   = Color(0xFF6366F1) // primary action
val ElectricIndigoLt = Color(0xFF818CF8) // hover / lighter
val ElectricIndigoDim= Color(0xFF3730A3) // pressed / dim

val NeonMint      = Color(0xFF34D399)   // success / accent
val NeonMintDim   = Color(0xFF059669)   // success dim
val NeonAmber     = Color(0xFFFBBF24)   // warning
val NeonRose      = Color(0xFFF43F5E)   // error

val GlassWhite    = Color(0x14FFFFFF)   // glass fill
val GlassBorder   = Color(0x20FFFFFF)   // glass stroke
val GlowIndigo    = Color(0x336366F1)   // glow layer
val GlowMint      = Color(0x2234D399)   // glow layer mint

val TextPrimary   = Color(0xFFF8FAFC)
val TextSecondary = Color(0xFF94A3B8)
val TextTertiary  = Color(0xFF475569)

private val DarkScheme = darkColorScheme(
    primary              = ElectricIndigo,
    onPrimary            = Color(0xFFFFFFFF),
    primaryContainer     = Color(0xFF1E1B4B),
    onPrimaryContainer   = ElectricIndigoLt,
    secondary            = NeonMint,
    onSecondary          = Color(0xFF022C22),
    secondaryContainer   = Color(0xFF064E3B),
    onSecondaryContainer = NeonMint,
    tertiary             = NeonAmber,
    onTertiary           = Color(0xFF1C1200),
    tertiaryContainer    = Color(0xFF3D2A00),
    onTertiaryContainer  = NeonAmber,
    error                = NeonRose,
    onError              = Color(0xFF1A0010),
    errorContainer       = Color(0xFF4C0519),
    onErrorContainer     = Color(0xFFFDA4AF),
    background           = Void,
    onBackground         = TextPrimary,
    surface              = VoidSurface,
    onSurface            = TextPrimary,
    surfaceVariant       = VoidElevated,
    onSurfaceVariant     = TextSecondary,
    outline              = VoidBorder,
    outlineVariant       = Color(0xFF1E1E3F),
    inverseSurface       = TextPrimary,
    inverseOnSurface     = Void,
    inversePrimary       = ElectricIndigoDim,
    surfaceTint          = ElectricIndigo,
    scrim                = Color(0xCC050510),
)

@Composable
fun BitLutExpressiveTheme(content: @Composable () -> Unit) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Void.toArgb()
            window.navigationBarColor = Void.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = false
                isAppearanceLightNavigationBars = false
            }
        }
    }
    MaterialTheme(
        colorScheme = DarkScheme,
        content = content
    )
}
