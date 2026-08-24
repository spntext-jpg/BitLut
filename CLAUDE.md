# CLAUDE.md

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
