# BitLut Huawei Health Kit production review package

BitLut is a production Android bridge from Huawei Health to Android Health Connect.

Requested Huawei Health Kit permissions:

- healthkit.step.read
- healthkit.distance.read
- healthkit.activity.read
- healthkit.activityrecord.read
- healthkit.historydata.open.week

The app reads only real user data from Huawei Health Kit and writes available records to Android Health Connect.

No fake health data is generated.
No mock data is written.
No placeholder records are written.

Reviewer flow:

1. Install the signed release APK.
2. Install or update HMS Core.
3. Install or update Huawei Health.
4. Sign in to Huawei Health with the test Huawei ID.
5. Make sure Huawei Health contains real step, distance and activity data.
6. Open BitLut.
7. Grant Android Health Connect permissions.
8. Tap Huawei Health.
9. Approve Huawei Health Kit permissions.
10. Tap Sync.
11. Verify data appears in Android Health Connect.

Package:

- com.openhealth.sync

If authorization returns 50005, at least one requested Health Kit scope is not fully approved, the release SHA-256 is not recognized, the Huawei App ID/agconnect-services.json does not match this package, or HMS Core still has cached permission state.
