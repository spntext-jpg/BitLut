#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
from PIL import Image

src = Path("BitLut.png")
if not src.exists():
    raise SystemExit("Put BitLut.png in repo root first")

img = Image.open(src).convert("RGBA")

sizes = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

for folder, size in sizes.items():
    out_dir = Path("app/src/main/res") / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    icon = img.resize((size, size), Image.LANCZOS)
    icon.save(out_dir / "ic_launcher.png")
    icon.save(out_dir / "ic_launcher_round.png")

docs = Path("docs")
docs.mkdir(exist_ok=True)
img.resize((512, 512), Image.LANCZOS).save(docs / "bitlut-icon.png")
PY

rm -f app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml
rm -f app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml

python3 - <<'PY'
from pathlib import Path
p = Path("README.md")
if p.exists():
    s = p.read_text()
    s = s.replace(
        'app/src/main/res/mipmap-xxxhdpi/ic_launcher.png',
        'docs/bitlut-icon.png'
    )
    p.write_text(s)
PY

git add -A
git status --short
