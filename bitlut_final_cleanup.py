#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
README = ROOT / "README.md"
HANDOFF = ROOT / "SESSION_HANDOFF.md"
CONTEXT = ROOT / "CONTEXT.md"

MARKER_START = "<!-- BITLUT_FINAL_STATE_2026_08_04_START -->"
MARKER_END = "<!-- BITLUT_FINAL_STATE_2026_08_04_END -->"

FINAL_STATE = f"""{MARKER_START}

## Current state — 2026-08-04

BitLut is an activity-only Android bridge between Huawei Health and Android
Health Connect. The current build is verified with `:app:assembleDebug`.

### Current data scope

- Steps
- Distance
- Floors climbed and elevation gain
- Active calories
- Exercise sessions and workout duration

Sleep, heart rate, SpO2, HRV, stress, blood pressure and other health metrics
are intentionally not requested, imported or displayed.

### Current reliability behavior

- Manual and background synchronization use WorkManager without observing
  discarded duplicate requests.
- Work observers are removed after terminal states.
- Huawei ZIP/JSON import is bounded and supports the known export layouts.
- Partial imports report only categories that were actually written.
- Dashboard snapshots and synchronization metadata are persisted locally.
- Local signing credentials are ignored by Git and are never committed.

### Current dashboard

- Today's steps, distance, calories and activity.
- Workout history without the maximum-cadence field.
- Elevation/floors summary for today and the last seven days.
- Seven-day average, best day and comparison with the previous seven days.
- Personal records for steps, distance, calories, elevation and workout duration.
- Locally accumulated achievements.
- Last successful synchronization time and selected data source.

### Build command for constrained Codespaces

```bash
./gradlew :app:assembleDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

### Maintenance rules

- Do not add new health permissions without an explicit product decision.
- Keep changes surgical; do not refactor unrelated working synchronization code.
- Deliver repository changes as idempotent Python patch scripts.
- Verify with a real Gradle build before commit and push.
- Version numbers for releases remain owned by the GitHub Actions release workflow.

{MARKER_END}
"""

HANDOFF_BLOCK = f"""{MARKER_START}

## Handoff update — 2026-08-04

The current `main` branch has a successful debug build after the synchronization,
Huawei import and dashboard insight work.

### Completed in the latest session

- Hardened immediate WorkManager synchronization and observer cleanup.
- Hardened Huawei archive import and partial-result reporting.
- Removed obsolete Huawei heart-rate scope configuration.
- Removed `.env.signing.local` from Git tracking and added it to `.gitignore`.
- Removed the decorative empty circle from the top steps card.
- Renamed the personal-record label to “Шаги за день”.
- Removed “Макс. каденс” from workout-card presentation.
- Added elevation/floors, seven-day trends, expanded records and achievements.
- Added source and last-successful-sync information beside the summary heading.
- Confirmed that sleep is not requested or imported; no sleep UI was added.

### Source-of-truth rule

Start future work from the current `main` branch, a fresh Repomix export and a
fresh successful build. Do not reconstruct current behavior from archived patch
backups or old verifier assumptions.

### User workflow

The user works in GitHub Codespaces and expects standalone, idempotent Python
patch scripts plus exact apply, build, commit and push commands. Do not ask them
to paste manual Kotlin diffs.

### Next safe product opportunities

Use only already imported activity data unless the user explicitly approves new
permissions. Suitable additions include richer trend visualization, activity
calendar views, export improvements and clearer synchronization diagnostics.

{MARKER_END}
"""

CONTEXT_BLOCK = f"""{MARKER_START}

## Active project context — 2026-08-04

### Product boundary

BitLut is activity-only. Approved application behavior is limited to steps,
distance, floors/elevation, active calories and workouts. Sleep and biometric
health categories are outside the current scope.

### Architecture anchors

- `HuaweiHealthManager`: reads approved Huawei activity data.
- `GoogleHealthManager`: reads/writes Health Connect activity records.
- `SyncOrchestrator`: coordinates manual synchronization.
- `BackgroundSyncScheduler` and `SyncWorker`: WorkManager scheduling/execution.
- `HuaweiExportParser`: bounded local Huawei ZIP/JSON import.
- `DashboardSnapshotCache`: last-known dashboard state.
- `AchievementsStore`: local records and accumulated achievements.
- `DashboardViewModel`: dashboard aggregation and trend calculation.
- `FinalBitLutShell`: Compose application shell and dashboard presentation.

### Current dashboard contract

The dashboard presents activity data already available locally: daily summary,
workout history, elevation/floors, seven-day comparison, personal records,
achievements and synchronization transparency. It must not imply that sleep or
other unsupported health data is available.

### Engineering constraints

- Preserve working sync and import behavior.
- Avoid unrelated refactors.
- No new permissions without explicit approval.
- Keep secrets and generated build artifacts out of Git.
- Use the low-memory Gradle command documented in README for Codespaces.
- A successful build is required before commit.

{MARKER_END}
"""

def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )

def require_repo() -> None:
    if not (ROOT / ".git").exists():
        raise SystemExit("ERROR: run this script from the BitLut repository root.")
    for path in (README, HANDOFF, CONTEXT):
        if not path.exists():
            raise SystemExit(f"ERROR: missing required file: {path.relative_to(ROOT)}")

def replace_managed_block(path: Path, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if MARKER_START in text and MARKER_END in text:
        before = text.split(MARKER_START, 1)[0].rstrip()
        after = text.split(MARKER_END, 1)[1].lstrip()
        text = before + "\n\n" + block.strip() + ("\n\n" + after if after else "\n")
    else:
        text = text.rstrip() + "\n\n" + block.strip() + "\n"
    path.write_text(text, encoding="utf-8")
    print(f"updated: {path.relative_to(ROOT)}")

def remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    print(f"removed: {path.relative_to(ROOT)}")

def cleanup() -> None:
    # Generated local backups and caches are never source files.
    remove_path(ROOT / ".bitlut_patch_backup")

    for directory in ROOT.rglob("__pycache__"):
        remove_path(directory)

    for pattern in ("*.pyc", "*.orig", "*.bak", "*.tmp", "*~"):
        for path in list(ROOT.rglob(pattern)):
            if ".git" not in path.parts:
                remove_path(path)

    for relative in (
        "compile_errors.log",
        "hotfix.sh",
        "build-release.sh",
        "bitlut_current_state_fix.py",
        "bitlut_current_state_fix_v2.py",
        "bitlut_workmanager_flow_hotfix.py",
        "bitlut_dashboard_polish_patch.py",
        "bitlut_dashboard_insights_patch.py",
        "scripts/verify_bitlut_current_state_fix.py",
        "scripts/verify_dashboard_polish_patch.py",
        "scripts/verify_dashboard_insights_patch.py",
    ):
        remove_path(ROOT / relative)

    # Remove any other root-level generated BitLut patch scripts, but keep this
    # finalizer until the process exits. It is ignored and should not be committed.
    current = Path(__file__).resolve()
    for path in ROOT.glob("bitlut_*_patch.py"):
        if path.resolve() != current:
            remove_path(path)

def normalize_gitignore() -> None:
    path = ROOT / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    required = [
        ".env.signing.local",
        ".bitlut_patch_backup/",
        "bitlut_*_patch.py",
        "__pycache__/",
        "*.pyc",
        "*.orig",
        "*.bak",
        "*.tmp",
        "compile_errors.log",
    ]
    lines = text.splitlines()
    seen = set()
    normalized = []
    for line in lines:
        key = line.strip()
        if key and key in seen:
            continue
        normalized.append(line)
        if key:
            seen.add(key)
    missing = [entry for entry in required if entry not in seen]
    if missing:
        normalized += ["", "# Local patching, backups and generated files", *missing]
    path.write_text("\n".join(normalized).rstrip() + "\n", encoding="utf-8")
    print("updated: .gitignore")

def verify() -> None:
    for path in (README, HANDOFF, CONTEXT):
        text = path.read_text(encoding="utf-8")
        if text.count(MARKER_START) != 1 or text.count(MARKER_END) != 1:
            raise SystemExit(f"ERROR: managed documentation block invalid in {path.name}")

    forbidden_tracked = [
        ".env.signing.local",
        ".bitlut_patch_backup",
        "bitlut_dashboard_insights_patch.py",
        "bitlut_dashboard_polish_patch.py",
        "bitlut_workmanager_flow_hotfix.py",
    ]
    tracked = run("git", "ls-files").stdout.splitlines()
    for item in forbidden_tracked:
        if any(line == item or line.startswith(item + "/") for line in tracked):
            run("git", "rm", "-r", "--cached", "--ignore-unmatch", item, check=False)
            print(f"removed from Git index: {item}")

    check = run("git", "diff", "--check", check=False)
    if check.returncode != 0:
        print(check.stdout)
        raise SystemExit("ERROR: git diff --check failed.")

    print("Final documentation and cleanup verification passed.")

def main() -> None:
    require_repo()
    replace_managed_block(README, FINAL_STATE)
    replace_managed_block(HANDOFF, HANDOFF_BLOCK)
    replace_managed_block(CONTEXT, CONTEXT_BLOCK)
    normalize_gitignore()
    cleanup()
    verify()
    print("\nFinal cleanup patch applied successfully.")
    print("Review with: git status --short")

if __name__ == "__main__":
    main()
