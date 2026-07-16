#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(".")

MAIN = ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt"
SHELL = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"

def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

def package_name(text: str) -> str:
    match = re.search(r"(?m)^package\s+([A-Za-z0-9_.]+)\s*$", text)
    if not match:
        raise RuntimeError("No package declaration found")
    return match.group(1)

def has_final_shell(text: str) -> bool:
    return re.search(
        r"(?m)^(?:@Composable\s*\n)?(?:private\s+)?fun\s+FinalBitLutShell\s*\(",
        text,
    ) is not None

main = read(MAIN)
shell = read(SHELL)

main_pkg = package_name(main)
shell_pkg = package_name(shell)

if not has_final_shell(shell):
    raise SystemExit("FinalBitLutShell function not found")

# Remove any stale FinalBitLutShell imports.
main = re.sub(
    r"(?m)^import\s+[A-Za-z0-9_.]+\.FinalBitLutShell\s*\n",
    "",
    main,
)

# If shell package differs from MainActivity package, add the correct import.
# If it is the same package, no import is needed.
if shell_pkg != main_pkg:
    correct_import = f"import {shell_pkg}.FinalBitLutShell"
    if correct_import not in main:
        package_match = re.search(r"^package [^\n]+\n", main)
        if not package_match:
            raise RuntimeError("MainActivity package declaration not found")
        main = main[:package_match.end()] + "\n" + correct_import + "\n" + main[package_match.end():]

# Normalize import block.
lines = main.splitlines()
package_line = lines[0]
imports = []
body = []

for line in lines[1:]:
    if line.startswith("import "):
        imports.append(line)
    else:
        body.append(line)

imports = sorted(dict.fromkeys(imports))
body_text = "\n".join(body).lstrip("\n").rstrip()

if imports:
    main = package_line + "\n\n" + "\n".join(imports) + "\n\n" + body_text + "\n"
else:
    main = package_line + "\n\n" + body_text + "\n"

write(MAIN, main)

# Self-check.
main = read(MAIN)
if shell_pkg == main_pkg and "import com.openhealth.sync.ui.screens.FinalBitLutShell" in main:
    raise SystemExit("Stale ui.screens FinalBitLutShell import remains")

if shell_pkg != main_pkg and f"import {shell_pkg}.FinalBitLutShell" not in main:
    raise SystemExit("Correct FinalBitLutShell import was not added")

print(f"Fixed FinalBitLutShell import: MainActivity package={main_pkg}, FinalBitLutShell package={shell_pkg}")
