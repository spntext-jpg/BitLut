#!/usr/bin/env python3
"""
BitLut patch: Activity rings + goal progress on the Steps card (sprint item 1
and part of item 4 from the "last sprint" list).

1. Steps card now shows its already-existing progress ring (ProgressRingChip
   was fully built in a previous session with a real "steps vs goal" comment,
   but the Steps card's own MinimalMetricCard call never actually passed
   `progress` -- it was always null, so nothing showed) plus a new
   "N to go" / "goal reached" text line underneath, using the goal value
   that was already being tracked for streaks either way.

2. New "Activity rings" card: three concentric rings (steps outer, active
   minutes middle, calories inner), Apple-Watch style. All three progress
   values (stepsProgress/activeMinutesProgress/caloriesProgress) already
   existed on DashboardUiState, fully computed from GoalPrefs -- this patch
   is almost entirely UI, not new data plumbing. Each ring animates in with
   its own tween on first composition.

3. Settings gets a new "Daily goals" section with +/- steppers for the three
   goals behind the rings (steps, active minutes, calories). This reuses
   DashboardViewModel.setStepsGoal/setActiveMinutesGoal/setCaloriesGoalKcal,
   which already existed with a doc comment literally saying "Called from
   the Settings goals editor" -- that editor never existed until now; the
   ViewModel-level wiring was already there, just unused.

No new Health Connect permission or Huawei scope -- purely UI plus wiring
up backend state that already existed but was never connected to anything
visible.

Every old/new text block in this script was generated and verified
programmatically (byte-diffed against the real source, uniqueness-checked,
and idempotency-checked for the old-remains-a-substring-of-new failure mode)
rather than transcribed by hand.

Run from the repo root:
    python3 add_activity_rings_and_goal_progress.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

UI = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
MAIN = "app/src/main/java/com/openhealth/sync/MainActivity.kt"
STRINGS_EN = "app/src/main/res/values/strings.xml"
STRINGS_RU = "app/src/main/res/values-ru/strings.xml"

TARGET_FILES = [UI, MAIN, STRINGS_EN, STRINGS_RU]


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
    dst = BACKUP_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def apply_edit(rel_path: str, old: str, new: str, desc: str) -> bool:
    """Regex-anchored (plain substring) replacement, exactly 1 occurrence.

    Checks the OLD anchor's count first; NEW-presence is only consulted as
    a fallback once OLD is confirmed absent.
    """
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    old_count = text.count(old)
    if old_count == 0:
        if text.count(new) >= 1:
            print(f"   (already applied, skipping) {desc}")
            return False
        die(f"Anchor not found for '{desc}' in {rel_path}, and patched text "
            f"is also absent. File may have changed since this script was "
            f"written -- aborting rather than guessing.")

    if old_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {old_count}. Aborting rather than guessing "
            f"which one to patch.")

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def apply_insertion(rel_path: str, anchor: str, new_with_anchor: str, unique_marker: str, desc: str) -> bool:
    """For edits that insert new text between two lines that stay unchanged
    on both sides. `anchor` (spanning both sides) remains a substring of
    `new_with_anchor`, so checking anchor-count-first would never see it as
    "gone" and would reapply forever. Idempotency here is instead decided by
    `unique_marker`, a string that only exists once the insertion has
    happened.
    """
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"   (already applied, skipping) {desc}")
        return False

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {anchor_count}. Aborting rather than "
            f"guessing which one to patch.")

    path.write_text(text.replace(anchor, new_with_anchor, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def main() -> None:
    print("==> Checking target files exist")
    for rel in TARGET_FILES:
        if not (ROOT / rel).exists():
            die(f"Expected file not found: {rel} (run this from the repo root)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)

    print("==> Applying edits")
    apply_edit(
        MAIN,
        old='                    onDataSourceSelected = { source -> selectDataSource(source) },\n                    hasSeenPermissionsOnboarding = hasSeenOnboarding,\n',
        new='                    onDataSourceSelected = { source -> selectDataSource(source) },\n                    onStepsGoalChanged = { value -> dashboardViewModel.setStepsGoal(value) },\n                    onActiveMinutesGoalChanged = { value -> dashboardViewModel.setActiveMinutesGoal(value) },\n                    onCaloriesGoalChanged = { value -> dashboardViewModel.setCaloriesGoalKcal(value) },\n                    hasSeenPermissionsOnboarding = hasSeenOnboarding,\n',
        desc='wire goal-change callbacks to DashboardViewModel setters',
    )

    apply_edit(
        UI,
        old='import androidx.compose.ui.unit.dp\nimport androidx.compose.ui.unit.sp\n',
        new='import androidx.compose.ui.unit.dp\nimport androidx.compose.ui.unit.Dp\nimport androidx.compose.ui.unit.sp\n',
        desc='add Dp type import',
    )

    apply_edit(
        UI,
        old='import androidx.compose.foundation.layout.heightIn\nimport androidx.compose.foundation.layout.FlowRow\n',
        new='import androidx.compose.foundation.layout.heightIn\nimport androidx.compose.foundation.layout.widthIn\nimport androidx.compose.foundation.layout.FlowRow\n',
        desc='add widthIn layout import',
    )

    apply_edit(
        UI,
        old='import androidx.compose.material.icons.rounded.Schedule\nimport androidx.compose.material3.Icon\n',
        new='import androidx.compose.material.icons.rounded.Schedule\nimport androidx.compose.material.icons.rounded.DonutLarge\nimport androidx.compose.material3.Icon\n',
        desc='add DonutLarge icon import',
    )

    apply_edit(
        UI,
        old='import androidx.compose.ui.text.style.TextOverflow\nimport com.openhealth.sync.ui.ImportScreen\n',
        new='import androidx.compose.ui.text.style.TextOverflow\nimport androidx.compose.ui.text.style.TextAlign\nimport com.openhealth.sync.ui.ImportScreen\n',
        desc='add TextAlign import',
    )

    apply_edit(
        UI,
        old='import androidx.compose.animation.core.Spring\nimport androidx.compose.foundation.interaction.MutableInteractionSource\n',
        new='import androidx.compose.animation.core.Spring\nimport androidx.compose.animation.core.tween\nimport androidx.compose.animation.core.FastOutSlowInEasing\nimport androidx.compose.ui.geometry.Offset\nimport androidx.compose.ui.geometry.Size\nimport androidx.compose.foundation.interaction.MutableInteractionSource\n',
        desc='add tween/FastOutSlowInEasing/Offset/Size imports',
    )

    apply_edit(
        UI,
        old='    onDataSourceSelected: (HealthDataSource) -> Unit = {},\n    hasSeenPermissionsOnboarding: Boolean = true,\n',
        new='    onDataSourceSelected: (HealthDataSource) -> Unit = {},\n    onStepsGoalChanged: (Long) -> Unit = {},\n    onActiveMinutesGoalChanged: (Int) -> Unit = {},\n    onCaloriesGoalChanged: (Double) -> Unit = {},\n    hasSeenPermissionsOnboarding: Boolean = true,\n',
        desc='add goal-change callback params to FinalBitLutShell signature',
    )

    apply_edit(
        UI,
        old='                    onWidgetVisibilityChanged = onWidgetVisibilityChanged,\n                    onDataSourceSelected = onDataSourceSelected)\n            }\n',
        new='                    onWidgetVisibilityChanged = onWidgetVisibilityChanged,\n                    onDataSourceSelected = onDataSourceSelected,\n                    stepsGoal = dashboardState.stepsGoal,\n                    activeMinutesGoal = dashboardState.activeMinutesGoal,\n                    caloriesGoalKcal = dashboardState.caloriesGoalKcal,\n                    onStepsGoalChanged = onStepsGoalChanged,\n                    onActiveMinutesGoalChanged = onActiveMinutesGoalChanged,\n                    onCaloriesGoalChanged = onCaloriesGoalChanged)\n            }\n',
        desc='wire goal params+callbacks into the SettingsScreen call site',
    )

    apply_edit(
        UI,
        old='                        accent = HealthAccent.activity,\n                        hero = true,\n',
        new='                        accent = HealthAccent.activity,\n                        progress = state.stepsProgress,\n                        progressText = stepsGoalProgressText(state.stepsToday, state.stepsGoal),\n                        hero = true,\n',
        desc='wire stepsProgress ring + progress-to-goal text into the Steps card',
    )

    apply_insertion(
        UI,
        anchor='                        pressLift = true\n                    )\n                }\n\n',
        new_with_anchor='                        pressLift = true\n                    )\n                }\n\n                item {\n                    ActivityRingsCard(palette = palette, state = state)\n                }\n\n',
        unique_marker='ActivityRingsCard(palette = palette, state = state)',
        desc='insert ActivityRingsCard item into the Today screen card list',
    )

    apply_insertion(
        UI,
        anchor='    else -> Icons.Rounded.DirectionsRun\n}\n',
        new_with_anchor='    else -> Icons.Rounded.DirectionsRun\n}\n\n/**\n * Apple-Watch-style concentric rings: Steps (outer), Active minutes (middle),\n * Calories (inner). All three progress values already exist on\n * DashboardUiState (stepsProgress/activeMinutesProgress/caloriesProgress,\n * backed by GoalPrefs) -- this card is the first thing in the UI that\n * actually shows them; the goals themselves are edited in Settings.\n * Distance intentionally has no ring here: it overlaps semantically with\n * Steps and a 4th ring made the card visually noisy without adding new\n * information.\n */\n@Composable\nprivate fun ActivityRingsCard(palette: BitPalette, state: DashboardUiState) {\n    SoftCard(palette = palette, accent = HealthAccent.activity, tintWithAccent = true, pressLift = true) {\n        Row(verticalAlignment = Alignment.CenterVertically) {\n            Icon(Icons.Rounded.DonutLarge, contentDescription = null, tint = HealthAccent.activity, modifier = Modifier.size(20.dp))\n            Spacer(Modifier.width(8.dp))\n            Text(\n                text = stringResource(R.string.dashboard_rings_title),\n                color = palette.text,\n                fontWeight = FontWeight.ExtraBold,\n                fontSize = 16.sp\n            )\n        }\n        Spacer(Modifier.height(16.dp))\n        Row(verticalAlignment = Alignment.CenterVertically) {\n            ActivityRings(\n                modifier = Modifier.size(112.dp),\n                trackColor = palette.stroke.copy(alpha = 0.35f),\n                rings = listOf(\n                    RingSpec(progress = state.stepsProgress, color = HealthAccent.activity),\n                    RingSpec(progress = state.activeMinutesProgress, color = HealthAccent.mind),\n                    RingSpec(progress = state.caloriesProgress, color = HealthAccent.violet)\n                )\n            )\n            Spacer(Modifier.width(20.dp))\n            Column(verticalArrangement = Arrangement.spacedBy(11.dp)) {\n                RingLegendRow(\n                    palette = palette,\n                    color = HealthAccent.activity,\n                    label = stringResource(R.string.dashboard_rings_steps),\n                    value = "${formatNumber(state.stepsToday)} / ${formatNumber(state.stepsGoal)}"\n                )\n                RingLegendRow(\n                    palette = palette,\n                    color = HealthAccent.mind,\n                    label = stringResource(R.string.dashboard_rings_active_minutes),\n                    value = "${state.workoutMinutesToday} / ${state.activeMinutesGoal} ${stringResource(R.string.minutes_short)}"\n                )\n                RingLegendRow(\n                    palette = palette,\n                    color = HealthAccent.violet,\n                    label = stringResource(R.string.dashboard_rings_calories),\n                    value = "${state.caloriesKcal.toInt()} / ${state.caloriesGoalKcal.toInt()} " + stringResource(R.string.kcal_unit)\n                )\n            }\n        }\n    }\n}\n\nprivate data class RingSpec(val progress: Float, val color: Color)\n\n@Composable\nprivate fun ActivityRings(\n    rings: List<RingSpec>,\n    trackColor: Color,\n    modifier: Modifier = Modifier,\n    strokeWidth: Dp = 13.dp,\n    gap: Dp = 5.dp\n) {\n    // Animated per-ring rather than a single shared animation so each ring\n    // visibly sweeps in on its own, matching the layered feel of Apple\'s\n    // activity rings instead of three rings snapping to their values at once.\n    val animatedProgresses = rings.map { ring ->\n        animateFloatAsState(\n            targetValue = ring.progress.coerceIn(0f, 1f),\n            animationSpec = tween(durationMillis = 900, easing = FastOutSlowInEasing),\n            label = "activityRingProgress"\n        ).value\n    }\n    Canvas(modifier = modifier) {\n        val strokePx = strokeWidth.toPx()\n        val gapPx = gap.toPx()\n        rings.forEachIndexed { index, ring ->\n            val inset = index * (strokePx + gapPx)\n            val diameter = size.minDimension - inset * 2f\n            val topLeft = Offset((size.width - diameter) / 2f, (size.height - diameter) / 2f)\n            val arcSize = Size(diameter, diameter)\n            drawArc(\n                color = trackColor,\n                startAngle = -90f,\n                sweepAngle = 360f,\n                useCenter = false,\n                topLeft = topLeft,\n                size = arcSize,\n                style = Stroke(width = strokePx, cap = StrokeCap.Round)\n            )\n            val sweep = 360f * animatedProgresses[index]\n            if (sweep > 0f) {\n                drawArc(\n                    color = ring.color,\n                    startAngle = -90f,\n                    sweepAngle = sweep,\n                    useCenter = false,\n                    topLeft = topLeft,\n                    size = arcSize,\n                    style = Stroke(width = strokePx, cap = StrokeCap.Round)\n                )\n            }\n        }\n    }\n}\n\n@Composable\nprivate fun RingLegendRow(palette: BitPalette, color: Color, label: String, value: String) {\n    Row(verticalAlignment = Alignment.CenterVertically) {\n        Box(\n            modifier = Modifier\n                .size(9.dp)\n                .clip(RoundedCornerShape(50))\n                .background(color)\n        )\n        Spacer(Modifier.width(8.dp))\n        Column {\n            Text(label, color = palette.secondaryText, fontWeight = FontWeight.SemiBold, fontSize = 11.sp)\n            Text(value, color = palette.text, fontWeight = FontWeight.ExtraBold, fontSize = 13.sp)\n        }\n    }\n}\n',
        unique_marker='private fun ActivityRingsCard(palette: BitPalette, state: DashboardUiState) {',
        desc='add ActivityRingsCard/ActivityRings/RingLegendRow composables',
    )

    apply_edit(
        UI,
        old='    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit,\n    onDataSourceSelected: (HealthDataSource) -> Unit\n) {\n',
        new='    onWidgetVisibilityChanged: (DashboardWidget, Boolean) -> Unit,\n    onDataSourceSelected: (HealthDataSource) -> Unit,\n    stepsGoal: Long,\n    activeMinutesGoal: Int,\n    caloriesGoalKcal: Double,\n    onStepsGoalChanged: (Long) -> Unit,\n    onActiveMinutesGoalChanged: (Int) -> Unit,\n    onCaloriesGoalChanged: (Double) -> Unit\n) {\n',
        desc='add goal params+callbacks to SettingsScreen signature',
    )

    apply_insertion(
        UI,
        anchor='            onSecondaryAction = onImportArchive\n        )\n\n        Text(\n',
        new_with_anchor='            onSecondaryAction = onImportArchive\n        )\n\n        Text(\n            text = stringResource(R.string.goals_section_title),\n            color = palette.text,\n            fontWeight = FontWeight.ExtraBold,\n            fontSize = 18.sp\n        )\n        SoftCard(palette = palette, accent = HealthAccent.activity, tintWithAccent = true) {\n            Text(\n                text = stringResource(R.string.goals_section_body),\n                color = palette.secondaryText,\n                fontWeight = FontWeight.Medium,\n                fontSize = 13.sp,\n                lineHeight = 18.sp\n            )\n            Spacer(Modifier.height(14.dp))\n            GoalStepperRow(\n                palette = palette,\n                accent = HealthAccent.activity,\n                label = stringResource(R.string.dashboard_rings_steps),\n                valueText = formatNumber(stepsGoal),\n                onDecrease = {\n                    onStepsGoalChanged((stepsGoal - STEPS_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.STEPS_GOAL_RANGE))\n                },\n                onIncrease = {\n                    onStepsGoalChanged((stepsGoal + STEPS_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.STEPS_GOAL_RANGE))\n                }\n            )\n            Spacer(Modifier.height(12.dp))\n            GoalStepperRow(\n                palette = palette,\n                accent = HealthAccent.mind,\n                label = stringResource(R.string.dashboard_rings_active_minutes),\n                valueText = "$activeMinutesGoal ${stringResource(R.string.minutes_short)}",\n                onDecrease = {\n                    onActiveMinutesGoalChanged((activeMinutesGoal - ACTIVE_MINUTES_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.ACTIVE_MINUTES_GOAL_RANGE))\n                },\n                onIncrease = {\n                    onActiveMinutesGoalChanged((activeMinutesGoal + ACTIVE_MINUTES_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.ACTIVE_MINUTES_GOAL_RANGE))\n                }\n            )\n            Spacer(Modifier.height(12.dp))\n            GoalStepperRow(\n                palette = palette,\n                accent = HealthAccent.violet,\n                label = stringResource(R.string.dashboard_rings_calories),\n                valueText = "${caloriesGoalKcal.toInt()} ${stringResource(R.string.kcal_unit)}",\n                onDecrease = {\n                    onCaloriesGoalChanged((caloriesGoalKcal - CALORIES_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.CALORIES_GOAL_RANGE))\n                },\n                onIncrease = {\n                    onCaloriesGoalChanged((caloriesGoalKcal + CALORIES_GOAL_STEP).coerceIn(com.openhealth.sync.config.GoalPrefs.CALORIES_GOAL_RANGE))\n                }\n            )\n        }\n\n        Text(\n',
        unique_marker='text = stringResource(R.string.goals_section_title),',
        desc='add Goals editor section to Settings',
    )

    apply_insertion(
        UI,
        anchor='\n/** Single toggle row inside the Widgets settings card: label + Switch. [isLast]\n',
        new_with_anchor='\n/** Step sizes for the +/- goal editor in Settings. Values stay within GoalPrefs\' own ranges via coerceIn at the call site. */\nprivate const val STEPS_GOAL_STEP = 500L\nprivate const val ACTIVE_MINUTES_GOAL_STEP = 5\nprivate const val CALORIES_GOAL_STEP = 50.0\n\n/** Label + a compact -/value/+ stepper, used by the three goal rows in Settings. */\n@Composable\nprivate fun GoalStepperRow(\n    palette: BitPalette,\n    accent: Color,\n    label: String,\n    valueText: String,\n    onDecrease: () -> Unit,\n    onIncrease: () -> Unit\n) {\n    Row(\n        modifier = Modifier.fillMaxWidth(),\n        horizontalArrangement = Arrangement.SpaceBetween,\n        verticalAlignment = Alignment.CenterVertically\n    ) {\n        Text(label, color = palette.text, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)\n        Row(verticalAlignment = Alignment.CenterVertically) {\n            GoalStepperButton(accent = accent, symbol = "–", onClick = onDecrease)\n            Text(\n                text = valueText,\n                color = palette.text,\n                fontWeight = FontWeight.Black,\n                fontSize = 14.sp,\n                textAlign = TextAlign.Center,\n                modifier = Modifier\n                    .padding(horizontal = 10.dp)\n                    .widthIn(min = 64.dp)\n            )\n            GoalStepperButton(accent = accent, symbol = "+", onClick = onIncrease)\n        }\n    }\n}\n\n@Composable\nprivate fun GoalStepperButton(accent: Color, symbol: String, onClick: () -> Unit) {\n    Box(\n        modifier = Modifier\n            .size(30.dp)\n            .clip(RoundedCornerShape(10.dp))\n            .background(accent.copy(alpha = 0.16f))\n            .clickable(onClick = onClick),\n        contentAlignment = Alignment.Center\n    ) {\n        Text(symbol, color = accent, fontWeight = FontWeight.Black, fontSize = 16.sp)\n    }\n}\n\n/** Single toggle row inside the Widgets settings card: label + Switch. [isLast]\n',
        unique_marker='private const val STEPS_GOAL_STEP = 500L',
        desc='add GoalStepperRow/GoalStepperButton composables + goal step constants',
    )

    apply_insertion(
        UI,
        anchor='}\n\n@Composable\nprivate fun MinimalMetricCard(\n',
        new_with_anchor='}\n\n/** Progress-to-goal text shown inside the Steps card. Null when no real goal is set (defensive; GoalPrefs always returns a positive default in practice). */\n@Composable\nprivate fun stepsGoalProgressText(stepsToday: Long, stepsGoal: Long): String? {\n    if (stepsGoal <= 0) return null\n    val remaining = stepsGoal - stepsToday\n    return if (remaining <= 0) {\n        stringResource(R.string.steps_goal_reached)\n    } else {\n        stringResource(R.string.steps_goal_remaining, formatNumber(remaining))\n    }\n}\n\n@Composable\nprivate fun MinimalMetricCard(\n',
        unique_marker='private fun stepsGoalProgressText(stepsToday: Long, stepsGoal: Long): String? {',
        desc='add stepsGoalProgressText() helper',
    )

    apply_edit(
        UI,
        old='    progress: Float? = null,\n    icon: ImageVector? = null,\n',
        new='    progress: Float? = null,\n    progressText: String? = null,\n    icon: ImageVector? = null,\n',
        desc='add progressText param to MinimalMetricCard',
    )

    apply_edit(
        UI,
        old='                }\n            }\n        }\n        if (onClick != null) {\n',
        new='                }\n            }\n        }\n        if (progressText != null) {\n            Spacer(Modifier.height(8.dp))\n            Text(\n                text = progressText,\n                color = palette.secondaryText,\n                fontWeight = FontWeight.SemiBold,\n                fontSize = 12.sp,\n                maxLines = 1,\n                overflow = TextOverflow.Ellipsis\n            )\n        }\n        if (onClick != null) {\n',
        desc='render progressText inside MinimalMetricCard',
    )

    apply_edit(
        STRINGS_EN,
        old='    <string name="steps_unit">steps</string>\n    <string name="no_data_short">—</string>\n',
        new='    <string name="steps_unit">steps</string>\n    <string name="steps_goal_reached">Goal reached today 🎉</string>\n    <string name="steps_goal_remaining">%1$s to go</string>\n    <string name="dashboard_rings_title">Activity rings</string>\n    <string name="dashboard_rings_steps">Steps</string>\n    <string name="dashboard_rings_active_minutes">Active minutes</string>\n    <string name="dashboard_rings_calories">Calories</string>\n    <string name="no_data_short">—</string>\n',
        desc='STR_EN hunk 1',
    )

    apply_edit(
        STRINGS_EN,
        old='    <string name="goal_template">Goal %1$s</string>\n    <string name="hours_unit">h</string>\n',
        new='    <string name="goal_template">Goal %1$s</string>\n    <string name="goals_section_title">Daily goals</string>\n    <string name="goals_section_body">Used by the activity rings and progress indicators on the dashboard.</string>\n    <string name="hours_unit">h</string>\n',
        desc='STR_EN hunk 2',
    )

    apply_edit(
        STRINGS_RU,
        old='    <string name="steps_unit">шагов</string>\n    <string name="no_data_short">—</string>\n',
        new='    <string name="steps_unit">шагов</string>\n    <string name="steps_goal_reached">Цель на сегодня достигнута 🎉</string>\n    <string name="steps_goal_remaining">Ещё %1$s до цели</string>\n    <string name="dashboard_rings_title">Кольца активности</string>\n    <string name="dashboard_rings_steps">Шаги</string>\n    <string name="dashboard_rings_active_minutes">Активные минуты</string>\n    <string name="dashboard_rings_calories">Калории</string>\n    <string name="no_data_short">—</string>\n',
        desc='STR_RU hunk 1',
    )

    apply_edit(
        STRINGS_RU,
        old='    <string name="goal_template">Цель %1$s</string>\n    <string name="hours_unit">ч</string>\n',
        new='    <string name="goal_template">Цель %1$s</string>\n    <string name="goals_section_title">Дневные цели</string>\n    <string name="goals_section_body">Используются кольцами активности и индикаторами прогресса на главном экране.</string>\n    <string name="hours_unit">ч</string>\n',
        desc='STR_RU hunk 2',
    )

    print("==> Best-effort compile check")
    gradlew = ROOT / "gradlew"
    if gradlew.exists():
        result = subprocess.run(
            ["./gradlew", ":app:compileDebugKotlin", "--console=plain"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            die("compileDebugKotlin failed -- NOT committing or pushing. "
                "Fix the error above (or paste it back) before re-running.")
        print("==> Compile check passed")
    else:
        print("   gradlew not found -- skipping compile check (unexpected outside "
              "a throwaway sandbox; NOT committing automatically).")
        return

    print("==> git add / commit / push")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m",
         "Add activity rings card + goal progress on Steps card + Settings goals editor"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
