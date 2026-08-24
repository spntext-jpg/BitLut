#!/usr/bin/env python3
"""
BitLut patch v6: refresh CLAUDE.md, CHANGELOG.md, README.md, SESSION_HANDOFF.md,
and CONTEXT.md to reflect today's four shipped patches, and remove the
now-superseded one-off housekeeping script.

Context:
  Four patches shipped and built successfully today (2026-08-22): the
  four-metric workout card contract, the August v3 dark theme activation,
  the Hero/Tangerine/navbar-width patch, and this session's dark-mode
  icon/text fix + navbar bounce + biking elevation metric. None of the
  five trusted docs reflected any of this -- they still described a
  six-slot workout card contract, a light-only August v3, and had no
  mention of Tangerine, the dark theme, or the navbar bounce.

  CONTEXT.md was not explicitly named in the request (CLAUDE.md, CHANGELOG,
  README, and SESSION_HANDOFF were) but is one of the same "trusted current
  docs" set the other four reference, and was making the identical stale
  claims (six-slot cards, light-only design system) that would immediately
  contradict the four files updated by explicit request. Included as an
  in-passing fix for that reason, not scope creep -- flagged here plainly
  rather than silently added.

  bitlut_housekeeping_2026_08_22.py (repo root) is deleted as part of the
  requested ".md cleanup": it is a one-off script (per its own docstring
  and filename date) whose job was to replace the four/five trusted docs
  with a frozen snapshot of their then-current content and delete a list of
  already-superseded historical docs -- both of which it already did
  successfully (verified: none of its REMOVE-listed files exist in the
  current repo). Its DOCS dict holds that frozen, now-stale snapshot; if
  run again with --apply, it would silently overwrite this exact patch's
  doc updates back to the old text. Nothing else in the repo references
  this script (verified: only its own docstring/print statements mention
  its filename). The two docs it explicitly listed as KEEP_REQUIRED --
  docs/BACKLOG.md and docs/DEEP_CODE_REVIEW_2026.md -- are untouched; they
  are deliberately retained historical references, not clutter, and were
  never part of the ".md cleanup" ask.

  Doc files are replaced wholesale (not anchored text edits) because docs
  are not part of any Android source set AGP scans, so whole-file
  replacement carries none of the risk it would for res/ or source files,
  and today's SESSION_HANDOFF.md rewrite in particular reorganized several
  sections rather than editing isolated lines in place, which does not
  anchor cleanly as a small set of text-anchored edits.

Files touched:
  - CLAUDE.md, CHANGELOG.md, SESSION_HANDOFF.md, README.md, CONTEXT.md
    (whole-file replacement with refreshed content)
  - bitlut_housekeeping_2026_08_22.py (deleted)

Usage:
    python3 patch_docs_refresh_v6.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / "docs_refresh"


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    relative = path.relative_to(ROOT)
    backup_path = BACKUP_DIR / relative
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        print(f"  backed up -> {backup_path.relative_to(ROOT)}")

CLAUDE_MD = """# CLAUDE.md

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
- August v3 is the active UI design system, **with a real system-driven dark
  theme** (activated 2026-08-22; see "August v3 Android contract" below).
- Workout cards show four metrics (Duration, Distance, Avg speed, and a
  4th slot that is type-aware: Steps for most exercise types, Elevation
  gain for biking specifically).

The former "waiting for Huawei 50005 approval" project-wide blocker, the
former Glass 2.0 / Haze navigation baseline, the former six-metric workout
card contract, and the former light-only August v3 baseline are all
obsolete.

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
- `workoutMetricDisplays()` is exercise-type-aware: the 4th metric slot is
  Steps for most types, Elevation gain specifically for
  `ExerciseSessionRecord.EXERCISE_TYPE_BIKING`. If adding a new exercise
  type with its own more-logical 4th metric, follow this same pattern
  rather than adding a new generic branch structure.
- `HealthAccent` is `@Composable` (dark-theme-aware); `BitPalette.light()`/
  `dark()` are plain non-composable factories and hardcode their own fixed
  accent values directly rather than calling `HealthAccent`.

`GlassCards.kt`
- legacy filename; do not infer that Glass 2.0 is still the design contract

`ui/components/GlassNavigation.kt`
- legacy filename retained for source continuity
- current implementation must remain dependency-free native Compose
- do not reintroduce Haze solely to make the filename literal
- `NAV_BAR_OUTER_HORIZONTAL_MARGIN` controls the nav bar pill's width
  (currently 24.dp, up from an original flat 16.dp); tune this single
  constant rather than touching individual button sizing to adjust overall
  nav bar width
- all three buttons (Today, Settings, Refresh) use a `spring()`-based
  bounce on press-release, by explicit product decision; do not revert to
  a flat `tween` for nav bar press feedback without a similarly explicit
  decision to do so

## August v3 Android contract

Canonical roles (light mode):

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
- Tangerine: `#F28500` (added 2026-08-22)
- Tangerine active: `#DD7A00` (added 2026-08-22)

Dark mode (activated 2026-08-22, `isSystemInDarkTheme()`-driven): extends
the existing Navy ramp's role rather than introducing a second dark
palette. Dark Canvas = Navy, dark Surface = NavyRaised, dark Soft =
NavySoft, mirroring light mode's own Canvas -> Surface -> Soft elevation
relationship. The Steps Hero card is NavyRaised in both modes unchanged
(it was always the dark anchor). Lime stays a filled surface with Ink
content in both modes. The source design doc has no "dark mode" section of
its own -- it only specifies Navy as a permanent architectural anchor
inside an otherwise light-canvas product (a different product, a web media
tool) -- so the dark-mode surface mapping above is this project's own
design decision, contrast-checked against WCAG math, not a literal doc
translation.

`HealthAccent` (`activity`/`mind`/`violet`, used for many icon tints and
value-number colors across dashboard cards) is `@Composable`, resolving to
Lime in dark mode and InkSoft in light mode. If you add a new call site
that needs this accent and it is NOT inside a `@Composable` function
(e.g. inside `BitPalette.light()`/`dark()`, which are plain factory
functions), you cannot call `HealthAccent.activity()` there -- hardcode the
correct fixed value directly for that one factory instead, matching what
`BitPalette.light()`/`dark()` already do.

Tangerine is the "on/active" signal for exactly two things: Settings toggle
tracks and the navbar Refresh button fill. It is not a second primary CTA
competing with Lime. Purple keeps its existing focus/link/selection-detail
role everywhere else, including the navbar's own focus-visible ring.

Rules:

1. Lime is a filled primary/brand surface, not small text on white.
2. Content on Lime is Ink, never white. Same rule for Tangerine (white on
   Tangerine fails WCAG AA at ~2.6:1; Ink clears ~6.9:1).
3. Purple is interaction/focus/secondary detail, not the primary CTA.
4. Navy is the dark anchor in both light and dark mode.
5. Main touch targets are at least 44 dp.
6. Standard primary control height is around 48 dp.
7. Press feedback on the bottom nav bar specifically uses a light spring
   bounce (`Spring.DampingRatioMediumBouncy`) by explicit product decision
   (2026-08-22) -- this is a deliberate, scoped exception to the general
   restrained-press-feedback rule below, not a contradiction of it. Every
   other press feedback stays a restrained `scale(0.98)` tween, not bouncy.
8. Avoid permanent glassmorphism and neon glow.
9. Inter Variable is the primary font.
10. Semantic roles should be centralized in the token/theme layer.

Haze was removed after it introduced Kotlin 2.2 metadata into a Kotlin 2.0.21
project. Do not solve a visual effect by forcing a project-wide compiler upgrade
unless that migration is independently justified and explicitly requested.

## Build rules

The reliable constrained-Codespaces command is:

```bash
./gradlew :app:assembleDebug \\
  --no-daemon \\
  --max-workers=1 \\
  --no-watch-fs \\
  --console=plain \\
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \\
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
current-context docs, verify against the code and current build before acting."""

CHANGELOG_MD = """# Changelog

## 2026-08-22 (d) -- dark-mode invisible icons/text, navbar bounce on every button, biking's 4th metric fixed

Fourth patch of the day, on real-device feedback after the dark theme and
Tangerine/navbar work shipped: several elements were still unreadable in
dark mode, and a bike workout card showed "Steps" as its 4th metric, which
made no sense for cycling.

- Root cause for all dark-mode gray text/icons (Last 7 Days card numbers,
  Personal Records trophy/flame icons, workout-type icons on
  WorkoutRecencyCard, several Settings/onboarding icons): `HealthAccent`
  (`activity`/`mind`/`violet`) was a single fixed `AugustColor.InkSoft`
  alias, correct against light mode's white Surface but never made
  theme-aware. Measured against dark mode's NavyRaised card background,
  InkSoft contrasts at ~1.2:1 -- effectively invisible, matching the report
  exactly. `palette.secondaryText` (used for some of the same labels) was
  already correctly theme-aware before this fix and needed no change --
  the bug was entirely in `HealthAccent`.
- `HealthAccent`'s three properties became `@Composable` functions reading
  `isSystemInDarkTheme()` directly (`HealthAccent.activity` ->
  `HealthAccent.activity()`, etc.), resolving to Lime in dark mode
  (~14.5:1 contrast against NavyRaised, contrast-checked) and unchanged
  InkSoft in light mode. All ~43 call sites across ~15 composables were
  converted from property access to function calls in the same patch.
  `BitPalette.light()`/`dark()` -- plain non-composable factory functions
  that previously also read `HealthAccent.activity`/`.mind` -- could not
  follow the same conversion (a non-composable function cannot call a
  `@Composable` one), so each now hardcodes its own already-correct value
  directly instead (InkSoft for `light()`, Lime for `dark()`).
- Navbar: all three buttons' press-release scale animation changed from a
  flat `tween` to a `spring` (`Spring.DampingRatioMediumBouncy`,
  `Spring.StiffnessMedium`), producing a slight overshoot-then-settle "light
  bounce" on release, as requested for every button. The two side
  destination buttons (Today/Settings) also gained a small icon tilt
  (-8 degrees on press, same spring) as their own distinct press flourish,
  echoing but not literally copying the Refresh button's existing -24-degree
  rotation, which is unchanged.
- Biking's 4th workout-card metric: `workoutMetricDisplays()` now takes the
  session's `exerciseType` and swaps Steps for Elevation gain specifically
  for `EXERCISE_TYPE_BIKING` (confirmed choice over Active Calories --
  elevation is more semantically meaningful for cycling despite being, like
  Steps, frequently unpopulated for a given ride; falls back to `--` same as
  every other slot). This re-introduces `workout_stat_elevation_label` /
  `workout_elevation_value` to `strings.xml` (en+ru), correctly removed as
  dead code by the four-metrics patch three days ago -- a deliberate,
  same-project follow-up reversal driven by new product direction, not an
  accidental duplicate of already-completed work. Active Calories is
  untouched: still dropped from the card entirely everywhere else, still
  scope-denied by Huawei independent of exercise type.
- Found and fixed in passing: `scripts/verify_workout_nav_freshness_sprint.py`
  still asserted the retired `AugustColor.LimeActive` string for the navbar
  Refresh button's pressed-fill token -- the Tangerine patch earlier this
  week (see below) changed that token to `AugustColor.TangerineActive` but
  never updated this assertion, which had been silently failing since that
  patch landed. Unrelated to today's five requests; fixed while already in
  this exact file for the elevation-related assertion updates.

## 2026-08-22 (c) -- Steps Hero two-value layout, Tangerine accent, narrower navbar

Third patch of the day. Three independent, confirmed UI changes.

- Steps Hero card: Distance now renders as its own big-number +
  small-"km" block, the same visual weight as Steps, instead of being
  folded into Steps' small trailing unit string ("steps · 0.1 km"). New
  `StepsHeroCard`/`HeroMetricBlock` composables handle this; `MinimalMetricCard`
  itself is untouched and stays in use everywhere else it already appeared
  (Connect Google lock screen, the Distance card inside
  `DashboardOrderedCard`, etc.) -- this is a dedicated Hero-only composable,
  not a generalization of the existing one. The steps-goal progress ring
  moved below both numbers instead of sitting beside them, since two
  big-number blocks plus a ring all competing for one row was too tight
  once Distance became first-class instead of trailing text. Added
  `distance_unit_km` string (en+ru) -- `distance_today_value` bundles the
  number and "km" into one template string, which is exactly why Distance
  couldn't be split into a big number + small unit before this patch.
- New `AugustColor.Tangerine`/`TangerineActive` tokens: replaces Purple as
  the "on/active" signal in exactly two places -- the two Settings toggle
  tracks (`DataSourceToggleRow`, `WidgetVisibilityRow`) and the navbar's
  center Refresh button fill (was Lime). Purple keeps every other existing
  role (focus rings, links, selection detail) untouched, including the
  navbar's own focus-visible ring. `#F28500` is the commonly documented
  "Tangerine" named color (ColorHexa/Wikipedia's canonical value), not any
  single company's brand orange. `TangerineActive` (`#DD7A00`, the Refresh
  button's pressed-state fill) is derived by applying the same relative HSV
  saturation/value shift that produces `LimeActive` from `Lime`, not
  eyeballed. Ink-on-Tangerine clears ~6.9:1 WCAG AA; white-on-Tangerine
  fails at ~2.6:1, so the Refresh icon moved from `LimeInk` to the
  equivalent `Ink`.
- Navbar: outer horizontal margin increased 16.dp -> 24.dp
  (`NAV_BAR_OUTER_HORIZONTAL_MARGIN`) so the two side destination buttons
  shrink and the pill reads narrower -- a deliberately conservative first
  pass, not the ~44.dp a literal "20% narrower" derivation would produce on
  a typical ~400.dp-wide screen, since that number could not be visually
  verified in this environment. The Refresh button itself grew 15%
  (58.dp -> 67.dp, icon 27.dp -> 31.dp) to read as the dominant middle
  action against the now-narrower side buttons.
- Found and fixed in passing: one pre-existing unused import
  (`AugustColor.AugustRadius`) in `GlassNavigation.kt` -- every shape in
  that file uses a raw `RoundedCornerShape(N.dp)` literal, never
  `AugustRadius.*`, verified by grep before removal.

## 2026-08-22 (b) -- August v3 dark theme activated, driven by system appearance

Second patch of the day. `BitPalette.dark()` already existed in
`FinalBitLutShell.kt` but was completely unreachable: the one call site was
hardcoded to `BitPalette.light()`, and two separate verify-script guardrails
explicitly asserted that OS dark mode must NOT be wired up. This was mostly
"finish and activate a dark theme someone already half-built," not a
from-scratch design.

- New `AugustDarkScheme` (`darkColorScheme(...)`) in `BitLutExpressiveTheme.kt`,
  wired to `isSystemInDarkTheme()`; status bar color and icon contrast now
  follow the active scheme. Dark Canvas = Navy, dark Surface = NavyRaised,
  dark Soft = NavySoft -- extending the existing Navy ramp's role rather
  than inventing a second, unrelated dark palette, matching the light
  scheme's own Canvas -> Surface -> Soft elevation relationship, just
  inverted. The source August v3 doc (re-attached this session) has no
  "dark mode" section of its own -- it only specifies Navy as a permanent
  architectural anchor inside an otherwise light-canvas product (a
  different product, a web media tool) -- so this dark theme's actual
  surface mapping is this session's own design decision, not a literal
  doc translation.
- Every reused color pairing checked against real WCAG contrast math before
  reuse, not eyeballed: Surface/DarkSecondaryText/Lime/Ink all clear 7:1+
  against Navy/NavyRaised/NavySoft. `DangerFg` (tuned for white) drops to
  2.62:1 on NavyRaised and was deliberately NOT reused for dark error text;
  `AugustColor`'s pre-existing but previously-unused `DarkErrorContainerFg`
  (`#FFC9C9`) is used instead, clearing 11:1+ against both Navy and
  NavyRaised.
- Confirmed product decisions (not inferred): Lime stays a filled surface
  with Ink text in both modes; the Steps Hero card stays NavyRaised
  unchanged in both modes (`SoftCard`'s `hero` branch in `GlassCards.kt`
  already hardcoded `NavyRaised` independent of `palette`, so it needed no
  change at all).
- Flipped the two verify-script guardrails in
  `scripts/verify_sync_august_v3_recovery.py` that explicitly forbade dark
  mode; added assertions for the new `AugustDarkScheme` content itself.
- Found and fixed in passing: a stale comment in `MainActivity.kt` that
  described an `isSystemInDarkTheme()` call inside `FinalBitLutShell` which
  did not actually exist anywhere in the codebase before this patch; two
  already-broken, unrelated verify-script assertions in
  `scripts/verify_reliability_and_design_sprint.py` (a `sleep =
  HealthAccent.sleep` check referencing a field removed by an earlier
  sleep-feature removal, and a `LightShadowTint` check referencing a symbol
  that no longer exists after `GlassCards.kt`'s phase-2 rewrite); one
  now-dead `glass_cards` file-read variable in that same verify script,
  orphaned by removing its only two checks.

## 2026-08-22 (a) -- workout cards narrowed to four metrics for every exercise type

First patch of the day, prompted by a real-device diagnostic log review.
The log's "last workout shows wrong steps, no distance" turned out to be
confirmed-expected data staleness, not a bug: that workout was more than 7
days old, outside BitLut's continuous per-minute Huawei sync window, and its
`steps=251` figure was a legitimate Health Connect aggregate over a
historical interval with genuinely sparse underlying Huawei source data
(0 distance points, 0 activeCalories, separately scope-denied). No code
path was misbehaving; this matches the project's own "do not reopen the
workout-distance fallback" rule.

- The requested change instead: `workoutMetricDisplays()` rewritten to drop
  Active Calories and Elevation gain from the workout card display
  entirely (not conditionally hidden -- removed as a display contract) for
  ALL exercise types, leaving Duration, Distance, Avg speed, Steps.
  Rationale: Huawei `activeCalories` is frequently scope-denied (50005) and
  elevation is rarely populated for the same reason, so the old six-slot
  layout mostly showed four real values and two permanent dashes.
  `ActivitySessionData.activeCaloriesKcal`/`.elevationMeters` are unchanged
  -- still read/synced for CSV export and daily totals; only this card's
  display was narrowed.
- `WorkoutStatsGrid`'s cap changed from `metrics.take(6)` to `metrics.take(4)`.
- Removed the now-dead `workout_stat_calories_label`/`workout_calories_value`/
  `workout_stat_elevation_label`/`workout_elevation_value` strings (en+ru) --
  nothing referenced them after the display change. (Two of these four were
  re-added three patches later the same day for biking's 4th metric; see
  2026-08-22 (d) above -- a deliberate follow-up, not a mistake undone.)
- Updated `scripts/verify_workout_nav_freshness_sprint.py`, which had
  hard-coded the old six-slot contract as a regression gate; left unpatched
  it would have permanently failed after this legitimate change.

## 2026-07-22 -- partial Huawei scope denial no longer discards the whole sync

Real device log evidence this time: `localHuaweiAuthorized=true`, with
steps (176 points) and distance (232 points) both read and deduplicated
successfully -- the first confirmed real-device authorization success in
this project's history. In the same sync attempt, `activeCalories` alone
failed with `HUAWEI_SCOPE_UNAUTHORIZED` (50005), while steps/distance/
elevation succeeded -- Huawei approves scopes incrementally, and the code
did not handle that.

- Root cause: `HuaweiHealthManager.readSnapshot()` built its
  `HuaweiHealthSnapshot` by evaluating all 6 category reads as constructor
  arguments in one expression. A `SecurityException` from any one of them
  (deliberately re-thrown by `readPointsRaw()`, "propagate to caller") threw
  out of the whole function, discarding every already-successfully-read
  category. `SyncWorker`'s catch block then called
  `huaweiManager.markAppGalleryVerificationRequired()` unconditionally on
  ANY 50005 -- which sets `isAuthorized=false`/`pendingApproval=true` --
  incorrectly resetting a *correctly obtained* authorization state back to
  "not authorized," so every subsequent sync attempt regressed to a full
  graceful no-op without even trying to read data again.
- Fix: `readSnapshot()` now reads each of the 6 categories (steps,
  distance, floors, elevation, activeCalories, activitySessions)
  independently, catching `SecurityException` per category and simply
  skipping that one (same graceful-degradation shape already used for
  floors on SDKs without a floors DataType). Authorization is only treated
  as fully denied -- re-throwing to trigger `SyncWorker`'s existing 50005
  handling exactly as before -- if EVERY category comes back denied with
  zero successes. A partial denial now proceeds normally with whatever
  categories ARE authorized, and no longer touches the persisted
  authorization state at all.
- Updated the stale comment on `readPointsRaw()`'s `SecurityException`
  re-throw (previously said "must propagate to SyncWorker" -- it now
  propagates to `readSnapshot()`, which decides skip-one-category vs.
  fully-unauthorized, not directly to `SyncWorker` for a single-category
  failure).
- Updated CLAUDE.md: refreshed "Current status" (first confirmed real
  device auth success; this fix), corrected Gotcha 13's now-stale "working
  theory" framing, added Gotcha 14 documenting the exact bug and fix.

## 2026-07-18 -- Huawei auth failure reasons + retry button (post-AppGallery-rejection)

Triggered by a real AppGallery review rejection: "does not collect to
Huawei Health successfully." The test evidence quoted was BitLut's own
`toast_huawei_pending` string, confirmed via exact text match -- meaning
the reviewer hit the same 50005 wall real devices had shown for weeks, with
no way to tell from that one message which of 5 different HMS failure
codes was actually in play (all 5 triggered the identical toast).

- Added `HuaweiAuthFailureReason` enum (`SCOPE_PENDING_APPROVAL`,
  `PRIVACY_NOT_ACCEPTED`, `CERTIFICATE_MISMATCH`, `INVALID_CONFIGURATION`,
  `UNKNOWN`) to `HealthDataContracts.kt`, plus `lastAuthFailureReason()` on
  `HuaweiHealthReader`.
- `HuaweiHealthManager.handleAuthorizationResult()` now classifies and
  persists the specific reason via a new `classifyFailure()` mapping (HMS
  codes 50005/50011/907135702/6003/907135000 -> the enum above), separately
  from the pre-existing `isAuthorized()`/`isPendingApproval()` booleans.
- Generalized the Settings screen's single 50005-only explanation card
  (`HuaweiPendingApprovalCard`) into `HuaweiAuthIssueCard`, which shows the
  right explanation for whichever of the 5 reasons actually happened --
  previously the other 4 cases showed nothing at all in Settings, just the
  same generic toast.
- Added a "Try connecting again" retry button on the card, shown only for
  `SCOPE_PENDING_APPROVAL` and `PRIVACY_NOT_ACCEPTED` (the two reasons a
  fresh attempt can plausibly fix) -- deliberately not shown for
  `CERTIFICATE_MISMATCH`/`INVALID_CONFIGURATION`, which need an AppGallery
  Connect-side fix first and would just fail the same way again.
- Replaced the old generic `toast_huawei_pending` toast (now dead, deleted)
  with `toast_huawei_failed`, which points to Settings for the specific
  explanation instead of trying to cram reason-specific detail into a
  fleeting Toast.
- Added `huawei_reason_*_title`/`_body` string resources for the 4
  previously-unhandled reasons, plus `huawei_retry_connect`, in both
  `values/strings.xml` and `values-ru/strings.xml`.
- Removed the now-dead `SyncUiState.isHuaweiPendingApproval` boolean field
  (fully superseded by `lastHuaweiAuthFailureReason`, confirmed zero
  remaining reads via grep) and its population in `refreshStatuses()`.

Separately: while this fix was in progress, Huawei approved BitLut's
Health Kit scope application at the app level (App ID 117824685). Device
logs taken immediately after still showed `localHuaweiAuthorized=false`/
50005 -- expected, not a regression, since that's a locally-cached flag
from the last real OAuth attempt, decoupled from the server-side approval
(see CLAUDE.md Gotcha 12). The new retry button exists specifically to
make the next required action -- a fresh authorization attempt -- obvious,
since Huawei's approval notification arrives outside the app entirely and
BitLut has no way to detect it on its own.

## 2026-07-16 -- two real-device hotfixes: widget colors, edge-to-edge insets, widget stuck while pending

Two separate real-device reports after the 2026-07-14 sprint below shipped,
each root-caused from device logs/screenshots rather than guessed.

**Widget colors (`Gradle compileDebugKotlin` failure, caught before commit)**
- `ColorProvider(day = Color(...), night = Color(...))` does not exist in
  `glance-appwidget:1.1.1` -- only `ColorProvider(color: Color)` and
  `ColorProvider(resId: Int)` do (see CLAUDE.md Gotcha 9). Switched
  `widget/HomeWidget.kt` to resource-qualified colors instead: added
  `widget_card`/`widget_text`/`widget_secondary_text` to both
  `values/colors.xml` (light) and a new `values-night/colors.xml` (dark).

**Edge-to-edge inset regression ("Copy button half covered" in Log Viewer)**
- `PermissionsOnboardingScreen` and `LogViewerScreen` both render as
  siblings of the main `Scaffold`, not through its content slot, so they
  never got the Scaffold's automatic safe-area inset padding -- invisible
  before `enableEdgeToEdge()`, a real visible bug the moment it shipped
  (see CLAUDE.md Gotcha 10). Fixed with `.statusBarsPadding()`/
  `.navigationBarsPadding()` on both screens' root `Box`. The 2026-07-14
  sprint's own new `DataScopesScreen` was unaffected -- it renders inside
  `SettingsScreen`, inside the Scaffold's own padding.

**Home screen widget stuck showing nothing while Huawei stayed pending**
- `SyncWorker` only ever called `refreshDashboardCacheAfterWrite()` (the
  function the widget's data ultimately comes from) deep inside the
  Huawei-sync-succeeded branch. While Huawei was pending -- true for weeks
  -- that branch was never reached, so the widget stayed stuck indefinitely
  even though Health Connect could already contain real data from other
  apps regardless of Huawei's state (see CLAUDE.md Gotcha 11). Fixed by
  calling the refresh on the `isPendingApproval()` and
  `!localHuaweiAuthorized` graceful-no-op paths too.
- Investigated but deliberately did NOT change: a separately reported
  "sync only works after opening Google Fit first" symptom. Traced
  `DashboardViewModel.load()`'s live `readDashboardSnapshot()` call and
  confirmed it does not depend on Huawei's auth state at all -- with
  Huawei still blocked at the time, BitLut could not have been writing the
  data being seen, so it was very likely coming from another app (Google
  Fit) that may only push to Health Connect when opened. Not a BitLut bug
  as far as the evidence showed; worth re-checking once Huawei sync is
  actually live and BitLut itself is writing on its own schedule.

## 2026-07-14 -- Sprint 2: edge-to-edge/predictive back, trust screen, Huawei pending-approval card, CSV export, home screen widget

Delivered as two scripts: Part 1 (no new Gradle dependency) and Part 2 (the
home screen widget, which adds `androidx.glance:glance-appwidget:1.1.1`),
kept separate specifically so a problem in the higher-risk widget piece
wouldn't block the other four.

**Edge-to-edge + predictive back**
- `MainActivity.onCreate()` now calls `enableEdgeToEdge()` before
  `setContent`. `AndroidManifest.xml`'s `<application>` tag gained
  `android:enableOnBackInvokedCallback="true"` for the predictive back
  gesture. targetSdk stayed at 35 (not bumped to 36) since the current AGP
  version doesn't support compileSdk 36.

**"What data is shared" trust screen**
- New `DataScopesScreen` composable, reachable any time from a link in
  Settings (not a one-time onboarding step) -- lists the actual 5 Huawei
  Health Kit scopes BitLut requests, matching `requestedScopeNames()`
  verbatim in substance, plus a one-line statement that everything goes to
  Google Health Connect on-device and nowhere else. Answers the most common
  complaint pattern in reviews of similar sync apps: "I don't understand
  what's being synced where."

**Huawei pending-approval status card**
- `SyncUiState` gained `isHuaweiPendingApproval`; a new
  `HuaweiPendingApprovalCard` in Settings explains the 50005 wait state in
  plain language instead of a silent no-op degrade, so a new install
  doesn't read "no data" as "broken." (Generalized into
  `HuaweiAuthIssueCard` on 2026-07-18 above -- this card's specific name
  and single-reason scope no longer exist as of that date.)

**CSV export**
- New `util/CsvExporter.kt`: writes daily totals (`GoogleHealthManager.
  readDailyTotals()`, added alongside it, same raw-records-not-aggregate
  pattern as the dashboard) plus recent workouts to a CSV in `cacheDir/
  export/`, handed off via a new `FileProvider` (`res/xml/file_paths.xml`)
  to the system share sheet. Reachable from a link in Settings.

**Home screen widget (Jetpack Glance)**
- New `widget/HomeWidget.kt` + `HomeWidgetReceiver`: one tile, today's
  steps + last-sync time, tap anywhere enqueues the same
  `BackgroundSyncScheduler.enqueueImmediateSync` work request the Settings
  "Sync now" button uses. Reads `DashboardSnapshotCache` only, never Health
  Connect directly, so `provideGlance()` stays cheap. New
  `res/xml/home_widget_info.xml` provider info (2x1 cell, 30-minute
  fallback `updatePeriodMillis`, real refresh driven by `SyncWorker`
  calling `updateAll()` after every successful cache write).

## 2026-07-14 -- full removal sprint: sleep/HR/SpO2/stress + History deleted outright

Follow-up to the 2026-07-10 series. That sprint removed History from the
bottom nav and stubbed sleep/heart-rate/SpO2/stress fields to empty/null,
but deliberately left the underlying code in place, dormant, as minimal-diff
precedent. This sprint changes that precedent for code proven to be
permanently dead (see CLAUDE.md Gotcha 8) and deletes it outright instead.

**Sleep / heart-rate / SpO2 / stress -- removed in full**
- `GoogleDashboardSnapshot`, `DashboardUiState`, and `DashboardSnapshotCache`
  no longer carry `sleepHours`, `sleepQualityScore`, `heartRateBpm`,
  `heartRateTodayBars`, `stressScore`, `spo2Percent`, `sleepBars`, or
  `heartRateBars` fields at all -- previously these existed and were just
  hardcoded to `0.0`/`null`/`emptyList()`.
- `HealthAccent.heart` deleted outright (confirmed zero real UI usage --
  only ever referenced by the also-deleted `BitPalette.heart` mapping).
  `HealthAccent.sleep` renamed to `HealthAccent.violet`: it *was* live UI
  (the Manual Sync card's accent color in Settings), just never actually
  representing sleep data, so the color stays and only the misleading name
  goes. `BitPalette.sleep`/`BitPalette.heart` fields deleted (confirmed
  zero reads anywhere, only ever assigned).
- Corrected a stale doc comment above `HealthAccent` describing a "Sleep
  progress ring on Summary" that had not existed in the UI for several
  sprints, and two similarly stale comments in `MinimalSquareTile`/
  `ProgressRingChip` referencing a "Heart/Sleep" 2x2 grid and "Sleep vs the
  8h reference" that describe a design that was never actually shipped.
- Removed 8 dead sleep/heart-rate-named string resources (`bpm`,
  `bpm_unit`, `avg_bpm_7d`, plus 5 History-only strings listed below) from
  both `values/strings.xml` and `values-ru/strings.xml`, confirmed unused
  via a full `R.string.<name>` grep first.

**History -- removed in full, not left dormant**
- Deleted `HistoryScreen`, `HistoryRangeChips`, and `WorkoutTypeCard`
  composables from `FinalBitLutShell.kt` (confirmed unreachable from the
  `MainTab` enum / nav dispatch -- History was already removed from the
  bottom nav in the 2026-07-10 sprint, this just finishes the job).
- Deleted the bar-chart infrastructure that existed solely to feed
  History's chart, once confirmed to have zero other callers: `MetricBar`
  data type, `computeMetricBarRanges`/`bucketsOfEqualSize`/
  `calendarMonthBuckets`, `readStepsBars()`, `readWorkoutSummariesByType()`,
  `MiniSparkline`, `formatBarValueShort()`, `barDateLabel()`. Deleted the
  entire `ui/components/MetricCharts.kt` file (existed only for the now-gone
  `MetricBarChartCard`) and the standalone `MetricBarReflectionTest.kt`
  scratch file (only exercised the now-gone `MetricBar` type).
- Removed the `stepsBars`/`workoutSummaries` fields from
  `GoogleDashboardSnapshot`/`DashboardUiState` and their
  `DashboardSnapshotCache` JSON (de)serialization -- these existed only to
  feed the deleted History chart and per-type workout list.
- Removed `HISTORY_RANGE_OPTIONS`, `DashboardViewModel.onHistoryRangeSelected()`,
  `DashboardUiState.selectedHistoryRangeDays`, and the
  `onHistoryRangeSelected` parameter/wiring through `FinalBitLutShell` and
  `MainActivity`.
- `HealthConnectManager.readDashboardSnapshot()` lost its `daysBack`
  parameter (in the interface, the `GoogleHealthManager` implementation,
  and the `SyncWorker` call site that had hardcoded it to `7` anyway) --
  it was only ever there to plumb History's range-chip selection through,
  and had been fully unused inside the function body since the 2026-07-10
  trim.
- Removed 6 dead History-named string resources (`tab_history`,
  `history_title`, `history_subtitle`, `history_short_title`, `tab_7days`,
  `history_title_final`) plus 3 more that were dead *and* referenced the
  removed screen in their text (`permissions_body`, `onboarding_step5`,
  `connect_google_history_body`) from both locale files, and reworded
  `widget_visibility_section_body` to drop its now-inaccurate "...and in
  history" clause.
- Updated `CLAUDE.md` to match: Gotcha 8's "deliberately unused, don't
  clean up reflexively" list no longer includes anything from History
  (only `DashboardWidgetGrid`/`WeeklyComparisonCard`/
  `readWeekOverWeekComparison` remain dormant by that precedent -- unrelated
  to today's change, still awaiting a possible future UI return).

## 2026-07-10 -- sync reliability + UI simplification sprint series

Six days, one continuous thread: get the log-viewer build green, get the
HUAWEI Health Kit application resubmitted cleanly, then chase a sync
freshness bug through five distinct real root causes using actual device
logs rather than guessing. Ends with a fully working, tested sync pipeline
that is simply waiting on HUAWEI's own scope approval to show real data.

**Build fix**
- Added the missing `collectAsStateWithLifecycle` import that broke the
  log-viewer build (the other two reported compiler errors were cascades
  from this one, not separate bugs).

**HUAWEI Health Kit application**
- Diagnosed the "Basic activity management permission and scenario
  description are not provided" rejection: Huawei's Data Usage Scenario
  tab requires a description for every checked scope, matched 1:1 -- ours
  was missing for the already-approved basic scope.
- Confirmed individual developers cannot access HUAWEI's advanced data tier
  (sleep/heart-rate/SpO2/stress) at all, regardless of application quality
  -- dropped those from scope entirely rather than fighting an unwinnable
  approval.
- Drafted the Data Usage / App Info / Self-Check sheet content for the 5
  scopes actually used in code (Step, Distance/ascent/altitude, Activity
  record, Activity, Reading historical data).

**Health-data cleanup**
- Removed 24 unused sleep/heart-rate/SpO2/stress string resources (in both
  `values/strings.xml` and `values-ru/strings.xml`) left over from before
  the activity-only pivot -- confirmed unused via a full grep for
  `R.string.<name>` across every `.kt` file first.
- Fixed a stale README section that falsely described pulse/sleep/SpO2/
  stress as currently-working features; removed 4 stale rows from the
  "supported Health Connect records" table for the same reason.

**History screen removed**
- The unresolved "history bars don't update on range toggle" bug was never
  fully root-caused; the screen was removed from the bottom nav entirely
  instead (2-tab nav: Today, Settings). Its composables/view-model logic
  were left in place, unreachable, not deleted.

**Sync reliability chase (chronological, each one a real fix to a real
regression, found from actual device logs)**
1. Cold launch showed cached data with no auto-refresh -> added an
   automatic Huawei -> Health Connect sync trigger.
2. That trigger only ran once (`onCreate`, once per process) -> moved to
   `onResume()` so every return to the app re-triggers it, not just the
   first one.
3. A lease-collision race meant a no-op "already syncing" result could
   trigger a premature dashboard refresh before the real sync had actually
   finished writing -> `SyncOrchestrator` now checks the completion reason
   and defers follow-up refreshes instead of refreshing immediately on a
   no-op.
4. Concurrent permission checks at cold launch could produce a false
   "permissions missing" flash -> coalesced behind a mutex + 3s cache in
   `GoogleHealthManager`.
5. Root cause of "only fresh after opening Google Fit first":
   `HealthConnectClient.aggregate()` is a provider-side cache that lags
   behind recent writes -> switched steps/distance/calories reads to raw
   `readRecords()` + manual sum, matching the pattern already used
   (correctly) by workout-minutes/active-hours reads.
6. Root cause of "sync got worse, widgets disappear, Connect Health Connect
   flashes": `DashboardViewModel.load()` was making ~16 Health Connect calls
   per invocation, including ~9 for screens/cards removed from the UI
   sprints ago (`stepsBars` alone was one call per day in range) -> trimmed
   to only what's actually rendered, and added a 5-second debounce on
   manual/resume sync triggers. A real device log showed 11+ triggers in 60
   seconds before this fix; confirmed gone after.
7. `DashboardViewModel.load()` was catching its own routine
   `CancellationException` (from cancelling a superseded prior call) as a
   generic error, logging noise and forcing `isLoading=false` on jobs that
   were only ever superseded -> re-throw `CancellationException` before the
   generic catch, matching the guard already used everywhere else in this
   codebase.

Confirmed via a clean final device log: no rate-limit errors, no swallowed
cancellations, no foreground-only read failures. The only remaining blocker
to real data is HUAWEI's own scope approval (`localHuaweiAuthorized=false`,
error 50005) -- not a code issue.

**UI simplification sprint**
- Today screen fixed to exactly 5 widgets matching the actual data scope:
  steps today, workout time, personal records, streak, last imported
  workout. Removed the calories/active-hours mini-grid and the
  week-over-week comparison card from the UI (their code was left dormant,
  see the trimming fix above for why the *data calls* also had to go, not
  just the UI).
- Both remaining screens switched from scrolling `LazyColumn` to a fixed,
  compact `Column`. Settings: connection cards dropped their body/status
  text (title + icon only), Connect/Refresh buttons compacted onto one row
  each. Daily goals moved to the top of Settings, calories dropped from it.
  Widget-visibility toggle section removed entirely -- widget set is fixed
  now, not user-configurable.
- Added a centered, larger (66dp vs 54dp), warm-orange manual refresh
  button to the bottom nav, wired to the same action as Settings' "Sync
  now".
- Fixed the steps-today value font clipping past 10,000 (dynamic font size
  based on formatted string length instead of a fixed 56sp)."""

SESSION_HANDOFF_MD = """# BitLut — Session Handoff

Current handoff date: 2026-08-22.

Read `CLAUDE.md` and this file before changing code. Source code plus a fresh
successful build are the final authority if an older historical note conflicts.

## Product

BitLut is a local-first Kotlin + Jetpack Compose Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect
```

Current product scope is activity-only. BitLut must never synthesize missing
health data.

## End-of-session baseline

Four patches shipped and built successfully today (2026-08-22), in this order:

1. Workout cards narrowed from six metrics to four, for every exercise type
   (Duration, Distance, Avg speed, Steps).
2. August v3 dark theme activated -- system-driven (`isSystemInDarkTheme()`),
   not a manual in-app toggle. `BitPalette.dark()` already existed in the
   codebase but was unreachable; this activated it.
3. Steps Hero card given a two-value layout (Steps + Distance each as their
   own big number), new Tangerine accent color for Settings toggles and the
   navbar Refresh button, navbar narrowed slightly and Refresh button
   enlarged 15%.
4. Dark-mode follow-up fixes from real-device feedback: several icons/text
   were still gray/invisible in dark mode (root cause: `HealthAccent` was
   not theme-aware, now fixed -- see "Dark theme" below); navbar buttons
   given a light spring-based bounce on press; biking's 4th workout metric
   changed from Steps (illogical for cycling) to Elevation gain.

Also still true from before today:

- HUAWEI -> Health Connect synchronization working on a real device.
- Manual and periodic WorkManager synchronization.
- Sync lease/reuse protection against concurrent jobs.
- Partial Huawei scope denial handled per category instead of failing the whole sync.
- Health Connect request-storm protection and bounded dashboard reads.
- Last-known permission state preserved across transient Health Connect provider failures.
- Dashboard freshness timestamp tied to real data changes rather than app-open time.
- Haze removed; no blur dependency/toolchain migration.
- Settings daily goals reduced to the only currently used goal: steps.

## Dark theme (2026-08-22)

System-driven, not an in-app toggle. Dark Canvas = Navy, dark Surface =
NavyRaised, dark Soft = NavySoft (extends the existing Navy ramp rather than
a second palette). Steps Hero card is NavyRaised in both modes, unchanged.
Lime stays a filled surface with Ink content in both modes.

`HealthAccent` (`activity`/`mind`/`violet`) is now `@Composable`, resolving
to Lime in dark mode (~14.5:1 contrast against NavyRaised) and the original
InkSoft in light mode. This was the root cause of a real-device bug found
today: these three properties were a single fixed InkSoft value that
measured ~1.2:1 contrast against dark-mode cards -- effectively invisible.
Affected the Last 7 Days card's numbers, Personal Records' icons, and
workout-type icons on `WorkoutRecencyCard`, among others. If you add a new
`HealthAccent` consumer, remember it must be called from a `@Composable`
context -- `BitPalette.light()`/`dark()` cannot call it and instead hardcode
their own matching fixed values directly.

If something still looks gray/low-contrast in dark mode that wasn't covered
by today's fix, it is very likely another hardcoded `AugustColor.*`
reference that bypasses both `palette` and `HealthAccent` -- grep for direct
`AugustColor.InkSoft`/`AugustColor.Muted` usage in the same style as
`HealthAccent` had before today's fix.

## Workout metric contract (revised 2026-08-22)

Every recent-workout card shows four slots. The first three are the same for
every exercise type; the fourth is exercise-type-aware:

1. Duration
2. Distance
3. Average speed
4. **Steps** for most exercise types, **Elevation gain** specifically for
   `ExerciseSessionRecord.EXERCISE_TYPE_BIKING`

Data rules (unchanged from before):

- Duration comes from the real ExerciseSessionRecord interval.
- Distance comes only from real imported/session/Health Connect distance data.
- Average speed is derived only when real distance exists.
- Steps come from real Health Connect step data overlapping the workout.
- Elevation comes only from real elevation data.
- Missing metrics render as `—`.
- Never estimate distance from steps.
- Never estimate calories from duration/body assumptions.
- Never invent elevation or speed.

Active calories and (for non-biking types) elevation gain were deliberately
removed from the card display entirely -- not hidden conditionally, removed
as a display contract -- because Huawei frequently scope-denies
`activeCalories` (50005) and elevation is rarely populated for the same
underlying reason, so the old six-slot layout mostly showed four real values
and two permanent dashes. `ActivitySessionData.activeCaloriesKcal` /
`.elevationMeters` are still read/synced for CSV export and daily totals;
only card display was narrowed.

The current distance boundary fallback is deliberately conservative:

- it runs only when exact aggregate/session distance is missing;
- it queries a narrow window around the displayed workout;
- it attributes only exact temporal overlap;
- source records longer than three hours are rejected;
- if no real overlap exists, distance remains missing.

**Do not reopen this fallback logic.** This is the same standing rule as
before today; nothing about today's four-metric-slot or biking-elevation
change touches this fallback at all.

## Health Connect quota rules

Do not reintroduce unbounded pagination into dashboard hot paths.

Keep:

- bounded newest-first dashboard reads;
- coalesced/throttled dashboard refreshes;
- permission caching;
- one authoritative post-sync snapshot;
- narrow per-workout fallback only where necessary.

CSV export or explicit diagnostic tools may use broader reads because they are
not hot-path UI operations.

## August v3

Canonical roles (light mode):

- Canvas `#F7F8FC`
- Surface `#FFFFFF`
- Ink / Navy `#151728`
- Navy Raised `#1C1E33`
- Navy Soft `#24263D`
- Lime `#DFFF6A`
- Lime Active `#C3E93E`
- Purple `#6E5CF6`
- Muted `#6F7385`
- Tangerine `#F28500` (2026-08-22)
- Tangerine Active `#DD7A00` (2026-08-22)

Dark mode (system-driven, 2026-08-22): dark Canvas = Navy, dark Surface =
NavyRaised, dark Soft = NavySoft. See "Dark theme" section above for the
full rationale and the `HealthAccent` gotcha.

Rules:

- Steps card is the dark Hero, in both light and dark theme.
- Normal cards are white Surface in light mode, NavyRaised in dark mode.
- Lime is the primary filled action color with Ink content, both modes.
- Tangerine is the "on/active" signal for Settings toggles and the navbar
  Refresh button only -- not a second primary CTA.
- Purple is for focus/selection/secondary interaction, unchanged role.
- Inter Variable is global typography.
- Nav bar press feedback uses a light spring bounce (explicit exception);
  everything else stays restrained motion.
- Do not reintroduce Haze or permanent glassmorphism.

## Settings goals

Only the steps goal is currently exposed in Settings.

Active-minutes and calorie goals are not product controls and should not be
reintroduced unless those goals become real product features with downstream use.

## Build gate

Use the constrained Codespaces build:

```bash
./gradlew :app:assembleDebug \\
  --no-daemon \\
  --max-workers=1 \\
  --no-watch-fs \\
  --console=plain \\
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \\
  -Pkotlin.compiler.execution.strategy=in-process
```

A full `assembleDebug` must pass before commit.

## Working convention

For all coding in this project:

- reason about code in English;
- write code, comments, identifiers, and commit messages in English;
- prefer one standalone Python patch script;
- embed verification in that script when practical;
- final delivery should contain the patch and one command block only;
- make surgical changes and preserve working behavior;
- every new patch script filename must differ from all previous ones in the
  project (append v2, v3, etc.) -- never reuse or overwrite a prior patch
  script's filename, even for a fix to that same patch.

## Trusted current docs

- `README.md`
- `CLAUDE.md`
- `CONTEXT.md`
- `SESSION_HANDOFF.md`
- `CHANGELOG.md`
- `docs/HEALTH_DATA_PERMISSION_MATRIX.md`
- `docs/HUAWEI_DAILY_CHUNKING_166.md`
- `docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md`
- `docs/PRIVACY_POLICY.md`

## Next-session rule

Start from the working sync baseline. Do not reopen the workout-distance
problem by trying to force a number into a session that has no real distance
record. Do not revert the dark-theme `HealthAccent` fix back to a plain
non-composable object without an equally thorough audit of every call site's
theme-awareness. Focus future work on new explicitly scoped product
improvements.
"""

README_MD = """<p align="center">
  <img src="docs/bitlut-mascot.png" width="140" alt="BitLut" />
</p>

<h1 align="center">BitLut</h1>

<p align="center">
  <strong>Открытый Android-мост между HUAWEI Health и Android Health Connect</strong>
</p>

<p align="center">
  Локально на устройстве · Без аккаунта · Без рекламы · Без выдуманных данных
</p>

---

## Что такое BitLut

BitLut переносит поддерживаемые данные активности из **HUAWEI Health** в
**Android Health Connect**, чтобы ими могли пользоваться другие совместимые
приложения.

```text
HUAWEI Health
      ↓
   BitLut
      ↓
Health Connect
      ↓
Совместимые приложения
```

BitLut не создаёт собственный профиль пользователя, не отправляет данные на
сервер BitLut и не подменяет отсутствующие показатели тестовыми значениями.

## Что синхронизируется

| Категория | Статус |
| --- | --- |
| Шаги | Поддерживается |
| Дистанция | Поддерживается, если HUAWEI Health отдаёт реальные записи |
| Набор высоты | Поддерживается при наличии данных |
| Активные калории | Поддерживается при доступном Huawei scope |
| Тренировки / активности | Поддерживается при доступном Huawei scope |
| Этажи | Huawei SDK не предоставляет подходящий DataType в текущей интеграции |

Сон, пульс, SpO2, HRV, стресс и другие биометрические категории не входят в
текущий продуктовый scope.

## Карточки тренировок

Каждая карточка тренировки показывает четыре показателя. Первые три —
одинаковые для любого типа тренировки, четвёртый зависит от типа:

1. **Длительность**
2. **Дистанция**
3. **Средняя скорость**
4. **Шаги** — для большинства типов тренировок; **Набор высоты** — для
   велотренировок (для велосипеда шаги нерелевантны)

Значения берутся из реальных данных Health Connect, уже импортированных BitLut.
Средняя скорость рассчитывается только из реальной дистанции и длительности.

Если источник не содержит конкретный показатель, BitLut показывает `—`.
Приложение не восстанавливает отсутствующую дистанцию по шагам, не оценивает
калории формулами и не создаёт mock-данные.

## Синхронизация

BitLut поддерживает:

- ручную синхронизацию;
- фоновую синхронизацию через WorkManager;
- защиту от параллельных sync jobs;
- устойчивый sync cursor;
- частичный успех, когда отдельный Huawei scope временно недоступен;
- локальный snapshot dashboard для быстрого и устойчивого открытия приложения.

Dashboard использует ограниченные Health Connect reads, чтобы не создавать
request storm и не исчерпывать quota провайдера.

## Интерфейс

Интерфейс использует дизайн-систему **August v3** со светлой и тёмной темой
(тёмная тема следует системной настройке устройства):

- светлый Canvas `#F7F8FC` / тёмный Canvas — Navy `#151728`;
- белые Surface-карточки / тёмные Surface-карточки — Navy Raised `#1C1E33`;
- Navy `#151728` как тёмный архитектурный цвет в обеих темах;
- Lime `#DFFF6A` для primary actions в обеих темах;
- Tangerine `#F28500` для активных переключателей в настройках и кнопки
  обновления в нижней навигации;
- Purple `#6E5CF6` для focus и secondary interaction;
- Inter Variable;
- верхняя карточка Steps — тёмный Hero в обеих темах, показывает шаги и
  дистанцию как два равнозначных крупных числа;
- компактная нижняя навигация на native Compose без Haze, с лёгкой
  пружинной анимацией при нажатии на каждую кнопку.

## Настройки

В разделе дневных целей остаётся только **цель по шагам** — единственная цель,
которая сейчас реально используется продуктом.

Настройки также включают:

- выбор источника данных;
- подключение Health Connect / HUAWEI Health;
- ручную синхронизацию;
- импорт архива HUAWEI;
- CSV export;
- фильтр тренировок;
- управление виджетами;
- диагностические и privacy-разделы.

## Принципы данных

> **Real data only.**

BitLut записывает и показывает только данные, полученные от реального источника
или корректно вычисленные из реальных исходных значений.

Отсутствующее значение означает `—`, а не приблизительную цифру.

## Технологии

- Kotlin
- Jetpack Compose
- Android Health Connect
- HUAWEI Health Kit
- WorkManager
- Gradle 8.9
- Android Gradle Plugin 8.7.3
- Kotlin 2.0.21
- Java 17

## Сборка в GitHub Codespaces

```bash
./gradlew :app:assembleDebug \\
  --no-daemon \\
  --max-workers=1 \\
  --no-watch-fs \\
  --console=plain \\
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \\
  -Pkotlin.compiler.execution.strategy=in-process
```

Перед commit сборка должна завершаться `BUILD SUCCESSFUL`.

## Privacy

BitLut работает локально и не имеет собственного backend для хранения health
data. Актуальная политика находится в
[`docs/PRIVACY_POLICY.md`](docs/PRIVACY_POLICY.md).

## Для разработки

Основные документы:

- [`CLAUDE.md`](CLAUDE.md) — инженерные правила и invariants;
- [`CONTEXT.md`](CONTEXT.md) — компактный текущий контекст;
- [`SESSION_HANDOFF.md`](SESSION_HANDOFF.md) — состояние проекта для следующей сессии;
- [`CHANGELOG.md`](CHANGELOG.md) — история изменений.

Главный принцип разработки: **не ломать работающую синхронизацию ради UI и не
выдумывать данные ради заполнения интерфейса**."""

CONTEXT_MD = """# BitLut Context

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

August v3 Android adaptation is canonical, with a real system-driven dark
theme (2026-08-22).

Semantic hierarchy (light mode):
- Canvas = `#F7F8FC`
- Surface = white
- Navy = dark anchor
- Lime = primary filled action/brand surface
- Ink = content on Lime
- Purple = focus/secondary interaction
- Tangerine (`#F28500`, added 2026-08-22) = "on/active" signal for Settings
  toggles and the navbar Refresh button specifically, not a second primary CTA

Dark mode (`isSystemInDarkTheme()`-driven, not a manual toggle): dark Canvas
= Navy, dark Surface = NavyRaised, dark Soft = NavySoft. `HealthAccent`
(many icon tints/value-number colors) is `@Composable` and resolves to Lime
in dark mode, InkSoft in light mode -- this was a real bug fixed 2026-08-22
(previously a fixed InkSoft value measured ~1.2:1 contrast on dark cards,
effectively invisible).

Rules:
- no white text on Lime or Tangerine
- no Lime/Tangerine small text on white/canvas
- no Purple primary CTA competing with Lime
- no dependency-heavy blur/glass effect for navigation
- touch targets >= 44 dp
- restrained motion (`scale(0.98)` for primary press) EXCEPT the bottom nav
  bar, which uses a light spring bounce on press by explicit decision
- Inter Variable is the primary font

Legacy filenames containing `Glass` do not mean Glass 2.0 is still canonical.

Workout cards show four metrics: Duration, Distance, Avg speed, and a
type-aware 4th slot (Steps for most types, Elevation gain for biking).

## Reliability rules

- Never generate fake health data.
- Preserve duplicate protection and existing WorkManager reliability semantics.
- Avoid N+1 Health Connect reads and refresh storms.
- Re-throw coroutine cancellation.
- Keep last-known dashboard/widget state resilient to transient provider failures.
- Preserve edge-to-edge safe-area handling for screens outside the main Scaffold.

## Codespaces build gate

```bash
./gradlew :app:assembleDebug \\
  --no-daemon \\
  --max-workers=1 \\
  --no-watch-fs \\
  --console=plain \\
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \\
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
- doc history goes to `CHANGELOG.md`, not current-context files"""


def replace_doc(rel_path: str, new_content: str) -> bool:
    path = ROOT / rel_path
    normalized = new_content.rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == normalized:
        print(f"  already applied, skipping: {rel_path}")
        return False
    if path.exists():
        backup(path)
    path.write_text(normalized, encoding="utf-8")
    print(f"  updated: {rel_path}")
    return True


def main() -> None:
    print("== Step 1/6: CLAUDE.md ==")
    replace_doc("CLAUDE.md", CLAUDE_MD)

    print("== Step 2/6: CHANGELOG.md ==")
    replace_doc("CHANGELOG.md", CHANGELOG_MD)

    print("== Step 3/6: SESSION_HANDOFF.md ==")
    replace_doc("SESSION_HANDOFF.md", SESSION_HANDOFF_MD)

    print("== Step 4/6: README.md ==")
    replace_doc("README.md", README_MD)

    print("== Step 5/6: CONTEXT.md ==")
    replace_doc("CONTEXT.md", CONTEXT_MD)

    print("== Step 6/6: remove superseded bitlut_housekeeping_2026_08_22.py ==")
    housekeeping = ROOT / "bitlut_housekeeping_2026_08_22.py"
    if housekeeping.exists():
        backup(housekeeping)
        housekeeping.unlink()
        print("  removed: bitlut_housekeeping_2026_08_22.py")
    else:
        print("  already applied, skipping: bitlut_housekeeping_2026_08_22.py (already absent)")

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    )
    if not status.stdout.strip():
        print("\nNothing staged -- already clean. No commit needed.")
        return

    print("\n== Committing (doc-only change; no compile gate needed) ==")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Refresh docs for today's four patches; remove superseded housekeeping script",
        ],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("Nothing to commit (already applied) -- skipping push.")
        return

    push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
    if push.returncode != 0:
        die("git push failed. Commit succeeded locally; push manually once resolved.")

    print("\nDone.")


if __name__ == "__main__":
    main()
