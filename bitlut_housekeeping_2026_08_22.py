#!/usr/bin/env python3
"""
BitLut housekeeping patch.

Purpose:
- Replace stale root documentation with a concise current source of truth.
- Remove superseded historical docs and obsolete one-off UI verification docs.
- Do not touch application source code, Gradle configuration, sync logic, secrets,
  release workflow, or current production reference documents.
- Never commit or push automatically.

Run from repository root:
    python3 bitlut_housekeeping_2026_08_22.py --apply
    python3 bitlut_housekeeping_2026_08_22.py --verify
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DOCS = {
    "README.md": r"""<p align="center">
  <img src="docs/bitlut-mascot.png" width="140" alt="BitLut" />
</p>

<h1 align="center">BitLut</h1>

<p align="center">
  <strong>Open-source bridge from HUAWEI Health to Android Health Connect</strong>
</p>

BitLut is a free Android application that reads supported activity data from
HUAWEI Health through HUAWEI Health Kit and writes it to Android Health Connect.
The app is designed for people who use Huawei wearables but want their activity
data to be available to other Health Connect-compatible apps.

BitLut works locally on the device. It has no BitLut account, no advertising,
no cloud backend, and no health-data selling.

## Supported activity scope

The production scope is intentionally activity-only:

- steps
- distance
- floors climbed / elevation gain
- active calories when the approved Huawei scope is available
- exercise / activity sessions

Sleep, heart rate, SpO2, HRV, stress, and other biometric categories are outside
the current product scope and must not be added without an explicit permission
and product decision.

## How synchronization works

```text
HUAWEI Health
    |
    | HUAWEI Health Kit (read-only)
    v
BitLut
    |
    | validated activity records
    v
Android Health Connect
    |
    v
Other Health Connect-compatible apps
```

BitLut never fabricates health data. Only real source-derived records may be
written to Health Connect.

The app also supports bounded local import of supported HUAWEI export data,
dashboard snapshots, CSV export, background synchronization, and a home-screen
widget.

## Current engineering baseline

As of 2026-08-22:

- Kotlin Gradle plugin remains on the project's stable 2.0.21 baseline.
- Android Gradle Plugin is 8.7.3 and Gradle is 8.9.
- Java/JVM target is 17.
- The debug build is green in GitHub Codespaces.
- Haze has been removed. UI blur must not introduce a dependency-driven
  Kotlin/toolchain migration.
- The UI uses the August v3 semantic design system.
- Primary actions use Lime with Ink content.
- Purple is reserved for focus and secondary interaction details.
- Navy is the dark architectural anchor.
- The bottom navigation uses native Compose surfaces rather than Haze blur.

## Architecture

Key runtime components:

- `HuaweiHealthManager` — HUAWEI Health Kit authorization and approved activity reads.
- `GoogleHealthManager` — Health Connect reads and writes.
- `SyncOrchestrator` — immediate/manual synchronization coordination.
- `BackgroundSyncScheduler` / `SyncWorker` — WorkManager scheduling and execution.
- `HuaweiExportParser` — bounded local archive import.
- `DashboardSnapshotCache` — last-known dashboard state for resilient cold launch.
- `AchievementsStore` — local activity records and achievements.
- `DashboardViewModel` — dashboard aggregation and UI state.
- `FinalBitLutShell` — main Compose application shell.
- `AugustTokens` / `BitLutExpressiveTheme` — canonical UI token/theme layer.

## Design system: August v3

BitLut follows the Android adaptation of August v3:

- Canvas: light neutral background.
- Navy: navigation/dark anchor.
- Surface: white controls and cards.
- Lime: filled primary action/brand surface with Ink foreground.
- Purple: focus, selection detail, and secondary interaction.
- Inter Variable: primary typeface.
- Main touch targets: at least 44 dp.
- Pressed scale for primary actions: approximately `0.98`.
- Avoid decorative glass layers and dependency-heavy blur effects.

Do not reintroduce the removed Haze integration. It caused a Kotlin metadata
mismatch because Haze 1.7.x was built with Kotlin 2.2.x while BitLut intentionally
remained on Kotlin 2.0.21.

## Codespaces build

For constrained GitHub Codespaces, use the low-memory build:

```bash
./gradlew :app:assembleDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

A successful build is required before commit.

## Release workflow

GitHub Actions builds signed release APKs using repository secrets and
`.github/workflows/release.yml`.

Required secrets include:

- `BITLUT_KEYSTORE_BASE64`
- `BITLUT_KEYSTORE_PASSWORD`
- `BITLUT_KEY_ALIAS`
- `BITLUT_KEY_PASSWORD`
- `HUAWEI_APP_ID`
- `AGCONNECT_SERVICES_JSON_BASE64`

Do not commit signing files, `.huawei.env`, `agconnect-services.json`,
local environment files, Repomix output, patch backups, or generated APKs.

## Development rules

1. Preserve working synchronization and import behavior.
2. Prefer small, surgical changes over unrelated refactors.
3. Do not add health permissions without an explicit product decision.
4. Do not generate fake health data.
5. Keep sync/background reliability semantics intact unless the task directly
   requires changing them.
6. Treat `CHANGELOG.md` as history; keep `README.md`, `CLAUDE.md`,
   `CONTEXT.md`, and `SESSION_HANDOFF.md` current rather than cumulative.
7. Run a real build before commit.

For implementation constraints and engineering gotchas, read `CLAUDE.md`.
For a compact machine-readable project context, read `CONTEXT.md`.
For continuation in a new conversation, read `SESSION_HANDOFF.md`.
""",

    "CLAUDE.md": r"""# CLAUDE.md

Read this first before changing BitLut. This file is a current engineering
contract, not a historical journal. Historical changes belong in `CHANGELOG.md`.

## Product boundary

BitLut is a free, open-source Android app built with Kotlin and Jetpack Compose.

Its core job is:

```text
HUAWEI Health -> BitLut -> Android Health Connect
```

BitLut reads approved activity data from HUAWEI Health and writes real,
source-derived records to Health Connect. There is no BitLut cloud backend,
account system, advertising, or health-data sale.

Current production scope is activity-only:

- steps
- distance
- floors / elevation
- active calories when available under the approved Huawei scope
- workouts / activity sessions

Do not add sleep, heart rate, SpO2, HRV, stress, or other biometric categories
without an explicit scope decision and permission review.

## Current baseline — 2026-08-22

- HUAWEI Health Kit application scope has been approved.
- Real-device authorization and real Huawei activity reads have succeeded.
- Partial Huawei scope availability must be handled per metric; one denied
  category must not invalidate otherwise successful activity reads.
- Kotlin Gradle plugin: 2.0.21.
- Gradle: 8.9.
- Android Gradle Plugin: 8.7.3.
- Java/JVM target: 17.
- Debug build passes in GitHub Codespaces.
- Haze is not part of the dependency graph.
- August v3 is the active UI design system.

The former "waiting for Huawei 50005 approval" project-wide blocker and the
former Glass 2.0 / Haze navigation baseline are obsolete.

## Architecture anchors

### HUAWEI side

`HuaweiHealthManager`
- owns Health Kit authorization
- reads only approved activity categories
- classifies authorization failures
- must tolerate partial scope rollout
- must never synthesize replacement data for unavailable categories

`HuaweiConfig`
- contains HUAWEI configuration/scope mapping
- changing requested scopes is a product/review decision, not a UI cleanup

### Health Connect side

`GoogleHealthManager`
- owns Health Connect read/write behavior
- uses deterministic metadata/client record IDs to prevent uncontrolled duplicates
- reads dashboard data from Health Connect
- writes only real Huawei/import-derived data

### Synchronization

`SyncOrchestrator`
- coordinates immediate synchronization

`BackgroundSyncScheduler` / `SyncWorker`
- own WorkManager scheduling/execution
- preserve existing lease/retry/reliability semantics unless the task is
  specifically about synchronization reliability

Never "fix" synchronization by inserting generated demo records.

### Local resilience

`DashboardSnapshotCache`
- preserves last-known dashboard data across cold launch/transient provider failure

`HuaweiExportParser`
- performs bounded local import of supported HUAWEI export data

`AchievementsStore`
- keeps local record/achievement state

### UI

`DashboardViewModel`
- aggregates dashboard state
- avoid multiplying Health Connect calls from UI recomposition or refresh loops

`FinalBitLutShell`
- current main Compose shell
- large file; do not split it during unrelated bugfix/design work

`GlassCards.kt`
- legacy filename; do not infer that Glass 2.0 is still the design contract

`ui/components/GlassNavigation.kt`
- legacy filename retained for source continuity
- current implementation must remain dependency-free native Compose
- do not reintroduce Haze solely to make the filename literal

## August v3 Android contract

Canonical roles:

- Ink: `#151728`
- Canvas: `#F7F8FC`
- Surface: `#FFFFFF`
- Soft surface: `#F2F3F7`
- Lime: `#DFFF6A`
- Lime hover: `#D2F650`
- Lime active: `#C3E93E`
- Purple: `#6E5CF6`
- Purple dark: `#5140DC`
- Purple soft: `#EEEAFF`
- Navy: `#151728`
- Navy raised: `#1C1E33`
- Navy soft: `#24263D`

Rules:

1. Lime is a filled primary/brand surface, not small text on white.
2. Content on Lime is Ink, never white.
3. Purple is interaction/focus/secondary detail, not the primary CTA.
4. Navy is the dark anchor.
5. Main touch targets are at least 44 dp.
6. Standard primary control height is around 48 dp.
7. Press feedback should be restrained (`scale(0.98)`), not bouncy.
8. Avoid permanent glassmorphism and neon glow.
9. Inter Variable is the primary font.
10. Semantic roles should be centralized in the token/theme layer.

Haze was removed after it introduced Kotlin 2.2 metadata into a Kotlin 2.0.21
project. Do not solve a visual effect by forcing a project-wide compiler upgrade
unless that migration is independently justified and explicitly requested.

## Build rules

The reliable constrained-Codespaces command is:

```bash
./gradlew :app:assembleDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

Why: D8/dex packaging may appear stalled under Codespaces memory pressure when
the default worker/heap behavior is used. A successful Kotlin compile alone is
not the full build gate; `assembleDebug` must pass.

Do not casually:
- bump Kotlin/AGP/compileSdk for a cosmetic dependency
- clear the entire Gradle cache as a first response
- add dependency-resolution `force` rules for a compiler metadata mismatch

## Critical engineering invariants

### No fake data

BitLut never generates placeholder health records to make a UI or sync test look
successful.

### Duplicate protection

Keep deterministic record identity and non-overlapping sync behavior. Do not
introduce parallel writers or broad historical overlap without understanding
the current metadata strategy.

### Partial HUAWEI scope behavior

HUAWEI may make approved categories available incrementally. Failure of one
optional/temporarily unavailable category must not erase successful steps,
distance, elevation, or session data from the same synchronization attempt.

### Health Connect call volume

Avoid N+1 provider calls from dashboard/UI code. Prior reliability work removed
expensive unused reads and refresh storms. If adding a metric, prefer bounded
bulk reads and local aggregation.

### Cancellation

Coroutine cancellation is control flow. Re-throw `CancellationException`;
do not convert routine cancellation into a user-facing failure.

### Edge-to-edge

Screens rendered outside the main `Scaffold` content slot need explicit safe
area handling. Do not assume `Scaffold` padding reaches sibling overlays/screens.

### Widget/cache

Background sync and graceful no-op paths must keep the dashboard/widget cache
fresh enough to display real local Health Connect data even if a Huawei action
cannot run at that moment.

## Coding principles

Use KISS, YAGNI, DRY, and small-change discipline.

- Prefer deleting accidental complexity over abstracting it.
- Do not add a library when a small native Compose implementation is enough.
- Do not refactor unrelated working sync code during UI work.
- One semantic component should own one semantic role; e.g. primary buttons
  should not receive arbitrary per-call-site brand colors.
- Keep compatibility aliases only when they reduce migration risk; remove them
  in a dedicated cleanup, not opportunistically.

## Patch script conventions

The user works through GitHub Codespaces and expects standalone Python patch
scripts for non-trivial repository edits.

Patch scripts should:

1. be written in English
2. be runnable from repository root
3. validate expected files/anchors
4. abort instead of guessing when the source state is unexpected
5. be idempotent
6. include a verify mode when practical
7. never expose secrets
8. not auto-push doc-only housekeeping changes
9. be tested for Python syntax before delivery

For text replacement:
- first determine whether the old anchor exists
- require a unique expected anchor when editing structurally
- only then treat the new state as "already applied"
- avoid generic fragments that can accidentally match unrelated code

## Git hygiene

Do not commit:

- `.huawei.env`
- `.env.signing.local`
- `.signing/`
- `app/agconnect-services.json`
- `local.properties`
- `.bitlut_patch_backup/`
- `repomix-output.xml`
- APK/build outputs
- Python bytecode/cache directories

One-off migration/patch scripts should not accumulate permanently in repository
root after their changes are committed and documented.

## Documentation source-of-truth

- `README.md` — human-facing product/build overview
- `CLAUDE.md` — current engineering contract and gotchas
- `CONTEXT.md` — compact machine-readable current context
- `SESSION_HANDOFF.md` — next-session continuation
- `CHANGELOG.md` — historical record
- `docs/HEALTH_DATA_PERMISSION_MATRIX.md` — health permission/data contract
- `docs/HUAWEI_DAILY_CHUNKING_166.md` — HUAWEI read chunking invariant
- `docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md` — production/review reference
- `docs/PRIVACY_POLICY.md` — privacy policy

If a historical document conflicts with current source code or the four root
current-context docs, verify against the code and current build before acting.
""",

    "CONTEXT.md": r"""# BitLut Context

Last refreshed: 2026-08-22

## Identity

BitLut is an open-source Android app that bridges supported HUAWEI Health
activity data into Android Health Connect.

```text
HUAWEI Health -> BitLut -> Android Health Connect
```

No BitLut cloud server. No account. No advertising. No fake health records.

## Production data scope

Allowed/current product scope:

- steps
- distance
- floors climbed / elevation gained
- active calories when available under approved Huawei scope
- exercise/activity sessions

Out of scope unless explicitly approved later:

- sleep
- heart rate
- SpO2
- HRV
- stress
- other biometric categories

## Current platform status

HUAWEI Health Kit:
- app-level scope approved
- real-device authorization has succeeded
- real activity reads have succeeded
- partial category availability must be tolerated
- one category returning 50005/denied must not invalidate successful categories

Health Connect:
- permission flow works
- dashboard reads work
- source-derived writes work
- deterministic metadata is used for duplicate protection

Build:
- Kotlin 2.0.21
- Gradle 8.9
- AGP 8.7.3
- JVM 17
- debug `assembleDebug` passes in constrained GitHub Codespaces mode
- Haze removed
- no Kotlin 2.2 dependency may leak into the current Kotlin 2.0 build

## Core architecture

- `HuaweiHealthManager` — HUAWEI auth and reads
- `GoogleHealthManager` — Health Connect reads/writes
- `SyncOrchestrator` — immediate sync coordination
- `BackgroundSyncScheduler` / `SyncWorker` — periodic/background sync
- `HuaweiExportParser` — local archive import
- `DashboardSnapshotCache` — resilient last-known dashboard snapshot
- `AchievementsStore` — local records/achievements
- `DashboardViewModel` — dashboard aggregation
- `FinalBitLutShell` — Compose shell
- `AugustTokens` / `BitLutExpressiveTheme` — UI semantic token/theme layer

## UI baseline

August v3 Android adaptation is canonical.

Semantic hierarchy:
- Canvas = `#F7F8FC`
- Surface = white
- Navy = dark anchor
- Lime = primary filled action/brand surface
- Ink = content on Lime
- Purple = focus/secondary interaction

Rules:
- no white text on Lime
- no Lime small text on white/canvas
- no Purple primary CTA competing with Lime
- no dependency-heavy blur/glass effect for navigation
- touch targets >= 44 dp
- restrained motion (`scale(0.98)` for primary press)
- Inter Variable is the primary font

Legacy filenames containing `Glass` do not mean Glass 2.0 is still canonical.

## Reliability rules

- Never generate fake health data.
- Preserve duplicate protection and existing WorkManager reliability semantics.
- Avoid N+1 Health Connect reads and refresh storms.
- Re-throw coroutine cancellation.
- Keep last-known dashboard/widget state resilient to transient provider failures.
- Preserve edge-to-edge safe-area handling for screens outside the main Scaffold.

## Codespaces build gate

```bash
./gradlew :app:assembleDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

Build must pass before commit.

## Git / secrets

Required release secrets are managed by GitHub Actions.

Never commit:
- `.huawei.env`
- `.env.signing.local`
- `.signing/`
- `app/agconnect-services.json`
- `local.properties`
- `.bitlut_patch_backup/`
- `repomix-output.xml`
- build outputs

## Change discipline

- KISS / YAGNI / DRY
- surgical edits
- no unrelated refactors
- no new health permission without explicit decision
- no compiler/toolchain migration for a purely cosmetic dependency
- doc history goes to `CHANGELOG.md`, not current-context files
""",

    "SESSION_HANDOFF.md": r"""# BitLut — Session Handoff

Current handoff date: 2026-08-22.

Use this file together with a fresh repository/Repomix export. Read `CLAUDE.md`
before making code changes. Treat source code plus a fresh successful build as
the final authority when any old historical note disagrees.

## What BitLut is

BitLut is a Kotlin + Jetpack Compose Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect
```

It is activity-only, local-first, open source, and does not generate fake
health records.

## Current state

The project is no longer globally blocked on HUAWEI Health Kit approval.

Confirmed project direction:
- HUAWEI app scope approved
- real-device Huawei authorization has succeeded
- real activity data has been read
- partial Huawei category availability is handled independently
- Health Connect integration and background synchronization are working
- dashboard/cache/import reliability hardening is already in place

On 2026-08-22 a GUI/build recovery sprint removed Haze after Haze 1.7.x brought
Kotlin 2.2 metadata into the Kotlin 2.0.21 project. The correct resolution was
to remove the cosmetic dependency rather than migrate the entire toolchain.

After that change:
- `compileDebugKotlin` passes
- constrained Codespaces `assembleDebug` passes
- Haze is absent from the intended dependency graph
- August v3 is the current UI baseline

## Current UI direction

Forget the old Glass 2.0 / neo-glassmorphism baseline.

August v3 Android adaptation:
- light Canvas
- Navy navigation/dark anchor
- white control surfaces
- Lime filled primary actions with Ink content
- Purple focus/secondary interaction
- restrained motion
- native Compose navigation surfaces
- no Haze blur dependency

Some source filenames still contain `Glass`; they are legacy names, not design
requirements.

## Non-negotiable engineering constraints

1. Preserve working Huawei -> Health Connect synchronization.
2. Never generate fake health data.
3. Do not add biometric/sleep scopes without explicit approval.
4. Do not refactor unrelated sync/data code during UI work.
5. Maintain duplicate protection.
6. Keep Health Connect call volume bounded.
7. Treat coroutine cancellation correctly.
8. Use low-memory Codespaces build settings before assuming dex packaging is hung.
9. Avoid adding libraries for effects native Compose can express simply.
10. Run a full debug assemble before commit.

## Reliable Codespaces command

```bash
./gradlew :app:assembleDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

The normal build previously appeared to stop around dex/global synthetics under
Codespaces resource pressure. The constrained command completed successfully.

## Working convention

- communicate in Russian
- write code/comments/commit messages in English
- use standalone Python patch scripts for non-trivial repository edits
- patch scripts must be idempotent and verify expected source state
- do not manually paste large Kotlin diffs
- doc-only housekeeping should be reviewed before commit/push
- preserve a working baseline instead of doing broad refactors

## Current files to trust

Primary:
- `README.md`
- `CLAUDE.md`
- `CONTEXT.md`
- `SESSION_HANDOFF.md`
- `CHANGELOG.md`

Production references:
- `docs/HEALTH_DATA_PERMISSION_MATRIX.md`
- `docs/HUAWEI_DAILY_CHUNKING_166.md`
- `docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md`
- `docs/HUAWEI_50005_APPGALLERY_VERIFICATION.md` for historical/diagnostic context
- `docs/PRIVACY_POLICY.md`

Do not treat removed one-off sprint/recovery documents as active architecture.

## Safe next work

Continue GUI modernization within August v3, but keep it isolated from sync/data
logic. Before adding a dependency, first ask whether the same result can be
implemented with existing Compose APIs and tokenized semantic components.

Larger architecture work such as splitting `FinalBitLutShell.kt`, introducing
new manager abstractions, or migrating the Gradle/toolchain should be separate,
explicitly scoped sprints rather than side effects of UI polish.
""",
}

REMOVE = [
    "docs/SUCCESSFUL_BUILD.md",
    "docs/release-1.9.9.md",
    "docs/SYNC_RELIABILITY_165.md",
    "docs/UI_LOCALIZATION_ARCHITECTURE_CLEANUP.md",
    "docs/V15_NAVIGATION_RECOVERY.md",
    "docs/HUAWEI_IMPORT_REENABLE.md",
    "docs/HUAWEI_IMPORT_DIAGNOSIS.md",
    "docs/HUAWEI_REVIEW_APPEAL_TEXT.txt",
    "docs/HUAWEI_REVIEW_NOTES.txt",
    "scripts/verify_gui_motion_patch.py",
    "add_activity_rings_and_goal_progress.py",
    "add_dashboard_card_layout_editor.py",
    "add_workout_pace_and_filter.py",
    "audit_remove_dead_code.py",
    "august_phase1_foundation_tokens.py",
    "august_phase2_card_depth_and_growth_lime.py",
    "august_phase3_buttons.py",
    "august_phase4_navigation.py",
    "august_phase5_inter_font.py",
    "fix_augustfont_experimental_api_optin.py",
    "fix_cold_launch_sync_reliability.py",
    "fix_composable_context_error.py",
    "fix_duplicate_goals_string.py",
    "fix_haze_aar_metadata_conflict.py",
    "fix_workout_icons_and_achievements.py",
    "navbar_neoglassmorphism.py",
    "navbar_real_blur_haze.py",
    "remove_activity_rings.py",
    "remove_elevation_card.py",
    "bitlut_august_v3_build_fix.py",
]

KEEP_REQUIRED = [
    "CHANGELOG.md",
    "docs/BACKLOG.md",
    "docs/DEEP_CODE_REVIEW_2026.md",
    "docs/HEALTH_DATA_PERMISSION_MATRIX.md",
    "docs/HUAWEI_50005_APPGALLERY_VERIFICATION.md",
    "docs/HUAWEI_DAILY_CHUNKING_166.md",
    "docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md",
    "docs/PRIVACY_POLICY.md",
    ".github/workflows/release.yml",
    "app/build.gradle.kts",
]

FORBIDDEN_CURRENT_DOC_TEXT = [
    "Glass 2.0 visual system",
    "icon-only floating bottom navigation",
    "current blocker: 50005 approval pending",
    "See also: docs/SUCCESSFUL_BUILD.md",
    'implementation("dev.chrisbanes.haze:haze:1.7.2")',
]

REQUIRED_CURRENT_DOC_TEXT = {
    "README.md": ["August v3", "Haze has been removed", "--max-workers=1"],
    "CLAUDE.md": ["Current baseline — 2026-08-22", "Haze is not part of the dependency graph", "scale(0.98)"],
    "CONTEXT.md": ["Last refreshed: 2026-08-22", "Haze removed", "Kotlin 2.0.21"],
    "SESSION_HANDOFF.md": ["Current handoff date: 2026-08-22", "constrained Codespaces `assembleDebug` passes", "Forget the old Glass 2.0"],
}


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def ensure_repo_root() -> None:
    required = [
        "README.md",
        "CLAUDE.md",
        "CONTEXT.md",
        "SESSION_HANDOFF.md",
        "app/build.gradle.kts",
        "build.gradle.kts",
        "gradlew",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    if missing:
        fail("Run this script from the BitLut repository root. Missing: " + ", ".join(missing))


def apply() -> None:
    ensure_repo_root()

    print("==> Updating current source-of-truth documentation")
    for rel, content in DOCS.items():
        path = ROOT / rel
        normalized = content.rstrip() + "\n"
        previous = path.read_text(encoding="utf-8") if path.exists() else None
        if previous == normalized:
            print(f"   unchanged: {rel}")
        else:
            path.write_text(normalized, encoding="utf-8")
            print(f"   updated:   {rel}")

    print("==> Removing superseded housekeeping artifacts")
    for rel in REMOVE:
        path = ROOT / rel
        if path.exists():
            if path.is_dir():
                fail(f"Refusing to remove directory unexpectedly listed as file: {rel}")
            path.unlink()
            print(f"   removed:   {rel}")
        else:
            print(f"   absent:    {rel}")

    print("==> Removing generated local housekeeping artifacts")
    for rel in [".bitlut_patch_backup", "__pycache__"]:
        path = ROOT / rel
        if path.exists():
            if not path.is_dir():
                fail(f"Expected directory but found file: {rel}")
            shutil.rmtree(path)
            print(f"   removed:   {rel}/")

    repomix = ROOT / "repomix-output.xml"
    if repomix.exists():
        repomix.unlink()
        print("   removed:   repomix-output.xml")

    print("==> Apply complete")
    print("Run: python3 bitlut_housekeeping_2026_08_22.py --verify")


def verify() -> None:
    ensure_repo_root()
    errors: list[str] = []

    for rel in KEEP_REQUIRED:
        if not (ROOT / rel).exists():
            errors.append(f"required file was removed: {rel}")

    for rel, markers in REQUIRED_CURRENT_DOC_TEXT.items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing current doc: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{rel} missing required marker: {marker!r}")

    combined = "\n".join(
        (ROOT / rel).read_text(encoding="utf-8")
        for rel in DOCS
        if (ROOT / rel).exists()
    )

    for marker in FORBIDDEN_CURRENT_DOC_TEXT:
        if marker in combined:
            errors.append(f"stale current-doc marker remains: {marker!r}")

    for rel in REMOVE:
        if (ROOT / rel).exists():
            errors.append(f"superseded file still exists: {rel}")

    app_gradle = (ROOT / "app/build.gradle.kts").read_text(encoding="utf-8")
    if "dev.chrisbanes.haze" in app_gradle:
        errors.append("Haze dependency/reference still exists in app/build.gradle.kts")

    root_gradle = (ROOT / "build.gradle.kts").read_text(encoding="utf-8")
    if 'version "2.0.21"' not in root_gradle:
        errors.append('root build.gradle.kts no longer contains expected Kotlin version "2.0.21"')

    if errors:
        print("==> Verification FAILED")
        for error in errors:
            print(f" - {error}")
        raise SystemExit(1)

    print("==> Verification passed")
    print("Current docs are refreshed, stale housekeeping artifacts are gone,")
    print("required production references remain, and Haze is absent from app Gradle config.")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.apply:
        apply()
    else:
        verify()


if __name__ == "__main__":
    main()
