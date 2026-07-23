<p align="center">
  <img src="docs/bitlut-mascot.png" width="140" alt="BitLut" />
</p>

<h1 align="center">BitLut</h1>

<p align="center">
  <strong>Премиальный open-source мост между Huawei Health и Android Health Connect</strong>
</p>

<p align="center">
  BitLut помогает владельцам Huawei Band и Huawei Watch переносить реальные данные активности
  из Huawei Health в Android Health Connect — прозрачно, безопасно и без фейковых записей.
</p>

<p align="center">
  <img alt="Android" src="https://img.shields.io/badge/Android-26%2B-C1FF05?style=for-the-badge&logo=android&logoColor=111111">
  <img alt="Kotlin" src="https://img.shields.io/badge/Kotlin-Android-7F52FF?style=for-the-badge&logo=kotlin&logoColor=white">
  <img alt="Jetpack Compose" src="https://img.shields.io/badge/Jetpack%20Compose-Material%203-4285F4?style=for-the-badge&logo=jetpackcompose&logoColor=white">
</p>

<p align="center">
  <img alt="Health Connect" src="https://img.shields.io/badge/Health%20Connect-ready-34A853?style=flat-square">
  <img alt="Huawei Health" src="https://img.shields.io/badge/Huawei%20Health-import%20ready-D61F26?style=flat-square">
  <img alt="Open Source" src="https://img.shields.io/badge/Open%20Source-free-111111?style=flat-square">
  <img alt="Release" src="https://img.shields.io/badge/release-v1.9.5-9E6FC3?style=flat-square">
</p>

<!-- BITLUT_STATUS:START -->
BitLut помогает переносить данные об активности из HUAWEI Health в Health Connect и просматривать их в удобном интерфейсе.

Приложение предназначено для пользователей, которые хотят использовать данные HUAWEI Health в других приложениях, совместимых с Health Connect.

Возможности BitLut

• Импорт шагов и пройденного расстояния
• Импорт поддерживаемых тренировок
• Передача данных в Health Connect
• Отображение шагов за текущий день
• Просмотр двух последних тренировок
• Домашний виджет с количеством шагов
• Экспорт данных в CSV
• Ручная и автоматическая фоновая синхронизация
• Выбор источника данных для главного экрана

BitLut работает локально на устройстве. Для использования приложения не требуется создавать аккаунт. В приложении нет рекламы, облачного сервера и продажи пользовательских данных.

Для синхронизации необходимы HUAWEI Health, HMS Core, Health Connect и соответствующие разрешения. Доступность отдельных типов данных зависит от разрешений HUAWEI Health Kit и от данных, сохранённых в HUAWEI Health.

BitLut получает данные из HUAWEI Health только для чтения и не изменяет информацию в HUAWEI Health.

BitLut — независимое приложение и не является официальным приложением HUAWEI.



BitLut transfers activity data from HUAWEI Health to Health Connect and presents it in a clear, convenient dashboard.

The app is designed for users who want to make their HUAWEI Health activity data available to other apps compatible with Health Connect.

BitLut features

• Import steps and distance
• Import supported workout sessions
• Transfer data to Health Connect
• View today’s step count
• View the two most recent workouts
• Home screen widget with today’s steps
• Export synchronized data as a CSV file
• Manual and automatic background synchronization
• Select the data source used by the dashboard

BitLut works locally on your device. No account is required. The app contains no advertising, has no cloud server, and does not sell user data.

HUAWEI Health, HMS Core, Health Connect, and the relevant permissions are required for synchronization. The availability of individual data types depends on the permissions provided by HUAWEI Health Kit and the data stored in HUAWEI Health.

BitLut accesses HUAWEI Health data in read-only mode and does not modify information stored in HUAWEI Health.

BitLut is an independent application and is not an official HUAWEI app.

---

## Open source

BitLut — бесплатный open-source проект для пользователей Huawei, которым нужен прозрачный контроль над своими health-данными и надежный мост в Android Health Connect.

Если вы используете Huawei Band или Huawei Watch и хотите видеть свои данные в Android Health Connect, BitLut создан именно для этого.

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

BitLut v1.9.6 is now locked to activity-only health sync.

Supported health data:
- steps
- distance
- floors / ascent / elevation
- active calories / active hours
- activity sessions / workout records

Unsupported metrics are intentionally removed from sync and UI:
- sleep
- pulse / heart rate
- SpO2
- HRV
- stress
- Activity Intensity

The UI uses the Glass 2.0 system: translucent surfaces, floating icon-only navigation, soft depth, radial glow, thin highlight borders and bounded charts.

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

BitLut now caches the last successfully read dashboard snapshot locally
(`DashboardSnapshotCache`, SharedPreferences-backed), so the app shows real,
last-known data immediately on launch instead of "Подключите Google Health"
while the first Health Connect read is still in progress.

* Cold start shows cached data instantly; live data replaces it once the
  first Health Connect read completes.
* A transient permission-check or read failure no longer downgrades the
  dashboard back to the connect screen -- it keeps showing the last good data.
* The "Обновить статус" button for Google Health in Settings now performs a
  real sync (Huawei -> Health Connect -> dashboard reload), not just a status
  re-check.
* The existing 30-minute periodic background sync (WorkManager) now also
  refreshes this local cache after each successful sync, so data stays fresh
  even when the app isn't open.

## v1.9.10 Dashboard persistence and force-refresh sprint

BitLut now caches the last successfully read dashboard snapshot locally
(`DashboardSnapshotCache`, SharedPreferences-backed), so the app shows real,
last-known data immediately on launch instead of "Подключите Google Health"
while the first Health Connect read is still in progress.

* Cold start shows cached data instantly; live data replaces it once the
  first Health Connect read completes.
* A transient permission-check or read failure no longer downgrades the
  dashboard back to the connect screen -- it keeps showing the last good data.
* The "Обновить статус" button for Google Health in Settings now performs a
  real sync (Huawei -> Health Connect -> dashboard reload), not just a status
  re-check.
* The existing 30-minute periodic background sync (WorkManager) now also
  refreshes this local cache after each successful sync, so data stays fresh
  even when the app isn't open.
