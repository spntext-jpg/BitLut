#!/usr/bin/env python3
"""
BitLut patch: 2026-08-05 session.

1. Workout cards on the Today screen showed the same running icon for every
   exercise type (a regression from manual edits after the last assistant
   session). Adds workoutIcon(exerciseType) and wires it into
   WorkoutRecencyCard instead of the hardcoded Icons.Rounded.DirectionsRun.
2. The "Elevation" ("Подъём") card was audited end-to-end (permissions ->
   Health Connect read -> ViewModel -> UI) and no bug was found -- this
   script does NOT touch it. Documented here so this isn't silently
   forgotten; see the chat writeup for the audit trail.
3. Removes the Achievements card (AchievementsCard/AchievementDisplay/
   AchievementRow + its call site + its now-unused strings) per request.
   AchievementsStore.achievementSummary() itself is left in place but now
   unused by any screen -- same "dormant, not deleted" precedent already
   used for DashboardWidgetGrid/WeeklyComparisonCard in this project, in
   case a different achievements UI comes back later. Say the word if you'd
   rather that be fully deleted too.

Run from the repo root:
    python3 fix_workout_icons_and_achievements.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

TARGET_FILES = [
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "app/src/main/res/values/strings.xml",
    "app/src/main/res/values-ru/strings.xml",
]


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
    a fallback once OLD is confirmed absent (see CLAUDE.md -- checking NEW
    first has bitten this project before when a short/generic NEW fragment
    coincidentally already existed in an untouched file).
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


def apply_insertion(rel_path: str, anchor: str, new_with_anchor: str,
                     unique_marker: str, desc: str) -> bool:
    """For edits that insert new text immediately before an unchanged
    anchor. `anchor` stays intact as a suffix of `new_with_anchor`, so
    checking anchor-count-first (like apply_edit does) would never see it
    as "gone" and would reapply forever. Idempotency here is instead
    decided by `unique_marker`, a string that only exists once the
    insertion has happened.
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

    kt = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
    strings_en = "app/src/main/res/values/strings.xml"
    strings_ru = "app/src/main/res/values-ru/strings.xml"

    print("==> Patching FinalBitLutShell.kt: workout-type icons")

    apply_edit(
        kt,
        old='import androidx.compose.material.icons.rounded.DirectionsRun\n'
            'import androidx.compose.material.icons.rounded.EmojiEvents',
        new='import androidx.compose.material.icons.rounded.DirectionsRun\n'
            'import androidx.compose.material.icons.rounded.DirectionsWalk\n'
            'import androidx.compose.material.icons.rounded.DirectionsBike\n'
            'import androidx.compose.material.icons.rounded.Pool\n'
            'import androidx.compose.material.icons.rounded.FitnessCenter\n'
            'import androidx.compose.material.icons.rounded.SelfImprovement\n'
            'import androidx.compose.material.icons.rounded.Hiking\n'
            'import androidx.compose.material.icons.rounded.EmojiEvents',
        desc="add workout-type icon imports",
    )

    apply_edit(
        kt,
        old='import androidx.compose.ui.graphics.StrokeCap\n'
            'import com.openhealth.sync.data.AchievementSummary',
        new='import androidx.compose.ui.graphics.StrokeCap\n'
            'import androidx.health.connect.client.records.ExerciseSessionRecord',
        desc="swap now-unused AchievementSummary import for ExerciseSessionRecord "
             "(needed by the new icon mapping)",
    )

    apply_insertion(
        kt,
        anchor='/**\n'
            ' * Premium summary of one of the two most recent exercise sessions. Health\n'
            ' * Connect exposes the session title/type and start/end timestamps here; the\n'
            ' * card deliberately does not invent distance or calories that are not linked\n'
            ' * to the session by the current data model.\n'
            ' */\n'
            '@Composable\n'
            'private fun WorkoutRecencyCard(',
        new_with_anchor='/**\n'
            ' * Maps a Health Connect exercise type to a representative icon so workout\n'
            ' * cards visually distinguish running from cycling, swimming, etc., instead\n'
            ' * of showing the same running icon for every session type. Only covers the\n'
            ' * exercise types common enough in Huawei Health exports to be worth a\n'
            ' * dedicated icon; anything else (including a null/unknown type, e.g. no\n'
            ' * recent workout yet) falls back to the generic running icon that was\n'
            ' * already the card\'s default before per-type icons existed.\n'
            ' */\n'
            'private fun workoutIcon(exerciseType: Int?): ImageVector = when (exerciseType) {\n'
            '    ExerciseSessionRecord.EXERCISE_TYPE_WALKING -> Icons.Rounded.DirectionsWalk\n'
            '    ExerciseSessionRecord.EXERCISE_TYPE_BIKING -> Icons.Rounded.DirectionsBike\n'
            '    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER,\n'
            '    ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL -> Icons.Rounded.Pool\n'
            '    ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING,\n'
            '    ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING -> Icons.Rounded.FitnessCenter\n'
            '    ExerciseSessionRecord.EXERCISE_TYPE_YOGA,\n'
            '    ExerciseSessionRecord.EXERCISE_TYPE_PILATES -> Icons.Rounded.SelfImprovement\n'
            '    ExerciseSessionRecord.EXERCISE_TYPE_HIKING -> Icons.Rounded.Hiking\n'
            '    else -> Icons.Rounded.DirectionsRun\n'
            '}\n'
            '\n'
            '/**\n'
            ' * Premium summary of one of the two most recent exercise sessions. Health\n'
            ' * Connect exposes the session title/type and start/end timestamps here; the\n'
            ' * card deliberately does not invent distance or calories that are not linked\n'
            ' * to the session by the current data model.\n'
            ' */\n'
            '@Composable\n'
            'private fun WorkoutRecencyCard(',
        unique_marker='private fun workoutIcon(exerciseType: Int?): ImageVector',
        desc="add workoutIcon(exerciseType) mapping function",
    )

    apply_edit(
        kt,
        old='                Icon(\n'
            '                    Icons.Rounded.DirectionsRun,\n'
            '                    contentDescription = null,\n'
            '                    tint = accent,\n'
            '                    modifier = Modifier.size(24.dp)\n'
            '                )\n'
            '            }\n'
            '            Spacer(Modifier.width(14.dp))',
        new='                Icon(\n'
            '                    workoutIcon(session?.exerciseType),\n'
            '                    contentDescription = null,\n'
            '                    tint = accent,\n'
            '                    modifier = Modifier.size(24.dp)\n'
            '                )\n'
            '            }\n'
            '            Spacer(Modifier.width(14.dp))',
        desc="use workoutIcon(session.exerciseType) in WorkoutRecencyCard instead "
             "of the hardcoded running icon",
    )

    print("==> Patching FinalBitLutShell.kt: remove Achievements card")

    apply_edit(
        kt,
        old='\n                item { AchievementsCard(palette = palette, summary = state.achievementSummary) }',
        new='',
        desc="remove AchievementsCard call site from the Today screen",
    )

    apply_edit(
        kt,
        old='@Composable\n'
            'private fun AchievementsCard(palette: BitPalette, summary: AchievementSummary) {\n'
            '    val distanceKm = summary.totalDistanceMeters / 1000.0\n'
            '    val items = listOf(\n'
            '        AchievementDisplay(\n'
            '            label = stringResource(R.string.achievement_distance_100),\n'
            '            progress = (distanceKm / 100.0).toFloat(),\n'
            '            value = stringResource(R.string.achievement_distance_progress, formatOneDecimal(distanceKm), "100")\n'
            '        ),\n'
            '        AchievementDisplay(\n'
            '            label = stringResource(R.string.achievement_distance_500),\n'
            '            progress = (distanceKm / 500.0).toFloat(),\n'
            '            value = stringResource(R.string.achievement_distance_progress, formatOneDecimal(distanceKm), "500")\n'
            '        ),\n'
            '        AchievementDisplay(\n'
            '            label = stringResource(R.string.achievement_steps_million),\n'
            '            progress = summary.totalSteps.toFloat() / 1_000_000f,\n'
            '            value = stringResource(R.string.achievement_steps_progress, formatNumber(summary.totalSteps), formatNumber(1_000_000L))\n'
            '        ),\n'
            '        AchievementDisplay(\n'
            '            label = stringResource(R.string.achievement_active_streak_10),\n'
            '            progress = summary.longestActiveStreakDays.toFloat() / 10f,\n'
            '            value = stringResource(R.string.achievement_days_progress, summary.longestActiveStreakDays, 10)\n'
            '        ),\n'
            '        AchievementDisplay(\n'
            '            label = stringResource(R.string.achievement_workouts_50),\n'
            '            progress = summary.totalWorkouts.toFloat() / 50f,\n'
            '            value = stringResource(R.string.achievement_workouts_progress, summary.totalWorkouts, 50)\n'
            '        )\n'
            '    )\n'
            '\n'
            '    SoftCard(palette = palette, accent = HealthAccent.mind, tintWithAccent = true, pressLift = true) {\n'
            '        Row(verticalAlignment = Alignment.CenterVertically) {\n'
            '            Icon(Icons.Rounded.EmojiEvents, contentDescription = null, tint = HealthAccent.mind, modifier = Modifier.size(20.dp))\n'
            '            Spacer(Modifier.width(8.dp))\n'
            '            Column {\n'
            '                Text(stringResource(R.string.dashboard_achievements_title), color = palette.text, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp)\n'
            '                Text(stringResource(R.string.dashboard_achievements_subtitle), color = palette.secondaryText, fontWeight = FontWeight.Medium, fontSize = 10.sp)\n'
            '            }\n'
            '        }\n'
            '        Spacer(Modifier.height(14.dp))\n'
            '        items.forEachIndexed { index, item ->\n'
            '            if (index > 0) Spacer(Modifier.height(12.dp))\n'
            '            AchievementRow(palette = palette, item = item)\n'
            '        }\n'
            '    }\n'
            '}\n'
            '\n'
            'private data class AchievementDisplay(val label: String, val progress: Float, val value: String)\n'
            '\n'
            '@Composable\n'
            'private fun AchievementRow(palette: BitPalette, item: AchievementDisplay) {\n'
            '    val progress = item.progress.coerceIn(0f, 1f)\n'
            '    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {\n'
            '        Column(modifier = Modifier.weight(1f)) {\n'
            '            Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {\n'
            '                Text(item.label, color = palette.text, fontWeight = FontWeight.Bold, fontSize = 12.sp, modifier = Modifier.weight(1f))\n'
            '                Text(if (progress >= 1f) "✓" else item.value, color = if (progress >= 1f) HealthAccent.mind else palette.secondaryText, fontWeight = FontWeight.Black, fontSize = 10.sp)\n'
            '            }\n'
            '            Spacer(Modifier.height(5.dp))\n'
            '            Box(\n'
            '                modifier = Modifier\n'
            '                    .fillMaxWidth()\n'
            '                    .height(6.dp)\n'
            '                    .clip(RoundedCornerShape(99.dp))\n'
            '                    .background(palette.secondaryText.copy(alpha = 0.14f))\n'
            '            ) {\n'
            '                Box(\n'
            '                    modifier = Modifier\n'
            '                        .fillMaxWidth(progress)\n'
            '                        .fillMaxHeight()\n'
            '                        .background(HealthAccent.mind)\n'
            '                )\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '}\n'
            '\n'
            '\n'
            '/**\n'
            ' * Streak card (v1.9.12, sprint 4). Shows the current consecutive-day streak',
        new='/**\n'
            ' * Streak card (v1.9.12, sprint 4). Shows the current consecutive-day streak',
        desc="delete AchievementsCard/AchievementDisplay/AchievementRow composables",
    )

    print("==> Patching strings.xml: remove unused Achievements strings (EN)")
    apply_edit(
        strings_en,
        old='    <string name="dashboard_workout_minutes_value">%1$d min</string>\n'
            '    <string name="dashboard_achievements_title">Achievements</string>\n'
            '    <string name="dashboard_achievements_subtitle">Based on data accumulated by BitLut</string>\n'
            '    <string name="achievement_distance_100">100 km</string>\n'
            '    <string name="achievement_distance_500">500 km</string>\n'
            '    <string name="achievement_steps_million">1 million steps</string>\n'
            '    <string name="achievement_active_streak_10">10 active days in a row</string>\n'
            '    <string name="achievement_workouts_50">50 workouts</string>\n'
            '    <string name="achievement_distance_progress">%1$s / %2$s km</string>\n'
            '    <string name="achievement_steps_progress">%1$s / %2$s steps</string>\n'
            '    <string name="achievement_days_progress">%1$d / %2$d days</string>\n'
            '    <string name="achievement_workouts_progress">%1$d / %2$d workouts</string>\n'
            '</resources>',
        new='    <string name="dashboard_workout_minutes_value">%1$d min</string>\n'
            '</resources>',
        desc="remove unused Achievements strings (EN)",
    )

    print("==> Patching strings.xml: remove unused Achievements strings (RU)")
    apply_edit(
        strings_ru,
        old='    <string name="dashboard_workout_minutes_value">%1$d мин</string>\n'
            '    <string name="dashboard_achievements_title">Достижения</string>\n'
            '    <string name="dashboard_achievements_subtitle">По данным, накопленным BitLut</string>\n'
            '    <string name="achievement_distance_100">100 км</string>\n'
            '    <string name="achievement_distance_500">500 км</string>\n'
            '    <string name="achievement_steps_million">1 миллион шагов</string>\n'
            '    <string name="achievement_active_streak_10">10 активных дней подряд</string>\n'
            '    <string name="achievement_workouts_50">50 тренировок</string>\n'
            '    <string name="achievement_distance_progress">%1$s / %2$s км</string>\n'
            '    <string name="achievement_steps_progress">%1$s / %2$s шагов</string>\n'
            '    <string name="achievement_days_progress">%1$d / %2$d дней</string>\n'
            '    <string name="achievement_workouts_progress">%1$d / %2$d тренировок</string>\n'
            '</resources>',
        new='    <string name="dashboard_workout_minutes_value">%1$d мин</string>\n'
            '</resources>',
        desc="remove unused Achievements strings (RU)",
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
         "Fix workout card icons per exercise type, remove Achievements card"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
