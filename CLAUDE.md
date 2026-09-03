# CLAUDE.md

Read this before changing BitLut. This is the current engineering contract; historical details belong in `CHANGELOG.md` and `SESSION_HANDOFF.md`.

## Product boundary

BitLut is a local-first Kotlin/Jetpack Compose Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect -> compatible readers
```

No BitLut backend/account. Production scope is activity/workout data only: steps, distance, floors/elevation, calories when available, and exercise sessions. Do not add sleep, heart rate, SpO2, HRV, stress, or other biometric categories without an explicit product/scope review.

Real-data rule: never fabricate missing metrics. The only approved exception is the existing workout total-calorie estimate used when Huawei supplies no workout calories; keep that exception isolated to `TotalCaloriesBurnedRecord`.

Current top-priority goal: lift the Huawei Health Kit 100-user test-phase cap, and add `HEALTHKIT_CALORIES_READ` if it can be done without an Enterprise account. See `docs/SCALING_ROADMAP.md` for the plan; do not add any Advanced-tier scope (sleep/heart rate/SpO2/stress) regardless -- that remains permanently closed to individual developers.

## Current baseline — 2026-08-31

- Huawei Health Kit authorization and real activity reads work.
- `HuaweiWorkoutTypeMapper` is the single Huawei workout-ID mapping source.
- Per-session Huawei workout distance has priority over aggregate reconstruction.
- Health Connect workouts are `ACTIVELY_RECORDED`, use Huawei device manufacturer metadata, deterministic client record IDs and stable versions, and write session + related calories as one bundle.
- Workout distance/steps/elevation are also written as their own Health Connect records scoped to the exact session interval (gated per exercise type), so third-party readers see real per-workout metrics instead of only a coarser background aggregate. See `sync.md` section 4.6-4.7 for the full mechanism.
- Dashboard workout metrics are type-aware and omit unavailable values.
- `DashboardCardLayoutPrefs` is the sole dashboard card order/visibility layer.
- `GoalPrefs` stores the steps goal only.
- August colors and system light/dark themes remain the design baseline; surfaces are now quieter and flatter.
- Bottom navbar: all controls share one common height (64dp); Refresh reads as primary via width (84dp pill), not height.
- `assembleDebug` and `lintDebug` are mandatory before commit.

## Architecture anchors

### Huawei

`HuaweiHealthManager` owns authorization/live reads. `HuaweiWorkoutTypeMapper` owns workout type normalization. `HuaweiExportParser` owns bounded local archive import and must use the same mapper.

Do not rebuild workout distance from daily Health Connect overlap aggregates. Use Huawei activity-scoped values when available. Do not maintain a second numeric workout table.

### Health Connect

`GoogleHealthManager` owns read/write behavior. Keep deterministic identities/upsert semantics. Do not change workout recording method back to automatic/unknown. Do not attempt to spoof `DataOrigin`; Health Connect attributes records to the actual writer package (`com.openhealth.sync`).

The corporate wellness app now reliably imports BitLut-origin workouts, confirmed on a real device after the 2026-08-31 session-scoped Distance/Steps/Elevation sub-metric write (see `sync.md` section 4.6). Do not mutate workout write metadata further on this front without new evidence of a different problem.

### Sync and resilience

`SyncWorker` / `SyncOrchestrator` own synchronization. Preserve retry/lease behavior unless a task explicitly targets sync reliability. `DashboardSnapshotCache` is the last-known-good UI cache. Never create demo/fake health records to make the dashboard look populated.

### UI

`FinalBitLutShell` owns current screens. `DashboardViewModel` owns dashboard state. Keep Settings minimal and preserve the existing Huawei/Google/Health Connect flows. Split files only when there is a concrete maintenance benefit; file size alone is not a reason.

## UI contract

- Keep August palette: Navy, Lime, Tangerine, Purple and Inter Variable.
- Normal cards: flat, subtle outline, no fake press animation. Hero may keep restrained depth.
- Pill buttons, practical touch targets, restrained tween motion. No routine bounce/elastic motion.
- One obvious primary action per group; Settings primary action is `Sync now`.
- Icon-only actions require content descriptions.
- Missing workout metrics are omitted, never replaced with invented zeroes.

## Localization contract

- UI strings belong in Android resources, not locale maps/hardcoded Kotlin.
- Every new/removal resource change must preserve key parity between `values/strings.xml` and `values-ru/strings.xml`.
- Parse both XML files before build.
- Never silence `MissingTranslation`; fix the locale resource.

## Cleanup rules

Apply YAGNI/KISS/DRY/SOLID conservatively:

- Do not delete a private method/import/layer from a lexical scan alone. Check all call sites and callbacks first.
- Remove plumbing only when the user-facing trigger and all remaining consumers are truly gone.
- Do not refactor unrelated working paths during cleanup.
- One-off patch/hotfix/verify scripts are delivery artifacts and should not remain in the repository after a successful sprint.

## Verification guardrails

Today's failed intermediate patches established these mandatory rules:

1. Run static structural checks before Gradle: duplicate declarations, dangling references, XML parse, EN/RU key parity.
2. Run `:app:assembleDebug` and `:app:lintDebug`; compile alone is insufficient.
3. Do not suppress lint or create a baseline merely to obtain green output.
4. If verification fails, print the concrete Kotlin/lint errors and stop before commit/push.
5. Keep Gradle console output compact; do not use `--stacktrace` unless specifically debugging a Gradle infrastructure failure.
6. Never include `git diff -- ...` in delivery commands.
7. Patch scripts should be idempotent/fail-closed where practical and must not guess when source anchors differ.

## Build gate

```bash
./gradlew :app:assembleDebug :app:lintDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```
