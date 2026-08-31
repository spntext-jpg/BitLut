#!/usr/bin/env python3
"""
patch_navbar_rebuild_sync_status_steps_diag_v1.py

Fixes three real-device regressions/bugs reported 2026-08-30:

1. Bottom navbar: Today/Settings labels were clipped invisible. The
   previous resize shrank AugustDestination's fixed HEIGHT (58->46dp) to
   make it read as secondary next to the Refresh action, but a
   Row.weight(1f) child's height has nothing to do with how prominent it
   looks relative to a sibling -- only width does -- and 46dp was too
   short for a 24dp icon + spacer + 10sp label to lay out without
   clipping. Fix: every control in the bar now shares one common height
   (64dp); visual hierarchy (Refresh = primary action) comes from Refresh
   being WIDER (84dp) than a destination button, not taller. Both
   destination buttons remain identical to each other (same composable,
   same modifier pattern) -- symmetry preserved.

2. Today header "Syncing..." status line: fading it out via
   AnimatedVisibility also collapsed its layout height to zero at the end
   of the exit animation, yanking the subtitle line upward the instant a
   sync finished. Fix: the line's Column is now always present at a fixed
   reserved height; only its alpha animates (graphicsLayer), never its
   presence/layout.

3. Walking workout steps still undercounted (2.5 km, ~200 steps). The
   2026-08-29 sum-across-points fix is real and correct for what it does,
   but only sums Huawei's own ActivitySummary.dataSummary points, which
   are apparently still emitting a low total for steps specifically. A
   raw-stream fallback (mirroring the distance fix) would repeat a
   category of approach this project's own code already documents as
   unreliable for Huawei step totals (see readDailyStepTotals()'s comment)
   -- shipping that blind would be a third unverified guess. This patch
   adds pure diagnostic logging only (every raw dataSummary point's type
   name + field name/value pairs, plus a final match-count summary) so the
   next real sync's logcat gives real evidence for a follow-up fix. No
   computed value changes.

Mandatory workflow already completed before this script was written:
hand-edited mirror -> real diff -> this script generated from that diff ->
tested on a clean extraction with a fake gradlew -> byte-diffed against
the mirror -> re-run for idempotency. See delivery notes.
"""
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

NAVBAR_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt"
SHELL_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
HUAWEI_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Cannot back up missing file: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rel = path.relative_to(REPO_ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(path, dest)


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, expected_new_count: int, description: str) -> None:
    """Genuine replacement. Idempotent via exact old_str occurrence count."""
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == 0 and new_count >= expected_new_count:
        print(f"  [skip] {description} (already applied)")
        return

    if old_count != expected_old_count:
        die(
            f"{description}: expected {expected_old_count} occurrence(s) of anchor "
            f"in {path.name}, found {old_count}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str, description: str) -> None:
    """Pure insertion next to text that itself stays unchanged. Idempotent via unique_marker."""
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"  [skip] {description} (already applied)")
        return

    if text.count(anchor) != 1:
        die(
            f"{description}: expected exactly 1 occurrence of anchor in {path.name}, "
            f"found {text.count(anchor)}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(anchor, new_with_anchor)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def validate_kotlin_braces(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count("{") != text.count("}"):
        die(f"Brace mismatch in {path.name} after patching -- aborting before build.")


def main() -> None:
    for f in (NAVBAR_FILE, SHELL_FILE, HUAWEI_FILE):
        if not f.exists():
            die(f"Expected file not found: {f}")

    print("== 1/3: Navbar rebuild (GlassNavigation.kt) ==")

    apply_edit(
        NAVBAR_FILE,
        old='import androidx.compose.foundation.layout.size\nimport androidx.compose.foundation.shape.RoundedCornerShape',
        new='import androidx.compose.foundation.layout.size\nimport androidx.compose.foundation.layout.width\nimport androidx.compose.foundation.shape.RoundedCornerShape',
        expected_old_count=1,
        expected_new_count=1,
        description="add Modifier.width import",
    )

    apply_insertion(
        NAVBAR_FILE,
        anchor='private val NAV_BAR_OUTER_VERTICAL_MARGIN = 8.dp\n',
        new_with_anchor=(
            'private val NAV_BAR_OUTER_VERTICAL_MARGIN = 8.dp\n'
            '\n'
            '// 2026-08-30: navbar rebuild. The previous resize shrank destination\n'
            "// buttons' HEIGHT (58->46dp) to make them read as secondary next to the\n"
            '// Refresh action, but a Row.weight(1f) child\'s *height* has nothing to do\n'
            '// with how prominent it looks relative to a sibling -- only *width* does,\n'
            '// and the 46dp fixed height was too short for a 24dp icon + spacer + 10sp\n'
            '// label to lay out without the label clipping (confirmed: 24 + 3 + ~13\n'
            '// text line height already exceeds the 36dp inner budget left after 5dp\n'
            '// top/bottom padding). Fix: every control in the bar now shares one\n'
            '// common height so nothing clips or looks vertically lopsided; visual\n'
            '// hierarchy (Refresh reads as the primary action) comes entirely from\n'
            '// Refresh being wider than a destination button, not taller.\n'
            '// BITLUT_NAVBAR_REBUILD_2026_08_30\n'
            'private val NAV_BAR_CONTROL_HEIGHT = 64.dp\n'
            'private val NAV_BAR_SYNC_ACTION_WIDTH = 84.dp\n'
        ),
        unique_marker="BITLUT_NAVBAR_REBUILD_2026_08_30",
        description="insert shared navbar sizing constants",
    )

    apply_edit(
        NAVBAR_FILE,
        old=(
            '    val iconSize by animateDpAsState(\n'
            '        targetValue = if (selected) 17.dp else 16.dp,\n'
            '        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),\n'
            '        label = "destinationIconSize"\n'
            '    )\n'
            '\n'
            '    Column(\n'
            '        modifier = modifier\n'
            '            .height(46.dp)\n'
        ),
        new=(
            '    val iconSize by animateDpAsState(\n'
            '        targetValue = if (selected) 18.dp else 17.dp,\n'
            '        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),\n'
            '        label = "destinationIconSize"\n'
            '    )\n'
            '\n'
            '    Column(\n'
            '        modifier = modifier\n'
            '            .height(NAV_BAR_CONTROL_HEIGHT)\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="AugustDestination: shared height + slightly larger icon size",
    )

    apply_edit(
        NAVBAR_FILE,
        old='            .padding(horizontal = 6.dp, vertical = 5.dp),\n        horizontalAlignment = Alignment.CenterHorizontally,',
        new='            .padding(horizontal = 6.dp, vertical = 6.dp),\n        horizontalAlignment = Alignment.CenterHorizontally,',
        expected_old_count=1,
        expected_new_count=1,
        description="AugustDestination: padding 5dp -> 6dp vertical",
    )

    apply_edit(
        NAVBAR_FILE,
        old=(
            '        Box(\n'
            '            modifier = Modifier\n'
            '                .size(24.dp)\n'
            '                .clip(iconShape)\n'
            '                .background(iconTile),\n'
        ),
        new=(
            '        Box(\n'
            '            modifier = Modifier\n'
            '                .size(26.dp)\n'
            '                .clip(iconShape)\n'
            '                .background(iconTile),\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="AugustDestination: icon tile 24dp -> 26dp",
    )

    apply_edit(
        NAVBAR_FILE,
        old=(
            '        Spacer(Modifier.height(3.dp))\n'
            '        Text(\n'
            '            text = label,\n'
            '            color = contentColor,\n'
            '            fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.SemiBold,\n'
            '            fontSize = 10.sp,\n'
            '            maxLines = 1\n'
            '        )\n'
            '    }\n'
            '}\n'
        ),
        new=(
            '        Spacer(Modifier.height(4.dp))\n'
            '        Text(\n'
            '            text = label,\n'
            '            color = contentColor,\n'
            '            fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.SemiBold,\n'
            '            fontSize = 11.sp,\n'
            '            maxLines = 1\n'
            '        )\n'
            '    }\n'
            '}\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="AugustDestination: label 10sp -> 11sp, spacer 3dp -> 4dp",
    )

    apply_edit(
        NAVBAR_FILE,
        old='    val shape = remember { RoundedCornerShape(22.dp) }\n    val scale by animateFloatAsState(\n        targetValue = if (pressed) 0.97f else 1f,',
        new='    val shape = remember { RoundedCornerShape(24.dp) }\n    val scale by animateFloatAsState(\n        targetValue = if (pressed) 0.97f else 1f,',
        expected_old_count=1,
        expected_new_count=1,
        description="AugustSyncAction: corner radius 22dp -> 24dp (pill, no longer a square)",
    )

    apply_edit(
        NAVBAR_FILE,
        old=(
            '    Box(\n'
            '        modifier = Modifier\n'
            '            .size(72.dp)\n'
            '            .graphicsLayer {\n'
            '                scaleX = scale\n'
            '                scaleY = scale\n'
            '            }\n'
            '            .clip(shape)\n'
            '            .background(fill)\n'
        ),
        new=(
            '    // Same shared height as AugustDestination (NAV_BAR_CONTROL_HEIGHT) so\n'
            '    // the whole bar aligns on one baseline; a wider fixed width (rather\n'
            '    // than a taller box) is what makes this read as the primary action,\n'
            '    // per the 2026-08-30 navbar rebuild note above.\n'
            '    Box(\n'
            '        modifier = Modifier\n'
            '            .width(NAV_BAR_SYNC_ACTION_WIDTH)\n'
            '            .height(NAV_BAR_CONTROL_HEIGHT)\n'
            '            .graphicsLayer {\n'
            '                scaleX = scale\n'
            '                scaleY = scale\n'
            '            }\n'
            '            .clip(shape)\n'
            '            .background(fill)\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="AugustSyncAction: fixed size(72dp) -> width(84dp) x height(shared 64dp)",
    )

    apply_edit(
        NAVBAR_FILE,
        old='            modifier = Modifier\n                .size(34.dp)\n                .graphicsLayer { rotationZ = rotation }',
        new='            modifier = Modifier\n                .size(32.dp)\n                .graphicsLayer { rotationZ = rotation }',
        expected_old_count=1,
        expected_new_count=1,
        description="AugustSyncAction: icon 34dp -> 32dp (fits narrower pill cleanly)",
    )

    validate_kotlin_braces(NAVBAR_FILE)

    print("== 2/3: Sync status layout-jump fix (FinalBitLutShell.kt) ==")

    apply_edit(
        SHELL_FILE,
        old=(
            'import androidx.compose.animation.core.animateFloatAsState\n'
            'import androidx.compose.animation.AnimatedVisibility\n'
            'import androidx.compose.animation.fadeIn\n'
            'import androidx.compose.animation.fadeOut\n'
            'import androidx.compose.foundation.background\n'
        ),
        new=(
            'import androidx.compose.animation.core.animateFloatAsState\n'
            'import androidx.compose.foundation.background\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="remove now-unused AnimatedVisibility/fadeIn/fadeOut imports",
    )

    apply_insertion(
        SHELL_FILE,
        anchor='@Composable\nprivate fun MinimalHeader(\n',
        new_with_anchor=(
            '// Fixed height reserved for MinimalHeader\'s "Syncing..." line at all times\n'
            '// (2026-08-30), so fading it out never collapses layout and shifts the\n'
            '// subtitle below it. 2dp top spacer + an 11sp Bold line\'s rendered height.\n'
            '// BITLUT_SYNC_STATUS_FIXED_HEIGHT_2026_08_30\n'
            'private val SYNC_STATUS_LINE_HEIGHT = 18.dp\n'
            '\n'
            '@Composable\n'
            'private fun MinimalHeader(\n'
        ),
        unique_marker="BITLUT_SYNC_STATUS_FIXED_HEIGHT_2026_08_30",
        description="insert SYNC_STATUS_LINE_HEIGHT constant",
    )

    apply_edit(
        SHELL_FILE,
        old=(
            '        // Background-sync status (2026-08-29): a quiet second line, right\n'
            '        // under the last-sync trailing text, shown only while a sync is\n'
            '        // actually in flight. AnimatedVisibility fades it in on\n'
            '        // isSyncing=true and fades it out (rather than snapping) once\n'
            '        // markSyncCompleted() flips isSyncing back to false, per product\n'
            '        // request. Uses the Tangerine "active" accent (already the navbar\n'
            '        // Refresh action\'s color) rather than introducing a new token.\n'
            '        AnimatedVisibility(\n'
            '            visible = isSyncing,\n'
            '            enter = fadeIn(animationSpec = tween(AugustMotion.MediumMs, easing = AugustMotion.StandardEasing)),\n'
            '            exit = fadeOut(animationSpec = tween(AugustMotion.MediumMs, easing = AugustMotion.StandardEasing))\n'
            '        ) {\n'
            '            Column {\n'
            '                Spacer(Modifier.height(2.dp))\n'
            '                Text(\n'
            '                    text = stringResource(R.string.sync_status_updating),\n'
            '                    color = AugustColor.Tangerine,\n'
            '                    fontWeight = FontWeight.Bold,\n'
            '                    fontSize = 11.sp,\n'
            '                    maxLines = 1,\n'
            '                    modifier = Modifier.fillMaxWidth()\n'
            '                )\n'
            '            }\n'
            '        }\n'
        ),
        new=(
            '        // Background-sync status (2026-08-29, fixed 2026-08-30): a quiet\n'
            '        // second line, right under the last-sync trailing text, shown only\n'
            '        // while a sync is actually in flight. The original AnimatedVisibility\n'
            '        // faded the line in/out but -- as AnimatedVisibility always does when\n'
            '        // it becomes invisible -- also collapsed its layout height to zero at\n'
            '        // the end of the exit animation, yanking the subtitle line upward the\n'
            '        // instant a sync finished (confirmed real-device report: a visible\n'
            '        // layout jump right when "Syncing..." disappeared). Fix: the Column\n'
            '        // is now always present at a fixed height (reserving the line\'s\n'
            '        // space at all times) and only its alpha animates via graphicsLayer,\n'
            '        // matching the alpha-only pattern already used elsewhere in this\n'
            '        // file (see AugustDestination\'s press-scale graphicsLayer in\n'
            '        // GlassNavigation.kt) rather than toggling presence/layout. Uses the\n'
            '        // Tangerine "active" accent (already the navbar Refresh action\'s\n'
            '        // color) rather than introducing a new token.\n'
            '        val syncStatusAlpha by animateFloatAsState(\n'
            '            targetValue = if (isSyncing) 1f else 0f,\n'
            '            animationSpec = tween(AugustMotion.MediumMs, easing = AugustMotion.StandardEasing),\n'
            '            label = "syncStatusAlpha"\n'
            '        )\n'
            '        Column(\n'
            '            modifier = Modifier\n'
            '                .height(SYNC_STATUS_LINE_HEIGHT)\n'
            '                .graphicsLayer { alpha = syncStatusAlpha }\n'
            '        ) {\n'
            '            Spacer(Modifier.height(2.dp))\n'
            '            Text(\n'
            '                text = stringResource(R.string.sync_status_updating),\n'
            '                color = AugustColor.Tangerine,\n'
            '                fontWeight = FontWeight.Bold,\n'
            '                fontSize = 11.sp,\n'
            '                maxLines = 1,\n'
            '                modifier = Modifier.fillMaxWidth()\n'
            '            )\n'
            '        }\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="replace AnimatedVisibility fade with alpha-only, fixed-height Column",
    )

    validate_kotlin_braces(SHELL_FILE)

    print("== 3/3: Steps diagnostic logging (HuaweiHealthManager.kt) ==")

    apply_edit(
        HUAWEI_FILE,
        old=(
            '        var distanceMeters: Double? = null\n'
            '        var totalCaloriesKcal: Double? = null\n'
            '        var elevationMeters: Double? = null\n'
            '        var steps: Long? = null\n'
            '\n'
            '        points.forEach { point ->\n'
            '            val dataType = try { point.dataType } catch (_: Exception) { null } ?: return@forEach\n'
            '            val typeName = dataType.name.lowercase(Locale.ROOT)\n'
            '            val values = dataType.fields.mapNotNull { field ->\n'
            '                val numeric = try { point.getFieldValue(field).toNumericDouble() } catch (_: Exception) { null }\n'
            '                numeric?.let { field.name.lowercase(Locale.ROOT) to it }\n'
            '            }\n'
            '            val positiveValues = values.filter { it.second > 0.0 }\n'
            '\n'
            '            // Sprint 2026-08-29: Huawei\'s per-activity dataSummary can split\n'
        ),
        new=(
            '        var distanceMeters: Double? = null\n'
            '        var totalCaloriesKcal: Double? = null\n'
            '        var elevationMeters: Double? = null\n'
            '        var steps: Long? = null\n'
            '        var stepsMatchedPointCount = 0\n'
            '\n'
            '        // Sprint 2026-08-30 diagnostic: the 2026-08-29 sum-across-points fix\n'
            '        // is confirmed correct for what it does, but a real-device report\n'
            '        // still shows an undercount (2.5 km correctly summed via the\n'
            '        // distance fallback path below, steps still far too low from this\n'
            '        // summary-only path). Distance has a second, richer data source\n'
            "        // (readActivityRecordDistance's raw getSampleSet(record) samples);\n"
            "        // steps has no equivalent, and this project's own prior lesson\n"
            "        // (see readDailyStepTotals()'s doc comment) already found raw\n"
            '        // DT_CONTINUOUS_STEPS_DELTA samples unreliable for Huawei step\n'
            '        // totals, so blindly adding a steps raw-stream fallback here would\n'
            '        // repeat a category of fix already flagged as unsafe, without real\n'
            '        // per-point evidence from this specific bug. Logging every raw\n'
            '        // dataSummary point (type name + every field name/value, matched or\n'
            '        // not) is a pure, zero-risk addition -- it changes no computed\n'
            "        // value -- so the next real sync's logcat gives ground truth\n"
            '        // (whether Huawei is only emitting one low-value steps.total point,\n'
            '        // several points that our name/field matching silently rejects, or\n'
            "        // a genuinely-authoritative-but-low total from Huawei's own side)\n"
            '        // instead of guessing a third structural fix blind.\n'
            '        points.forEach { point ->\n'
            '            val dataType = try { point.dataType } catch (_: Exception) { null } ?: return@forEach\n'
            '            val typeName = dataType.name.lowercase(Locale.ROOT)\n'
            '            val values = dataType.fields.mapNotNull { field ->\n'
            '                val numeric = try { point.getFieldValue(field).toNumericDouble() } catch (_: Exception) { null }\n'
            '                numeric?.let { field.name.lowercase(Locale.ROOT) to it }\n'
            '            }\n'
            '            val positiveValues = values.filter { it.second > 0.0 }\n'
            '            AppLogger.d(\n'
            '                TAG,\n'
            '                "Huawei activity summary point: type=$typeName fields=$values"\n'
            '            )\n'
            '\n'
            '            // Sprint 2026-08-29: Huawei\'s per-activity dataSummary can split\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="add per-point diagnostic logging + match counter declaration",
    )

    apply_edit(
        HUAWEI_FILE,
        old=(
            '                "steps.total" in typeName -> {\n'
            '                    val sum = positiveValues.sumOf { it.second }.toLong()\n'
            '                    if (sum > 0L) {\n'
            '                        steps = (steps ?: 0L) + sum\n'
            '                    }\n'
            '                }\n'
        ),
        new=(
            '                "steps.total" in typeName -> {\n'
            '                    stepsMatchedPointCount += 1\n'
            '                    val sum = positiveValues.sumOf { it.second }.toLong()\n'
            '                    if (sum > 0L) {\n'
            '                        steps = (steps ?: 0L) + sum\n'
            '                    }\n'
            '                }\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="count matched steps.total points",
    )

    apply_edit(
        HUAWEI_FILE,
        old=(
            '        }\n'
            '\n'
            '        return HuaweiWorkoutSummaryMetrics(\n'
            '            distanceMeters = distanceMeters?.takeIf { it > 0.0 },\n'
            '            totalCaloriesKcal = totalCaloriesKcal?.takeIf { it > 0.0 },\n'
            '            elevationMeters = elevationMeters?.takeIf { it > 0.0 },\n'
            '            steps = steps?.takeIf { it > 0L }\n'
            '        )\n'
            '    }\n'
        ),
        new=(
            '        }\n'
            '\n'
            '        AppLogger.i(\n'
            '            TAG,\n'
            '            "Huawei activity summary steps diagnostic: totalPoints=${points.size} " +\n'
            '                "stepsTotalPointsMatched=$stepsMatchedPointCount summedSteps=${steps ?: "missing"}"\n'
            '        )\n'
            '\n'
            '        return HuaweiWorkoutSummaryMetrics(\n'
            '            distanceMeters = distanceMeters?.takeIf { it > 0.0 },\n'
            '            totalCaloriesKcal = totalCaloriesKcal?.takeIf { it > 0.0 },\n'
            '            elevationMeters = elevationMeters?.takeIf { it > 0.0 },\n'
            '            steps = steps?.takeIf { it > 0L }\n'
            '        )\n'
            '    }\n'
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="add final steps diagnostic summary log",
    )

    validate_kotlin_braces(HUAWEI_FILE)

    print("== Build gate: :app:compileDebugKotlin ==")
    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found at repo root")

    result = subprocess.run(
        [
            str(gradlew), ":app:compileDebugKotlin",
            "--no-daemon", "--max-workers=1", "--no-watch-fs", "--console=plain",
            "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
            "-Pkotlin.compiler.execution.strategy=in-process",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    print(result.stdout[-4000:])
    if result.returncode != 0:
        print(result.stderr[-4000:], file=sys.stderr)
        die("compileDebugKotlin failed -- not committing/pushing. See output above.")

    print("== Compile gate passed. Checking for changes to commit. ==")
    subprocess.run(["git", "add", "-A"], cwd=str(REPO_ROOT), check=True)

    status_result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    if not status_result.stdout.strip():
        print("Nothing staged to commit (all steps already applied on a prior run). Skipping commit/push.")
        print("Done.")
        return

    commit_msg = (
        "Fix navbar label clipping, sync-status layout jump, add steps diagnostic logging\n\n"
        "- GlassNavigation.kt: navbar controls now share one height (64dp) so\n"
        "  Today/Settings labels no longer clip; Refresh reads as primary via\n"
        "  width (84dp) not height. Both destination buttons remain identical.\n"
        "- FinalBitLutShell.kt: 'Syncing...' status line now animates alpha only\n"
        "  at a fixed reserved height, eliminating the layout jump when a sync\n"
        "  completes and the line fades out.\n"
        "- HuaweiHealthManager.kt: added pure diagnostic logging (no behavior\n"
        "  change) around readActivityRecordSummary()'s steps handling to gather\n"
        "  real-device evidence for the still-open walking-steps undercount.\n"
    )
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    if commit_result.returncode != 0:
        print(commit_result.stdout)
        print(commit_result.stderr, file=sys.stderr)
        die("git commit failed")
    print(commit_result.stdout)

    push_result = subprocess.run(
        ["git", "push", "origin", "HEAD:main"], cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    print(push_result.stdout)
    if push_result.returncode != 0:
        print(push_result.stderr, file=sys.stderr)
        die("git push failed")

    print("Done.")


if __name__ == "__main__":
    main()
