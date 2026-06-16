#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
MAIN = ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"

if not MAIN.exists():
    raise SystemExit(f"MainActivity.kt not found: {MAIN}")

text = MAIN.read_text(encoding="utf-8")
required_import = "import androidx.compose.foundation.layout.Column"

if required_import not in text:
    # Keep imports sorted enough for AI-readable code without a risky full formatter.
    anchor = "import androidx.compose.foundation.layout.Box\n"
    if anchor in text:
        text = text.replace(anchor, anchor + required_import + "\n", 1)
    else:
        # Fallback: insert after package line block, before first existing import.
        first_import = text.find("import ")
        if first_import == -1:
            raise SystemExit("No import block found in MainActivity.kt")
        text = text[:first_import] + required_import + "\n" + text[first_import:]

MAIN.write_text(text, encoding="utf-8")
print("OK: MainActivity.kt has Column import")
