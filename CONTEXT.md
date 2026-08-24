# BitLut Context

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
