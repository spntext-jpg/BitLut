# Huawei Health Kit 50005 diagnosis

## Confirmed state

- Huawei authorization screen opens.
- HMS Core is installed.
- Huawei Health is installed.
- Huawei Health shows BitLut as connected.
- Android Health Connect permissions work.
- Real Huawei Health Kit read fails on steps with 50005.

## Root cause

Huawei Health Kit requires server-side approval for the app, package name, release SHA-256 and requested scopes.

User permission inside Huawei Health is not enough.

Huawei documentation states that if the application for Health Kit data has not been approved, a third-party app cannot access user data even after the user grants permission. HMS Core may also cache scope permission information for 24 hours.

## Required production scopes

- HEALTHKIT_STEP_READ
- HEALTHKIT_DISTANCE_READ
- HEALTHKIT_ACTIVITY_READ
- HEALTHKIT_ACTIVITY_RECORD_READ
- HEALTHKIT_HISTORYDATA_OPEN_WEEK

## Required AppGallery checks

- Package name: com.openhealth.sync
- Huawei App ID matches the APK
- agconnect-services.json belongs to the same Huawei app
- Health Kit / Health Service is enabled
- All requested scopes are approved
- Release SHA-256 from the signed APK is configured
- The installed APK is signed with the same release key
- Wait up to 24 hours after approval or permission changes

## Current conclusion

The app reaches DataController.read().
The failure is server-side Huawei Health Kit authorization, not Google Health Connect and not the local sync pipeline.
