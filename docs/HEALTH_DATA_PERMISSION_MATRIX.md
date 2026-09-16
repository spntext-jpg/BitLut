# BitLut Health Data Permission Matrix

This document is the sprint contract for Huawei Health -> BitLut -> Android Health Connect.

## Huawei Basic Sport Health Data scope

| Huawei data family | Import status | Health Connect export target | Notes |
|---|---:|---|---|
| Step | Required | `StepsRecord` | Direct 1:1 mapping. |
| Distance | Required | `DistanceRecord` | Direct 1:1 mapping. |
| Ascent | Required | `FloorsClimbedRecord` | Huawei floors/ascent must be normalized before export. |
| Altitude / elevation gain | Required | `ElevationGainedRecord` | Export only positive elevation gain intervals. |
| Active Hours | Required | `ActivityIntensityRecord` when Health Connect 1.2.x + runtime feature are available | Do not fake workouts for active hours. |
| Daily Activity Summary | Required | Components: steps, distance, active calories, floors/elevation, intensity if available | Health Connect has no single daily summary record. Export the honest component records. |
| Activity record | Required | `ExerciseSessionRecord` | Export sessions with valid start/end time. |
| Activity | Required | `ExerciseSessionRecord` or component records | Depends on Huawei payload granularity. |

## Current production policy

- Huawei import is enabled in `FeatureFlags`.
- Health Connect permissions are declared in `AndroidManifest.xml`.
- Runtime permission requests are centralized in `HealthPermissionPolicy`.
- Huawei Health Kit application scope is approved for 5 of 6 reachable
  Basic-tier categories; individual metric availability may still vary and
  must be handled independently. `HEALTHKIT_CALORIES_READ` is the one
  reachable-but-unrequested scope -- see `docs/SCALING_ROADMAP.md`.
- The app is currently limited to 100 trial users under Huawei's Health
  Kit test phase; lifting this is tracked in `docs/SCALING_ROADMAP.md`.
- The app must never synthesize fake health data to satisfy a visual KPI.

## Documented exception: estimated workout calories (2026-08-25) — dashboard display only since 2026-09-10

When Huawei does not provide workout calories for a session, BitLut may use the
existing user-approved MET-formula **estimate** for the workout card's own
calorie display (`workoutMetricDisplays` in `FinalBitLutShell.kt`).
Measured Huawei workout calories always win when present. This exception is
scoped narrowly:

- Only the workout card's own calorie display is estimated. No record type
  in this matrix is or should be synthesized and written to Health Connect.
- Dashboard strength calories may use the same documented estimator only as a clearly bounded fallback when a measured workout calorie value is absent. Other workout metrics are never synthesized.
- **Until 2026-09-10, this estimate was also written to Health Connect** as
  a `TotalCaloriesBurnedRecord` bundled with every workout. That write was
  removed to shrink the per-workout Health Connect payload after a
  corporate wellness-app reader started failing to sync ("binder died" /
  rate-limit errors) — see `sync.md` sections 4.7 and 4.11 for the full
  detail, and `docs/BACKLOG.md` for the open question of whether this
  actually explains the reader's failure. The MET estimate itself, and its
  use for BitLut's own dashboard, are unchanged.
- `ActiveCaloriesBurnedRecord` (Huawei's active-calorie category, currently
  returning 50005 because BitLut has never requested the
  `HEALTHKIT_CALORIES_READ` scope for it -- see `docs/SCALING_ROADMAP.md`
  -- not because it is permanently blocked) is a separate, distinct record
  type from the estimate discussed here and was never itself estimated;
  it is only ever written with a real Huawei-provided value, which is
  currently always absent.
- `READ_TOTAL_CALORIES_BURNED` remains available for the Google Fit
  dashboard source, which may contain real total-calorie records written by
  another app. `WRITE_TOTAL_CALORIES_BURNED` was removed on 2026-09-16 because
  BitLut has had no TotalCalories writer since 2026-09-10; keeping an unused
  write permission in the Huawei export preflight could unnecessarily block
  every export when that grant is lost or stranded.

## Session-scoped workout sub-records (2026-08-30, reduced 2026-09-10)

`writeActivitySessionsBatch()` bundles Distance and Steps records scoped to
each workout's own exact time window, for exercise types where that metric
is plausible (`sessionSubMetricsFor()` in `GoogleHealthManager.kt`; see
`sync.md` section 4.7 for the full per-type table). Elevation and total
calories were removed from this bundle on 2026-09-10 -- both metrics
remain unaffected in the **continuous, non-workout-scoped** background
elevation/calorie streams covered by the main scope table above, and in
BitLut's own dashboard display, which reads the live Huawei snapshot
directly rather than what was written to Health Connect.

## Health Connect Activity Intensity

`ActivityIntensityRecord` is the correct Health Connect target for active-hours/moderate-to-vigorous activity, but it is not part of the stable 1.1.x API line. Enable it only after the project intentionally moves to the 1.2.x API line and verifies `FEATURE_ACTIVITY_INTENSITY` on target devices.