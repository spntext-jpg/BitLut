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
- Huawei Health Kit application scope is approved; individual metric availability may still vary and must be handled independently.
- The app must never synthesize fake health data to satisfy a visual KPI.

## Documented exception: estimated workout calories (2026-08-25)

When Huawei does not provide workout calories for a session, BitLut may use the
existing user-approved MET-formula **estimate** as a `TotalCaloriesBurnedRecord`.
Measured Huawei workout calories always win when present. This exception is
scoped narrowly:

- Only `TotalCaloriesBurnedRecord` is estimated. No other record type in
  this matrix is or should be synthesized.
- Dashboard strength calories may use the same documented estimator only as a clearly bounded fallback when a measured workout calorie value is absent. Other workout metrics are never synthesized.
- `TotalCaloriesBurnedRecord` is used specifically because it is a distinct
  Health Connect data type from `ActiveCaloriesBurnedRecord` (Huawei's
  permanently-blocked, sensor-measured category) -- this avoids conflating
  an estimate with the exact record type users and other apps already
  expect to mean "measured by a real sensor."
- Requires `android.permission.health.READ_TOTAL_CALORIES_BURNED` /
  `WRITE_TOTAL_CALORIES_BURNED`, declared in `AndroidManifest.xml` and
  requested via `HealthPermissionPolicy` -- itself a deliberate, one-off
  exception to this project's general "no new Health Connect/Huawei
  permissions" rule.

## Health Connect Activity Intensity

`ActivityIntensityRecord` is the correct Health Connect target for active-hours/moderate-to-vigorous activity, but it is not part of the stable 1.1.x API line. Enable it only after the project intentionally moves to the 1.2.x API line and verifies `FEATURE_ACTIVITY_INTENSITY` on target devices.