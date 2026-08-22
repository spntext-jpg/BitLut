#!/usr/bin/env python3
"""
BitLut recovery patch for workout metric composable helpers.

Fixes the compile error introduced by the workout/nav/freshness sprint:
local helper functions inside workoutMetricDisplays() call stringResource(),
therefore they must themselves be marked @Composable.

This patch is intentionally surgical:
- touches only FinalBitLutShell.kt
- does not change workout data logic
- does not change navbar behavior
- does not change freshness timestamps
- is idempotent
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"

HELPERS = [
    "duration",
    "distance",
    "caloriesMetric",
    "elevationMetric",
    "stepsMetric",
    "started",
    "ended",
    "pace",
    "speed",
    "swimPace",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def ensure_repo() -> None:
    if not TARGET.exists():
        fail(f"Missing target file: {TARGET}")
    if not (ROOT / "gradlew").exists():
        fail("Run this script from the BitLut repository root.")


def apply() -> None:
    ensure_repo()
    text = TARGET.read_text(encoding="utf-8")

    if "@Composable\nprivate fun workoutMetricDisplays(" not in text:
        fail("Expected patched workoutMetricDisplays() function was not found.")

    changed = False

    for name in HELPERS:
        plain = f"    fun {name}() = WorkoutMetricDisplay("
        fixed = f"    @Composable\n    fun {name}() = WorkoutMetricDisplay("

        if fixed in text:
            continue

        count = text.count(plain)
        if count != 1:
            fail(
                f"Expected exactly one unannotated local helper {name}(), found {count}. "
                "Source state is unexpected; refusing to guess."
            )

        text = text.replace(plain, fixed, 1)
        changed = True

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print(f"Updated: {TARGET.relative_to(ROOT)}")
    else:
        print("Already applied: no source changes needed.")


def verify_static() -> None:
    ensure_repo()
    text = TARGET.read_text(encoding="utf-8")

    errors = []

    if "@Composable\nprivate fun workoutMetricDisplays(" not in text:
        errors.append("workoutMetricDisplays() is not @Composable")

    for name in HELPERS:
        expected = f"    @Composable\n    fun {name}() = WorkoutMetricDisplay("
        if expected not in text:
            errors.append(f"local helper {name}() is not @Composable")

    # Guard against duplicate annotations from repeated execution.
    if "@Composable\n    @Composable\n    fun " in text:
        errors.append("duplicate @Composable annotation detected")

    if errors:
        print("Static verification FAILED:")
        for error in errors:
            print(f" - {error}")
        raise SystemExit(1)

    print("Static verification passed.")


def run_build() -> None:
    command = [
        "./gradlew",
        ":app:assembleDebug",
        "--no-daemon",
        "--max-workers=1",
        "--no-watch-fs",
        "--console=plain",
        "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
        "-Pkotlin.compiler.execution.strategy=in-process",
    ]

    print("==> " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        fail(f"Build failed with exit code {result.returncode}")

    print("Android build passed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--verify-static", action="store_true")
    args = parser.parse_args()

    if args.apply:
        apply()
        verify_static()
    elif args.verify_static:
        verify_static()
    else:
        verify_static()
        run_build()


if __name__ == "__main__":
    main()
