#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")

SHELL = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
README = ROOT / "README.md"
CONTEXT = ROOT / "CONTEXT.md"
VERIFY = ROOT / "scripts/verify_glass20_gui_self_heal.py"

OLD_TEMP_PATCHES = [
    "scripts/patch_v196_gui_neoglass_activity_only.py",
    "scripts/patch_v196_gui_neoglass_activity_only_recovery.py",
    "scripts/patch_v196_glass20_gui_polish.py",
]

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def cleanup_temp_files() -> None:
    for pattern in [
        "app/src/main/**/*.orig",
        "app/src/main/**/*.bak",
        "app/src/main/**/*.tmp",
    ]:
        for path in ROOT.glob(pattern):
            path.unlink(missing_ok=True)

    for patch in OLD_TEMP_PATCHES:
        Path(patch).unlink(missing_ok=True)

def ensure_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text
    package_match = re.search(r"^package [^\n]+\n", text)
    if not package_match:
        return import_line + "\n" + text
    return text[:package_match.end()] + import_line + "\n" + text[package_match.end():]

def remove_import(text: str, import_line: str) -> str:
    return text.replace(import_line + "\n", "")

def find_matching(text: str, open_index: int, open_char: str = "{", close_char: str = "}") -> int:
    depth = 0
    i = open_index
    in_string = False
    triple = False
    escaped = False
    in_line_comment = False
    in_block_comment = False

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
        elif in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 1
        elif in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif triple and text.startswith('"""', i):
                in_string = False
                triple = False
                i += 2
            elif not triple and ch == '"':
                in_string = False
        else:
            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 1
            elif ch == "/" and nxt == "*":
                in_block_comment = True
                i += 1
            elif text.startswith('"""', i):
                in_string = True
                triple = True
                i += 2
            elif ch == '"':
                in_string = True
            elif ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return i
        i += 1

    raise RuntimeError(f"Matching {close_char} not found")

def remove_function(text: str, name: str) -> str:
    # Include stacked @Composable annotations immediately above the function.
    pattern = re.compile(
        r"(?m)^(?:\s*@Composable\s*\n)*(?:private\s+)?fun\s+"
        + re.escape(name)
        + r"\s*\("
    )

    while True:
        match = pattern.search(text)
        if not match:
            return text

        start = match.start()
        brace = text.find("{", match.end())
        if brace == -1:
            return text[:start]

        end = find_matching(text, brace) + 1
        while end < len(text) and text[end] in " \t\r\n":
            end += 1
        text = text[:start] + text[end:]

def insertion_index_before_composable_function(text: str, function_name: str) -> int:
    # Prefer inserting before @Composable annotation, not between annotation and function.
    annotated = re.search(
        r"(?m)^@Composable\s*\nprivate\s+fun\s+" + re.escape(function_name) + r"\s*\(",
        text,
    )
    if annotated:
        return annotated.start()

    plain = re.search(
        r"(?m)^private\s+fun\s+" + re.escape(function_name) + r"\s*\(",
        text,
    )
    if plain:
        return plain.start()

    return len(text)

def insert_before_function(text: str, function_name: str, block: str) -> str:
    index = insertion_index_before_composable_function(text, function_name)
    if index >= len(text):
        return text.rstrip() + "\n\n" + block.strip() + "\n"
    return text[:index].rstrip() + "\n\n" + block.strip() + "\n\n" + text[index:]

def replace_bottom_bar_lambda(text: str) -> str:
    start = text.find("bottomBar = {")
    if start == -1:
        return text

    brace = text.find("{", start)
    if brace == -1:
        return text

    end = find_matching(text, brace) + 1
    replacement = '''bottomBar = {
            Glass20BottomNavigation(
                selected = selected,
                palette = palette,
                onSelected = { selected = it }
            )
        }'''
    return text[:start] + replacement + text[end:]

def normalize_composable_annotations(text: str) -> str:
    # Collapse repeated annotations.
    text = re.sub(r"(?m)(^@Composable\s*\n){2,}", "@Composable\n", text)

    # If an annotation was stranded before a helper insertion, move it back to SummaryScreen.
    text = re.sub(
        r"(?m)^@Composable\s*\n(?=@Composable\s*\n)",
        "",
        text,
    )

    return text

def patch_shell() -> None:
    shell = read(SHELL)

    shell = remove_import(shell, "import androidx.compose.material3.NavigationBar")
    shell = remove_import(shell, "import androidx.compose.material3.NavigationBarItem")

    for import_line in [
        "import androidx.compose.animation.animateColorAsState",
        "import androidx.compose.animation.core.Spring",
        "import androidx.compose.animation.core.animateFloatAsState",
        "import androidx.compose.animation.core.spring",
        "import androidx.compose.foundation.background",
        "import androidx.compose.foundation.border",
        "import androidx.compose.foundation.clickable",
        "import androidx.compose.foundation.interaction.MutableInteractionSource",
        "import androidx.compose.foundation.layout.Arrangement",
        "import androidx.compose.foundation.layout.Box",
        "import androidx.compose.foundation.layout.Column",
        "import androidx.compose.foundation.layout.ColumnScope",
        "import androidx.compose.foundation.layout.Row",
        "import androidx.compose.foundation.layout.Spacer",
        "import androidx.compose.foundation.layout.defaultMinSize",
        "import androidx.compose.foundation.layout.fillMaxHeight",
        "import androidx.compose.foundation.layout.fillMaxWidth",
        "import androidx.compose.foundation.layout.height",
        "import androidx.compose.foundation.layout.navigationBarsPadding",
        "import androidx.compose.foundation.layout.padding",
        "import androidx.compose.foundation.layout.size",
        "import androidx.compose.foundation.shape.RoundedCornerShape",
        "import androidx.compose.material3.Icon",
        "import androidx.compose.material3.Text",
        "import androidx.compose.runtime.Composable",
        "import androidx.compose.runtime.getValue",
        "import androidx.compose.runtime.remember",
        "import androidx.compose.ui.Alignment",
        "import androidx.compose.ui.Modifier",
        "import androidx.compose.ui.draw.clip",
        "import androidx.compose.ui.draw.drawBehind",
        "import androidx.compose.ui.draw.shadow",
        "import androidx.compose.ui.geometry.Offset",
        "import androidx.compose.ui.graphics.Brush",
        "import androidx.compose.ui.graphics.Color",
        "import androidx.compose.ui.graphics.graphicsLayer",
        "import androidx.compose.ui.text.font.FontWeight",
        "import androidx.compose.ui.text.style.TextOverflow",
        "import androidx.compose.ui.unit.dp",
        "import androidx.compose.ui.unit.sp",
    ]:
        shell = ensure_import(shell, import_line)

    shell = shell.replace("MainTab.entries.forEach", "MainTab.values().forEach")
    shell = replace_bottom_bar_lambda(shell)

    for fn in [
        "NeoGlassBottomBar",
        "NeoGlassNavButton",
        "Glass20BottomNavigation",
        "Glass20NavButton",
        "SoftCard",
        "MetricBarChartCard",
    ]:
        shell = remove_function(shell, fn)

    glass20_nav = '''
@Composable
private fun Glass20BottomNavigation(
    selected: MainTab,
    palette: BitPalette,
    onSelected: (MainTab) -> Unit
) {
    val shellShape = RoundedCornerShape(34.dp)

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
                .background(
                    Brush.linearGradient(
                        listOf(
                            palette.card.copy(alpha = if (palette.dark) 0.76f else 0.74f),
                            palette.card.copy(alpha = if (palette.dark) 0.46f else 0.54f),
                            palette.systemBackground.copy(alpha = if (palette.dark) 0.28f else 0.38f)
                        )
                    )
                )
                .drawBehind {
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = listOf(
                                palette.activity.copy(alpha = 0.22f),
                                Color.Transparent
                            ),
                            center = Offset(size.width * 0.14f, size.height * 0.08f),
                            radius = size.maxDimension * 0.72f
                        )
                    )
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = listOf(
                                palette.mind.copy(alpha = 0.18f),
                                Color.Transparent
                            ),
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
    val shape = RoundedCornerShape(26.dp)

    Box(
        modifier = Modifier
            .size(54.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .pressScale(interactionSource)
            .clip(shape)
            .background(
                if (selected) {
                    Brush.linearGradient(
                        listOf(
                            palette.activity.copy(alpha = 0.98f),
                            palette.mind.copy(alpha = 0.76f),
                            palette.activity.copy(alpha = 0.30f)
                        )
                    )
                } else {
                    Brush.linearGradient(
                        listOf(
                            Color.White.copy(alpha = if (palette.dark) 0.08f else 0.34f),
                            palette.card.copy(alpha = if (palette.dark) 0.05f else 0.18f)
                        )
                    )
                }
            )
            .drawBehind {
                if (selected) {
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = listOf(
                                Color.White.copy(alpha = 0.34f),
                                Color.Transparent
                            ),
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
                    .clip(RoundedCornerShape(99.dp))
                    .background(Color.White.copy(alpha = 0.72f))
            )
        }
    }
}
'''

    soft_card = '''
@Composable
private fun SoftCard(
    palette: BitPalette,
    modifier: Modifier = Modifier.fillMaxWidth(),
    accent: Color = palette.activity,
    hero: Boolean = false,
    tintWithAccent: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = RoundedCornerShape(if (hero) 34.dp else 28.dp)
    val targetCardColor = if (palette.dark) {
        lerp(palette.card, accent, if (hero || tintWithAccent) 0.12f else 0.07f)
    } else {
        lerp(palette.card, accent, if (hero || tintWithAccent) 0.045f else 0.025f)
    }
    val bg by animateColorAsState(targetCardColor, label = "glass20CardBg")

    Column(
        modifier = modifier
            .shadow(
                elevation = if (hero) 36.dp else 24.dp,
                shape = shape,
                ambientColor = Color.Black.copy(alpha = if (palette.dark) 0.32f else 0.06f),
                spotColor = accent.copy(alpha = if (palette.dark) 0.24f else 0.12f)
            )
            .clip(shape)
            .background(
                Brush.linearGradient(
                    listOf(
                        bg.copy(alpha = if (palette.dark) 0.86f else 0.90f),
                        bg.copy(alpha = if (palette.dark) 0.62f else 0.72f),
                        palette.systemBackground.copy(alpha = if (palette.dark) 0.16f else 0.28f)
                    )
                )
            )
            .drawBehind {
                drawRect(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            accent.copy(alpha = if (hero) 0.22f else 0.15f),
                            Color.Transparent
                        ),
                        center = Offset(size.width * 0.88f, size.height * 0.08f),
                        radius = size.maxDimension * 0.62f
                    )
                )
                drawRect(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            palette.mind.copy(alpha = if (hero) 0.14f else 0.08f),
                            Color.Transparent
                        ),
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
'''

    metric_chart = '''
@Composable
private fun MetricBarChartCard(
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
            val maxValue = bars.maxOf { it.value }.takeIf { it > 0.0 } ?: 1.0

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(132.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.Bottom
            ) {
                bars.forEach { bar ->
                    val fraction = (bar.value / maxValue).toFloat().coerceIn(0.05f, 1f)

                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight(),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = formatBarValueShort(bar.value),
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
                                    .clip(RoundedCornerShape(999.dp))
                                    .background(
                                        Brush.verticalGradient(
                                            listOf(
                                                accent.copy(alpha = 0.98f),
                                                accent.copy(alpha = 0.62f)
                                            )
                                        )
                                    )
                                    .drawBehind {
                                        drawRect(
                                            brush = Brush.radialGradient(
                                                colors = listOf(
                                                    Color.White.copy(alpha = 0.28f),
                                                    Color.Transparent
                                                ),
                                                center = Offset(size.width * 0.35f, 0f),
                                                radius = size.maxDimension * 0.80f
                                            )
                                        )
                                    }
                            )
                        }

                        Spacer(Modifier.height(5.dp))

                        Text(
                            text = barDateLabel(bar),
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
'''

    shell = insert_before_function(shell, "SummaryScreen", glass20_nav)
    shell = insert_before_function(shell, "StatusPill", soft_card)
    shell = insert_before_function(shell, "WorkoutSummaryCard", metric_chart)

    # Apply glass tint globally without changing call signatures.
    shell = shell.replace(
        "val showMeshGradient = tintWithAccent && palette.dark",
        "val showMeshGradient = true"
    )
    shell = shell.replace(
        "SoftCard(palette = palette, accent = accent, hero = false) {",
        "SoftCard(palette = palette, accent = accent, hero = false, tintWithAccent = true) {"
    )
    shell = shell.replace(
        "SoftCard(palette = palette, accent = HealthAccent.activity, hero = false) {",
        "SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {"
    )

    shell = normalize_composable_annotations(shell)
    shell = re.sub(r"\n{3,}", "\n\n", shell)

    write(SHELL, shell)

def patch_docs() -> None:
    note = """
## BitLut v1.9.6 Glass 2.0 UI system

The UI uses a premium activity-only glass system across all screens: translucent surfaces, floating glass navigation, soft depth shadows, radial glow, thin highlight borders and bounded charts.

History charts reserve fixed vertical space for values, bars and dates so large step values cannot push bars outside card bounds.
""".strip()

    for doc in [README, CONTEXT]:
        if doc.exists():
            content = read(doc)
            if "## BitLut v1.9.6 Glass 2.0 UI system" not in content:
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

def require(condition, message):
    if not condition:
        errors.append(message)

require("Glass20BottomNavigation(" in shell, "Missing Glass20BottomNavigation")
require("Glass20NavButton(" in shell, "Missing Glass20NavButton")
require("NavigationBarItem(" not in shell, "Material NavigationBarItem must not remain")
require("NavigationBar(" not in shell, "Material NavigationBar must not remain")
require("contentDescription = null" in shell, "Bottom navigation must be icon-only")
require("Brush.linearGradient" in shell and "Brush.radialGradient" in shell, "Glass gradients are missing")
require("drawLine(" in shell, "Glass highlight line is missing")
require("defaultMinSize(minHeight = 6.dp)" in shell, "Metric bars need bounded minimum visible height")
require(".height(84.dp)" in shell, "Metric bar drawing area must be bounded")
require(".height(132.dp)" in shell, "Metric chart row must reserve stable vertical space")
require("TextOverflow.Ellipsis" in shell, "Large chart labels must be clipped safely")
require("val targetCardColor = if (palette.dark)" in shell, "Global SoftCard glass system missing")

duplicate_annotations = re.findall(r"@Composable\s*\n@Composable", shell)
require(not duplicate_annotations, "Duplicate @Composable annotation found")

for fn in [
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
]:
    require(shell.count(f"private fun {fn}(") == 1, f"{fn} must exist exactly once")
    pattern = r"@Composable\s*\nprivate fun " + re.escape(fn) + r"\("
    require(re.search(pattern, shell) is not None, f"{fn} must be @Composable")

if errors:
    print("Glass 2.0 UI self-heal verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Glass 2.0 UI self-heal verification passed.")
''')
    VERIFY.chmod(0o755)

def self_check() -> None:
    shell = read(SHELL)
    errors = []

    if "@Composable\n@Composable" in shell:
        errors.append("Duplicate @Composable remains")

    for forbidden in [
        "NavigationBarItem(",
        "NavigationBar(",
    ]:
        if forbidden in shell:
            errors.append(f"Forbidden Material nav term remains: {forbidden}")

    for required in [
        "Glass20BottomNavigation(",
        "Glass20NavButton(",
        "contentDescription = null",
        "defaultMinSize(minHeight = 6.dp)",
        ".height(84.dp)",
        ".height(132.dp)",
        "val targetCardColor = if (palette.dark)",
    ]:
        if required not in shell:
            errors.append(f"Required GUI token missing: {required}")

    for fn in [
        "Glass20BottomNavigation",
        "Glass20NavButton",
        "SoftCard",
        "MetricBarChartCard",
    ]:
        if shell.count(f"private fun {fn}(") != 1:
            errors.append(f"{fn} must exist exactly once")

    if errors:
        print("Glass 2.0 UI patch failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

def main() -> None:
    cleanup_temp_files()
    patch_shell()
    patch_docs()
    write_verifier()
    self_check()
    print("Applied self-healing Glass 2.0 UI patch.")

if __name__ == "__main__":
    main()
