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
