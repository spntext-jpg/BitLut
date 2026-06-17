<p align="center">
  <img src="docs/bitlut-mascot.png" width="180" alt="BitLut mascot" />
</p>

<div align="center">

<h1>BitLut</h1>

<p>
  <strong>Премиальный open-source мост между Huawei Health и Android Health Connect.</strong><br>
  Красивый Health Connect dashboard сегодня. Huawei Health import — после Health Kit approval.
</p>

<p>
  <img alt="Android" src="https://img.shields.io/badge/Android-26%2B-C1FF05?logo=android&logoColor=111111">
  <img alt="Kotlin" src="https://img.shields.io/badge/Kotlin-Android-9E6FC3?logo=kotlin&logoColor=white">
  <img alt="Compose" src="https://img.shields.io/badge/Jetpack%20Compose-Material%203-FF7D32?logo=jetpackcompose&logoColor=white">
  <img alt="Health Connect" src="https://img.shields.io/badge/Health%20Connect-ready-C8E1FC">
  <img alt="Open Source" src="https://img.shields.io/badge/Open%20Source-free-111111">
</p>

</div>

<br>

<div align="center">

<table>
<tr>
<td align="center" width="33%">
<h2>⚡</h2>
<h3>Быстрый</h3>
<p>Только важные данные: шаги за день, неделя и тренировки.</p>
</td>
<td align="center" width="33%">
<h2>🧊</h2>
<h3>Премиальный</h3>
<p>Светлый glass-интерфейс, крупные KPI и выразительные акценты.</p>
</td>
<td align="center" width="33%">
<h2>🔒</h2>
<h3>Безопасный</h3>
<p>Минимальные разрешения и read-only Health Connect dashboard.</p>
</td>
</tr>
</table>

</div>

<br>

<div>

<h2>✨ Что такое BitLut</h2>

<p>
  <strong>BitLut</strong> — Android-приложение для пользователей Huawei Band, Huawei Watch
  и других устройств Huawei, которым нужен понятный путь к экосистеме
  <strong>Android Health Connect</strong>.
</p>

<p>
  Сейчас BitLut работает как <strong>dashboard-first приложение</strong>: показывает данные
  из Google Health Connect в чистом, крупном и читаемом интерфейсе.
  Модуль импорта из <strong>Huawei Health</strong> уже сохраняется в структуре проекта,
  но остаётся заблокированным до согласования Huawei Health Kit.
</p>

</div>

<br>

<div align="center">

<h2>🎨 Visual System</h2>

<table>
<tr>
<td align="center">
<h3 style="color:#C1FF05;">#C1FF05</h3>
<b>Энергичный лайм</b><br>
Главный акцент
</td>
<td align="center">
<h3 style="color:#FF7D32;">#FF7D32</h3>
<b>Тёплый оранжевый</b><br>
KPI и действия
</td>
<td align="center">
<h3 style="color:#9E6FC3;">#9E6FC3</h3>
<b>Привет фиолет</b><br>
Умные сценарии
</td>
</tr>
<tr>
<td align="center">
<h3 style="color:#C8E1FC;">#C8E1FC</h3>
<b>Воздушный голубой</b><br>
Мягкие подложки
</td>
<td align="center">
<h3 style="color:#BAB8BA;">#BAB8BA</h3>
<b>Уверенный металл</b><br>
Вторичный текст
</td>
<td align="center">
<h3>#FFFFFF</h3>
<b>Чистый белый</b><br>
Основной фон
</td>
</tr>
</table>

</div>

<br>

<div align="center">

<h2>🚀 Возможности</h2>

<table>
<tr>
<td width="50%">
<h3>📊 Главная</h3>
<p>
  Крупные показатели активности: шаги за сегодня, недельная динамика
  и тренировки, импортированные в Health Connect.
</p>
</td>
<td width="50%">
<h3>🔄 Синхронизация</h3>
<p>
  Единая панель для Google Health Connect и будущего Huawei Health import.
</p>
</td>
</tr>
<tr>
<td width="50%">
<h3>🔐 Контроль доступа</h3>
<p>
  BitLut запрашивает только необходимые разрешения и не включает Huawei runtime
  до официального approval.
</p>
</td>
<td width="50%">
<h3>🌍 Локализация</h3>
<p>
  Русский интерфейс для устройств на русском языке и английский fallback
  для остальных локалей.
</p>
</td>
</tr>
</table>

</div>

<br>

<div>

<h2>🧭 Текущий статус</h2>

<table>
<tr>
<td><strong>Google Health Connect dashboard</strong></td>
<td>✅ Активно</td>
</tr>
<tr>
<td><strong>Шаги за день</strong></td>
<td>✅ Активно</td>
</tr>
<tr>
<td><strong>Шаги за неделю</strong></td>
<td>✅ Активно</td>
</tr>
<tr>
<td><strong>Тренировки</strong></td>
<td>✅ Активно</td>
</tr>
<tr>
<td><strong>Huawei Health import</strong></td>
<td>🔒 Подготовлен, скрыт до Health Kit approval</td>
</tr>
<tr>
<td><strong>Фоновая синхронизация</strong></td>
<td>🔒 Будет включена после Huawei approval</td>
</tr>
</table>

</div>

<br>

<div>

<h2>🏗 Архитектура</h2>

<pre>
Huawei Band / Watch
        │
        ▼
Huawei Health
        │
        ▼
Huawei Health Kit
        │
        ▼
BitLut Import Module
        │
        ▼
Android Health Connect
        │
        ▼
BitLut Dashboard
</pre>

<h3>Текущая production-логика</h3>

<pre>
Android Health Connect
        │
        ▼
GoogleHealthManager
        │
        ▼
DashboardViewModel
        │
        ▼
Jetpack Compose UI
</pre>

</div>

<br>

<div align="center">

<h2>🛠 Stack</h2>

<table>
<tr>
<td>Kotlin</td>
<td>Jetpack Compose</td>
<td>Material 3</td>
</tr>
<tr>
<td>Android Health Connect</td>
<td>Huawei Health Kit</td>
<td>HMS Core</td>
</tr>
<tr>
<td>WorkManager</td>
<td>MVVM + StateFlow</td>
<td>Feature Flags</td>
</tr>
</table>

</div>

<br>

<div>

<h2>🦾 Engineering Principles</h2>

<ul>
  <li><strong>KISS</strong> — простые компоненты вместо тяжёлой архитектуры.</li>
  <li><strong>YAGNI</strong> — Huawei runtime не включается до approval.</li>
  <li><strong>AID</strong> — код читаем человеком и LLM.</li>
  <li><strong>Secure by Design</strong> — минимальные разрешения и read-only режим.</li>
  <li><strong>Zero Trust</strong> — health-данные считаются неполными, пока не проверены.</li>
  <li><strong>Observability First</strong> — синхронизация должна быть диагностируемой.</li>
</ul>

</div>

<br>

<div>

<h2>🗺 Roadmap</h2>

<table>
<tr>
<td><strong>v1.5</strong></td>
<td>Health Connect dashboard, русский UI, light premium design.</td>
</tr>
<tr>
<td><strong>v1.6</strong></td>
<td>Полировка синхронизации, журнал событий, UX разрешений.</td>
</tr>
<tr>
<td><strong>v1.7</strong></td>
<td>Включение Huawei Health import после Health Kit approval.</td>
</tr>
<tr>
<td><strong>v2.0</strong></td>
<td>Полноценный Huawei Health → Android Health Connect bridge.</td>
</tr>
</table>

</div>

<br>

<div align="center">

<h2>💚 Open Source</h2>

<p>
  BitLut — бесплатный open-source проект для пользователей Huawei,
  которым нужен прозрачный и независимый способ работать со своими health-данными.
</p>

</div>
