#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")

SHELL = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
COMPONENT_DIR = ROOT / "app/src/main/java/com/openhealth/sync/ui/components"

GLASS_NAV = COMPONENT_DIR / "GlassNavigation.kt"
GLASS_CARDS = COMPONENT_DIR / "GlassCards.kt"
METRIC_CHARTS = COMPONENT_DIR / "MetricCharts.kt"

README = ROOT / "README.md"
CONTEXT = ROOT / "CONTEXT.md"
VERIFY = ROOT / "scripts/verify_ui_file_split_sprint1.py"

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def expose_shared_dependencies() -> None:
    shell = read(SHELL)

    replacements = [
        (r"(?m)^private\s+enum\s+class\s+MainTab\b", "internal enum class MainTab"),
        (r"(?m)^private\s+data\s+class\s+BitPalette\b", "internal data class BitPalette"),
        (r"(?m)^private\s+class\s+BitPalette\b", "internal class BitPalette"),
        (r"(?m)^private\s+data\s+class\s+MetricBar\b", "internal data class MetricBar"),
        (r"(?m)^private\s+class\s+MetricBar\b", "internal class MetricBar"),
        (r"(?m)^private\s+object\s+HealthAccent\b", "internal object HealthAccent"),
        (r"(?m)^private\s+fun\s+Modifier\.pressScale\s*\(", "internal fun Modifier.pressScale("),
        (r"(?m)^private\s+fun\s+formatBarValueShort\s*\(", "internal fun formatBarValueShort("),
        (r"(?m)^private\s+fun\s+barDateLabel\s*\(", "internal fun barDateLabel("),
    ]

    for pattern, replacement in replacements:
        shell = re.sub(pattern, replacement, shell)

    write(SHELL, shell)

def write_glass_navigation() -> None:
    write(GLASS_NAV, '''package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp

@Composable
internal fun Glass20BottomNavigation(
    selected: MainTab,
    palette: BitPalette,
    onSelected: (MainTab) -> Unit
) {
    val shellShape = remember { RoundedCornerShape(34.dp) }
    val shellBackground = remember(palette.card, palette.systemBackground, palette.dark) {
        Brush.linearGradient(
            listOf(
                palette.card.copy(alpha = if (palette.dark) 0.76f else 0.74f),
                palette.card.copy(alpha = if (palette.dark) 0.46f else 0.54f),
                palette.systemBackground.copy(alpha = if (palette.dark) 0.28f else 0.38f)
            )
        )
    }
    val activityGlowColors = remember(palette.activity) {
        listOf(palette.activity.copy(alpha = 0.22f), Color.Transparent)
    }
    val mindGlowColors = remember(palette.mind) {
        listOf(palette.mind.copy(alpha = 0.18f), Color.Transparent)
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(horizontal = 22.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Box(
            modifier = Modifier
                .shadow(
                    elevation = 40.dp,
                    shape = shellShape,
                    ambientColor = Color.Black.copy(alpha = if (palette.dark) 0.34f else 0.09f),
                    spotColor = palette.activity.copy(alpha = if (palette.dark) 0.32f else 0.14f)
                )
                .clip(shellShape)
                .background(shellBackground)
                .drawBehind {
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = activityGlowColors,
                            center = Offset(size.width * 0.14f, size.height * 0.08f),
                            radius = size.maxDimension * 0.72f
                        )
                    )
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = mindGlowColors,
                            center = Offset(size.width * 0.92f, size.height * 0.92f),
                            radius = size.maxDimension * 0.84f
                        )
                    )
                    drawLine(
                        color = Color.White.copy(alpha = if (palette.dark) 0.18f else 0.46f),
                        start = Offset(size.width * 0.08f, 1.2f),
                        end = Offset(size.width * 0.92f, 1.2f),
                        strokeWidth = 1.2f
                    )
                }
                .border(
                    width = 1.dp,
                    color = palette.stroke.copy(alpha = if (palette.dark) 0.72f else 0.52f),
                    shape = shellShape
                )
                .padding(horizontal = 12.dp, vertical = 8.dp)
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                MainTab.values().forEach { tab ->
                    Glass20NavButton(
                        tab = tab,
                        selected = selected == tab,
                        palette = palette,
                        onClick = { onSelected(tab) }
                    )
                }
            }
        }
    }
}

@Composable
private fun Glass20NavButton(
    tab: MainTab,
    selected: Boolean,
    palette: BitPalette,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val shape = remember { RoundedCornerShape(26.dp) }
    val selectedHighlightShape = remember { RoundedCornerShape(99.dp) }
    val iconTint by animateColorAsState(
        targetValue = if (selected) Color.White else palette.secondaryText.copy(alpha = 0.84f),
        label = "glass20NavIconTint"
    )
    val scale by animateFloatAsState(
        targetValue = if (selected) 1.0f else 0.94f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "glass20NavScale"
    )
    val selectedBrush = remember(palette.activity, palette.mind) {
        Brush.linearGradient(
            listOf(
                palette.activity.copy(alpha = 0.98f),
                palette.mind.copy(alpha = 0.76f),
                palette.activity.copy(alpha = 0.30f)
            )
        )
    }
    val idleBrush = remember(palette.card, palette.dark) {
        Brush.linearGradient(
            listOf(
                Color.White.copy(alpha = if (palette.dark) 0.08f else 0.34f),
                palette.card.copy(alpha = if (palette.dark) 0.05f else 0.18f)
            )
        )
    }
    val selectedGlowColors = remember {
        listOf(Color.White.copy(alpha = 0.34f), Color.Transparent)
    }

    Box(
        modifier = Modifier
            .size(54.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .pressScale(interactionSource)
            .clip(shape)
            .background(if (selected) selectedBrush else idleBrush)
            .drawBehind {
                if (selected) {
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = selectedGlowColors,
                            center = Offset(size.width * 0.34f, size.height * 0.12f),
                            radius = size.maxDimension * 0.70f
                        )
                    )
                }
            }
            .border(
                width = 1.dp,
                color = if (selected) {
                    Color.White.copy(alpha = 0.34f)
                } else {
                    palette.stroke.copy(alpha = if (palette.dark) 0.38f else 0.32f)
                },
                shape = shape
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = tab.icon,
            contentDescription = null,
            tint = iconTint,
            modifier = Modifier.size(if (selected) 27.dp else 24.dp)
        )

        if (selected) {
            Box(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 6.dp)
                    .size(width = 16.dp, height = 3.dp)
                    .clip(selectedHighlightShape)
                    .background(Color.White.copy(alpha = 0.72f))
            )
        }
    }
}
''')

def write_glass_cards() -> None:
    write(GLASS_CARDS, '''package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.unit.dp

@Composable
internal fun SoftCard(
    palette: BitPalette,
    modifier: Modifier = Modifier.fillMaxWidth(),
    accent: Color = palette.activity,
    hero: Boolean = false,
    tintWithAccent: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = remember(hero) { RoundedCornerShape(if (hero) 34.dp else 28.dp) }
    val targetCardColor = if (palette.dark) {
        lerp(palette.card, accent, if (hero || tintWithAccent) 0.12f else 0.07f)
    } else {
        lerp(palette.card, accent, if (hero || tintWithAccent) 0.045f else 0.025f)
    }
    val bg by animateColorAsState(targetCardColor, label = "glass20CardBg")
    val backgroundBrush = remember(bg, palette.systemBackground, palette.dark) {
        Brush.linearGradient(
            listOf(
                bg.copy(alpha = if (palette.dark) 0.86f else 0.90f),
                bg.copy(alpha = if (palette.dark) 0.62f else 0.72f),
                palette.systemBackground.copy(alpha = if (palette.dark) 0.16f else 0.28f)
            )
        )
    }
    val accentGlowColors = remember(accent, hero) {
        listOf(accent.copy(alpha = if (hero) 0.22f else 0.15f), Color.Transparent)
    }
    val mindGlowColors = remember(palette.mind, hero) {
        listOf(palette.mind.copy(alpha = if (hero) 0.14f else 0.08f), Color.Transparent)
    }

    Column(
        modifier = modifier
            .shadow(
                elevation = if (hero) 36.dp else 24.dp,
                shape = shape,
                ambientColor = Color.Black.copy(alpha = if (palette.dark) 0.32f else 0.06f),
                spotColor = accent.copy(alpha = if (palette.dark) 0.24f else 0.12f)
            )
            .clip(shape)
            .background(backgroundBrush)
            .drawBehind {
                drawRect(
                    brush = Brush.radialGradient(
                        colors = accentGlowColors,
                        center = Offset(size.width * 0.88f, size.height * 0.08f),
                        radius = size.maxDimension * 0.62f
                    )
                )
                drawRect(
                    brush = Brush.radialGradient(
                        colors = mindGlowColors,
                        center = Offset(size.width * 0.10f, size.height * 0.98f),
                        radius = size.maxDimension * 0.58f
                    )
                )
                drawLine(
                    color = Color.White.copy(alpha = if (palette.dark) 0.15f else 0.36f),
                    start = Offset(size.width * 0.08f, 1.1f),
                    end = Offset(size.width * 0.92f, 1.1f),
                    strokeWidth = 1.1f
                )
            }
            .border(
                width = 1.dp,
                color = palette.stroke.copy(alpha = if (palette.dark) 0.70f else 0.50f),
                shape = shape
            )
            .padding(if (hero) 24.dp else 16.dp),
        content = content
    )
}
'''.replace("import androidx.compose.material3.ColorScheme\n", ""))

def write_metric_charts() -> None:
    write(METRIC_CHARTS, '''package com.openhealth.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
internal fun MetricBarChartCard(
    palette: BitPalette,
    title: String,
    periodValueLabel: String,
    bars: List<MetricBar>,
    accent: Color,
    valueFormatter: (Double) -> String
) {
    SoftCard(palette = palette, accent = accent, hero = false, tintWithAccent = true) {
        Text(
            text = title,
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 14.sp
        )
        Spacer(Modifier.height(2.dp))
        Text(
            text = periodValueLabel,
            color = palette.secondaryText,
            fontWeight = FontWeight.SemiBold,
            fontSize = 12.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
        Spacer(Modifier.height(14.dp))

        if (bars.isNotEmpty()) {
            val maxValue = remember(bars) {
                bars.maxOf { it.value }.takeIf { it > 0.0 } ?: 1.0
            }
            val barShape = remember { RoundedCornerShape(999.dp) }
            val barBrush = remember(accent) {
                Brush.verticalGradient(
                    listOf(
                        accent.copy(alpha = 0.98f),
                        accent.copy(alpha = 0.62f)
                    )
                )
            }
            val shineColors = remember {
                listOf(Color.White.copy(alpha = 0.28f), Color.Transparent)
            }

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(132.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.Bottom
            ) {
                bars.forEach { bar ->
                    val fraction = (bar.value / maxValue).toFloat().coerceIn(0.05f, 1f)
                    val valueLabel = remember(bar.value) { formatBarValueShort(bar.value) }
                    val dateLabel = remember(bar) { barDateLabel(bar) }

                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight(),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = valueLabel,
                            color = palette.secondaryText,
                            fontWeight = FontWeight.Bold,
                            fontSize = 8.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier
                                .height(18.dp)
                                .fillMaxWidth()
                        )

                        Box(
                            modifier = Modifier
                                .height(84.dp)
                                .fillMaxWidth(),
                            contentAlignment = Alignment.BottomCenter
                        ) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .fillMaxHeight(fraction)
                                    .defaultMinSize(minHeight = 6.dp)
                                    .clip(barShape)
                                    .background(barBrush)
                                    .drawBehind {
                                        drawRect(
                                            brush = Brush.radialGradient(
                                                colors = shineColors,
                                                center = Offset(size.width * 0.35f, 0f),
                                                radius = size.maxDimension * 0.80f
                                            )
                                        )
                                    }
                            )
                        }

                        Spacer(Modifier.height(5.dp))

                        Text(
                            text = dateLabel,
                            color = palette.secondaryText,
                            fontWeight = FontWeight.Bold,
                            fontSize = 8.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier
                                .height(18.dp)
                                .fillMaxWidth()
                        )
                    }
                }
            }
        }
    }
}
''')

def patch_docs() -> None:
    note = """
## v1.9.6 UI File Split Sprint 1

Implemented:

- Restored missing Glass 2.0 component definitions as extracted component files.
- Added `GlassNavigation.kt` for `Glass20BottomNavigation`.
- Added `GlassCards.kt` for `SoftCard`.
- Added `MetricCharts.kt` for `MetricBarChartCard`.
- Kept `FinalBitLutShell.kt` as the screen coordinator.
- Kept sync behavior, Health Connect contract and Huawei scope unchanged.
""".strip()

    for doc in [README, CONTEXT]:
        content = read(doc)
        if "## v1.9.6 UI File Split Sprint 1" not in content:
            content = content.rstrip() + "\n\n" + note + "\n"
        write(doc, content)

def write_verifier() -> None:
    write(VERIFY, r'''#!/usr/bin/env python3
from pathlib import Path
import re
import sys

errors = []

def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
nav = read("app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt")
cards = read("app/src/main/java/com/openhealth/sync/ui/components/GlassCards.kt")
charts = read("app/src/main/java/com/openhealth/sync/ui/components/MetricCharts.kt")
readme = read("README.md")
context = read("CONTEXT.md")

def require(condition, message):
    if not condition:
        errors.append(message)

require("Glass20BottomNavigation(" in shell, "Shell must still call Glass20BottomNavigation")
require("SoftCard(" in shell, "Shell must still call SoftCard")
require("MetricBarChartCard(" in shell, "Shell must still call MetricBarChartCard")

require("internal fun Glass20BottomNavigation(" in nav, "GlassNavigation.kt must define Glass20BottomNavigation")
require("private fun Glass20NavButton(" in nav, "GlassNavigation.kt must define private Glass20NavButton")
require("internal fun SoftCard(" in cards, "GlassCards.kt must define SoftCard")
require("internal fun MetricBarChartCard(" in charts, "MetricCharts.kt must define MetricBarChartCard")

require("internal enum class MainTab" in shell or "enum class MainTab" in shell, "MainTab must be visible")
require("internal fun Modifier.pressScale" in shell or "fun Modifier.pressScale" in shell, "pressScale must be visible")
require("internal fun formatBarValueShort(" in shell or "fun formatBarValueShort(" in shell, "formatBarValueShort must be visible")
require("internal fun barDateLabel(" in shell or "fun barDateLabel(" in shell, "barDateLabel must be visible")

for text_name, text in [
    ("GlassNavigation.kt", nav),
    ("GlassCards.kt", cards),
    ("MetricCharts.kt", charts),
]:
    require("package com.openhealth.sync" in text, f"{text_name} must stay in root package")
    require("@Composable" in text, f"{text_name} must contain composables")

require("## v1.9.6 UI File Split Sprint 1" in readme, "README missing UI split note")
require("## v1.9.6 UI File Split Sprint 1" in context, "CONTEXT missing UI split note")

if errors:
    print("UI File Split Sprint 1 verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("UI File Split Sprint 1 verification passed.")
''')
    VERIFY.chmod(0o755)

def self_check() -> None:
    expose_shared_dependencies()
    write_glass_navigation()
    write_glass_cards()
    write_metric_charts()
    patch_docs()
    write_verifier()

    shell = read(SHELL)
    nav = read(GLASS_NAV)
    cards = read(GLASS_CARDS)
    charts = read(METRIC_CHARTS)

    errors = []

    for token, text, path in [
        ("internal fun Glass20BottomNavigation(", nav, GLASS_NAV),
        ("internal fun SoftCard(", cards, GLASS_CARDS),
        ("internal fun MetricBarChartCard(", charts, METRIC_CHARTS),
    ]:
        if token not in text:
            errors.append(f"{path} missing {token}")

    for token in [
        "Glass20BottomNavigation(",
        "SoftCard(",
        "MetricBarChartCard(",
    ]:
        if token not in shell:
            errors.append(f"Shell no longer calls {token}")

    if errors:
        print("UI component restore failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

    print("Restored extracted Glass component files.")

if __name__ == "__main__":
    self_check()
