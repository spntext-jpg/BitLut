#!/usr/bin/env python3
"""
patch_settings_engraved_signature_v1.py

Adds a small wood-carved-style signature at the very bottom of the
Settings screen (2026-08-29, product request: "для вас старался
пашенька").

Font constraint: BitLut only bundles Inter Variable -- no serif/script
font ships in the APK, and this app's GMS-free Huawei audience means the
Android Downloadable Fonts API is not a safe option (see CLAUDE.md).
Adding a whole new bundled font file for one decorative string was judged
disproportionate. The "carved" look is instead built from Inter Black
with wide letter-spacing plus a two-layer engraved-shadow effect (a light
"catch the light" highlight offset up-left, a dark "recessed" shadow
offset down-right) -- the closest achievable effect with the existing
font asset, not a literal wood texture (which Compose text styling can't
produce without a texture asset either).

Colors are computed, not eyeballed: base walnut-brown #6B4326, with the
highlight/shadow each derived by lightening/darkening that same base by a
fixed 55% blend toward white/black respectively (highlight #BCAA9D,
shadow #301E11). This is a one-off decorative Easter egg, not a
design-system component, so the palette lives locally in this composable
rather than being added to AugustTokens.kt.

Changes:
  1. FinalBitLutShell.kt
     - New imports: androidx.compose.foundation.layout.offset,
       androidx.compose.ui.text.TextStyle, androidx.compose.ui.graphics.Shadow,
       androidx.compose.ui.geometry.Offset.
     - SettingsScreen() calls a new EngravedSignature() composable right
       after the existing daily-goals card, still inside the scrollable
       Column.
     - New private composable EngravedSignature().
  2. res/values/strings.xml / res/values-ru/strings.xml
     - New string `settings_signature`, added to both locales (RU keeps
       the exact requested text; EN gets a natural equivalent), preserving
       EN/RU key parity.

Usage (run from repo root, inside GitHub Codespaces):
    python3 patch_settings_engraved_signature_v1.py
"""

import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SHELL_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"
STRINGS_EN = REPO_ROOT / "app/src/main/res/values/strings.xml"
STRINGS_RU = REPO_ROOT / "app/src/main/res/values-ru/strings.xml"
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Expected file not found: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / (path.name + ".bak_settings_engraved_signature_v1")
    if not target.exists():
        shutil.copy2(path, target)
        print(f"Backed up {path} -> {target}")


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str, description: str) -> bool:
    """Pure insertion: `anchor` itself survives unchanged in the result, so
    idempotency must be keyed on `unique_marker`, never on the anchor's own
    occurrence count."""
    text = path.read_text(encoding="utf-8")
    if unique_marker in text:
        print(f"SKIP (already applied): {description}")
        return False
    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(
            f"Anchor count mismatch for '{description}': expected exactly 1 "
            f"occurrence of anchor, found {anchor_count}. Refusing to guess."
        )
    text = text.replace(anchor, new_with_anchor, 1)
    path.write_text(text, encoding="utf-8")
    print(f"APPLIED: {description}")
    return True


def add_string_resource(path: Path, after_name: str, new_name: str, new_value: str, description: str) -> bool:
    text = path.read_text(encoding="utf-8")
    marker = f'<string name="{new_name}">'
    if marker in text:
        print(f"SKIP (already applied): {description}")
        return False

    anchor_pattern = f'<string name="{after_name}">'
    if text.count(anchor_pattern) != 1:
        die(f"Could not find unique anchor string '{after_name}' in {path}")

    lines = text.splitlines(keepends=True)
    anchor_line_index = None
    for i, line in enumerate(lines):
        if anchor_pattern in line and line.strip().startswith("<string"):
            anchor_line_index = i
            break
    if anchor_line_index is None:
        die(f"Could not locate anchor line for '{after_name}' in {path}")

    indent = lines[anchor_line_index][: len(lines[anchor_line_index]) - len(lines[anchor_line_index].lstrip())]
    new_line = f'{indent}<string name="{new_name}">{new_value}</string>\n'
    lines.insert(anchor_line_index + 1, new_line)
    path.write_text("".join(lines), encoding="utf-8")
    print(f"APPLIED: {description}")
    return True


def validate_strings_xml_parity() -> None:
    try:
        en_root = ET.parse(STRINGS_EN).getroot()
        ru_root = ET.parse(STRINGS_RU).getroot()
    except ET.ParseError as e:
        die(f"strings.xml is not well-formed after patch: {e}")

    en_names = {el.get("name") for el in en_root.findall("string")}
    ru_names = {el.get("name") for el in ru_root.findall("string")}

    only_en = en_names - ru_names
    only_ru = ru_names - en_names
    if only_en or only_ru:
        die(
            "EN/RU string key parity broken after patch. "
            f"EN-only: {sorted(only_en)} RU-only: {sorted(only_ru)}"
        )
    print(f"strings.xml EN/RU parity OK ({len(en_names)} keys each).")


def main() -> None:
    backup(SHELL_FILE)
    backup(STRINGS_EN)
    backup(STRINGS_RU)

    changed = False

    # 1) New imports.
    changed |= apply_insertion(
        SHELL_FILE,
        anchor="import androidx.compose.foundation.layout.size\nimport androidx.compose.foundation.layout.width\n",
        new_with_anchor=(
            "import androidx.compose.foundation.layout.size\n"
            "import androidx.compose.foundation.layout.offset\n"
            "import androidx.compose.foundation.layout.width\n"
        ),
        unique_marker="import androidx.compose.foundation.layout.offset",
        description="add Modifier.offset import",
    ) or changed

    changed |= apply_insertion(
        SHELL_FILE,
        anchor="import androidx.compose.ui.text.font.FontWeight\n",
        new_with_anchor=(
            "import androidx.compose.ui.text.font.FontWeight\n"
            "import androidx.compose.ui.text.TextStyle\n"
        ),
        unique_marker="import androidx.compose.ui.text.TextStyle",
        description="add TextStyle import",
    ) or changed

    changed |= apply_insertion(
        SHELL_FILE,
        anchor="import androidx.compose.ui.graphics.vector.ImageVector\n",
        new_with_anchor=(
            "import androidx.compose.ui.graphics.vector.ImageVector\n"
            "import androidx.compose.ui.graphics.Shadow\n"
            "import androidx.compose.ui.geometry.Offset\n"
        ),
        unique_marker="import androidx.compose.ui.graphics.Shadow",
        description="add Shadow/Offset imports",
    ) or changed

    # 2) Call EngravedSignature() at the bottom of SettingsScreen, and
    #    define the composable right after the function.
    changed |= apply_insertion(
        SHELL_FILE,
        anchor=(
            "                }\n"
            "            )\n"
            "        }\n"
            "    }\n"
            "    }\n"
            "}\n"
        ),
        new_with_anchor=(
            "                }\n"
            "            )\n"
            "        }\n"
            "\n"
            "        Spacer(Modifier.height(24.dp))\n"
            "        EngravedSignature()\n"
            "    }\n"
            "    }\n"
            "}\n"
            "\n"
            "/**\n"
            " * Small wood-carved-style signature at the very bottom of Settings\n"
            " * (2026-08-29, product request -- a personal touch, not a design-system\n"
            " * component, so its wood-brown palette is computed locally here rather\n"
            " * than added to AugustTokens.kt).\n"
            " *\n"
            " * BitLut only bundles Inter Variable (no serif/script font is included in\n"
            " * the APK, and this app's GMS-free Huawei audience means the Android\n"
            " * Downloadable Fonts API is not a safe option -- see CLAUDE.md). Adding a\n"
            " * whole new bundled font file for one decorative string was judged\n"
            " * disproportionate, so the \"carved\" look is built from Inter at a heavy\n"
            " * weight with wide letter-spacing plus a two-layer engraved-shadow effect\n"
            " * (a light \"catch the light\" highlight offset up-left, a dark \"recessed\"\n"
            " * shadow offset down-right) rather than a literal wood texture, which\n"
            " * Compose text styling cannot produce without a texture asset either.\n"
            " *\n"
            " * Colors are computed, not eyeballed: base walnut-brown #6B4326, with the\n"
            " * highlight/shadow each derived by lightening/darkening that same base by\n"
            " * a fixed 55% blend toward white/black respectively (highlight #BCAA9D,\n"
            " * shadow #301E11).\n"
            " */\n"
            "@Composable\n"
            "private fun EngravedSignature() {\n"
            "    val woodBase = Color(0xFF6B4326)\n"
            "    val woodHighlight = Color(0xFFBCAA9D)\n"
            "    val woodShadow = Color(0xFF301E11)\n"
            "    val text = stringResource(R.string.settings_signature)\n"
            "\n"
            "    Box(\n"
            "        modifier = Modifier\n"
            "            .fillMaxWidth()\n"
            "            .padding(vertical = 8.dp),\n"
            "        contentAlignment = Alignment.Center\n"
            "    ) {\n"
            "        Text(\n"
            "            text = text,\n"
            "            fontWeight = FontWeight.Black,\n"
            "            fontSize = 13.sp,\n"
            "            letterSpacing = 2.sp,\n"
            "            color = woodHighlight,\n"
            "            style = TextStyle(\n"
            "                shadow = Shadow(color = woodHighlight, offset = Offset(-1f, -1f), blurRadius = 0.5f)\n"
            "            ),\n"
            "            modifier = Modifier.offset(x = 0.6.dp, y = 0.6.dp)\n"
            "        )\n"
            "        Text(\n"
            "            text = text,\n"
            "            fontWeight = FontWeight.Black,\n"
            "            fontSize = 13.sp,\n"
            "            letterSpacing = 2.sp,\n"
            "            color = woodBase,\n"
            "            style = TextStyle(\n"
            "                shadow = Shadow(color = woodShadow, offset = Offset(1f, 1f), blurRadius = 0.5f)\n"
            "            )\n"
            "        )\n"
            "    }\n"
            "}\n"
        ),
        unique_marker="private fun EngravedSignature()",
        description="add EngravedSignature() call + composable at bottom of SettingsScreen",
    ) or changed

    # 3) New string resources, EN + RU.
    changed |= add_string_resource(
        STRINGS_EN,
        after_name="goals_section_body",
        new_name="settings_signature",
        new_value="made with care by pashenka",
        description="add settings_signature to values/strings.xml",
    ) or changed

    changed |= add_string_resource(
        STRINGS_RU,
        after_name="goals_section_body",
        new_name="settings_signature",
        new_value="\u0434\u043b\u044f \u0432\u0430\u0441 \u0441\u0442\u0430\u0440\u0430\u043b\u0441\u044f \u043f\u0430\u0448\u0435\u043d\u044c\u043a\u0430",
        description="add settings_signature to values-ru/strings.xml",
    ) or changed

    if not changed:
        print("Nothing to do: engraved signature already applied.")
    else:
        print("Engraved signature applied.")

    validate_strings_xml_parity()

    text = SHELL_FILE.read_text(encoding="utf-8")
    if text.count("{") != text.count("}"):
        die("Brace mismatch detected in FinalBitLutShell.kt after patch -- aborting before build.")

    print("patch_settings_engraved_signature_v1.py: structural checks passed.")


if __name__ == "__main__":
    main()
