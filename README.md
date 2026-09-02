# BitLut

Open-source, local Android bridge between **HUAWEI Health** and **Android Health Connect**.

```text
HUAWEI Health -> BitLut -> Health Connect -> compatible apps
```

No BitLut account, backend, ads, or server-side health data storage.

## What syncs

Current scope is activity and workout data only: steps, distance, floors/elevation gain, calories when available, and workout sessions. HUAWEI workout types are normalized through a single `HuaweiWorkoutTypeMapper`; non-workout states are filtered out.

Workout distance comes from HUAWEI's activity-scoped data when available. BitLut does not reconstruct workout distance from coarse daily Health Connect aggregates.

## Workout records

Exercise sessions are written to Health Connect as `ACTIVELY_RECORDED` with Huawei device metadata, a deterministic `clientRecordId`, and a stable `clientRecordVersion` for an unchanged workout. The session and its related total calories are written as one bundle. Since 2026-08-31, distance/steps/elevation are also written as their own Health Connect records scoped to the exact session interval (per exercise type), so third-party readers see real per-workout metrics.

The only approved derived value is the documented fallback for total workout calories, used when HUAWEI doesn't provide calories for a specific real workout. This exception is not extended to distance, steps, elevation, or any other metric.

## Dashboard

Workout cards depend on exercise type: walking/running use pace, cycling uses average speed, hiking uses elevation, swimming uses pace/100 m, strength uses duration/calories. Missing metrics are never replaced with invented zeros.

## Corporate wellness compatibility

The corporate wellness app now reliably imports and accepts BitLut-synced workouts, confirmed on a real device after workout distance/steps/elevation began being written as Health Connect records scoped to the workout's own time window (see `sync.md` section 4.6 for the full mechanism).

## Interface

Keeps the August palette: Navy, Lime, Tangerine, Purple, Inter Variable, and system light/dark themes. Current UI direction is calm and content-first: flat outlined cards, restrained hero depth, pill controls, comfortable touch targets, and minimal animation.

Settings is deliberately minimal: data source, one grouped connection/sync actions card, a Health Connect settings deep link, and the steps goal. Workout-filter UI has been removed, but `WorkoutFilterPrefs` still applies in the sync path.

## Verification before commit

Both checks are mandatory:

```bash
./gradlew :app:assembleDebug :app:lintDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

Before making changes, read `CLAUDE.md`, `CONTEXT.md`, `SESSION_HANDOFF.md`, `design.md`, and `sync.md`.