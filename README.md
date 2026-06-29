<p align="center">
  <img src="docs/bitlut-mascot.png" width="168" alt="BitLut" />
</p>

<div align="center">

<h1>BitLut</h1>

<p>
  <strong>Премиальный open-source мост между Huawei Health и Android Health Connect.</strong><br>
  BitLut помогает владельцам Huawei Band и Huawei Watch переносить реальные данные активности в экосистему Android Health Connect — прозрачно, безопасно и без фейковых записей.
</p>

<p>
  <img alt="Android" src="https://img.shields.io/badge/Android-26%2B-C1FF05?logo=android&logoColor=111111">
  <img alt="Kotlin" src="https://img.shields.io/badge/Kotlin-Android-9E6FC3?logo=kotlin&logoColor=white">
  <img alt="Jetpack Compose" src="https://img.shields.io/badge/Jetpack%20Compose-Material%203-FF7D32?logo=jetpackcompose&logoColor=white">
  <img alt="Health Connect" src="https://img.shields.io/badge/Health%20Connect-ready-C8E1FC">
  <img alt="Huawei Health" src="https://img.shields.io/badge/Huawei%20Health-import%20ready-D61F26">
  <img alt="Open Source" src="https://img.shields.io/badge/Open%20Source-free-111111">
</p>

</div>

---

<div align="center">

<table>
<tr>
<td align="center" width="33%">
<h3>📊 Единая сводка здоровья</h3>
<p>Шаги, дистанция, активные калории, пульс, сон, SpO2, стресс и активность — в одном аккуратном dashboard.</p>
</td>
<td align="center" width="33%">
<h3>🔄 Синхронизация Huawei → Health Connect</h3>
<p>Данные из Huawei Health импортируются в Android Health Connect через надежный фоновый sync-пайплайн.</p>
</td>
<td align="center" width="33%">
<h3>🛡️ Безопасно и прозрачно</h3>
<p>BitLut не генерирует искусственные health records. Только реальные данные, полученные от Huawei Health.</p>
</td>
</tr>
</table>

</div>

---

## Что такое BitLut

**BitLut** — это Android-приложение для пользователей Huawei Band, Huawei Watch и Huawei Health, которым нужен независимый и прозрачный способ перенести данные активности в **Android Health Connect**.

Приложение решает простую проблему: данные с Huawei-устройств часто остаются внутри Huawei Health, а пользователю хочется видеть их в общей Android health-экосистеме, где могут работать другие приложения, аналитика и сервисы.

BitLut работает как аккуратный health bridge:

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
Главные возможности
<table> <tr> <td width="32%"><strong>Шаги и дистанция</strong></td> <td>Крупный счетчик шагов за сегодня, прогресс к дневной цели и пройденная дистанция.</td> </tr> <tr> <td><strong>Активные калории</strong></td> <td>Отображение активного расхода энергии за день.</td> </tr> <tr> <td><strong>Время тренировок</strong></td> <td>Минуты активности и тренировок, полученные из Health Connect / Huawei-derived данных.</td> </tr> <tr> <td><strong>Часы активности</strong></td> <td>Количество часов, в которые пользователь двигался хотя бы одну минуту.</td> </tr> <tr> <td><strong>Пульс</strong></td> <td>Последнее значение ЧСС и мини-график изменений в течение дня.</td> </tr> <tr> <td><strong>Сон</strong></td> <td>Продолжительность ночного сна и оценка качества сна, если данные доступны.</td> </tr> <tr> <td><strong>Стресс</strong></td> <td>Оценка уровня стресса на основе доступных HRV-данных.</td> </tr> <tr> <td><strong>SpO2</strong></td> <td>Последнее измерение насыщения крови кислородом.</td> </tr> <tr> <td><strong>История</strong></td> <td>Графики и тренды по ключевым health-показателям.</td> </tr> <tr> <td><strong>Настройки виджетов</strong></td> <td>Пользователь может включать и выключать виджеты на главном экране.</td> </tr> </table>
Экраны приложения
<div align="center"> <table> <tr> <td align="center" width="33%"> <h3>Summary</h3> <p>Главный экран с текущими health-показателями и красивыми карточками метрик.</p> </td> <td align="center" width="33%"> <h3>History</h3> <p>История активности, сна и пульса за последние дни.</p> </td> <td align="center" width="33%"> <h3>Settings</h3> <p>Подключение Health Connect, Huawei Health, ручная синхронизация и управление виджетами.</p> </td> </tr> </table> </div>
Текущий production-статус
<table> <tr> <td width="32%"><strong>Публикация</strong></td> <td>Приложение опубликовано в Huawei AppGallery.</td> </tr> <tr> <td><strong>Android Health Connect</strong></td> <td>Permission flow работает. Dashboard читает данные из Health Connect.</td> </tr> <tr> <td><strong>Huawei Health Kit</strong></td> <td>Авторизация реализована. Полный импорт защищен approval gate со стороны Huawei Health Kit.</td> </tr> <tr> <td><strong>Фоновая синхронизация</strong></td> <td>Настроена через WorkManager с 30-минутным periodic cadence request, retry/backoff, circuit breaker и защитой от параллельных запусков.</td> </tr> <tr> <td><strong>Политика данных</strong></td> <td>Приложение никогда не создает фейковые health-записи.</td> </tr> </table>
Какие данные поддерживаются

BitLut ориентирован на базовый набор спортивных и activity-данных Huawei Health.

<table> <tr> <th align="left">Категория</th> <th align="left">Назначение в Health Connect</th> <th align="left">Принцип</th> </tr> <tr> <td>Шаги</td> <td><code>StepsRecord</code></td> <td>Прямой перенос количества шагов.</td> </tr> <tr> <td>Дистанция</td> <td><code>DistanceRecord</code></td> <td>Перенос пройденной дистанции.</td> </tr> <tr> <td>Подъем / этажи</td> <td><code>FloorsClimbedRecord</code></td> <td>Нормализация Huawei ascent/floors перед записью.</td> </tr> <tr> <td>Набор высоты</td> <td><code>ElevationGainedRecord</code></td> <td>Запись только валидных положительных интервалов.</td> </tr> <tr> <td>Активные калории</td> <td><code>ActiveCaloriesBurnedRecord</code></td> <td>Перенос активного расхода энергии.</td> </tr> <tr> <td>Тренировки</td> <td><code>ExerciseSessionRecord</code></td> <td>Запись тренировок с валидным временем начала и окончания.</td> </tr> <tr> <td>Пульс</td> <td><code>HeartRateRecord</code></td> <td>Чтение для dashboard и графиков.</td> </tr> <tr> <td>Сон</td> <td><code>SleepSessionRecord</code></td> <td>Чтение ночного сна для summary/history.</td> </tr> <tr> <td>SpO2</td> <td><code>OxygenSaturationRecord</code></td> <td>Чтение последнего доступного измерения.</td> </tr> <tr> <td>HRV / стресс</td> <td><code>HeartRateVariabilityRmssdRecord</code></td> <td>Оценка стресса на основе доступной вариабельности пульса.</td> </tr> </table>
Дизайн

BitLut использует аккуратный premium health-интерфейс на базе Jetpack Compose и Material 3.

<table> <tr> <td width="32%"><strong>Светлая тема</strong></td> <td>Мягкий системный фон, белые карточки, чистая медицинская эстетика.</td> </tr> <tr> <td><strong>Темная тема</strong></td> <td>Глубокий темный фон, glass-like поверхности и контрастные health-акценты.</td> </tr> <tr> <td><strong>Карточки</strong></td> <td>Большие скругления, мягкие тени, понятная визуальная иерархия.</td> </tr> <tr> <td><strong>Цветовые акценты</strong></td> <td>Activity, Heart, Sleep и Mind-метрики имеют собственные визуальные акценты.</td> </tr> </table>
Техническая часть
Стек
<table> <tr><td><strong>Язык</strong></td><td>Kotlin</td></tr> <tr><td><strong>UI</strong></td><td>Jetpack Compose, Material 3</td></tr> <tr><td><strong>Архитектура UI</strong></td><td>MVVM, StateFlow</td></tr> <tr><td><strong>Health layer</strong></td><td>Android Health Connect</td></tr> <tr><td><strong>Huawei layer</strong></td><td>Huawei Health Kit, HMS Core</td></tr> <tr><td><strong>Background jobs</strong></td><td>WorkManager</td></tr> <tr><td><strong>CI/CD</strong></td><td>GitHub Actions release pipeline</td></tr> <tr><td><strong>Локализация</strong></td><td>Русский интерфейс + English fallback</td></tr> </table>
Архитектура синхронизации
┌────────────────────────┐
│ Huawei Band / Watch    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Huawei Health          │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Huawei Health Kit      │
│ Approval-gated import  │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ BitLut SyncWorker      │
│ WorkManager            │
│ Retry + backoff        │
│ Circuit breaker        │
│ Single-flight lease    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Android Health Connect │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Summary / History UI   │
└────────────────────────┘
Как работает background sync

Фоновая синхронизация построена вокруг WorkManager.

Ключевые принципы:

<table> <tr> <td width="32%"><strong>30-минутный cadence</strong></td> <td>Приложение запрашивает periodic sync каждые 30 минут. Android может сдвигать выполнение из-за Doze Mode, battery optimization и OEM-политик, поэтому корректность обеспечивается catch-up window.</td> </tr> <tr> <td><strong>Single-flight guard</strong></td> <td>Manual sync и periodic sync не должны выполняться параллельно. Для этого используется lease-механизм.</td> </tr> <tr> <td><strong>Retry with backoff</strong></td> <td>Временные сбои обрабатываются повторными попытками с exponential backoff и jitter.</td> </tr> <tr> <td><strong>Circuit breaker</strong></td> <td>Если зависимость нестабильна, sync временно уходит в graceful no-op и не ломает приложение.</td> </tr> <tr> <td><strong>Catch-up window</strong></td> <td>Если Android задержал фоновую задачу, следующий запуск синхронизирует пропущенный диапазон.</td> </tr> <tr> <td><strong>No fake data</strong></td> <td>Если Huawei Health возвращает пустой snapshot, BitLut не продвигает sync cursor и не создает искусственные записи.</td> </tr> </table>
Как работает dashboard

Dashboard читает данные из Android Health Connect.

При обновлении:

Проверяются runtime permissions.
Данные читаются единым snapshot.
Если Health Connect временно возвращает ошибку, UI сохраняет последний хороший state.
Временный сбой не превращается в нулевые значения.
Пользователь может включать и выключать отдельные виджеты в Settings.
Разрешения и privacy policy

BitLut использует минимально необходимые health permissions.

Принципы:

пользователь явно выдает доступ через Android Health Connect;
Huawei Health Kit используется только для реального импорта Huawei-derived данных;
данные не подменяются и не синтезируются;
приложение не должно записывать placeholder records;
технические ошибки логируются для диагностики;
пользовательские экраны не перегружаются внутренним debug-шумом.
Huawei Health Kit approval

Полный Huawei import зависит от approval со стороны Huawei Health Kit.

Текущий статус:

Huawei authorization flow реализован;
приложение корректно обрабатывает approval gate;
код готов к реальному импорту после подтверждения scope set;
при ошибке 50005 приложение не падает и не пишет фейковые данные.
Release process

Релизы собираются через GitHub Actions.

Ожидаемые secrets:

BITLUT_KEYSTORE_BASE64
BITLUT_KEYSTORE_PASSWORD
BITLUT_KEY_ALIAS
BITLUT_KEY_PASSWORD
HUAWEI_APP_ID
AGCONNECT_SERVICES_JSON_BASE64

Базовый ручной release flow:

git checkout main
git pull origin main
./gradlew clean
./gradlew :app:assembleRelease
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main
git push origin vX.Y.Z

Если включен auto-tag workflow, tag создается автоматически при изменении версии релиза.

Engineering principles
<table> <tr><td><strong>KISS</strong></td><td>Простые и проверяемые компоненты вместо магии.</td></tr> <tr><td><strong>DRY</strong></td><td>Единые политики permissions, sync window и reliability.</td></tr> <tr><td><strong>Zero Trust</strong></td><td>Любые внешние health-данные валидируются перед записью.</td></tr> <tr><td><strong>Observability First</strong></td><td>Ключевые решения sync-пайплайна логируются.</td></tr> <tr><td><strong>Graceful Degradation</strong></td><td>Отсутствие Health Kit approval, HMS Core или permissions не должно ломать приложение.</td></tr> <tr><td><strong>No Fake Health Data</strong></td><td>BitLut никогда не генерирует искусственные health records.</td></tr> </table>
Open source

BitLut — бесплатный open-source проект для пользователей Huawei, которым нужен прозрачный контроль над своими health-данными и независимый мост в Android Health Connect.

