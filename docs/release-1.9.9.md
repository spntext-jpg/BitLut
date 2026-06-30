# BitLut 1.9.9 Release Readiness

Release target: `1.9.9`

Important: app versioning is owned by GitHub Actions / release workflow. This sprint intentionally does not modify `versionName` or `versionCode`.

## Included

- Strict activity-only Huawei / Health Connect sync scope.
- Sync orchestration moved out of `MainActivity`.
- Lifecycle-aware Compose state collection.
- Glass 2.0 UI split into stable component files.
- Metric chart component compile fix after UI split.
- Split-aware UI verification scripts.

## Health-data scope

Allowed activity categories only: steps, distance, floors, elevation gain, active calories, exercise sessions.

Not included: sleep, heart rate, SpO2, HRV, stress, body temperature, blood pressure, respiratory rate.

## Release build

Release artifact is produced by GitHub Actions.

Do not manually bump `versionName` or `versionCode` in this sprint.

## Manual smoke test before publishing

- App launches.
- Bottom navigation works.
- Summary tab opens.
- History tab opens.
- Metric charts render.
- Settings tab opens.
- Permission request remains activity-only.
- Immediate sync can be triggered.
- Background sync can be scheduled.
