#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        errors.append(f"Missing {rel}")
        return ""
    return path.read_text(encoding="utf-8")

root_gradle = read("build.gradle.kts")
app_gradle = read("app/build.gradle.kts")
tokens = read("app/src/main/java/com/openhealth/sync/ui/theme/AugustTokens.kt")
theme = read("app/src/main/java/com/openhealth/sync/ui/theme/BitLutExpressiveTheme.kt")
nav = read("app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

live_build_and_ui = "\n".join([app_gradle, tokens, theme, nav, shell])
require("dev.chrisbanes.haze" not in live_build_and_ui, "Haze still exists in live build/UI sources")
require("hazeEffect" not in live_build_and_ui, "hazeEffect still exists in live sources")
require("hazeSource" not in live_build_and_ui, "hazeSource still exists in live sources")
require("rememberHazeState" not in live_build_and_ui, "rememberHazeState still exists in live sources")
require("configurations.all" not in app_gradle, "obsolete Haze dependency-resolution workaround still exists")
require('id("org.jetbrains.kotlin.android") version "2.0.21"' in root_gradle,
        "Kotlin plugin baseline changed unexpectedly; this sprint intentionally keeps 2.0.21")

for token in [
    "val Ink = Color(0xFF151728)",
    "val Lime = Color(0xFFDFFF6A)",
    "val LimeInk = Ink",
    "val Purple = Color(0xFF6E5CF6)",
    "val PurpleSoft = Color(0xFFEEEAFF)",
    "val Navy = Color(0xFF151728)",
    "val NavyRaised = Color(0xFF1C1E33)",
    "val NavySoft = Color(0xFF24263D)",
    "val DarkSecondaryText = Color(0xFFB8BDCE)",
    "val WorkSurface = 22.dp",
]:
    require(token in tokens, f"Missing August v3 token: {token}")

require("internal object AugustGlass" not in tokens, "AugustGlass should be removed with Haze")
require("containerColor = AugustColor.Lime" in shell, "PrimaryButton is not Lime")
require("contentColor = AugustColor.LimeInk" in shell, "PrimaryButton does not use Ink on Lime")
require("val minHeight = if (compact) 44.dp else 48.dp" in shell, "Primary button touch target is below August v3 minimum")
require("collectIsFocusedAsState()" in shell, "Button focus state is not wired")
require("BorderStroke(2.dp, AugustColor.Purple)" in shell, "Primary focus is not Purple")
require("targetValue = if (pressed) 0.98f else 1f" in shell, "Pressed-scale contract is not 0.98")
require("navBarClearance" not in shell, "Haze-only navBarClearance plumbing still exists")
require(".padding(padding)" in shell, "Scaffold padding was not restored")

for token in [
    ".background(AugustColor.Navy)",
    "AugustColor.Surface",
    "AugustColor.Lime",
    "AugustColor.LimeInk",
    "AugustColor.Purple",
    "Role.Tab",
    "Role.Button",
]:
    require(token in nav, f"August v3 navigation marker missing: {token}")
require("0.92f" not in nav, "Legacy over-aggressive 0.92 nav press scale remains")
require("contentDescription = null" not in nav, "Navigation still has unlabeled icons")
require("private val NavAccent" not in nav, "Legacy generic NavAccent alias remains")

require("primary              = AugustColor.Lime" in theme, "Material primary is not Lime")
require("secondary            = AugustColor.Purple" in theme, "Material secondary is not Purple")
require("surfaceTint          = Color.Transparent" in theme, "Material surfaces still receive brand tint")

# PrimaryButton calls must no longer be parameterized by arbitrary accent colors.
for match in re.finditer(r"PrimaryButton\(", shell):
    snippet = shell[match.start():match.start() + 420]
    require("accent =" not in snippet, "A PrimaryButton call still overrides the canonical Lime action color")

if errors:
    print("BitLut August v3/build-fix verification FAILED:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("BitLut August v3/build-fix static verification passed.")
