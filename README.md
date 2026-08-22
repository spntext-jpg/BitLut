<p align="center">
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
