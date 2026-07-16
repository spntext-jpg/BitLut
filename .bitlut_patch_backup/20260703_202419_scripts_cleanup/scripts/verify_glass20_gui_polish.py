#!/usr/bin/env python3
from pathlib import Path
import sys

errors = []

def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")

def require(condition, message):
    if not condition:
        errors.append(message)

require("Glass20BottomNavigation(" in shell, "Missing Glass20BottomNavigation")
require("Glass20NavButton(" in shell, "Missing Glass20NavButton")
require("NavigationBarItem(" not in shell, "Material NavigationBarItem must not remain")
require("NavigationBar(" not in shell, "Material NavigationBar must not remain")
require("contentDescription = null" in shell, "Bottom navigation must stay icon-only")
require("Brush.linearGradient" in shell and "Brush.radialGradient" in shell, "Glass 2.0 gradients are missing")
require("drawLine(" in shell, "Glass highlight line is missing")
require("defaultMinSize(minHeight = 6.dp)" in shell, "Metric bars need a minimum visible height")
require(".height(84.dp)" in shell, "Metric bar drawing area must be bounded")
require(".height(132.dp)" in shell, "Metric chart row must reserve stable vertical space")
require("TextOverflow.Ellipsis" in shell, "Large values must be clipped safely")
require("val targetCardColor = if (palette.dark)" in shell, "Global SoftCard glass system was not updated")

if errors:
    print("Glass 2.0 GUI verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Glass 2.0 GUI verification passed.")
