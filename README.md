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
## Текущий статус

_Этот блок поддерживается скриптом `update_readme_status.py` — перезапускайте его при смене статуса, не редактируйте руками между маркерами._

**HUAWEI Health Kit:** заявка на scope одобрена Huawei на уровне приложения (App ID 117824685, одобрение получено 2026-07-18). Это **не значит**, что синк уже работает — `localHuaweiAuthorized` на устройстве это отдельный, локально закэшированный флаг с последней попытки авторизации, и он не обновляется автоматически при серверном одобрении. Реальный лог, снятый уже после одобрения, всё ещё показывал `localHuaweiAuthorized=false`/`50005` — это ожидаемо, а не регресс: нужно вручную нажать «Connect Huawei Health» (или новую кнопку «Попробовать снова» в Settings) ещё раз на реальном устройстве, чтобы подхватить одобрение. Если после этого снова 50005 в течение 1–2 дней — вероятно, дело в несовпадении сертификата (см. CLAUDE.md).

**AppGallery review:** было одно отклонение (2026-07-18) с формулировкой «does not collect to Huawei Health successfully» — ревьюер увидел тот же обобщённый тост на 50005, что и разработчик неделями видел в логах. Причина найдена и исправлена: теперь 5 разных причин ошибки авторизации Huawei показывают разные, конкретные объяснения в Settings вместо одного общего сообщения. Перед повторной отправкой на ревью нужно подтвердить, что живое устройство успешно проходит авторизацию.

**Запрошенный/ожидаемый scope у Huawei** (activity-only, индивидуальный разработчик): `HEALTHKIT_STEP_READ`, `HEALTHKIT_DISTANCE_READ`, `HEALTHKIT_ACTIVITY_READ`, `HEALTHKIT_ACTIVITY_RECORD_READ`, `HEALTHKIT_HISTORYDATA_OPEN_WEEK`. Только чтение из Huawei — запись обратно не производится.

**Sleep / heart-rate / SpO2 / stress отсутствуют намеренно** — не запрашиваются у Huawei, не читаются и не пишутся в Health Connect, нет UI, и (с 2026-07-14) в коде не осталось даже мёртвых полей/сериализации/цветовых токенов под них — убраны полностью, а не просто отключены. Индивидуальным разработчикам Huawei не открывает advanced-уровень данных вообще, независимо от качества заявки.

**Экраны:** ровно 2 — Today (Summary) и Settings. History-экран убран из нижней навигации ещё в прошлом спринте; с 2026-07-14 его код (экран, чипы диапазона, карточка типа тренировки, вся инфраструктура bar-графика под него) удалён из репозитория полностью, а не просто оставлен неиспользуемым.

**Виджеты на Today (фиксированный набор, без возможности отключения):** шаги сегодня, время тренировок, личные рекорды, дней с целью подряд, последняя импортированная тренировка.

**Также добавлено с 2026-07-14 по 2026-07-18:** виджет на рабочий стол (Jetpack Glance — шаги + время последней синхронизации, тап = синк); экспорт данных в CSV; экран «Что именно передаётся» со списком реальных 5 scope; edge-to-edge + жест «назад» (Android 15/16); карточка объяснения проблемы авторизации Huawei с конкретной причиной вместо общего сообщения.

**Синхронизация:** автоматический триггер на каждом возврате в приложение (`onResume`, не только холодный старт), плюс кнопка Refresh в нижней навигации, плюс периодический воркер каждые 30 минут. Защищена debounce (5 сек между ручными триггерами) и process-wide lease против параллельных синков. Чтение сегодняшних метрик — через `readRecords()` с суммированием, не через `aggregate()` (у последнего есть задержка кэша на стороне Health Connect, что было подтверждённой причиной "синк работает только после открытия Google Fit").

_Обновлено: 2026-07-22_
<!-- BITLUT_STATUS:END -->

---

---

## Один мост для данных Huawei Health

BitLut создан для пользователей Huawei-устройств, которым нужен чистый и понятный способ перенести данные активности в Android Health Connect.

Многие показатели с Huawei Band и Huawei Watch остаются внутри Huawei Health. BitLut делает эти данные доступными в общей Android health-экосистеме, чтобы пользователь мог видеть, анализировать и использовать их в совместимых приложениях.

```text
Huawei Band / Huawei Watch
        ↓
Huawei Health
        ↓
Huawei Health Kit
        ↓
BitLut
        ↓
Android Health Connect
```

---

## Что умеет BitLut

### Активность

* **Шаги за сегодня** — крупный счетчик, дневная цель и процент выполнения.
* **Дистанция** — пройденное расстояние в километрах.
* **Активные калории** — расход энергии за день.
* **Часы активности** — количество часов, когда пользователь двигался хотя бы одну минуту.
* **Время тренировок** — минуты активности и тренировок.

### История и контроль

* **Summary dashboard** — чистый главный экран со всеми ключевыми метриками.
* **History** — история показателей и тренды за последние дни.
* **Settings** — подключение Health Connect, Huawei Health и управление виджетами.
* **Widget toggles** — пользователь сам выбирает, какие карточки показывать на главном экране.

---

## Почему это важно

BitLut не пытается заменить Huawei Health. Он дополняет его.

Приложение решает конкретную задачу: аккуратно связать Huawei Health с Android Health Connect, сохранив контроль, прозрачность и доверие к данным.

* **Без рекламы**
* **Open source**
* **Без фейковых health-записей**
* **Без лишней аналитики**
* **Без скрытой подмены данных**
* **С понятной архитектурой синхронизации**
* **С современным Android UI на Jetpack Compose**

---

## Production-статус

* Приложение опубликовано в **Huawei AppGallery**.
* Android Health Connect permission flow работает.
* Dashboard читает данные из Health Connect.
* Полный Huawei Health import подключен через Settings.
* Huawei Health Kit import защищен approval gate со стороны Huawei.
* Фоновая синхронизация построена на WorkManager.
* Последний релиз: **v1.9.5**.

---

## Интерфейс

BitLut использует современный premium health-интерфейс на базе Jetpack Compose и Material 3.

### Summary

Главный экран с ключевыми показателями: шаги, дистанция, активные калории, пульс, сон, стресс, SpO₂ и активность.

### History

История здоровья и активности: графики, тренды и показатели за выбранный период.

### Settings

Подключение Health Connect, Huawei Health, ручная синхронизация, статус разрешений и настройка виджетов.

---

# Техническая часть

## Стек

* **Kotlin**
* **Jetpack Compose**
* **Material 3**
* **MVVM**
* **StateFlow**
* **Android Health Connect**
* **Huawei Health Kit**
* **HMS Core**
* **WorkManager**
* **GitHub Actions**

---

## Архитектура

```text
app/
├── data/
│   ├── GoogleHealthManager.kt
│   ├── HuaweiHealthManager.kt
│   ├── remote/
│   │   └── HuaweiConfig.kt
│   └── worker/
│       ├── BackgroundSyncScheduler.kt
│       ├── SyncReliability.kt
│       └── SyncWorker.kt
├── ui/
│   ├── DashboardViewModel.kt
│   ├── SyncStatusViewModel.kt
│   ├── screens/
│   │   └── FinalBitLutShell.kt
│   └── theme/
└── config/
    ├── HealthPermissionPolicy.kt
    └── WidgetVisibilityPrefs.kt
```

---

## Как работает синхронизация

BitLut использует два направления работы с health-данными.

### 1. Чтение dashboard

Dashboard читает данные из Android Health Connect.

```text
Health Connect
      ↓
GoogleHealthManager
      ↓
DashboardViewModel
      ↓
Summary / History UI
```

При обновлении dashboard:

1. Проверяются разрешения Health Connect.
2. Данные читаются единым snapshot.
3. Если Health Connect временно возвращает ошибку, UI сохраняет последний хороший state.
4. Временный сбой не превращает реальные показатели в нули.
5. Пользователь может включать и выключать отдельные виджеты в Settings.

---

### 2. Импорт Huawei Health

Huawei import работает через Huawei Health Kit.

```text
Huawei Health
      ↓
Huawei Health Kit
      ↓
HuaweiHealthManager
      ↓
SyncWorker
      ↓
GoogleHealthManager
      ↓
Android Health Connect
```

BitLut переносит только реальные данные, полученные от Huawei Health. Если Huawei Health возвращает пустой snapshot, приложение не создает искусственные записи и не продвигает sync cursor.

---

## Background sync

Фоновая синхронизация построена на **WorkManager**.

BitLut запрашивает запуск sync каждые 30 минут. Android может сдвигать выполнение из-за Doze Mode, battery optimization и OEM-политик, поэтому корректность обеспечивается не “идеальным таймером”, а устойчивой архитектурой.

### Reliability-механизмы

* **30-minute periodic cadence request**
  WorkManager планирует регулярный sync каждые 30 минут.

* **Single-flight lease**
  Manual sync и periodic sync не выполняются параллельно.

* **Exponential backoff + jitter**
  Временные сбои повторяются с безопасной задержкой.

* **Circuit breaker**
  Если зависимость нестабильна, sync временно уходит в graceful no-op.

* **Catch-up window**
  Если Android задержал фоновую задачу, следующий запуск подхватывает пропущенный диапазон.

* **Bounded execution timeout**
  Worker не может зависнуть бесконечно.

* **No fake data policy**
  Пустой ответ Huawei Health не превращается в фейковые записи.

---

## Поддерживаемые Health Connect records

| Категория        | Health Connect record             | Назначение                 |
| ---------------- | --------------------------------- | -------------------------- |
| Шаги             | `StepsRecord`                     | Количество шагов           |
| Дистанция        | `DistanceRecord`                  | Пройденное расстояние      |
| Этажи            | `FloorsClimbedRecord`             | Подъемы и этажи            |
| Набор высоты     | `ElevationGainedRecord`           | Положительный набор высоты |
| Активные калории | `ActiveCaloriesBurnedRecord`      | Активный расход энергии    |
| Тренировки       | `ExerciseSessionRecord`           | Сессии активности          |

---

## Разрешения

BitLut использует только те разрешения, которые нужны для отображения и синхронизации health-данных.

Пользователь явно выдает доступ через Android Health Connect. Huawei Health Kit используется только для реального импорта Huawei-derived данных.

Принципы privacy:

* данные не подменяются;
* данные не синтезируются;
* placeholder records не создаются;
* ошибки логируются только для диагностики;
* пользовательский интерфейс не перегружается debug-информацией.

---

## Huawei Health Kit approval

Полный импорт из Huawei Health зависит от approval со стороны Huawei Health Kit.

BitLut уже содержит:

* Huawei authorization flow;
* обработку approval gate;
* защиту от ошибки `50005`;
* graceful degradation без падения приложения;
* запрет на создание фейковых данных при недоступности Huawei import.

---

## Release process

Текущий релиз:

```text
v1.9.5
```

Базовый release flow:

```bash
git checkout main
git pull origin main
./gradlew clean
./gradlew :app:assembleRelease
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```

Ожидаемые secrets для production-сборки:

```text
BITLUT_KEYSTORE_BASE64
BITLUT_KEYSTORE_PASSWORD
BITLUT_KEY_ALIAS
BITLUT_KEY_PASSWORD
HUAWEI_APP_ID
AGCONNECT_SERVICES_JSON_BASE64
```

---

## Engineering principles

* **KISS** — простые компоненты вместо скрытой магии.
* **DRY** — единые политики permissions, sync window и reliability.
* **Zero Trust** — любые внешние health-данные валидируются перед записью.
* **Observability First** — ключевые решения sync-пайплайна логируются.
* **Graceful Degradation** — отсутствие approval, HMS Core или permissions не ломает приложение.
* **No Fake Health Data** — BitLut никогда не генерирует искусственные health records.

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
