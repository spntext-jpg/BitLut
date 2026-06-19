<p align="center">
  <img src="docs/bitlut-mascot.png" width="180" alt="BitLut mascot" />
</p>


<div align="center">

<h1>BitLut</h1>

<p>
  <strong>Premium open-source health bridge for Huawei Health and Android Health Connect.</strong><br>
  A clean Summary and History dashboard today. Full Huawei Health import is wired through Settings and guarded by Health Kit approval.
</p>

<p>
  <img alt="Android" src="https://img.shields.io/badge/Android-26%2B-C1FF05?logo=android&logoColor=111111">
  <img alt="Kotlin" src="https://img.shields.io/badge/Kotlin-Android-9E6FC3?logo=kotlin&logoColor=white">
  <img alt="Compose" src="https://img.shields.io/badge/Jetpack%20Compose-Material%203-FF7D32?logo=jetpackcompose&logoColor=white">
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
<h2>◎</h2>
<h3>Summary</h3>
<p>Steps, sleep and heart metrics in large, readable health cards.</p>
</td>
<td align="center" width="33%">
<h2>⌁</h2>
<h3>History</h3>
<p>Seven-day trends for activity, sleep and heart rate.</p>
</td>
<td align="center" width="33%">
<h2>⚙</h2>
<h3>Settings</h3>
<p>Google Health Connect, Huawei Health authorization and manual sync.</p>
</td>
</tr>
</table>
</div>

---

## What BitLut does

BitLut is an Android app for people using Huawei Band, Huawei Watch and Huawei Health who want their sport and activity data available in Android Health Connect.

The app is now structured around three screens:

- **Summary** — current health snapshot.
- **History** — the last seven days of imported and available Health Connect data.
- **Settings** — connection, permission checks and Huawei → Health Connect sync.

## Health data coverage

BitLut is prepared for the Basic Sport Health Data scope set:

<table>
<tr><td><strong>Step</strong></td><td>Read from Huawei Health and write to Health Connect steps.</td></tr>
<tr><td><strong>Distance, ascent & altitude</strong></td><td>Mapped to distance, floors climbed and elevation gain where available.</td></tr>
<tr><td><strong>Active Hours</strong></td><td>Tracked as Huawei coverage; Health Connect export is implemented only where a safe compatible record exists.</td></tr>
<tr><td><strong>Daily Activity Summary</strong></td><td>Used as coverage for activity totals and diagnostics.</td></tr>
<tr><td><strong>Activity record</strong></td><td>Mapped to Health Connect exercise sessions where supported.</td></tr>
<tr><td><strong>Activity</strong></td><td>Used for workouts and movement sessions.</td></tr>
</table>

## Design system

BitLut uses a premium health interface inspired by Material 3 Expressive and modern mobile health apps.

<table>
<tr><td><strong>Light mode</strong></td><td><code>#F2F2F7</code> system background, <code>#FFFFFF</code> elevated cards.</td></tr>
<tr><td><strong>Dark mode</strong></td><td><code>#0C0C0E</code> and <code>#1C1C1E</code> with glass-like card surfaces.</td></tr>
<tr><td><strong>Cards</strong></td><td>Large 28-32dp squircle radius, soft shadows and floating layers.</td></tr>
<tr><td><strong>Activity</strong></td><td>Coral / red category accent.</td></tr>
<tr><td><strong>Sleep</strong></td><td>Deep turquoise-purple accent.</td></tr>
<tr><td><strong>Heart</strong></td><td>Rich red accent.</td></tr>
</table>

## Architecture

```text
Huawei Band / Watch
        │
        ▼
Huawei Health
        │
        ▼
Huawei Health Kit
        │
        ▼
BitLut SyncWorker
        │
        ▼
Android Health Connect
        │
        ▼
Summary / History UI
```

## Stack

- Kotlin
- Jetpack Compose
- Material 3
- Android Health Connect
- Huawei Health Kit / HMS Core
- WorkManager
- MVVM + StateFlow
- Feature flags
- GitHub Actions release pipeline

## Localization

- Russian UI for devices whose system language is Russian.
- English fallback for all other devices.
- New UI copy must be added to both localization resource files.

## Engineering principles

- **KISS** — simple, inspectable components.
- **YAGNI** — no fake health records and no speculative data mapping.
- **AID** — AI-readable code and explicit contracts.
- **Secure by Design** — minimum required permissions.
- **Zero Trust** — external health data is validated before writing.
- **Observability First** — sync decisions and failures are logged.

## Roadmap

<table>
<tr><td><strong>Current</strong></td><td>Summary / History / Settings shell, Health Connect dashboard, Huawei import pipeline enabled behind runtime checks.</td></tr>
<tr><td><strong>Next</strong></td><td>Move all remaining compatibility strings from code into Android resources.</td></tr>
<tr><td><strong>Health Kit approval</strong></td><td>Verify Huawei read scopes with reviewer account and run end-to-end Huawei → Health Connect sync.</td></tr>
<tr><td><strong>v2.0</strong></td><td>Production-grade Huawei Health bridge with complete diagnostics and release documentation.</td></tr>
</table>

## Open source

BitLut is a free open-source project for Huawei users who want transparent and independent control over their health data.

<!-- BitLut UI Sprint Note -->

## Current Product Shape

BitLut is now organized around three production tabs: **Summary**, **History** and **Settings**. Summary focuses on the most important health KPIs, History shows 7-day trends, and Settings controls Google Health Connect, Huawei Health and manual sync.
