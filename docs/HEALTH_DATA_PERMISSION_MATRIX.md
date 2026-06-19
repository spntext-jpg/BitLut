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
- Huawei Health Kit 50005 remains a pending approval/server-side verification state.
- The app must never synthesize fake health data to satisfy a visual KPI.

## Health Connect Activity Intensity

`ActivityIntensityRecord` is the correct Health Connect target for active-hours/moderate-to-vigorous activity, but it is not part of the stable 1.1.x API line. Enable it only after the project intentionally moves to the 1.2.x API line and verifies `FEATURE_ACTIVITY_INTENSITY` on target devices.
