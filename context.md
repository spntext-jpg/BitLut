# BitLut current context

Updated: 2026-11-18. Current source is authoritative; older changelog entries describe past states.

BitLut is a free, private, on-device Kotlin/Compose bridge: Huawei Health → BitLut → Android Health Connect → independently authorized readers. It has no backend or account. Package remains `com.openhealth.sync`.

## Current work

- August sync recovery: Health Connect is intentionally pinned to `1.2.0-alpha06` for August certificate/signature fixes, with the AAR-required compile SDK 37.0 / AGP 9.1.1 / Gradle 9.3.1 migration and explicit legacy Kotlin/DSL compatibility switches; Huawei runtime is unchanged. Continuous and imported raw metrics now version source corrections; unchanged values keep their versions. Workouts are packed into bounded transactions without splitting their session/metric bundles. Provider/quota failures abort the cycle and defer to existing WorkManager backoff. Deterministic IDs, recording semantics and the seven-day window remain.
- Optional, feature-gated background-read access supports the existing worker dashboard refresh. Denial cannot block Huawei writes; foreground completion can refresh the dashboard directly. The Settings export check reads at most 100 BitLut exercise records from the last week and indicates truncation.
- The corporate reader’s React Native source/logs are absent. Its regression is **not confirmed resolved**. `docs/HEALTH_CONNECT_RECOVERY.md` separates findings from hypotheses and gives the reader-side checklist and an integration probe.
- Theme: shared Material color roles, System/Light/Dark preference, theme-aware dashboard hero/tiles, neutral outlined cards, restrained navigation motion, larger-window rail and bounded content. Navy/Lime/Tangerine/Purple/Inter remain.
- Nutrition: exactly 200 offline common foods/dishes, retained USDA source IDs and preparation descriptions, EN/RU search, gram-based calories/protein/fat/carbs, custom entries, edit/delete/undo, history and optional user-defined calorie target. Today reads the same journal, including before Health Connect connection. Nothing nutritional is uploaded or exported.

## Build baseline

Android compile SDK 37.0 / target 36 / min 26; AGP 9.1.1; Gradle 9.3.1; Kotlin/Compose plugin 2.3.21; JDK 17. Huawei AGConnect 1.9.6.300, Health Kit 6.11.0.303. Compose BOM 2026.06.01, Core 1.18.0, Activity 1.13.0, Lifecycle 2.10.0, AppCompat 1.8.0, Glance 1.2.0, WorkManager 2.11.2. Health Connect 1.2.0-alpha06 is the sole intentional preview exception.

## Invariants

Read `agents.md` for the workflow. Keep Huawei activity-only scope, real-data rules, workout normalization/helpers, stable IDs, no range deletion of daily Steps, process-wide lease, cache midnight guard and cancellation behavior. Huawei per-session distance wins over coarse aggregates. Calorie estimation remains display-only. The dashboard excludes workout-scoped steps from its daily-step sum because Huawei’s daily total already includes them.

Nutrition retains the original private preference file/key; old calories-only records decode without invented weight/macros. Logged nutrients are snapshots. Corrupt data is never silently erased. The reference catalog is a curated starter selection, not a worldwide popularity ranking.

## Validation boundary

Codespaces: resource/data checks, whitespace/AAR checks and mandatory Kotlin compilation before commit/push. CI: unit tests, AAR metadata, lint and APK build on every push/PR; signed release remains manual. AAR/Kotlin compilation and 10 unit regressions passed in the temporary JDK 17 checkout (omitted binary resources used build-only fixtures). Device acceptance is still required for Huawei auth, screen-off export, Health Connect provider versions, corporate import, live theme changes, keyboard, TalkBack, font scaling and midnight rollover. See `docs/VALIDATION_2026_11.md`.

Huawei scaling/user-cap review and optional calorie-scope approval remain external console tasks in `docs/SCALING_ROADMAP.md`.
