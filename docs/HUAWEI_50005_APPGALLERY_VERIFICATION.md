# Huawei Health Kit 50005 diagnosis

## Confirmed app behavior

- Huawei authorization screen opens.
- HMS Core is installed.
- Huawei Health is installed.
- Android Health Connect works.
- BitLut reaches Huawei Health Kit DataController.read().
- Huawei Health Kit returns 50005 on real data read.

## Meaning

50005 means the requested Health Kit permission is not approved or not available for the app/package/release signing certificate/scope set.

Huawei user authorization inside Huawei Health is necessary but not sufficient. Huawei Health Kit server-side approval is also required.

## Required approval scope

- Step read
- Distance read
- Activity read
- Activity record read
- Historical data open week

## Important

The app must be tested after Health Kit verification is granted. HMS Core permission cache may require up to 24 hours after approval or permission changes.
