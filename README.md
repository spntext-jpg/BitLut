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

### Здоровье

* **Пульс** — последнее измерение ЧСС и мини-график в течение дня.
* **Сон** — продолжительность ночного сна и оценка качества, если данные доступны.
* **SpO₂** — последнее измерение насыщения крови кислородом.
* **Стресс** — оценка уровня стресса на основе доступных HRV-данных.

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
| Пульс            | `HeartRateRecord`                 | ЧСС и графики              |
| Сон              | `SleepSessionRecord`              | Продолжительность сна      |
| SpO₂             | `OxygenSaturationRecord`          | Насыщение крови кислородом |
| HRV              | `HeartRateVariabilityRmssdRecord` | Основа для оценки стресса  |

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
