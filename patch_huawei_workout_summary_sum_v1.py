#!/usr/bin/env python3
"""
patch_huawei_workout_summary_sum_v1.py

Fixes a confirmed real-device bug (2026-08-29): a walking workout imported
from Huawei Health showed a correct 2.5 km distance but only 250 steps in
the BitLut dashboard -- an impossible combination for a real walk.

Root cause: HuaweiHealthManager.readActivityRecordSummary() reads Huawei's
per-activity dataSummary sample points. Huawei can split one metric across
multiple SamplePoints of the same DataType within a single activity (one
point per walked segment rather than one point for the whole activity).
The steps/calories/elevation branches took only
`positiveValues.firstOrNull()?.second` -- the FIRST matching point -- and
silently discarded the rest. Distance did not show the same symptom only
because it already had a working fallback (readActivityRecordDistance,
which correctly sums every matching sample) that kicks in whenever the
summary's own distance field is null; steps had no such fallback, so the
bug was fully exposed.

Fix: steps, calories, and elevation/ascent now sum every matching sample
point, exactly like distance already does via its fallback path -- for
consistency, not just a one-off patch, since all four metrics are
equally additive across segments.

Touches only:
  app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt

No Health Connect / Huawei permission, sync-window, or data-contract
changes. No new data categories are read -- this only fixes aggregation
of data BitLut was already reading.

Usage (run from repo root, inside GitHub Codespaces):
    python3 patch_huawei_workout_summary_sum_v1.py
"""

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
MANAGER_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Expected file not found: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / (path.name + ".bak_huawei_workout_summary_sum_v1")
    if not target.exists():
        shutil.copy2(path, target)
        print(f"Backed up {path} -> {target}")


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, description: str) -> bool:
    """Genuine replacement. `old` is not a substring of `new`'s surviving
    text after the edit (the entire `when` block body is restructured), so
    idempotency can safely be keyed on old_str's count alone."""
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == 0 and new_count >= expected_old_count:
        print(f"SKIP (already applied): {description}")
        return False

    if old_count != expected_old_count:
        die(
            f"Anchor count mismatch for '{description}': expected {expected_old_count} "
            f"occurrence(s) of old text, found {old_count}. Refusing to guess."
        )

    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"APPLIED: {description}")
    return True


OLD_BLOCK = '''        points.forEach { point ->
            val dataType = try { point.dataType } catch (_: Exception) { null } ?: return@forEach
            val typeName = dataType.name.lowercase(Locale.ROOT)
            val values = dataType.fields.mapNotNull { field ->
                val numeric = try { point.getFieldValue(field).toNumericDouble() } catch (_: Exception) { null }
                numeric?.let { field.name.lowercase(Locale.ROOT) to it }
            }
            val positiveValues = values.filter { it.second > 0.0 }

            when {
                "distance.total" in typeName -> {
                    distanceMeters = positiveValues.firstOrNull()?.second ?: distanceMeters
                }
                "calories.burnt.total" in typeName || "calories.burned.total" in typeName -> {
                    totalCaloriesKcal = positiveValues.firstOrNull()?.second ?: totalCaloriesKcal
                }
                "steps.total" in typeName -> {
                    steps = positiveValues.firstOrNull()?.second?.toLong()?.takeIf { it > 0L } ?: steps
                }
                "altitude.statistics" in typeName -> {
                    elevationMeters = positiveValues
                        .firstOrNull { (fieldName, _) -> fieldName == "ascent_total" || "ascent" in fieldName }
                        ?.second
                        ?: elevationMeters
                }
            }
        }
'''

NEW_BLOCK = '''        points.forEach { point ->
            val dataType = try { point.dataType } catch (_: Exception) { null } ?: return@forEach
            val typeName = dataType.name.lowercase(Locale.ROOT)
            val values = dataType.fields.mapNotNull { field ->
                val numeric = try { point.getFieldValue(field).toNumericDouble() } catch (_: Exception) { null }
                numeric?.let { field.name.lowercase(Locale.ROOT) to it }
            }
            val positiveValues = values.filter { it.second > 0.0 }

            // Sprint 2026-08-29: Huawei's per-activity dataSummary can split
            // one metric across multiple SamplePoints of the same DataType
            // (e.g. one steps/calories/ascent point per walked segment
            // rather than one point for the whole activity -- the same
            // reason readActivityRecordDistance already sums every matching
            // sample point instead of taking the first). The previous
            // `positiveValues.firstOrNull()` here silently kept only the
            // first segment's value and discarded the rest, which is the
            // confirmed root cause of a real-device report: a walking
            // workout with a correct 2.5 km distance (summed via the
            // fallback path below) showing only 250 steps (the first
            // segment's point, not the activity total). Steps, calories,
            // and ascent are all additive across segments the same way
            // distance is, so all three now sum every matching point
            // instead of keeping only the first.
            when {
                "distance.total" in typeName -> {
                    val sum = positiveValues.sumOf { it.second }
                    if (sum > 0.0) {
                        distanceMeters = (distanceMeters ?: 0.0) + sum
                    }
                }
                "calories.burnt.total" in typeName || "calories.burned.total" in typeName -> {
                    val sum = positiveValues.sumOf { it.second }
                    if (sum > 0.0) {
                        totalCaloriesKcal = (totalCaloriesKcal ?: 0.0) + sum
                    }
                }
                "steps.total" in typeName -> {
                    val sum = positiveValues.sumOf { it.second }.toLong()
                    if (sum > 0L) {
                        steps = (steps ?: 0L) + sum
                    }
                }
                "altitude.statistics" in typeName -> {
                    val sum = positiveValues
                        .filter { (fieldName, _) -> fieldName == "ascent_total" || "ascent" in fieldName }
                        .sumOf { it.second }
                    if (sum > 0.0) {
                        elevationMeters = (elevationMeters ?: 0.0) + sum
                    }
                }
            }
        }
'''


def main() -> None:
    backup(MANAGER_FILE)

    changed = apply_edit(
        MANAGER_FILE,
        old=OLD_BLOCK,
        new=NEW_BLOCK,
        expected_old_count=1,
        description="sum steps/calories/elevation across all Huawei sample points instead of taking only the first",
    )

    if not changed:
        print("Nothing to do: HuaweiHealthManager.kt already sums workout summary metrics.")
    else:
        print("Huawei workout summary fix applied.")

    text = MANAGER_FILE.read_text(encoding="utf-8")
    if text.count("{") != text.count("}"):
        die("Brace mismatch detected in HuaweiHealthManager.kt after patch -- aborting before build.")

    print("patch_huawei_workout_summary_sum_v1.py: structural checks passed.")


if __name__ == "__main__":
    main()
