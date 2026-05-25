#!/usr/bin/env bash
set -euo pipefail

log() { printf "\n==> %s\n" "$*"; }

if [ ! -f "settings.gradle.kts" ] || [ ! -d "app/src/main" ]; then
  echo "ERROR: run this script from BitLut repository root." >&2
  exit 1
fi

log "Bump version to 1.0.3 / versionCode 4"
python3 - <<'PY'
from pathlib import Path
import re
p = Path("app/build.gradle.kts")
s = p.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 4', s)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.0.3"', s)
p.write_text(s)
PY

log "Add expressive Material 3 theme"
mkdir -p app/src/main/java/com/openhealth/sync/ui/theme
cat > app/src/main/java/com/openhealth/sync/ui/theme/BitLutExpressiveTheme.kt <<'KOTLIN'
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
KOTLIN

log "Switch MainActivity from raw MaterialTheme to BitLutExpressiveTheme and remove broken helper"
python3 - <<'PY'
from pathlib import Path
p = Path("app/src/main/java/com/openhealth/sync/MainActivity.kt")
s = p.read_text()

if "com.openhealth.sync.ui.theme.BitLutExpressiveTheme" not in s:
    lines = s.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import "):
            insert_at = i + 1
    lines.insert(insert_at, "import com.openhealth.sync.ui.theme.BitLutExpressiveTheme")
    s = "\n".join(lines) + "\n"

# Replace the simple top-level MaterialTheme wrapper only.
s = s.replace("MaterialTheme {", "BitLutExpressiveTheme {", 1)

# Remove previously broken local helper if it still exists.
for marker in ["private fun ensureHmsCoreOrOpenInstall()", "fun ensureHmsCoreOrOpenInstall()"]:
    while marker in s:
        start = s.find(marker)
        brace = s.find("{", start)
        if brace == -1:
            break
        depth = 0
        end = brace
        for i in range(brace, len(s)):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        s = s[:start] + s[end:]

# Keep Huawei action safe but avoid relying on removed local helper.
s = s.replace("if (ensureHmsCoreOrOpenInstall()) viewModel.authorizeHuawei()", "viewModel.authorizeHuawei()")
s = s.replace("if (ensureHmsCoreOrOpenInstall()) viewModel.requestHuaweiAuthorization()", "viewModel.requestHuaweiAuthorization()")
s = s.replace("if (ensureHmsCoreOrOpenInstall()) viewModel.connectHuawei()", "viewModel.connectHuawei()")

p.write_text(s)
PY

log "Fix known HuaweiHealthManager missingMessage compile issue"
python3 - <<'PY'
from pathlib import Path
p = Path("app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt")
if p.exists():
    s = p.read_text()
    s = s.replace("HmsCoreHelper.missingMessage()", "HmsCoreHelper.missingMessage")
    s = s.replace("missingMessage()", "missingMessage")
    p.write_text(s)
PY

log "Add expressive README note if README exists"
python3 - <<'PY'
from pathlib import Path
p = Path("README.md")
if p.exists():
    s = p.read_text()
    block = """
## Дизайн

BitLut использует визуальный язык **Material 3 Expressive**: мягкие тональные поверхности, живой синий бренд-акцент, фиолетовый второй акцент для умных сценариев, спокойные карточки и чистую адаптивную сетку. Интерфейс задуман как дружелюбный health-bridge, а не как техническая панель администратора.
"""
    if "## Дизайн" not in s:
        # Put after intro badges/first separator when possible.
        marker = "---"
        pos = s.find(marker)
        if pos != -1:
            pos2 = s.find("\n", pos)
            s = s[:pos2+1] + block + s[pos2+1:]
        else:
            s += "\n" + block
    p.write_text(s)
PY

log "No local build was run"
echo "Review changes:"
echo "git diff -- app/build.gradle.kts app/src/main/java/com/openhealth/sync/ui/theme/BitLutExpressiveTheme.kt app/src/main/java/com/openhealth/sync/MainActivity.kt app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt README.md"
echo
echo "Commit and push:"
echo "git add -A && git commit -m 'style: add Material 3 Expressive UI for 1.0.3' && git push origin main"
echo
echo "Run Actions manually:"
echo "gh workflow run build.yml -f version_name=1.0.3 -f version_code=4"
