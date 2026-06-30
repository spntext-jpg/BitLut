#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess

ROOT = Path(".")

SHELL = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
PREFS = ROOT / "app/src/main/java/com/openhealth/sync/config/WidgetVisibilityPrefs.kt"
MAIN = ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
README = ROOT / "README.md"
CONTEXT = ROOT / "CONTEXT.md"
VERIFY = ROOT / "scripts/verify_gui_neoglass_activity_only.py"

GUI_FILES = [
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "app/src/main/java/com/openhealth/sync/config/WidgetVisibilityPrefs.kt",
    "app/src/main/java/com/openhealth/sync/MainActivity.kt",
]

OLD_TEMP_PATCHES = [
    "scripts/patch_v196_gui_neoglass_activity_only.py",
    "scripts/patch_v196_apply_huawei_scope_fix.py",
    "scripts/patch_v196_remove_optional_health_metrics.py",
    "scripts/patch_v196_recover_strict_activity_only.py",
    "scripts/patch_v196_strict_huawei_scope.py",
    "scripts/patch_v196_verify_health_coverage.py",
    "scripts/patch_v196_fix_optional_dashboard_false_positive.py",
]

FORBIDDEN_UI = [
    "DashboardWidget.HEART_RATE",
    "DashboardWidget.SLEEP",
    "DashboardWidget.STRESS",
    "DashboardWidget.SPO2",
    "HeartRateWidgetCard(",
    "SleepWidgetCard(",
    "widget_toggle_heart",
    "widget_toggle_sleep",
    "widget_toggle_stress",
    "widget_toggle_spo2",
    "NavigationBarItem(",
]

def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def cleanup_temp_files():
    for pattern in [
        "app/src/main/**/*.orig",
        "app/src/main/**/*.bak",
        "app/src/main/**/*.tmp",
    ]:
        for path in ROOT.glob(pattern):
            path.unlink(missing_ok=True)

    for path in OLD_TEMP_PATCHES:
        Path(path).unlink(missing_ok=True)

def restore_gui_files_from_head():
    # Recovery from the failed GUI patch only. This does not touch Health Connect sync files.
    result = run(["git", "checkout", "--"] + GUI_FILES)
    if result.returncode != 0:
        print("Warning: could not restore GUI files from HEAD.")
        print(result.stderr.strip())

def ensure_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text
    package_match = re.search(r"^package [^\n]+\n", text)
    if not package_match:
        return import_line + "\n" + text
    insert_at = package_match.end()
    return text[:insert_at] + import_line + "\n" + text[insert_at:]

def remove_import(text: str, import_line: str) -> str:
    return text.replace(import_line + "\n", "")

def find_matching(text: str, open_index: int, open_char: str, close_char: str) -> int:
    depth = 0
    i = open_index
    in_string = False
    escaped = False
    in_line_comment = False
    in_block_comment = False
    triple = False

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
    pattern = re.compile(r"(?m)^(?:@Composable\s*\n)?(?:private\s+)?fun\s+" + re.escape(name) + r"\s*\(")
    while True:
        m = pattern.search(text)
        if not m:
            return text
        brace = text.find("{", m.end())
        if brace == -1:
            return text[:m.start()]
        end = find_matching(text, brace, "{", "}") + 1
        while end < len(text) and text[end] in " \t\r\n":
            end += 1
        text = text[:m.start()] + text[end:]

def replace_bottom_bar(text: str) -> str:
    start = text.find("bottomBar = {")
    if start == -1:
        return text
    brace = text.find("{", start)
    end = find_matching(text, brace, "{", "}") + 1
    replacement = '''bottomBar = {
            NeoGlassBottomBar(
                selected = selected,
                palette = palette,
                onSelected = { selected = it }
            )
        }'''
    return text[:start] + replacement + text[end:]

def patch_summary_screen(text: str) -> str:
    # Remove top refresh action from MinimalTopBar.
    text = re.sub(
        r'''item\s*\{\s*
\s*MinimalTopBar\(
\s*palette = palette,
\s*title = stringResource\(R\.string\.summary_short_title\),
\s*action = stringResource\(R\.string\.refresh_status\),
\s*onAction = onRefresh
\s*\)
\s*\}''',
        '''item {
            MinimalHeader(
                palette = palette,
                title = stringResource(R.string.summary_short_title)
            )
        }''',
        text,
        flags=re.M,
    )

    # Remove unsupported dashboard card blocks and dashboard refresh button.
    text = re.sub(
        r'''\n\s*if \(state\.isWidgetVisible\(DashboardWidget\.HEART_RATE\)\) \{\s*
\s*item \{\s*
\s*HeartRateWidgetCard\(
\s*palette = palette,
\s*state = state
\s*\)
\s*\}
\s*\}''',
        "",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'''\n\s*if \(state\.isWidgetVisible\(DashboardWidget\.SLEEP\)\) \{\s*
\s*item \{\s*
\s*SleepWidgetCard\(
\s*palette = palette,
\s*state = state
\s*\)
\s*\}
\s*\}''',
        "",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'''\n\s*item \{\s*
\s*PrimaryButton\(
\s*text = stringResource\(R\.string\.refresh_status\),
\s*accent = HealthAccent\.activity,
\s*onClick = onRefresh
\s*\)
\s*\}''',
        "",
        text,
        flags=re.M,
    )
    return text

def patch_history_screen(text: str) -> str:
    text = re.sub(r"\n\s*val heartAvg = state\.heartRateBars\.map \{ it\.value \}\.filter \{ it > 0\.0 \}\.safeAverage\(\)", "", text)
    text = re.sub(r"\n\s*val sleepTotal = state\.sleepBars\.sumOf \{ it\.value \}", "", text)

    text = re.sub(
        r'''\n\s*if \(state\.isWidgetVisible\(DashboardWidget\.HEART_RATE\)\) \{\s*
\s*item \{\s*
\s*MetricBarChartCard\(
[\s\S]*?
\s*valueFormatter = \{ it\.toLong\(\)\.toString\(\) \}
\s*\)
\s*\}
\s*\}''',
        "",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'''\n\s*if \(state\.isWidgetVisible\(DashboardWidget\.SLEEP\)\) \{\s*
\s*item \{\s*
\s*MetricBarChartCard\(
[\s\S]*?
\s*valueFormatter = \{ formatOneDecimal\(it\) \}
\s*\)
\s*\}
\s*\}''',
        "",
        text,
        flags=re.M,
    )
    return text

def patch_dashboard_widget_grid(text: str) -> str:
    text = re.sub(
        r'''\n\s*if \(state\.isWidgetVisible\(DashboardWidget\.STRESS\)\)
\s*Triple\(stringResource\(R\.string\.stress_title\), state\.stressScore\?\.toString\(\) \?: stringResource\(R\.string\.no_data_short\), stringResource\(R\.string\.score_100_unit\)\) to HealthAccent\.mind else null,''',
        "",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'''\n\s*if \(state\.isWidgetVisible\(DashboardWidget\.SPO2\)\)
\s*Triple\(stringResource\(R\.string\.spo2_title\), state\.spo2Percent\?\.let \{ formatOneDecimal\(it\) \} \?: stringResource\(R\.string\.no_data_short\), "%"\) to HealthAccent\.mind else null''',
        "",
        text,
        flags=re.M,
    )
    # If CALORIES/WORKOUT/ACTIVE_HOURS are now last items, remove trailing comma before closing list.
    text = re.sub(r",\s*\n\s*\)", "\n    )", text)
    return text

def patch_settings_toggles(text: str) -> str:
    for widget, label, accent in [
        ("HEART_RATE", "widget_toggle_heart", "HealthAccent.heart"),
        ("SLEEP", "widget_toggle_sleep", "HealthAccent.sleep"),
        ("STRESS", "widget_toggle_stress", "HealthAccent.mind"),
        ("SPO2", "widget_toggle_spo2", "HealthAccent.mind"),
    ]:
        pattern = rf'''\n\s*WidgetVisibilityRow\(
\s*palette = palette,
\s*label = stringResource\(R\.string\.{label}\),
\s*accent = {re.escape(accent)},
\s*checked = dashboardState\.isWidgetVisible\(DashboardWidget\.{widget}\),
\s*onCheckedChange = \{{ onWidgetVisibilityChanged\(DashboardWidget\.{widget}, it\) \}}
\s*\)'''
        text = re.sub(pattern, "", text, flags=re.M)
    return text

def patch_prefs():
    write(PREFS, '''package com.openhealth.sync.config

import android.content.Context
import android.content.SharedPreferences
import com.openhealth.sync.data.remote.HuaweiConfig

/**
 * Activity-only dashboard widget visibility for BitLut v1.9.6.
 *
 * Unsupported optional metrics are intentionally absent:
 * pulse, sleep, stress, SpO2, HRV and Activity Intensity.
 */
enum class DashboardWidget(val prefKey: String) {
    STEPS("widget_visible_steps"),
    CALORIES("widget_visible_calories"),
    WORKOUT_MINUTES("widget_visible_workout_minutes"),
    ACTIVE_HOURS("widget_visible_active_hours"),
    WORKOUTS("widget_visible_workouts")
}

class WidgetVisibilityPrefs(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(
        HuaweiConfig.PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun isVisible(widget: DashboardWidget): Boolean =
        prefs.getBoolean(widget.prefKey, true)

    fun setVisible(widget: DashboardWidget, visible: Boolean) {
        prefs.edit().putBoolean(widget.prefKey, visible).apply()
    }

    fun snapshot(): Map<DashboardWidget, Boolean> =
        DashboardWidget.entries.associateWith { isVisible(it) }
}
''')

def patch_main():
    main = read(MAIN)

    if "private fun refreshUiStatusOnLaunch()" not in main:
        method = '''
    private fun refreshUiStatusOnLaunch() {
        syncViewModel.refreshStatuses()
        dashboardViewModel.refresh()
    }
'''
        anchor = "\n    private fun startHuaweiAuthorization()"
        if anchor in main:
            main = main.replace(anchor, "\n" + method + anchor, 1)
        else:
            main = main.replace("\n}", "\n" + method + "\n}", 1)

    if "setupPeriodicSync()\n        refreshUiStatusOnLaunch()" not in main:
        main = main.replace(
            "setupPeriodicSync()\n        setContent",
            "setupPeriodicSync()\n        refreshUiStatusOnLaunch()\n        setContent",
            1,
        )

    write(MAIN, main)

def patch_shell():
    shell = read(SHELL)

    shell = remove_import(shell, "import androidx.compose.material3.NavigationBar")
    shell = remove_import(shell, "import androidx.compose.material3.NavigationBarItem")
    shell = ensure_import(shell, "import androidx.compose.foundation.layout.navigationBarsPadding")

    shell = shell.replace("MainTab.values().forEach", "MainTab.entries.forEach")
    shell = replace_bottom_bar(shell)

    # Remove old/new nav helpers before appending final versions.
    shell = remove_function(shell, "NeoGlassBottomBar")
    shell = remove_function(shell, "NeoGlassNavButton")

    neo_helpers = '''
@Composable
private fun NeoGlassBottomBar(
    selected: MainTab,
    palette: BitPalette,
    onSelected: (MainTab) -> Unit
) {
    val shape = RoundedCornerShape(36.dp)

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(horizontal = 24.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(
            modifier = Modifier
                .shadow(
                    elevation = 34.dp,
                    shape = shape,
                    ambientColor = palette.activity.copy(alpha = if (palette.dark) 0.34f else 0.18f),
                    spotColor = palette.mind.copy(alpha = if (palette.dark) 0.28f else 0.14f)
                )
                .clip(shape)
                .background(
                    Brush.linearGradient(
                        listOf(
                            palette.card.copy(alpha = if (palette.dark) 0.78f else 0.86f),
                            palette.card.copy(alpha = if (palette.dark) 0.44f else 0.62f)
                        )
                    )
                )
                .drawBehind {
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = listOf(palette.activity.copy(alpha = 0.18f), Color.Transparent),
                            center = Offset(size.width * 0.16f, size.height * 0.0f),
                            radius = size.maxDimension * 0.76f
                        )
                    )
                    drawRect(
                        brush = Brush.radialGradient(
                            colors = listOf(palette.mind.copy(alpha = 0.18f), Color.Transparent),
                            center = Offset(size.width * 0.94f, size.height * 0.86f),
                            radius = size.maxDimension * 0.84f
                        )
                    )
                }
                .border(1.dp, palette.stroke.copy(alpha = if (palette.dark) 0.62f else 0.42f), shape)
                .padding(horizontal = 14.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically
        ) {
            MainTab.entries.forEach { tab ->
                NeoGlassNavButton(
                    tab = tab,
                    selected = selected == tab,
                    palette = palette,
                    onClick = { onSelected(tab) }
                )
            }
        }
    }
}

@Composable
private fun NeoGlassNavButton(
    tab: MainTab,
    selected: Boolean,
    palette: BitPalette,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val tint by animateColorAsState(
        targetValue = if (selected) Color.White else palette.secondaryText,
        label = "navIconTint"
    )
    val brush = if (selected) {
        Brush.radialGradient(
            listOf(
                palette.activity.copy(alpha = 0.96f),
                palette.mind.copy(alpha = 0.56f),
                palette.activity.copy(alpha = 0.16f)
            )
        )
    } else {
        Brush.linearGradient(
            listOf(
                palette.card.copy(alpha = 0.18f),
                Color.Transparent
            )
        )
    }

    Box(
        modifier = Modifier
            .size(56.dp)
            .pressScale(interactionSource)
            .clip(RoundedCornerShape(28.dp))
            .background(brush)
            .border(
                1.dp,
                if (selected) Color.White.copy(alpha = 0.28f) else palette.stroke.copy(alpha = 0.32f),
                RoundedCornerShape(28.dp)
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
            tint = tint,
            modifier = Modifier.size(if (selected) 27.dp else 24.dp)
        )
    }
}
'''

    marker = "\n@Composable\nprivate fun SummaryScreen"
    if marker in shell:
        shell = shell.replace(marker, "\n" + neo_helpers + marker, 1)
    else:
        shell += "\n" + neo_helpers

    shell = patch_summary_screen(shell)
    shell = patch_history_screen(shell)
    shell = patch_dashboard_widget_grid(shell)
    shell = patch_settings_toggles(shell)

    shell = remove_function(shell, "HeartRateWidgetCard")
    shell = remove_function(shell, "SleepWidgetCard")
    shell = remove_function(shell, "formatSleepDuration")
    shell = re.sub(r"\nprivate const val SLEEP_GOAL_HOURS = 8\.0\s*", "\n", shell)

    shell = shell.replace("val showMeshGradient = tintWithAccent && palette.dark", "val showMeshGradient = true")

    # Make non-hero SoftCards subtly glass-tinted by default where old code did not pass tintWithAccent.
    shell = shell.replace(
        "SoftCard(palette = palette, accent = accent, hero = false) {",
        "SoftCard(palette = palette, accent = accent, hero = false, tintWithAccent = true) {",
    )
    shell = shell.replace(
        "SoftCard(palette = palette, accent = HealthAccent.activity, hero = false) {",
        "SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {",
    )

    shell = re.sub(r"\n{3,}", "\n\n", shell)
    write(SHELL, shell)

def patch_docs():
    note = """
## BitLut v1.9.6 GUI scope

The app UI is activity-only in v1.9.6. Dashboard and Settings must not expose widgets, toggles or permission prompts for pulse, sleep, stress, SpO2, HRV or Activity Intensity.

The bottom navigation is icon-only neo-glassmorphism. Status refresh actions live in Settings only; app startup refreshes status automatically.
""".strip()

    for doc in [README, CONTEXT]:
        if doc.exists():
            content = read(doc)
            if "## BitLut v1.9.6 GUI scope" not in content:
                content = content.rstrip() + "\n\n" + note + "\n"
            write(doc, content)

def write_verifier():
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
prefs = read("app/src/main/java/com/openhealth/sync/config/WidgetVisibilityPrefs.kt")
main = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("NeoGlassBottomBar(" in shell, "Bottom navigation must use NeoGlassBottomBar")
require("NeoGlassNavButton(" in shell, "Bottom navigation must use NeoGlassNavButton")
require("NavigationBarItem(" not in shell, "Material NavigationBarItem must be removed")
require("NavigationBar(" not in shell, "Material NavigationBar must be removed")
require("contentDescription = null" in shell, "Icon-only nav should avoid visible labels")
require("label =" not in shell[shell.find("NeoGlassBottomBar"):shell.find("private fun NeoGlassNavButton")], "Bottom bar must be icon-only")

for forbidden in [
    "DashboardWidget.HEART_RATE",
    "DashboardWidget.SLEEP",
    "DashboardWidget.STRESS",
    "DashboardWidget.SPO2",
    "HeartRateWidgetCard(",
    "SleepWidgetCard(",
    "widget_toggle_heart",
    "widget_toggle_sleep",
    "widget_toggle_stress",
    "widget_toggle_spo2",
    "readSleepLastNight",
    "readLatestSpo2Percent",
    "readStressScoreToday",
    "optionalDashboardRead(",
]:
    require(forbidden not in shell, f"Unsupported UI term remains in shell: {forbidden}")
    require(forbidden not in prefs, f"Unsupported widget term remains in prefs: {forbidden}")

for forbidden_widget in ["HEART_RATE", "SLEEP", "STRESS", "SPO2"]:
    require(forbidden_widget not in prefs, f"Unsupported DashboardWidget remains: {forbidden_widget}")

summary_start = shell.find("private fun SummaryScreen")
history_start = shell.find("private fun HistoryScreen")
summary = shell[summary_start:history_start if history_start != -1 else len(shell)]
require("refresh_status" not in summary, "Dashboard Summary must not contain refresh status button")
require("refreshUiStatusOnLaunch()" in main, "MainActivity must refresh status on launch")
require("setupPeriodicSync()\n        refreshUiStatusOnLaunch()" in main, "Launch refresh must run after periodic sync setup")
require("val showMeshGradient = true" in shell, "SoftCard must apply neo-glass glow mesh globally")

if errors:
    print("GUI neo-glass activity-only verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("GUI neo-glass activity-only verification passed.")
''')
    VERIFY.chmod(0o755)

def self_check():
    shell = read(SHELL)
    prefs = read(PREFS)
    main = read(MAIN)
    errors = []

    for term in FORBIDDEN_UI:
        if term in shell:
            errors.append(f"Forbidden UI term remains in shell: {term}")
        if term in prefs:
            errors.append(f"Forbidden UI term remains in prefs: {term}")

    summary_start = shell.find("private fun SummaryScreen")
    history_start = shell.find("private fun HistoryScreen")
    summary = shell[summary_start:history_start if history_start != -1 else len(shell)]
    if "refresh_status" in summary:
        errors.append("Dashboard Summary still contains refresh_status")

    if "refreshUiStatusOnLaunch()" not in main:
        errors.append("MainActivity missing refreshUiStatusOnLaunch")

    if errors:
        print("GUI recovery patch failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)

def main():
    cleanup_temp_files()
    restore_gui_files_from_head()
    patch_prefs()
    patch_main()
    patch_shell()
    patch_docs()
    write_verifier()
    self_check()
    print("Applied v1.9.6 GUI neo-glass activity-only recovery patch.")

if __name__ == "__main__":
    main()
