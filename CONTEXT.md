# BitLut Context

BitLut is an open-source Android app that syncs Huawei Health activity data into Android Health Connect / Google Health.

## Production MVP goal

Huawei Health -> BitLut -> Android Health Connect

Primary MVP sync scope:

- Steps
- Distance
- Floors climbed
- Elevation gained / ascent
- Active calories
- Exercise / activity sessions

Huawei approval-requested scope:

- Step
- Distance, ascent & altitude
- Active Hours
- Daily Activity Summary
- Activity record
- Activity
- Reading historical data
- Basic activity management

## Current production status

Google Health Connect:
- permission flow works
- permissions are granted
- multi-record writer architecture prepared

Huawei Health Kit:
- authorization flow works
- current blocker: 50005 approval pending

## Huawei project

- Project ID: 101653523864196965
- App ID: 117824685
- Package: com.openhealth.sync
- Client ID: 1958319989043812544

## Required GitHub secrets

- BITLUT_KEYSTORE_BASE64
- BITLUT_KEYSTORE_PASSWORD
- BITLUT_KEY_ALIAS
- BITLUT_KEY_PASSWORD
- HUAWEI_APP_ID
- AGCONNECT_SERVICES_JSON_BASE64

## Release process

git tag -a v1.0.1 -m "BitLut v1.0.1 production MVP"
git push origin v1.0.1

GitHub Actions:
- builds signed APK
- uploads workflow artifact
- creates GitHub Release asset

## Production rule

Never generate fake health data.
Only sync real Huawei-derived records.


## Successful baseline

The current internal production baseline is confirmed:

- signed APK installs successfully
- Google Health Connect permissions work
- Huawei authorization reaches expected approval gate
- CI release pipeline creates signed APKs
- no fake health data is generated

See also: docs/SUCCESSFUL_BUILD.md

## UI log policy

The in-app log screen should show only useful user-level events.
Verbose technical checks are kept in Logcat but hidden from UI logs.

Hidden from UI logs:

- repeated Health Connect availability checks
- granted permission debug dumps
- Huawei pending approval noise
- expected not-authorized state before Huawei approval

## Duplicate sync protection policy

Before Huawei approval, sync must not write fake data.
After approval, duplicate protection must be implemented around real Huawei-derived records only:

- use last successful sync timestamp
- avoid overlapping historical windows
- avoid parallel WorkManager runs
- never insert generated placeholder records

## BitLut v1.9.6 strict health-data scope

BitLut v1.9.6 is locked to the Huawei Health approval scope requested in AppGallery:

- Step
- Distance, ascent and altitude
- Active Hours
- Daily Activity Summary
- Activity record
- Activity

The app does not request, read, write or infer sleep, heart rate, SpO2, HRV, stress or Activity Intensity data in this release.

Health Connect export is limited to Huawei-derived activity/basic sport records: `StepsRecord`, `DistanceRecord`, `FloorsClimbedRecord`, `ElevationGainedRecord`, `ActiveCaloriesBurnedRecord` and `ExerciseSessionRecord`.

## BitLut v1.9.6 GUI scope

The app UI is activity-only in v1.9.6. Dashboard and Settings must not expose widgets, toggles or permission prompts for pulse, sleep, stress, SpO2, HRV or Activity Intensity.

The bottom navigation is icon-only neo-glassmorphism. Status refresh actions live in Settings only; app startup refreshes status automatically.

## BitLut v1.9.6 Glassmorphism 2.0 GUI polish

The UI uses a premium activity-only glass system across all screens: translucent cards, soft depth shadows, radial glow, thin glass borders and an icon-only floating bottom navigation.

The History chart reserves fixed vertical space for values, bars and dates so large step values cannot push bars outside the card bounds.

## BitLut v1.9.6 Glass 2.0 UI system

The UI uses a premium activity-only glass system across all screens: translucent surfaces, floating glass navigation, soft depth shadows, radial glow, thin highlight borders and bounded charts.

History charts reserve fixed vertical space for values, bars and dates so large step values cannot push bars outside card bounds.

## v1.9.6 current baseline

BitLut v1.9.6 is activity-only for Huawei Health and Google Health Connect.

Do not reintroduce sleep, pulse, SpO2, HRV, stress or Activity Intensity until Huawei approval scope is expanded.

GUI baseline:
- Glass 2.0 visual system
- icon-only floating bottom navigation
- premium translucent cards
- bounded history charts
- refresh status buttons only in Settings
- automatic status refresh on app launch

## v1.9.6 lifecycle and Glass performance hardening

Implemented after deep code review:

- Compose state collection in `MainActivity` is lifecycle-aware via `collectAsStateWithLifecycle`.
- Glass 2.0 UI helpers cache stable shapes, gradient color lists and static brushes with `remember(...)`.
- History chart bars are bounded with fixed value/bar/date regions to avoid overflow on large step values.
- App logger has conservative memory guards for retained in-app logs.

Deferred to a separate architecture sprint:

- Splitting `FinalBitLutShell.kt` into feature-level UI files.
- Moving WorkManager orchestration out of `MainActivity`.
- Introducing interfaces for `GoogleHealthManager` / `HuaweiHealthManager`.
- Gradle Version Catalog migration.
