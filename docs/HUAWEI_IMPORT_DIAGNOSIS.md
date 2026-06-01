# Huawei import diagnosis

Current symptom:

- Google Health Connect permission flow works.
- Huawei Health shows BitLut as connected/authorized.
- Sync starts, but Huawei import does not complete.

Root cause fixed in this patch:

- SyncWorker previously stopped on the local `huawei_authorized` SharedPreferences flag.
- That flag depended on `ActivityResult.data` from Huawei authorization.
- On some Huawei Health/HMS Core builds, authorization can be visible in Huawei Health but return empty data to the app.
- Therefore the local flag can be false while real Huawei Health permissions are granted.

Production fix:

- SyncWorker no longer treats the local flag as the source of truth.
- Real authorization is verified by calling Huawei Health Kit `DataController.read()`.
- If the read succeeds, the app marks Huawei authorization as true.
- If the read fails, the exact exception is logged in the in-app log screen and Logcat.

Reviewer rule:

- The app does not generate fake data.
- The app only writes records derived from real Huawei Health Kit reads.
