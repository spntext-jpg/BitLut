#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt"
if not path.exists():
    raise SystemExit("Missing GlassNavigation.kt")
text = path.read_text(encoding="utf-8")
errors = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require("collectIsPressedAsState" in text, "pressed-state animation missing")
require("refreshButtonBounce" in text, "refresh button bounce missing")
require("iconRotation.animateTo" in text, "refresh icon rotation missing")
require("glass20NavButtonBounce" in text, "tab button bounce missing")
require("iconBounce.animateTo" in text, "tab icon bounce missing")
require("iconTilt.animateTo" in text, "tab icon tilt missing")
require("glass20NavIndicatorWidth" in text, "selection indicator animation missing")
require(text.count(".pressScale(interactionSource)") == 0, "bottom nav still applies a second conflicting press scale")
require("onSettingsTabTapped()" in text, "secret log-viewer gesture was lost")

if errors:
    print("BitLut GUI motion verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)
print("BitLut GUI motion verification passed.")
