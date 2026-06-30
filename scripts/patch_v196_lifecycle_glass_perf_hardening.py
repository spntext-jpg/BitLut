#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")

APP_BUILD = ROOT / "app/build.gradle.kts"
MAIN = ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
SHELL = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
APP_LOGGER = ROOT / "app/src/main/java/com/openhealth/sync/util/AppLogger.kt"
README = ROOT / "README.md"
CONTEXT = ROOT / "CONTEXT.md"
VERIFY = ROOT / "scripts/verify_lifecycle_glass_perf_hardening.py"

OLD_TEMP_PATCHES = [
    "scripts/patch_v196_glass20_gui_polish.py",
    "scripts/patch_v196_gui_neoglass_activity_only.py",
    "scripts/patch_v196_gui_neoglass_activity_only_recovery.py",
]

CORE_COMPOSABLES = [
    "SummaryScreen",
    "HistoryScreen",
    "SettingsScreen",
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
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
    pattern = re.compile(
        r"(?m)^(?:\s*@Composable\s*\n)*(?:private\s+)?fun\s+"
        + re.escape(name)
        + r"\s*\("
    )

    while True:
        match = pattern.search(text)
        if not match:
            return text

        brace = text.find("{", match.end())
        if brace == -1:
            return text[:match.start()]

        end = find_matching(text, brace) + 1
        while end < len(text) and text[end] in " \t\r\n":
            end += 1
        text = text[:match.start()] + text[end:]

def insertion_index_before_function(text: str, function_name: str) -> int:
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
    index = insertion_index_before_function(text, function_name)
    if index >= len(text):
        return text.rstrip() + "\n\n" + block.strip() + "\n"
    return text[:index].rstrip() + "\n\n" + block.strip() + "\n\n" + text[index:]

def ensure_composable(text: str, fn: str) -> str:
    if f"private fun {fn}(" not in text:
        return text

    text = re.sub(
        rf"(?m)(?:^@Composable\s*\n)+(?=private fun {re.escape(fn)}\()",
        "@Composable\n",
        text,
    )
    text = re.sub(
        rf"(?m)^(private fun {re.escape(fn)}\()",
        r"@Composable\n\1",
        text,
    )
    return text

def normalize_composable_annotations(text: str) -> str:
    return re.sub(r"(?m)(^@Composable\s*\n){2,}", "@Composable\n", text)

def patch_build_gradle() -> None:
    if not APP_BUILD.exists():
        return

    build = read(APP_BUILD)

    if "androidx.lifecycle:lifecycle-runtime-compose" in build:
        write(APP_BUILD, build)
        return

    dependency = '    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")\n'

    # Prefer placing near other lifecycle deps.
    lifecycle_match = re.search(r'(?m)^    implementation\("androidx\.lifecycle:[^"]+"\)\s*$', build)
    if lifecycle_match:
        insert_at = lifecycle_match.end()
        build = build[:insert_at] + "\n" + dependency.rstrip() + build[insert_at:]
    else:
        deps = build.find("dependencies {")
        if deps == -1:
            raise RuntimeError("app/build.gradle.kts has no dependencies block")
        brace_end = build.find("\n", deps)
        build = build[:brace_end + 1] + dependency + build[brace_end + 1:]

    write(APP_BUILD, build)

def patch_main_activity() -> None:
    main = read(MAIN)

    main = remove_import(main, "import androidx.compose.runtime.collectAsState")
    main = ensure_import(main, "import androidx.lifecycle.compose.collectAsStateWithLifecycle")

    # Minimal, low-risk migration: keep existing provider API but collect lifecycle-aware.
    main = main.replace(".collectAsState().value", ".collectAsStateWithLifecycle().value")

    # If code uses delegated state, upgrade that too.
    main = main.replace(".collectAsState()", ".collectAsStateWithLifecycle()")

    write(MAIN, main)

def patch_shell() -> None:
    shell = read(SHELL)

    for import_line in [
        "import androidx.compose.runtime.remember",
        "import androidx.compose.animation.animateColorAsState",
        "import androidx.compose.animation.core.Spring",
        "import androidx.compose.animation.core.animateFloatAsState",
        "import androidx.compose.animation.core.spring",
        "import androidx.compose.ui.graphics.graphicsLayer",
        "import androidx.compose.foundation.layout.defaultMinSize",
        "import androidx.compose.ui.text.style.TextOverflow",
    ]:
        shell = ensure_import(shell, import_line)

    for fn in CORE_COMPOSABLES:
        shell = ensure_composable(shell, fn)

    shell = normalize_composable_annotations(shell)

    # Remove existing generated Glass 2.0 helpers and replace with allocation-aware versions.
    for fn in [
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
                    val dateLabel = remember(bar.startDate, bar.endDate) { barDateLabel(bar) }

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
'''

    shell = insert_before_function(shell, "SummaryScreen", glass20_nav)
    shell = insert_before_function(shell, "StatusPill", soft_card)
    shell = insert_before_function(shell, "WorkoutSummaryCard", metric_chart)

    # Global Glass 2.0 card adoption.
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

    for fn in CORE_COMPOSABLES:
        shell = ensure_composable(shell, fn)

    shell = normalize_composable_annotations(shell)
    shell = re.sub(r"\n{3,}", "\n\n", shell)

    write(SHELL, shell)

def patch_app_logger() -> None:
    if not APP_LOGGER.exists():
        return

    logger = read(APP_LOGGER)

    # Conservative memory hardening. Avoid broad rewrites if current logger differs.
    if "MAX_LOG_ENTRIES" not in logger:
        logger = logger.replace(
            "object AppLogger {",
            "object AppLogger {\n    private const val MAX_LOG_ENTRIES = 120\n    private const val MAX_LOG_MESSAGE_LENGTH = 700\n",
            1,
        )

    # Common patterns: takeLast(160), take(160), 160 entries.
    logger = logger.replace("takeLast(160)", "takeLast(MAX_LOG_ENTRIES)")
    logger = logger.replace("take(160)", "take(MAX_LOG_ENTRIES)")
    logger = logger.replace("160 entries", "120 entries")

    # Add a local sanitizer if it is not present and a log append method exists.
    if "private fun sanitizeLogMessage(" not in logger:
        insertion = '''
    private fun sanitizeLogMessage(message: String): String =
        if (message.length <= MAX_LOG_MESSAGE_LENGTH) {
            message
        } else {
            message.take(MAX_LOG_MESSAGE_LENGTH) + "…"
        }

'''
        first_fun = logger.find("\n    fun ")
        if first_fun != -1:
            logger = logger[:first_fun] + "\n" + insertion + logger[first_fun:]
        else:
            logger = logger.replace("object AppLogger {", "object AppLogger {\n" + insertion, 1)

    # Only apply safe textual sanitization if obvious variables exist.
    logger = logger.replace("val line = message", "val line = sanitizeLogMessage(message)")
    logger = logger.replace("val entry = message", "val entry = sanitizeLogMessage(message)")

    write(APP_LOGGER, logger)

def patch_docs() -> None:
    note = """
## v1.9.6 lifecycle and Glass performance hardening

Implemented after deep code review:

- Compose state collection in `MainActivity` is lifecycle-aware via `collectAsStateWithLifecycle`.
- Glass 2.0 UI helpers cache stable shapes, gradient color lists and static brushes with `remember(...)`.
- History chart bars are bounded with fixed value/bar/date regions to avoid overflow on large step values.
- App logger has conservative memory guards for retained in-app logs.

Deferred to a separate architecture sprint:

- Splitting `FinalBitLutShell.kt` into feature-level UI files.
- Moving WorkManager orchestration out of `MainActivity`.
- Introducing interfaces for `GoogleHealthManager` / `HuaweiHealthManager`.
- Gradle Version Catalog migration.
""".strip()

    for doc in [README, CONTEXT]:
        if doc.exists():
            content = read(doc)
            if "## v1.9.6 lifecycle and Glass performance hardening" not in content:
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

build = read("app/build.gradle.kts")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
logger = read("app/src/main/java/com/openhealth/sync/util/AppLogger.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("androidx.lifecycle:lifecycle-runtime-compose" in build, "Missing lifecycle-runtime-compose dependency")
require("collectAsStateWithLifecycle" in main, "MainActivity must use collectAsStateWithLifecycle")
require("collectAsState().value" not in main, "MainActivity still uses collectAsState().value")
require("import androidx.lifecycle.compose.collectAsStateWithLifecycle" in main, "Missing lifecycle compose import")

for fn in [
    "SummaryScreen",
    "HistoryScreen",
    "SettingsScreen",
    "Glass20BottomNavigation",
    "Glass20NavButton",
    "SoftCard",
    "MetricBarChartCard",
]:
    if f"private fun {fn}(" in shell:
        require(
            re.search(r"@Composable\s*\nprivate fun " + re.escape(fn) + r"\(", shell) is not None,
            f"{fn} must be @Composable"
        )

require("@Composable\n@Composable" not in shell, "Duplicate @Composable annotation found")
require("NavigationBarItem(" not in shell, "Material NavigationBarItem must not remain")
require("NavigationBar(" not in shell, "Material NavigationBar must not remain")

for token in [
    "val shellShape = remember",
    "val selectedBrush = remember",
    "val backgroundBrush = remember",
    "val accentGlowColors = remember",
    "val maxValue = remember(bars)",
    "defaultMinSize(minHeight = 6.dp)",
    ".height(84.dp)",
    ".height(132.dp)",
    "TextOverflow.Ellipsis",
]:
    require(token in shell, f"Missing Compose performance/bounded chart token: {token}")

if "object AppLogger" in logger:
    require("MAX_LOG_ENTRIES" in logger, "AppLogger should define MAX_LOG_ENTRIES")
    require("MAX_LOG_MESSAGE_LENGTH" in logger, "AppLogger should define MAX_LOG_MESSAGE_LENGTH")

if errors:
    print("Lifecycle and Glass performance verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Lifecycle and Glass performance verification passed.")
''')
    VERIFY.chmod(0o755)

def self_check() -> None:
    build = read(APP_BUILD) if APP_BUILD.exists() else ""
    main = read(MAIN)
    shell = read(SHELL)

    errors = []

    if "androidx.lifecycle:lifecycle-runtime-compose" not in build:
        errors.append("Missing lifecycle-runtime-compose dependency")
    if "collectAsStateWithLifecycle" not in main:
        errors.append("MainActivity missing collectAsStateWithLifecycle")
    if "collectAsState().value" in main:
        errors.append("MainActivity still has collectAsState().value")

    for fn in CORE_COMPOSABLES:
        if f"private fun {fn}(" in shell:
            if re.search(r"@Composable\s*\nprivate fun " + re.escape(fn) + r"\(", shell) is None:
                errors.append(f"{fn} missing @Composable")

    for token in [
        "val shellShape = remember",
        "val selectedBrush = remember",
        "val backgroundBrush = remember",
        "val maxValue = remember(bars)",
        "defaultMinSize(minHeight = 6.dp)",
        ".height(84.dp)",
        ".height(132.dp)",
    ]:
        if token not in shell:
            errors.append(f"Missing UI performance token: {token}")

    if errors:
        print("Lifecycle/Glass hardening patch failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

def main() -> None:
    cleanup_temp_files()
    patch_build_gradle()
    patch_main_activity()
    patch_shell()
    patch_app_logger()
    patch_docs()
    write_verifier()
    self_check()
    print("Applied lifecycle-aware Compose and Glass performance hardening patch.")

if __name__ == "__main__":
    main()
