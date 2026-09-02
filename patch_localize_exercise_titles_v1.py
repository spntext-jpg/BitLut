#!/usr/bin/env python3
"""
patch_localize_exercise_titles_v1.py

Localizes the fallback workout title BitLut writes to Health Connect when
Huawei does not provide its own name for a session (e.g. "Yoga" always
being exported in English, regardless of device locale). Adds a Russian
title for Russian-locale devices, matching Google's own official Russian
terminology for these activity types (support.google.com/fit, which uses
the same activity taxonomy as Health Connect).

WHAT THIS DOES NOT TOUCH:
- HuaweiWorkoutTypeMapper.canonicalName() / .healthConnectType(): these
  remain byte-for-byte unchanged. They are the internal English routing
  key used to pick the Health Connect ExerciseType constant, and nothing
  about that logic is locale-sensitive or should ever be.
- Any workout that already has a real Huawei-provided name (session.title
  from rawName): those pass through completely unaffected, exactly as
  before. Only the *fallback* used when Huawei gives no name of its own
  is now locale-aware.
- HuaweiExportParser's own explicit-name fallback gets the identical
  treatment for consistency between the live-sync and archive-import
  paths.

HOW: Health Connect's ExerciseType int constant is the platform's only
locale-independent identifier -- it does not ship its own localized
label (verified: no getLocalizedName()-style API exists on
ExerciseSessionRecord's client library). So this patch adds:
  1. 57 new string resources (one per EXERCISE_TYPE_* constant reachable
     from healthConnectType()) to values/strings.xml (English) and
     values-ru/strings.xml (Russian).
  2. HuaweiWorkoutTypeMapper.localizedDisplayName(context, exerciseType),
     a new function mapping the stable int constant to the right string
     resource via context.getString() -- which already returns the
     locale-correct value in whichever values-* folder Android picked
     for the device, no manual locale detection needed.
  3. Both title-fallback call sites (HuaweiHealthManager's live read,
     HuaweiExportParser's archive import) now call this instead of
     falling back to the English canonical string.

ONE-TIME SIDE EFFECT WORTH KNOWING ABOUT: GoogleHealthManager's
workoutFingerprint() hashes session.title as part of its content
signature used for clientRecordVersion (see workoutRecordVersion()). On
a Russian-locale device, changing what this fallback title reads (e.g.
"Yoga" -> "Йога") changes that fingerprint for every already-synced
workout that used the fallback. This means the very next background
sync after this patch lands will detect a "changed" fingerprint for
those workouts and upsert them with a new clientRecordVersion (bumping
the record, not duplicating or losing anything) -- this is exactly the
mechanism workoutRecordVersion() was built for (letting a genuine
Huawei-side correction propagate), it just also fires here as a
one-time consequence of the title now being localized. No permissions,
sync window, or advanced-category logic changes.

Mandatory workflow already completed before this script was written:
hand-edited mirror -> real diff (diff -u against the original tree) ->
this script generated from that diff -> tested on a clean extraction
with a fake gradlew -> byte-diffed against the mirror -> re-run for
idempotency.
"""
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

STRINGS_EN = REPO_ROOT / "app/src/main/res/values/strings.xml"
STRINGS_RU = REPO_ROOT / "app/src/main/res/values-ru/strings.xml"
WORKOUT_MAPPER_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiWorkoutTypeMapper.kt"
HUAWEI_MANAGER_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"
EXPORT_PARSER_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/import/HuaweiExportParser.kt"


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


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, description: str) -> None:
    """Genuine replacement. Idempotent via exact old_str occurrence count.
    Use only when old_str does NOT survive as a substring of new_str."""
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == 0 and new_count > 0:
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
    """Pure insertion: anchor text survives unchanged in the result, so
    idempotency is checked via unique_marker (present only in the newly
    inserted content), not via anchor occurrence count."""
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"  [skip] {description} (already applied)")
        return

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(
            f"{description}: expected exactly 1 occurrence of insertion anchor "
            f"in {path.name}, found {anchor_count}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(anchor, new_with_anchor)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def validate_xml(path: Path, description: str) -> None:
    try:
        ET.parse(path)
    except ET.ParseError as e:
        die(f"{description}: {path.name} failed to parse as XML after edits: {e}")
    print(f"  [ok] {description}: {path.name} parses cleanly")


def check_string_parity() -> None:
    def keys(path: Path) -> set:
        return {c.get("name") for c in ET.parse(path).getroot() if c.get("name")}

    en_keys = keys(STRINGS_EN)
    ru_keys = keys(STRINGS_RU)
    missing_in_ru = sorted(en_keys - ru_keys)
    missing_in_en = sorted(ru_keys - en_keys)
    if missing_in_ru or missing_in_en:
        die(
            "EN/RU string key parity broken after patch. "
            f"Missing in RU: {missing_in_ru}. Missing in EN: {missing_in_en}."
        )
    print(f"  [ok] EN/RU string parity: {len(en_keys)} keys on both sides")


def run_compile_gate() -> None:
    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found; cannot run compile gate")

    cmd = [
        str(gradlew),
        ":app:compileDebugKotlin",
        "--no-daemon",
        "--max-workers=1",
        "--no-watch-fs",
        "--console=plain",
        "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
        "-Pkotlin.compiler.execution.strategy=in-process",
    ]
    print("Running compile gate: " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        die("Compile gate failed. No commit/push performed. See Gradle output above.")


def git_commit_and_push() -> None:
    subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT, check=True)
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    if not status.stdout.strip():
        print("Nothing to commit (already applied and clean).")
        return

    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Localize exported workout title fallback (RU) for Health Connect exercise types",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT, check=True)


EN_STRINGS_BLOCK = """
    <!-- Localized exercise-type display names (2026-09-01): fallback title
         used only when Huawei does not provide its own workout name, so
         the exported Health Connect title matches the device locale
         instead of always being English. See
         HuaweiWorkoutTypeMapper.localizedDisplayName(). -->
    <string name="exercise_type_badminton">Badminton</string>
    <string name="exercise_type_baseball">Baseball</string>
    <string name="exercise_type_basketball">Basketball</string>
    <string name="exercise_type_biking">Cycling</string>
    <string name="exercise_type_biking_stationary">Indoor cycling</string>
    <string name="exercise_type_boxing">Boxing</string>
    <string name="exercise_type_calisthenics">Calisthenics</string>
    <string name="exercise_type_cricket">Cricket</string>
    <string name="exercise_type_dancing">Dancing</string>
    <string name="exercise_type_elliptical">Elliptical</string>
    <string name="exercise_type_exercise_class">Aerobics</string>
    <string name="exercise_type_fencing">Fencing</string>
    <string name="exercise_type_football_american">American football</string>
    <string name="exercise_type_football_australian">Australian football</string>
    <string name="exercise_type_frisbee_disc">Flying disc</string>
    <string name="exercise_type_golf">Golf</string>
    <string name="exercise_type_gymnastics">Gymnastics</string>
    <string name="exercise_type_handball">Handball</string>
    <string name="exercise_type_hiit">HIIT</string>
    <string name="exercise_type_hiking">Hiking</string>
    <string name="exercise_type_ice_hockey">Ice hockey</string>
    <string name="exercise_type_ice_skating">Ice skating</string>
    <string name="exercise_type_martial_arts">Martial arts</string>
    <string name="exercise_type_other_workout">Workout</string>
    <string name="exercise_type_paddling">Paddling</string>
    <string name="exercise_type_paragliding">Paragliding</string>
    <string name="exercise_type_pilates">Pilates</string>
    <string name="exercise_type_racquetball">Racquetball</string>
    <string name="exercise_type_rock_climbing">Rock climbing</string>
    <string name="exercise_type_rowing">Rowing</string>
    <string name="exercise_type_rowing_machine">Rowing machine</string>
    <string name="exercise_type_rugby">Rugby</string>
    <string name="exercise_type_running">Running</string>
    <string name="exercise_type_running_treadmill">Treadmill running</string>
    <string name="exercise_type_sailing">Sailing</string>
    <string name="exercise_type_scuba_diving">Scuba diving</string>
    <string name="exercise_type_skating">Skating</string>
    <string name="exercise_type_skiing">Skiing</string>
    <string name="exercise_type_snowboarding">Snowboarding</string>
    <string name="exercise_type_snowshoeing">Snowshoeing</string>
    <string name="exercise_type_soccer">Football</string>
    <string name="exercise_type_softball">Softball</string>
    <string name="exercise_type_squash">Squash</string>
    <string name="exercise_type_stair_climbing">Stair climbing</string>
    <string name="exercise_type_stair_climbing_machine">Stair climbing machine</string>
    <string name="exercise_type_strength_training">Strength training</string>
    <string name="exercise_type_surfing">Surfing</string>
    <string name="exercise_type_swimming_open_water">Open water swimming</string>
    <string name="exercise_type_swimming_pool">Pool swimming</string>
    <string name="exercise_type_table_tennis">Table tennis</string>
    <string name="exercise_type_tennis">Tennis</string>
    <string name="exercise_type_volleyball">Volleyball</string>
    <string name="exercise_type_walking">Walking</string>
    <string name="exercise_type_water_polo">Water polo</string>
    <string name="exercise_type_weightlifting">Weightlifting</string>
    <string name="exercise_type_wheelchair">Wheelchair</string>
    <string name="exercise_type_yoga">Yoga</string>
</resources>"""

RU_STRINGS_BLOCK = """
    <!-- Localized exercise-type display names (2026-09-01): fallback title
         used only when Huawei does not provide its own workout name, so
         the exported Health Connect title matches the device locale
         instead of always being English. See
         HuaweiWorkoutTypeMapper.localizedDisplayName(). -->
    <string name="exercise_type_badminton">Бадминтон</string>
    <string name="exercise_type_baseball">Бейсбол</string>
    <string name="exercise_type_basketball">Баскетбол</string>
    <string name="exercise_type_biking">Велоспорт</string>
    <string name="exercise_type_biking_stationary">Велоаэробика</string>
    <string name="exercise_type_boxing">Бокс</string>
    <string name="exercise_type_calisthenics">Калистеника</string>
    <string name="exercise_type_cricket">Крикет</string>
    <string name="exercise_type_dancing">Танцы</string>
    <string name="exercise_type_elliptical">Эллиптический тренажёр</string>
    <string name="exercise_type_exercise_class">Аэробика</string>
    <string name="exercise_type_fencing">Фехтование</string>
    <string name="exercise_type_football_american">Американский футбол</string>
    <string name="exercise_type_football_australian">Австралийский футбол</string>
    <string name="exercise_type_frisbee_disc">Фрисби</string>
    <string name="exercise_type_golf">Гольф</string>
    <string name="exercise_type_gymnastics">Гимнастика</string>
    <string name="exercise_type_handball">Гандбол</string>
    <string name="exercise_type_hiit">Интенсивная интервальная тренировка</string>
    <string name="exercise_type_hiking">Пеший туризм</string>
    <string name="exercise_type_ice_hockey">Хоккей</string>
    <string name="exercise_type_ice_skating">Катание на коньках</string>
    <string name="exercise_type_martial_arts">Единоборства</string>
    <string name="exercise_type_other_workout">Тренировка</string>
    <string name="exercise_type_paddling">Гребля на каноэ</string>
    <string name="exercise_type_paragliding">Парапланеризм</string>
    <string name="exercise_type_pilates">Пилатес</string>
    <string name="exercise_type_racquetball">Рэкетбол</string>
    <string name="exercise_type_rock_climbing">Скалолазание</string>
    <string name="exercise_type_rowing">Академическая гребля</string>
    <string name="exercise_type_rowing_machine">Гребной тренажёр</string>
    <string name="exercise_type_rugby">Регби</string>
    <string name="exercise_type_running">Бег</string>
    <string name="exercise_type_running_treadmill">Бег на дорожке</string>
    <string name="exercise_type_sailing">Парусный спорт</string>
    <string name="exercise_type_scuba_diving">Дайвинг</string>
    <string name="exercise_type_skating">Катание на роликах</string>
    <string name="exercise_type_skiing">Лыжи</string>
    <string name="exercise_type_snowboarding">Сноубординг</string>
    <string name="exercise_type_snowshoeing">Ходьба на снегоступах</string>
    <string name="exercise_type_soccer">Футбол</string>
    <string name="exercise_type_softball">Софтбол</string>
    <string name="exercise_type_squash">Сквош</string>
    <string name="exercise_type_stair_climbing">Подъём по лестнице</string>
    <string name="exercise_type_stair_climbing_machine">Степпер</string>
    <string name="exercise_type_strength_training">Силовой тренинг</string>
    <string name="exercise_type_surfing">Сёрфинг</string>
    <string name="exercise_type_swimming_open_water">Плавание в открытой воде</string>
    <string name="exercise_type_swimming_pool">Плавание</string>
    <string name="exercise_type_table_tennis">Настольный теннис</string>
    <string name="exercise_type_tennis">Теннис</string>
    <string name="exercise_type_volleyball">Волейбол</string>
    <string name="exercise_type_walking">Ходьба</string>
    <string name="exercise_type_water_polo">Водное поло</string>
    <string name="exercise_type_weightlifting">Тяжёлая атлетика</string>
    <string name="exercise_type_wheelchair">Инвалидная коляска</string>
    <string name="exercise_type_yoga">Йога</string>
</resources>"""

MAPPER_FUNCTION_BLOCK = """

    /**
     * Health Connect's ExerciseType int constant is the only locale-independent
     * identifier the platform standardizes; it does not ship its own localized
     * label. Every entry here maps one EXERCISE_TYPE_* constant reachable from
     * healthConnectType() above to a string resource in values/values-ru, so
     * getString() returns the right language for the device's locale.
     */
    // BITLUT_EXERCISE_TYPE_LOCALIZATION_2026_09_01
    private val displayNameRes: Map<Int, Int> = mapOf(
        ExerciseSessionRecord.EXERCISE_TYPE_BADMINTON to R.string.exercise_type_badminton,
        ExerciseSessionRecord.EXERCISE_TYPE_BASEBALL to R.string.exercise_type_baseball,
        ExerciseSessionRecord.EXERCISE_TYPE_BASKETBALL to R.string.exercise_type_basketball,
        ExerciseSessionRecord.EXERCISE_TYPE_BIKING to R.string.exercise_type_biking,
        ExerciseSessionRecord.EXERCISE_TYPE_BIKING_STATIONARY to R.string.exercise_type_biking_stationary,
        ExerciseSessionRecord.EXERCISE_TYPE_BOXING to R.string.exercise_type_boxing,
        ExerciseSessionRecord.EXERCISE_TYPE_CALISTHENICS to R.string.exercise_type_calisthenics,
        ExerciseSessionRecord.EXERCISE_TYPE_CRICKET to R.string.exercise_type_cricket,
        ExerciseSessionRecord.EXERCISE_TYPE_DANCING to R.string.exercise_type_dancing,
        ExerciseSessionRecord.EXERCISE_TYPE_ELLIPTICAL to R.string.exercise_type_elliptical,
        ExerciseSessionRecord.EXERCISE_TYPE_EXERCISE_CLASS to R.string.exercise_type_exercise_class,
        ExerciseSessionRecord.EXERCISE_TYPE_FENCING to R.string.exercise_type_fencing,
        ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AMERICAN to R.string.exercise_type_football_american,
        ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AUSTRALIAN to R.string.exercise_type_football_australian,
        ExerciseSessionRecord.EXERCISE_TYPE_FRISBEE_DISC to R.string.exercise_type_frisbee_disc,
        ExerciseSessionRecord.EXERCISE_TYPE_GOLF to R.string.exercise_type_golf,
        ExerciseSessionRecord.EXERCISE_TYPE_GYMNASTICS to R.string.exercise_type_gymnastics,
        ExerciseSessionRecord.EXERCISE_TYPE_HANDBALL to R.string.exercise_type_handball,
        ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING to R.string.exercise_type_hiit,
        ExerciseSessionRecord.EXERCISE_TYPE_HIKING to R.string.exercise_type_hiking,
        ExerciseSessionRecord.EXERCISE_TYPE_ICE_HOCKEY to R.string.exercise_type_ice_hockey,
        ExerciseSessionRecord.EXERCISE_TYPE_ICE_SKATING to R.string.exercise_type_ice_skating,
        ExerciseSessionRecord.EXERCISE_TYPE_MARTIAL_ARTS to R.string.exercise_type_martial_arts,
        ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT to R.string.exercise_type_other_workout,
        ExerciseSessionRecord.EXERCISE_TYPE_PADDLING to R.string.exercise_type_paddling,
        ExerciseSessionRecord.EXERCISE_TYPE_PARAGLIDING to R.string.exercise_type_paragliding,
        ExerciseSessionRecord.EXERCISE_TYPE_PILATES to R.string.exercise_type_pilates,
        ExerciseSessionRecord.EXERCISE_TYPE_RACQUETBALL to R.string.exercise_type_racquetball,
        ExerciseSessionRecord.EXERCISE_TYPE_ROCK_CLIMBING to R.string.exercise_type_rock_climbing,
        ExerciseSessionRecord.EXERCISE_TYPE_ROWING to R.string.exercise_type_rowing,
        ExerciseSessionRecord.EXERCISE_TYPE_ROWING_MACHINE to R.string.exercise_type_rowing_machine,
        ExerciseSessionRecord.EXERCISE_TYPE_RUGBY to R.string.exercise_type_rugby,
        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING to R.string.exercise_type_running,
        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING_TREADMILL to R.string.exercise_type_running_treadmill,
        ExerciseSessionRecord.EXERCISE_TYPE_SAILING to R.string.exercise_type_sailing,
        ExerciseSessionRecord.EXERCISE_TYPE_SCUBA_DIVING to R.string.exercise_type_scuba_diving,
        ExerciseSessionRecord.EXERCISE_TYPE_SKATING to R.string.exercise_type_skating,
        ExerciseSessionRecord.EXERCISE_TYPE_SKIING to R.string.exercise_type_skiing,
        ExerciseSessionRecord.EXERCISE_TYPE_SNOWBOARDING to R.string.exercise_type_snowboarding,
        ExerciseSessionRecord.EXERCISE_TYPE_SNOWSHOEING to R.string.exercise_type_snowshoeing,
        ExerciseSessionRecord.EXERCISE_TYPE_SOCCER to R.string.exercise_type_soccer,
        ExerciseSessionRecord.EXERCISE_TYPE_SOFTBALL to R.string.exercise_type_softball,
        ExerciseSessionRecord.EXERCISE_TYPE_SQUASH to R.string.exercise_type_squash,
        ExerciseSessionRecord.EXERCISE_TYPE_STAIR_CLIMBING to R.string.exercise_type_stair_climbing,
        ExerciseSessionRecord.EXERCISE_TYPE_STAIR_CLIMBING_MACHINE to R.string.exercise_type_stair_climbing_machine,
        ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING to R.string.exercise_type_strength_training,
        ExerciseSessionRecord.EXERCISE_TYPE_SURFING to R.string.exercise_type_surfing,
        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER to R.string.exercise_type_swimming_open_water,
        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL to R.string.exercise_type_swimming_pool,
        ExerciseSessionRecord.EXERCISE_TYPE_TABLE_TENNIS to R.string.exercise_type_table_tennis,
        ExerciseSessionRecord.EXERCISE_TYPE_TENNIS to R.string.exercise_type_tennis,
        ExerciseSessionRecord.EXERCISE_TYPE_VOLLEYBALL to R.string.exercise_type_volleyball,
        ExerciseSessionRecord.EXERCISE_TYPE_WALKING to R.string.exercise_type_walking,
        ExerciseSessionRecord.EXERCISE_TYPE_WATER_POLO to R.string.exercise_type_water_polo,
        ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING to R.string.exercise_type_weightlifting,
        ExerciseSessionRecord.EXERCISE_TYPE_WHEELCHAIR to R.string.exercise_type_wheelchair,
        ExerciseSessionRecord.EXERCISE_TYPE_YOGA to R.string.exercise_type_yoga
    )

    /**
     * Localized fallback title for a workout, used only when Huawei did not
     * provide its own name for the session. [exerciseType] should be the
     * value already returned by [healthConnectType] for this record. Falls
     * back to the generic "Workout"/"Тренировка" string for any type not in
     * the table (there should not be any, since every branch of
     * [healthConnectType] is covered above).
     */
    fun localizedDisplayName(context: Context, exerciseType: Int): String {
        val resId = displayNameRes[exerciseType] ?: R.string.exercise_type_other_workout
        return context.getString(resId)
    }
}"""


def main() -> None:
    print("=== 1/5: Adding localized string resources (EN) ===")
    apply_insertion(
        STRINGS_EN,
        anchor="</resources>",
        new_with_anchor=EN_STRINGS_BLOCK,
        unique_marker="exercise_type_badminton",
        description="values/strings.xml: add 57 exercise_type_* strings",
    )

    print("=== 2/5: Adding localized string resources (RU) ===")
    apply_insertion(
        STRINGS_RU,
        anchor="</resources>",
        new_with_anchor=RU_STRINGS_BLOCK,
        unique_marker="exercise_type_badminton",
        description="values-ru/strings.xml: add 57 exercise_type_* strings",
    )

    print("=== 3/5: Adding HuaweiWorkoutTypeMapper.localizedDisplayName() ===")
    apply_edit(
        WORKOUT_MAPPER_FILE,
        old=(
            "package com.openhealth.sync.data\n"
            "\n"
            "import androidx.health.connect.client.records.ExerciseSessionRecord\n"
            "import java.util.Locale\n"
        ),
        new=(
            "package com.openhealth.sync.data\n"
            "\n"
            "import android.content.Context\n"
            "import androidx.health.connect.client.records.ExerciseSessionRecord\n"
            "import com.openhealth.sync.R\n"
            "import java.util.Locale\n"
        ),
        expected_old_count=1,
        description="HuaweiWorkoutTypeMapper.kt: add Context/R imports",
    )
    apply_insertion(
        WORKOUT_MAPPER_FILE,
        anchor=(
            "    private fun exerciseTypeConstant(name: String): Int = try {\n"
            "        ExerciseSessionRecord::class.java.getField(name).getInt(null)\n"
            "    } catch (_: Exception) {\n"
            "        ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT\n"
            "    }\n"
            "}"
        ),
        new_with_anchor=(
            "    private fun exerciseTypeConstant(name: String): Int = try {\n"
            "        ExerciseSessionRecord::class.java.getField(name).getInt(null)\n"
            "    } catch (_: Exception) {\n"
            "        ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT\n"
            "    }"
            + MAPPER_FUNCTION_BLOCK
        ),
        unique_marker="BITLUT_EXERCISE_TYPE_LOCALIZATION_2026_09_01",
        description="HuaweiWorkoutTypeMapper.kt: add displayNameRes map + localizedDisplayName()",
    )

    print("=== 4/5: Using localized fallback in HuaweiHealthManager (live sync) ===")
    apply_edit(
        HUAWEI_MANAGER_FILE,
        old=(
            "            val title = rawName\n"
            "                ?.trim()\n"
            "                ?.takeIf { it.isNotBlank() && !isSyntheticHuaweiActivityName(it, recordId) }\n"
            "                ?: canonicalType\n"
        ),
        new=(
            "            val title = rawName\n"
            "                ?.trim()\n"
            "                ?.takeIf { it.isNotBlank() && !isSyntheticHuaweiActivityName(it, recordId) }\n"
            "                ?: HuaweiWorkoutTypeMapper.localizedDisplayName(context, exerciseType)\n"
        ),
        expected_old_count=1,
        description="HuaweiHealthManager.kt: localize title fallback",
    )

    print("=== 5/5: Using localized fallback in HuaweiExportParser (archive import) ===")
    apply_edit(
        EXPORT_PARSER_FILE,
        old=(
            "            val explicitName = sequenceOf(\"name\", \"title\", \"workoutName\")\n"
            "                .map { key -> obj.optString(key, \"\").trim() }\n"
            "                .firstOrNull { it.isNotBlank() }\n"
            "            val title = explicitName ?: canonicalType\n"
        ),
        new=(
            "            val explicitName = sequenceOf(\"name\", \"title\", \"workoutName\")\n"
            "                .map { key -> obj.optString(key, \"\").trim() }\n"
            "                .firstOrNull { it.isNotBlank() }\n"
            "            val title = explicitName ?: HuaweiWorkoutTypeMapper.localizedDisplayName(context, exerciseType)\n"
        ),
        expected_old_count=1,
        description="HuaweiExportParser.kt: localize title fallback",
    )

    print("=== Validating XML and string parity after edits ===")
    validate_xml(STRINGS_EN, "values/strings.xml post-edit validation")
    validate_xml(STRINGS_RU, "values-ru/strings.xml post-edit validation")
    check_string_parity()

    print("=== Running compile gate ===")
    run_compile_gate()

    print("=== Compile gate passed. Committing and pushing. ===")
    git_commit_and_push()

    print("Done.")


if __name__ == "__main__":
    main()
