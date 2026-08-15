
#!/usr/bin/env python3
"""
Remove the activity rings card.

Prompted by a direct check: steps sync reliably, but the other two rings
usually don't have real data to show. Verified against the source rather
than taken on faith:

  - Read-side (GoogleHealthManager.kt): ActiveCaloriesBurnedRecord and
    ExerciseSessionRecord ARE both read and written correctly -- the code
    path is complete, this isn't a bug in this app's own sync logic.
  - The actual gap is upstream: Huawei approves Health Kit scopes
    per-category rather than all at once, and CLAUDE.md / this project's
    own history already document activeCalories specifically returning
    error 50005 (denied) on real devices while other categories succeeded.
    Active minutes has the same practical problem from a different cause --
    it's sourced from ExerciseSessionRecord, which only has data on days
    with a logged, structured workout, not from ambient daily activity.

So in practice the card usually rendered one real ring (steps) and two
empty ones, most days, for reasons outside this app's control. A 3-ring
visual promising three tracked metrics when only one reliably has data
is worse than not showing the promise at all -- so this removes the
whole card rather than patching around the other two rings.

What this script does:

1. FinalBitLutShell.kt: removes ActivityRingsCard, the private RingSpec
   data class, the ActivityRings canvas-drawing composable, and
   RingLegendRow -- all four existed only to support this one card (all
   confirmed 1-consumer via a repo-wide grep before removal, not assumed).
   Also removes the two `when` branches that dispatched to it
   (DashboardOrderedCard's renderer, dashboardCardLabel's editor-title
   lookup) and four now-fully-unused imports (DonutLarge, Offset, Size,
   FastOutSlowInEasing -- each verified to have zero remaining references
   anywhere else in the file after the card itself is gone).

2. DashboardCardLayoutPrefs.kt: removes the ACTIVITY_RINGS entry from the
   DashboardCardType enum (the reorderable/hideable card list backing the
   pencil-icon editor) and from DEFAULT_ORDER. No migration needed for
   people who already have a saved card order/hidden-state mentioning
   "activity_rings" -- DashboardCardType.fromKey() already returns null
   for unknown keys, and allCardsForEditor()/orderedVisibleCards() already
   drop those via mapNotNull/filter. That's existing, general-purpose
   forward-compatibility, not something this script adds.

3. DashboardViewModel.kt: removes activeMinutesProgress and
   caloriesProgress from DashboardUiState -- verified (repo-wide grep)
   that the removed card was their only consumer anywhere in the app.
   workoutMinutesToday and caloriesKcal themselves are NOT touched -- they
   remain real, synced fields; only the goal-progress fraction that
   nothing reads anymore is gone. stepsProgress and distanceProgress are
   untouched (stepsProgress still powers the pinned Steps hero card).

4. strings.xml (both locales): removes dashboard_rings_title, the one
   string exclusive to this card. dashboard_rings_steps/active_minutes/
   calories are deliberately NOT removed -- they're also used by the
   unrelated "Daily goals" section in Settings (GoalStepperRow), confirmed
   by grep before deciding, not assumed from the similar name.

Every old/new text block in this script was hand-edited against a real
extraction of the current codebase first, then generated from that edited
copy's actual diff, and tested for idempotency (a second run makes zero
changes) before being included here.

Run from the repo root:
    python3 remove_activity_rings.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

UI_SHELL = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
CARD_LAYOUT_PREFS = "app/src/main/java/com/openhealth/sync/config/DashboardCardLayoutPrefs.kt"
DASHBOARD_VM = "app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt"
STRINGS_EN = "app/src/main/res/values/strings.xml"
STRINGS_RU = "app/src/main/res/values-ru/strings.xml"

TARGET_FILES = [UI_SHELL, CARD_LAYOUT_PREFS, DASHBOARD_VM, STRINGS_EN, STRINGS_RU]


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
    dst = BACKUP_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def apply_edit(rel_path: str, old: str, new: str, desc: str) -> bool:
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


def main() -> None:
    print("==> Checking target files exist")
    for rel in TARGET_FILES:
        if not (ROOT / rel).exists():
            die(f"Expected file not found: {rel} (run this from the repo root)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)

    # -- FinalBitLutShell.kt --------------------------------------------
    print("==> Removing dead imports (DonutLarge, FastOutSlowInEasing, Offset, Size)")
    apply_edit(
        UI_SHELL,
        old="import androidx.compose.material.icons.rounded.Schedule\nimport androidx.compose.material.icons.rounded.DonutLarge\nimport androidx.compose.material.icons.rounded.Edit",
        new="import androidx.compose.material.icons.rounded.Schedule\nimport androidx.compose.material.icons.rounded.Edit",
        desc="remove DonutLarge import",
    )
    apply_edit(
        UI_SHELL,
        old="import androidx.compose.animation.core.tween\nimport androidx.compose.animation.core.FastOutSlowInEasing\nimport androidx.compose.ui.geometry.Offset\nimport androidx.compose.ui.geometry.Size\nimport androidx.compose.foundation.interaction.MutableInteractionSource",
        new="import androidx.compose.animation.core.tween\nimport androidx.compose.foundation.interaction.MutableInteractionSource",
        desc="remove FastOutSlowInEasing/Offset/Size imports",
    )

    print("==> Removing ACTIVITY_RINGS dispatch from DashboardOrderedCard")
    apply_edit(
        UI_SHELL,
        old='''    when (cardType) {
        com.openhealth.sync.config.DashboardCardType.ACTIVITY_RINGS ->
            ActivityRingsCard(palette = palette, state = state)

        com.openhealth.sync.config.DashboardCardType.WORKOUT_LATEST ->''',
        new='''    when (cardType) {
        com.openhealth.sync.config.DashboardCardType.WORKOUT_LATEST ->''',
        desc="remove ACTIVITY_RINGS branch from DashboardOrderedCard",
    )

    print("==> Removing ACTIVITY_RINGS branch from dashboardCardLabel")
    apply_edit(
        UI_SHELL,
        old='''private fun dashboardCardLabel(type: com.openhealth.sync.config.DashboardCardType): String = when (type) {
    com.openhealth.sync.config.DashboardCardType.ACTIVITY_RINGS -> stringResource(R.string.dashboard_rings_title)
    com.openhealth.sync.config.DashboardCardType.WORKOUT_LATEST -> stringResource(R.string.dashboard_latest_workout)''',
        new='''private fun dashboardCardLabel(type: com.openhealth.sync.config.DashboardCardType): String = when (type) {
    com.openhealth.sync.config.DashboardCardType.WORKOUT_LATEST -> stringResource(R.string.dashboard_latest_workout)''',
        desc="remove ACTIVITY_RINGS branch from dashboardCardLabel",
    )

    print("==> Removing ActivityRingsCard/RingSpec/ActivityRings/RingLegendRow")
    apply_edit(
        UI_SHELL,
        old='''/**
 * Apple-Watch-style concentric rings: Steps (outer), Active minutes (middle),
 * Calories (inner). All three progress values already exist on
 * DashboardUiState (stepsProgress/activeMinutesProgress/caloriesProgress,
 * backed by GoalPrefs) -- this card is the first thing in the UI that
 * actually shows them; the goals themselves are edited in Settings.
 * Distance intentionally has no ring here: it overlaps semantically with
 * Steps and a 4th ring made the card visually noisy without adding new
 * information.
 */
@Composable
private fun ActivityRingsCard(palette: BitPalette, state: DashboardUiState) {
    SoftCard(palette = palette, accent = HealthAccent.activity, tintWithAccent = true, pressLift = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.DonutLarge, contentDescription = null, tint = HealthAccent.activity, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(8.dp))
            Text(
                text = stringResource(R.string.dashboard_rings_title),
                color = palette.text,
                fontWeight = FontWeight.ExtraBold,
                fontSize = 16.sp
            )
        }
        Spacer(Modifier.height(16.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            ActivityRings(
                modifier = Modifier.size(112.dp),
                trackColor = palette.stroke.copy(alpha = 0.35f),
                rings = listOf(
                    RingSpec(progress = state.stepsProgress, color = HealthAccent.activity),
                    RingSpec(progress = state.activeMinutesProgress, color = HealthAccent.mind),
                    RingSpec(progress = state.caloriesProgress, color = HealthAccent.violet)
                )
            )
            Spacer(Modifier.width(20.dp))
            Column(verticalArrangement = Arrangement.spacedBy(11.dp)) {
                RingLegendRow(
                    palette = palette,
                    color = HealthAccent.activity,
                    label = stringResource(R.string.dashboard_rings_steps),
                    value = "${formatNumber(state.stepsToday)} / ${formatNumber(state.stepsGoal)}"
                )
                RingLegendRow(
                    palette = palette,
                    color = HealthAccent.mind,
                    label = stringResource(R.string.dashboard_rings_active_minutes),
                    value = "${state.workoutMinutesToday} / ${state.activeMinutesGoal} ${stringResource(R.string.minutes_short)}"
                )
                RingLegendRow(
                    palette = palette,
                    color = HealthAccent.violet,
                    label = stringResource(R.string.dashboard_rings_calories),
                    value = "${state.caloriesKcal.toInt()} / ${state.caloriesGoalKcal.toInt()} " + stringResource(R.string.kcal_unit)
                )
            }
        }
    }
}

private data class RingSpec(val progress: Float, val color: Color)

@Composable
private fun ActivityRings(
    rings: List<RingSpec>,
    trackColor: Color,
    modifier: Modifier = Modifier,
    strokeWidth: Dp = 13.dp,
    gap: Dp = 5.dp
) {
    // Animated per-ring rather than a single shared animation so each ring
    // visibly sweeps in on its own, matching the layered feel of Apple's
    // activity rings instead of three rings snapping to their values at once.
    val animatedProgresses = rings.map { ring ->
        animateFloatAsState(
            targetValue = ring.progress.coerceIn(0f, 1f),
            animationSpec = tween(durationMillis = 900, easing = FastOutSlowInEasing),
            label = "activityRingProgress"
        ).value
    }
    Canvas(modifier = modifier) {
        val strokePx = strokeWidth.toPx()
        val gapPx = gap.toPx()
        rings.forEachIndexed { index, ring ->
            val inset = index * (strokePx + gapPx)
            val diameter = size.minDimension - inset * 2f
            val topLeft = Offset((size.width - diameter) / 2f, (size.height - diameter) / 2f)
            val arcSize = Size(diameter, diameter)
            drawArc(
                color = trackColor,
                startAngle = -90f,
                sweepAngle = 360f,
                useCenter = false,
                topLeft = topLeft,
                size = arcSize,
                style = Stroke(width = strokePx, cap = StrokeCap.Round)
            )
            val sweep = 360f * animatedProgresses[index]
            if (sweep > 0f) {
                drawArc(
                    color = ring.color,
                    startAngle = -90f,
                    sweepAngle = sweep,
                    useCenter = false,
                    topLeft = topLeft,
                    size = arcSize,
                    style = Stroke(width = strokePx, cap = StrokeCap.Round)
                )
            }
        }
    }
}

@Composable
private fun RingLegendRow(palette: BitPalette, color: Color, label: String, value: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(9.dp)
                .clip(RoundedCornerShape(50))
                .background(color)
        )
        Spacer(Modifier.width(8.dp))
        Column {
            Text(label, color = palette.secondaryText, fontWeight = FontWeight.SemiBold, fontSize = 11.sp)
            Text(value, color = palette.text, fontWeight = FontWeight.ExtraBold, fontSize = 13.sp)
        }
    }
}

/**
 * Premium summary of one of the two most recent exercise sessions. Health''',
        new='''/**
 * Premium summary of one of the two most recent exercise sessions. Health''',
        desc="remove ActivityRingsCard + RingSpec + ActivityRings + RingLegendRow",
    )

    # -- DashboardCardLayoutPrefs.kt -------------------------------------
    print("==> Removing ACTIVITY_RINGS from DashboardCardType enum")
    apply_edit(
        CARD_LAYOUT_PREFS,
        old='''/**
 * The reorderable/hideable cards on the Today screen, below the pinned Steps
 * hero card (Steps itself is not part of this list -- it always stays first,
 * it's the screen's anchor). Order here is only the fallback DEFAULT_ORDER;
 * the person's actual order/visibility lives in DashboardCardLayoutPrefs.
 */
enum class DashboardCardType(val key: String) {
    ACTIVITY_RINGS("activity_rings"),
    WORKOUT_LATEST("workout_latest"),
    WORKOUT_PREVIOUS("workout_previous"),
    LAST_7_DAYS("last_7_days"),
    PERSONAL_RECORDS("personal_records"),
    STREAK("streak");

    companion object {
        val DEFAULT_ORDER: List<DashboardCardType> = listOf(
            ACTIVITY_RINGS, WORKOUT_LATEST, WORKOUT_PREVIOUS, LAST_7_DAYS, PERSONAL_RECORDS, STREAK
        )''',
        new='''/**
 * The reorderable/hideable cards on the Today screen, below the pinned Steps
 * hero card (Steps itself is not part of this list -- it always stays first,
 * it's the screen's anchor). Order here is only the fallback DEFAULT_ORDER;
 * the person's actual order/visibility lives in DashboardCardLayoutPrefs.
 *
 * ACTIVITY_RINGS was removed (2026-08): steps synced reliably, but Huawei's
 * per-category scope approval left activeCalories denied on real devices
 * far more often than not (see CLAUDE.md / HuaweiAuthFailureReason), and
 * active-minutes only has data on days with a logged workout session rather
 * than ambient activity -- so in practice 2 of the 3 rings usually sat empty
 * regardless of how active the day actually was. A 3-ring visual promising
 * three tracked metrics when only one reliably has data was worse than not
 * showing it at all. Existing users' saved card order/hidden-state strings
 * that still mention "activity_rings" are handled gracefully already --
 * DashboardCardType.fromKey() returns null for unknown keys and
 * allCardsForEditor()/orderedVisibleCards() already drop those via
 * mapNotNull/filter, so no migration was needed for this removal.
 */
enum class DashboardCardType(val key: String) {
    WORKOUT_LATEST("workout_latest"),
    WORKOUT_PREVIOUS("workout_previous"),
    LAST_7_DAYS("last_7_days"),
    PERSONAL_RECORDS("personal_records"),
    STREAK("streak");

    companion object {
        val DEFAULT_ORDER: List<DashboardCardType> = listOf(
            WORKOUT_LATEST, WORKOUT_PREVIOUS, LAST_7_DAYS, PERSONAL_RECORDS, STREAK
        )''',
        desc="remove ACTIVITY_RINGS enum entry + DEFAULT_ORDER reference",
    )

    # -- DashboardViewModel.kt -------------------------------------------
    print("==> Removing dead activeMinutesProgress/caloriesProgress properties")
    apply_edit(
        DASHBOARD_VM,
        old='''    val stepsProgress: Float get() = (stepsToday.toFloat() / stepsGoal.toFloat()).coerceIn(0f, 1f)
    val distanceProgress: Float get() = (distanceMeters / distanceGoalMeters).toFloat().coerceIn(0f, 1f)
    val activeMinutesProgress: Float get() = (workoutMinutesToday.toFloat() / activeMinutesGoal.toFloat()).coerceIn(0f, 1f)
    val caloriesProgress: Float get() = (caloriesKcal / caloriesGoalKcal).toFloat().coerceIn(0f, 1f)
''',
        new='''    val stepsProgress: Float get() = (stepsToday.toFloat() / stepsGoal.toFloat()).coerceIn(0f, 1f)
    val distanceProgress: Float get() = (distanceMeters / distanceGoalMeters).toFloat().coerceIn(0f, 1f)
    // activeMinutesProgress/caloriesProgress removed (2026-08): their only
    // consumer was the removed activity-rings card (see DashboardCardType's
    // doc comment in DashboardCardLayoutPrefs.kt for why). workoutMinutesToday
    // and caloriesKcal themselves are untouched -- still real, synced data,
    // just no longer paired with a goal-progress fraction nothing reads.
''',
        desc="remove activeMinutesProgress/caloriesProgress",
    )

    # -- strings.xml ------------------------------------------------------
    print("==> Removing dashboard_rings_title (EN)")
    apply_edit(
        STRINGS_EN,
        old='    <string name="steps_goal_remaining">%1$s to go</string>\n    <string name="dashboard_rings_title">Activity rings</string>\n    <string name="dashboard_rings_steps">Steps</string>',
        new='    <string name="steps_goal_remaining">%1$s to go</string>\n    <string name="dashboard_rings_steps">Steps</string>',
        desc="remove dashboard_rings_title (EN)",
    )

    print("==> Removing dashboard_rings_title (RU)")
    apply_edit(
        STRINGS_RU,
        old='    <string name="steps_goal_remaining">Ещё %1$s до цели</string>\n    <string name="dashboard_rings_title">Кольца активности</string>\n    <string name="dashboard_rings_steps">Шаги</string>',
        new='    <string name="steps_goal_remaining">Ещё %1$s до цели</string>\n    <string name="dashboard_rings_steps">Шаги</string>',
        desc="remove dashboard_rings_title (RU)",
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
        ["git", "commit", "-m", "Remove activity rings card: 2 of 3 rings rarely had real data"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
