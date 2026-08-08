#!/usr/bin/env python3
"""
BitLut patch: remove the Elevation ("Подъём") card.

Removes the card entirely per request: the call site, the ElevationSummaryCard
composable itself, and its two helper functions (elevationAndFloorsText,
InsightValueRow) which were only used by this card. dashboard_elevation_value
is kept in strings.xml -- PersonalRecordsCard's "best elevation day" record
still uses it. The underlying elevation/floors sync pipeline (permissions,
Health Connect read/write) is untouched; this is a UI-only removal.

Run from the repo root:
    python3 remove_elevation_card.py
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

    kt = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
    strings_en = "app/src/main/res/values/strings.xml"
    strings_ru = "app/src/main/res/values-ru/strings.xml"

    print("==> Removing Elevation card call site")
    apply_edit(
        kt,
        old='                item { ElevationSummaryCard(palette = palette, state = state) }\n'
            '                item { LastSevenDaysCard(palette = palette, state = state) }',
        new='                item { LastSevenDaysCard(palette = palette, state = state) }',
        desc="remove ElevationSummaryCard call site",
    )

    print("==> Deleting ElevationSummaryCard + its two helper functions")
    apply_edit(
        kt,
        old='@Composable\n'
            'private fun ElevationSummaryCard(palette: BitPalette, state: DashboardUiState) {\n'
            '    SoftCard(palette = palette, accent = HealthAccent.violet, tintWithAccent = true, pressLift = true) {\n'
            '        Row(verticalAlignment = Alignment.CenterVertically) {\n'
            '            Icon(Icons.Rounded.TrendingUp, contentDescription = null, tint = HealthAccent.violet, modifier = Modifier.size(20.dp))\n'
            '            Spacer(Modifier.width(8.dp))\n'
            '            Text(\n'
            '                text = stringResource(R.string.dashboard_elevation_title),\n'
            '                color = palette.text,\n'
            '                fontWeight = FontWeight.ExtraBold,\n'
            '                fontSize = 16.sp\n'
            '            )\n'
            '        }\n'
            '        Spacer(Modifier.height(14.dp))\n'
            '        InsightValueRow(\n'
            '            palette = palette,\n'
            '            label = stringResource(R.string.dashboard_today_short),\n'
            '            value = elevationAndFloorsText(state.elevationMetersToday, state.floorsToday),\n'
            '            accent = HealthAccent.violet\n'
            '        )\n'
            '        Spacer(Modifier.height(10.dp))\n'
            '        InsightValueRow(\n'
            '            palette = palette,\n'
            '            label = stringResource(R.string.dashboard_last_7_days_short),\n'
            '            value = elevationAndFloorsText(state.elevationMeters7d, state.floors7d),\n'
            '            accent = HealthAccent.violet\n'
            '        )\n'
            '    }\n'
            '}\n'
            '\n'
            '@Composable\n'
            'private fun elevationAndFloorsText(elevationMeters: Double, floors: Double): String {\n'
            '    val parts = mutableListOf<String>()\n'
            '    if (elevationMeters > 0.0) {\n'
            '        parts += stringResource(R.string.dashboard_elevation_value, formatOneDecimal(elevationMeters))\n'
            '    }\n'
            '    if (floors > 0.0) {\n'
            '        parts += stringResource(R.string.dashboard_floors_value, formatOneDecimal(floors))\n'
            '    }\n'
            '    return if (parts.isEmpty()) stringResource(R.string.no_data_short) else parts.joinToString(" · ")\n'
            '}\n'
            '\n'
            '@Composable\n'
            'private fun InsightValueRow(palette: BitPalette, label: String, value: String, accent: Color) {\n'
            '    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {\n'
            '        Text(label, color = palette.secondaryText, fontWeight = FontWeight.SemiBold, fontSize = 12.sp, modifier = Modifier.weight(1f))\n'
            '        Text(value, color = accent, fontWeight = FontWeight.Black, fontSize = 15.sp)\n'
            '    }\n'
            '}\n'
            '\n'
            '@Composable\n'
            'private fun LastSevenDaysCard(palette: BitPalette, state: DashboardUiState) {',
        new='@Composable\n'
            'private fun LastSevenDaysCard(palette: BitPalette, state: DashboardUiState) {',
        desc="delete ElevationSummaryCard, elevationAndFloorsText, InsightValueRow",
    )

    print("==> Removing unused Elevation strings (EN) -- dashboard_elevation_value is kept, PersonalRecordsCard still uses it")
    apply_edit(
        strings_en,
        old='    <string name="dashboard_elevation_title">Elevation</string>\n'
            '    <string name="dashboard_today_short">Today</string>\n'
            '    <string name="dashboard_last_7_days_short">Last 7 days</string>\n'
            '    <string name="dashboard_elevation_value">%1$s m</string>\n'
            '    <string name="dashboard_floors_value">%1$s floors</string>',
        new='    <string name="dashboard_elevation_value">%1$s m</string>',
        desc="remove unused Elevation-card strings (EN)",
    )

    print("==> Removing unused Elevation strings (RU)")
    apply_edit(
        strings_ru,
        old='    <string name="dashboard_elevation_title">Подъём</string>\n'
            '    <string name="dashboard_today_short">Сегодня</string>\n'
            '    <string name="dashboard_last_7_days_short">7 дней</string>\n'
            '    <string name="dashboard_elevation_value">%1$s м</string>\n'
            '    <string name="dashboard_floors_value">%1$s эт.</string>',
        new='    <string name="dashboard_elevation_value">%1$s м</string>',
        desc="remove unused Elevation-card strings (RU)",
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
        ["git", "commit", "-m", "Remove Elevation card from Today screen"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
