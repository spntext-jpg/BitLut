<p align="center">
  <img src="docs/bitlut-icon.png" width="96" alt="BitLut logo" />
</p>

<h1 align="center">BitLut</h1>

<p align="center">
  Бесплатный open-source мост для синхронизации данных из <b>Huawei Health</b> в <b>Android Health Connect</b>.
</p>

<p align="center">
  <img alt="Android" src="https://img.shields.io/badge/Android-26%2B-3DDC84?logo=android&logoColor=white">
  <img alt="Kotlin" src="https://img.shields.io/badge/Kotlin-Android-7F52FF?logo=kotlin&logoColor=white">
  <img alt="Jetpack Compose" src="https://img.shields.io/badge/Jetpack%20Compose-Material%203-4285F4?logo=jetpackcompose&logoColor=white">
  <img alt="Health Connect" src="https://img.shields.io/badge/Health%20Connect-enabled-34A853">
  <img alt="Huawei Health" src="https://img.shields.io/badge/Huawei%20Health-bridge-D61F26">
  <img alt="License" src="https://img.shields.io/badge/Open%20Source-free-black">
</p>

---

## Что такое BitLut

**BitLut** — это Android-приложение для пользователей Huawei Band, Huawei Watch и других устройств, которые передают данные в **Huawei Health**, но не синхронизируются напрямую с экосистемой Google.

Приложение помогает перенести базовые показатели активности в локальное системное хранилище **Android Health Connect**, чтобы данные могли быть доступны совместимым приложениям здоровья и фитнеса.

BitLut создан как бесплатная open-source альтернатива платным синхронизаторам.

---

## Зачем это нужно

Из-за ограничений между экосистемами Huawei и Google пользователи часто оказываются в ситуации, где:

- браслет или часы Huawei корректно собирают данные;
- Huawei Health эти данные видит;
- Google Health / Health Connect эти данные не получает;
- для синхронизации приходится использовать платные сторонние приложения.

BitLut решает эту проблему простым способом:  
он читает разрешённые пользователем данные из Huawei Health и записывает их в Android Health Connect.

---

## Возможности

<table>
  <tr>
    <td><b>Шаги</b></td>
    <td>Синхронизация количества шагов из Huawei Health в Health Connect.</td>
  </tr>
  <tr>
    <td><b>Пульс</b></td>
    <td>Передача данных о сердечном ритме, если они доступны в аккаунте пользователя.</td>
  </tr>
  <tr>
    <td><b>Ручной запуск</b></td>
    <td>Пользователь сам контролирует момент синхронизации.</td>
  </tr>
  <tr>
    <td><b>Фоновая работа</b></td>
    <td>Синхронизация через системный механизм Android WorkManager.</td>
  </tr>
  <tr>
    <td><b>Логи</b></td>
    <td>Встроенный журнал диагностики с возможностью копирования.</td>
  </tr>
  <tr>
    <td><b>HMS Core check</b></td>
    <td>Подсказка и переход к установке HMS Core, если он отсутствует.</td>
  </tr>
</table>

---

## Стек

- **Kotlin**
- **Jetpack Compose**
- **Material 3**
- **Android WorkManager**
- **Android Health Connect**
- **Huawei Health Kit / HMS Core**
- **Manual Dependency Injection**
- **MVVM + StateFlow**
- **GitHub Actions release pipeline**

---

## Архитектура

```text
Huawei Band / Watch
        │
        ▼
Huawei Health
        │
        ▼
BitLut
        │
        ├── HuaweiHealthManager
        │       └── читает данные через Huawei Health Kit
        │
        ├── SyncWorker
        │       └── выполняет безопасную фоновую синхронизацию
        │
        └── GoogleHealthManager
                └── записывает данные в Android Health Connect
        │
        ▼
Android Health Connect
Требования

Для работы приложения нужны:

Android 8.0+;
установленный Huawei Health;
установленный HMS Core;
установленный или системно доступный Android Health Connect;
разрешения пользователя на доступ к данным здоровья.
Безопасность и приватность

BitLut не продаёт данные, не использует рекламные SDK и не предназначен для медицинской диагностики.

Приложение работает только после явного разрешения пользователя и использует данные исключительно для синхронизации между Huawei Health и Android Health Connect.

Политика конфиденциальности:
https://spntext-jpg.github.io/bitlut-privacy/

Статус проекта

Текущая версия:

1.0.1

Фокус ближайших релизов:

улучшение UX авторизации Huawei Health;
стабильная работа с HMS Core;
расширение типов синхронизируемых данных;
улучшение диагностики ошибок;
тестирование на большем количестве Huawei/Honor устройств.
Сборка
./gradlew :app:assembleRelease

Для локальной release-сборки нужен release keystore.
Секреты не должны попадать в репозиторий.

Вклад в проект

Pull requests и issues приветствуются.

Особенно полезны:

тесты на разных Huawei/Honor устройствах;
отчёты о совместимости HMS Core;
предложения по UX;
улучшение синхронизации Health Connect;
локализация.
Disclaimer

BitLut не является медицинским приложением.
Приложение не предоставляет диагностику, лечение, медицинские рекомендации или интерпретацию состояния здоровья.

Данные используются только для личного учёта активности.
