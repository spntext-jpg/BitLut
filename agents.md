# BitLut engineering workflow

Updated: 2026-11-18. Read this first. The project owner’s current task authorizes the November recovery, theme refactor and offline nutrition catalog. Earlier restrictions against these specific additions are superseded; unrelated scope remains closed.

## Start efficiently

1. Read `context.md`, `design.md`, the current section at the top of `sync.md`, and `SESSION_HANDOFF.md`. Open the relevant deeper reference only for the subsystem being changed.
2. Inspect current source and all call sites before editing. Source plus actual compiler/CI results outrank historical notes. Clearly distinguish a code defect, an externally documented change, a hypothesis and a device-confirmed result.
3. Make a small plan around the user’s acceptance criteria. Batch independent file reads/searches. Do not introduce unrelated cleanup, dependency upgrades, new architecture or speculative work.
4. Edit the actual captured text. Never reconstruct a long existing function from memory: that previously deleted real overlap-normalization helpers. Review the complete change against the original file, including deletions.
5. Keep the user informed about findings, remaining uncertainty and verification. Ask only for genuinely missing information that blocks progress. Do not delegate to other agents unless explicitly requested.

## Product and privacy boundaries

BitLut is free, local-first, Kotlin/Compose, Huawei Health → Android Health Connect → independent compatible readers. No backend, account, paid service, advertising or analytics. Preserve package `com.openhealth.sync`, Huawei App ID/configuration and signing requirements.

Activity/workout categories only; no sleep, heart rate, SpO2, HRV or stress. Missing source values stay absent. The existing bounded workout calorie estimate is display-only and never exported. Never fabricate records or spoof Health Connect `DataOrigin`.

The nutrition journal is a separate, private on-device file: food names, portion grams, calories, macros and an optional user-entered target. The bundled 200-item public reference catalog needs no network, key or permission. User nutrition entries never go to Huawei or Health Connect and remain excluded from Android backup. Database reference values are estimates for the named preparation, not measured personal health data or a prescription.

## Architectural ownership

| Concern | Owner |
|---|---|
| Huawei authorization and reads | `HuaweiHealthManager` |
| Huawei workout IDs | `HuaweiWorkoutTypeMapper` (one table only) |
| Local archive input | `HuaweiExportParser` |
| Health Connect IO and permissions | `GoogleHealthManager`, `HealthPermissionPolicy` |
| Sync scheduling, lease and retry | `SyncWorker`, `SyncOrchestrator`, `BackgroundSyncScheduler` |
| Last-known-good activity UI | `DashboardSnapshotCache`, `DashboardViewModel` |
| Theme | `AugustTokens`, `BitLutExpressiveTheme`, `ThemeMode` |
| Shell and adaptive navigation | `FinalBitLutShell`, `AdaptiveBitLutScaffold` |
| Offline nutrition and journal | `FoodCatalog`, `NutritionJournalPrefs`, `NutritionScreen` |
| Dashboard card preferences | `DashboardCardLayoutPrefs` |

## Do not regress

- Keep Huawei’s seven-day history ceiling, process-wide sync lease, cancellation propagation, stable record IDs/versions, session normalization and session-scoped Distance/Steps. Do not range-delete daily Steps.
- A quota, service or binder failure aborts provider writes and goes to WorkManager backoff; do not retry every remaining workout against a failed provider.
- Keep complete workout bundles inside one transaction; batches may hold multiple complete bundles.
- Only successful permission reads refresh the cache. Optional background reading never gates Huawei export. Foreground reading still works when that grant is denied.
- A local export check proves only the bounded records found in Health Connect. It cannot prove the corporate reader consumed them. Do not claim the August incident resolved without a correlated device test and corporate-reader evidence.
- Historical cache totals must be zeroed after local midnight before display. Never label yesterday’s totals as today’s.
- Nutrition migration preserves IDs/dates/calories. Missing legacy macros remain unknown. Malformed journals fail closed and are never replaced with an empty list. Writes must surface storage errors.
- EN/RU resource keys stay in parity. New UI copy belongs in resources; the public food catalog carries its own EN/RU names. No hardcoded locale maps for UI controls.
- Palette stays Navy, Lime, Tangerine, Purple and Inter. All content surfaces, including hero and tiles, resolve from the same selected Material theme. Do not sample OS dark mode inside individual components.
- Keep 48 dp actions, scalable type, labelled icons, keyboard-safe scrolling and restrained tween motion. Larger windows use a rail; content width stays bounded.

## Verification and delivery

Run free static checks first: real XML parsing, locale key/format parity, catalog schema/200 unique source IDs/nutrient ranges, source references and `git diff --check`. Structural delimiter checks are useful early signals, never proof of compilation.

The Codespaces patch gate is **`:app:checkDebugAarMetadata` plus `:app:compileDebugKotlin`** with JDK 17 and constrained workers/memory:

```bash
./gradlew :app:checkDebugAarMetadata :app:compileDebugKotlin --no-daemon --max-workers=1 --no-watch-fs --console=plain -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" -Pkotlin.compiler.execution.strategy=in-process
```

AGP 9 no longer makes the Kotlin-only task run AAR validation automatically, so the explicit metadata task is required. This is a small compatibility check, not assembly or lint.

Meaningful unit regressions live in `app/src/test/`; the push/PR workflow runs tests, AAR compatibility, lint and APK assembly. The signed release workflow remains separate. Do not suppress lint, disable tests, fake compilation or add a baseline to obtain green output. Full assembly/lint stays in CI; do not duplicate it in a delivery script. A source compile does not establish device behavior or release signing.

One-shot patch delivery must be self-contained, verify captured source fingerprints before mutation, support mixed original/already-applied states, preserve unrelated edits, and stop before commit/push on verification failure. Stage only intended paths. Use a normal non-force push. Verify the remote branch hash before deleting the untracked delivery script. Retain the script and edits after build/network/push failures so the same command can resume. Never commit secrets or the delivery script. Never overwrite a source that matches neither the expected base nor target.

## Documentation discipline

Every code task updates `context.md`, `design.md`, `sync.md` and the handoff to describe the final implementation and test evidence. Update README/privacy/backlog/roadmap when the feature changes their claims. Keep historical changelog entries labelled as history; do not copy old assumptions into current docs. Keep the short context useful and put detailed decisions in subsystem references.

The deliberate Health Connect `1.2.0-alpha06` pin is an exception for the August 2026 certificate/signature fixes; its AAR requires compile SDK 37.0, AGP 9.1.1 and Gradle 9.3.1. Target SDK stays 36 and min SDK 26. Huawei runtime and Kotlin/Compose versions stay pinned. `android.builtInKotlin=false` and `android.newDsl=false` retain the external Kotlin and AGConnect legacy integration; these are official temporary migration switches, not weakened AAR checks. Reassess this exception when a stable release contains those fixes, after verifying official release notes and AAR compatibility.
