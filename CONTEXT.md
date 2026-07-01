# BitLut Context

BitLut is an open-source Android app that syncs Huawei Health activity data into Android Health Connect / Google Health.

## Production MVP goal

Huawei Health -> BitLut -> Android Health Connect

Primary MVP sync scope:

- Steps
- Distance
- Floors climbed
- Elevation gained / ascent
- Active calories
- Exercise / activity sessions

Huawei approval-requested scope:

- Step
- Distance, ascent & altitude
- Active Hours
- Daily Activity Summary
- Activity record
- Activity
- Reading historical data
- Basic activity management

## Current production status

Google Health Connect:
- permission flow works
- permissions are granted
- multi-record writer architecture prepared

Huawei Health Kit:
- authorization flow works
- current blocker: 50005 approval pending

## Huawei project

- Project ID: 101653523864196965
- App ID: 117824685
- Package: com.openhealth.sync
- Client ID: 1958319989043812544

## Required GitHub secrets

- BITLUT_KEYSTORE_BASE64
- BITLUT_KEYSTORE_PASSWORD
- BITLUT_KEY_ALIAS
- BITLUT_KEY_PASSWORD
- HUAWEI_APP_ID
- AGCONNECT_SERVICES_JSON_BASE64

## Release process

git tag -a v1.0.1 -m "BitLut v1.0.1 production MVP"
git push origin v1.0.1

GitHub Actions:
- builds signed APK
- uploads workflow artifact
- creates GitHub Release asset

## Production rule

Never generate fake health data.
Only sync real Huawei-derived records.


## Successful baseline

The current internal production baseline is confirmed:

- signed APK installs successfully
- Google Health Connect permissions work
- Huawei authorization reaches expected approval gate
- CI release pipeline creates signed APKs
- no fake health data is generated

See also: docs/SUCCESSFUL_BUILD.md

## UI log policy

The in-app log screen should show only useful user-level events.
Verbose technical checks are kept in Logcat but hidden from UI logs.

Hidden from UI logs:

- repeated Health Connect availability checks
- granted permission debug dumps
- Huawei pending approval noise
- expected not-authorized state before Huawei approval

## Duplicate sync protection policy

Before Huawei approval, sync must not write fake data.
After approval, duplicate protection must be implemented around real Huawei-derived records only:

- use last successful sync timestamp
- avoid overlapping historical windows
- avoid parallel WorkManager runs
- never insert generated placeholder records

## BitLut v1.9.6 strict health-data scope

BitLut v1.9.6 is locked to the Huawei Health approval scope requested in AppGallery:

- Step
- Distance, ascent and altitude
- Active Hours
- Daily Activity Summary
- Activity record
- Activity

The app does not request, read, write or infer sleep, heart rate, SpO2, HRV, stress or Activity Intensity data in this release.

Health Connect export is limited to Huawei-derived activity/basic sport records: `StepsRecord`, `DistanceRecord`, `FloorsClimbedRecord`, `ElevationGainedRecord`, `ActiveCaloriesBurnedRecord` and `ExerciseSessionRecord`.

## BitLut v1.9.6 GUI scope

The app UI is activity-only in v1.9.6. Dashboard and Settings must not expose widgets, toggles or permission prompts for pulse, sleep, stress, SpO2, HRV or Activity Intensity.

The bottom navigation is icon-only neo-glassmorphism. Status refresh actions live in Settings only; app startup refreshes status automatically.

## BitLut v1.9.6 Glassmorphism 2.0 GUI polish

The UI uses a premium activity-only glass system across all screens: translucent cards, soft depth shadows, radial glow, thin glass borders and an icon-only floating bottom navigation.

The History chart reserves fixed vertical space for values, bars and dates so large step values cannot push bars outside the card bounds.

## BitLut v1.9.6 Glass 2.0 UI system

The UI uses a premium activity-only glass system across all screens: translucent surfaces, floating glass navigation, soft depth shadows, radial glow, thin highlight borders and bounded charts.

History charts reserve fixed vertical space for values, bars and dates so large step values cannot push bars outside card bounds.

## v1.9.6 current baseline

BitLut v1.9.6 is activity-only for Huawei Health and Google Health Connect.

Do not reintroduce sleep, pulse, SpO2, HRV, stress or Activity Intensity until Huawei approval scope is expanded.

GUI baseline:
- Glass 2.0 visual system
- icon-only floating bottom navigation
- premium translucent cards
- bounded history charts
- refresh status buttons only in Settings
- automatic status refresh on app launch

## v1.9.6 lifecycle and Glass performance hardening

Implemented after deep code review:

- Compose state collection in `MainActivity` is lifecycle-aware via `collectAsStateWithLifecycle`.
- Glass 2.0 UI helpers cache stable shapes, gradient color lists and static brushes with `remember(...)`.
- History chart bars are bounded with fixed value/bar/date regions to avoid overflow on large step values.
- App logger has conservative memory guards for retained in-app logs.

Deferred to a separate architecture sprint:

- Splitting `FinalBitLutShell.kt` into feature-level UI files.
- Moving WorkManager orchestration out of `MainActivity`.
- Introducing interfaces for `GoogleHealthManager` / `HuaweiHealthManager`.
- Gradle Version Catalog migration.

## v1.9.6 Architecture Hardening 1

Implemented:

- `HealthConnectManager` and `HuaweiHealthReader` interfaces define the app-facing health contracts.
- `GoogleHealthManager` and `HuaweiHealthManager` implement these contracts.
- `DashboardViewModel`, `SyncViewModel`, `ImportViewModel` and the Health Connect permission requester depend on interfaces instead of concrete manager classes.
- `AppContainer` exposes health dependencies through interfaces.
- Huawei snapshot reads are explicitly offloaded through an injectable `CoroutineDispatcher`, defaulting to `Dispatchers.IO`.

Still deferred to a later sprint:

- Moving WorkManager orchestration out of `MainActivity`.
- Splitting `FinalBitLutShell.kt` into feature-level UI files.
- Gradle Version Catalog migration.

## v1.9.6 Sync Orchestrator Sprint

Implemented:

- Added `SyncOrchestrator` as the UI-safe boundary for manual and periodic sync orchestration.
- `MainActivity` no longer directly imports or observes WorkManager sync classes.
- Manual sync permission preflight moved out of `MainActivity`.
- `MainActivity` now delegates scheduling to `syncOrchestrator.schedulePeriodic()`.
- Manual sync callbacks remain lifecycle-owned by the Activity and update ViewModels through explicit callbacks.

Still deferred:

- Moving Huawei authorization UI flow out of `MainActivity`.
- Converting archive-import intent handling into a dedicated import orchestrator.
- Splitting `FinalBitLutShell.kt` into feature-level screen files.

## v1.9.6 MainActivity recovery

`MainActivity.kt` was clean-room rewritten after the Sync Orchestrator migration to remove a broken partial WorkManager block and restore:

- lifecycle-aware Compose state collection;
- Google Health permission flow;
- Huawei authorization flow;
- archive import picker;
- launch-time status refresh;
- periodic sync delegation;
- manual sync delegation through `SyncOrchestrator`.

`MainActivity` must not directly import WorkManager or `BackgroundSyncScheduler`.

## v1.9.6 UI File Split Sprint 1

Implemented:

- Extracted stable Glass 2.0 UI components from `FinalBitLutShell.kt`.
- Added `GlassNavigation.kt` for the floating icon-only bottom navigation.
- Added `GlassCards.kt` for the shared translucent `SoftCard` surface.
- Added `MetricCharts.kt` for bounded metric chart rendering.
- Kept screen behavior, sync behavior, Health Connect contract and Huawei scope unchanged.

This is intentionally a low-risk first split. Screen-level extraction remains deferred to the next UI architecture sprint.

## v1.9.6 split-aware Glass performance verification

`verify_lifecycle_glass_perf_hardening.py` now validates Glass 2.0 performance tokens across both `FinalBitLutShell.kt` and extracted `ui/components/*.kt` files.

## v1.9.6 split-aware Glass GUI verification

`verify_glass20_gui_self_heal.py` and `verify_gui_neoglass_activity_only.py` now validate Glass 2.0 UI across both `FinalBitLutShell.kt` and extracted `ui/components/*.kt` files.

## v1.9.6 Metric chart split compile fix

`MetricBarChartCard` no longer depends on the missing `MetricBar` type after the UI split. It now accepts the existing chart bar objects from call-sites as `List<Any?>` and reads value/label fields defensively.

This keeps the extracted chart component compile-safe without changing sync, Health Connect or Huawei behavior.

## v1.9.6 MetricCharts self-check fix

Fixed the UI split verifier/self-check so it allows `MetricBarChartCard` as a function name while preventing dependency on the missing `List<MetricBar>` type.

v1.9.9 release-readiness sprint

Prepared BitLut for the 1.9.9 release without touching app version fields because versioning is owned by GitHub Actions.

Included:

release checklist in docs/release-1.9.9.md;
release-readiness verifier;
strict activity-only scope guard;
UI split guard;
SyncOrchestrator guard;
cleanup of failed local recovery scripts.

v1.9.9 release-readiness sprint

Prepared BitLut for the 1.9.9 release without touching app version fields because versioning is owned by GitHub Actions.

Included:

release checklist in docs/release-1.9.9.md;
release-readiness verifier;
strict activity-only scope guard;
UI split guard;
SyncOrchestrator guard;
cleanup of failed local recovery scripts.

## v1.9.9 release-readiness sprint

Prepared BitLut for the `1.9.9` release without touching app version fields because versioning is owned by GitHub Actions.

Included: release checklist, release-readiness verifier, strict activity-only scope guard, UI split guard, SyncOrchestrator guard, and cleanup of failed local recovery scripts.


## v1.9.10 Dashboard persistence and force-refresh sprint

Root cause of "Подключите Google Health" appearing on every cold start: BitLut
had no local cache at all (no Room, no DataStore, not even a SharedPreferences
snapshot). `DashboardViewModel` always started from
`DashboardUiState(hasPermissions = false, isLoading = true)` and the UI showed
the "Connect Google Health" lock screen for any state where
`hasPermissions == false` -- including the brief window before the first async
Health Connect permission check completed, and any transient failure of that
check.

Implemented:

- `DashboardSnapshotCache` -- a SharedPreferences-backed (same `bitlut_prefs`
  file BitLut already uses) JSON cache of the last successfully read
  `GoogleDashboardSnapshot`. No new dependency (Room/DataStore) was introduced.
- `DashboardViewModel` now builds its initial `DashboardUiState` synchronously
  from this cache, so the dashboard shows real, last-known numbers immediately
  on cold start instead of a loading spinner or the lock screen.
- `DashboardUiState.showConnectLockScreen` replaces raw `!hasPermissions`
  checks in the UI. It is only true once a permission check has actually run
  and confirmed permissions are missing (`permissionsChecked == true`), never
  purely because the app just started.
- A transient `hasAllPermissions()` failure or a transient
  `readDashboardSnapshot()` failure no longer resets `hasPermissions` to
  `false`; the dashboard keeps showing the last good data instead.
- `SyncWorker` now refreshes `DashboardSnapshotCache` after every successful
  background Huawei -> Health Connect write, so the existing 30-minute
  periodic sync (`BackgroundSyncScheduler`, unchanged) keeps the cold-start
  cache warm even when the app isn't open.
- The Google Health "Обновить статус" / "refresh status" button in Settings
  now triggers the same `SyncOrchestrator.triggerImmediateSync` pipeline as
  "Sync now" (Huawei read -> Health Connect write -> dashboard reload)
  instead of only re-reading whatever Health Connect already reports locally.

Explicitly unchanged in this sprint:

- `BackgroundSyncScheduler` periodic cadence (still 30 minutes,
  `ExistingPeriodicWorkPolicy.UPDATE`).
- `SyncWorker` retry/circuit-breaker/lease reliability mechanics.
- Activity-only Health Connect scope and the no-fake-data policy.

Verified by `scripts/verify_dashboard_persistence_sprint.py`.


## v1.9.10 Dashboard persistence and force-refresh sprint

Root cause of "Подключите Google Health" appearing on every cold start: BitLut
had no local cache at all (no Room, no DataStore, not even a SharedPreferences
snapshot). `DashboardViewModel` always started from
`DashboardUiState(hasPermissions = false, isLoading = true)` and the UI showed
the "Connect Google Health" lock screen for any state where
`hasPermissions == false` -- including the brief window before the first async
Health Connect permission check completed, and any transient failure of that
check.

Implemented:

- `DashboardSnapshotCache` -- a SharedPreferences-backed (same `bitlut_prefs`
  file BitLut already uses) JSON cache of the last successfully read
  `GoogleDashboardSnapshot`. No new dependency (Room/DataStore) was introduced.
- `DashboardViewModel` now builds its initial `DashboardUiState` synchronously
  from this cache, so the dashboard shows real, last-known numbers immediately
  on cold start instead of a loading spinner or the lock screen.
- `DashboardUiState.showConnectLockScreen` replaces raw `!hasPermissions`
  checks in the UI. It is only true once a permission check has actually run
  and confirmed permissions are missing (`permissionsChecked == true`), never
  purely because the app just started.
- A transient `hasAllPermissions()` failure or a transient
  `readDashboardSnapshot()` failure no longer resets `hasPermissions` to
  `false`; the dashboard keeps showing the last good data instead.
- `SyncWorker` now refreshes `DashboardSnapshotCache` after every successful
  background Huawei -> Health Connect write, so the existing 30-minute
  periodic sync (`BackgroundSyncScheduler`, unchanged) keeps the cold-start
  cache warm even when the app isn't open.
- The Google Health "Обновить статус" / "refresh status" button in Settings
  now triggers the same `SyncOrchestrator.triggerImmediateSync` pipeline as
  "Sync now" (Huawei read -> Health Connect write -> dashboard reload)
  instead of only re-reading whatever Health Connect already reports locally.

Explicitly unchanged in this sprint:

- `BackgroundSyncScheduler` periodic cadence (still 30 minutes,
  `ExistingPeriodicWorkPolicy.UPDATE`).
- `SyncWorker` retry/circuit-breaker/lease reliability mechanics.
- Activity-only Health Connect scope and the no-fake-data policy.

Verified by `scripts/verify_dashboard_persistence_sprint.py`.
