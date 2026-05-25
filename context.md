# BitLut Context

BitLut is an open-source Android/Kotlin bridge that syncs Huawei Health data into Android Health Connect.

## Production baseline

- Package/applicationId: `com.openhealth.sync`
- Version: `1.0.0` / versionCode `1`
- Active Huawei path: Huawei Health Kit Android SDK (`HuaweiHealthManager`)
- Active Google target: Android Health Connect (`GoogleHealthManager`)
- No mock or fake sync data is allowed in production. `SyncWorker` must only write records read from Huawei Health Kit.
- The old Huawei OAuth/REST prototype and `HuaweiAuthManager` are removed from production code.

## Local hidden files

Do not commit these files:

- `.huawei.env`
- `.signing/bitlut-release.jks`
- `local.properties`
- `agconnect-services.json`

`.huawei.env` example:

```env
HUAWEI_APP_ID=117824685
HUAWEI_CLIENT_ID=
HUAWEI_CLIENT_SECRET=
HUAWEI_REDIRECT_URI=https://com.openhealth.sync/oauth_callback
```

## Local release build

```bash
./gradlew --no-daemon :app:clean :app:assembleRelease
```

Output:

```text
app/build/outputs/apk/release/app-release.apk
```

## GitHub Actions release secrets

Set these repository secrets before using the release workflow:

- `BITLUT_KEYSTORE_BASE64`
- `BITLUT_KEYSTORE_PASSWORD`
- `BITLUT_KEY_ALIAS`
- `BITLUT_KEY_PASSWORD`
- `HUAWEI_APP_ID`
- optional: `HUAWEI_CLIENT_ID`, `HUAWEI_CLIENT_SECRET`, `HUAWEI_REDIRECT_URI`

Create `BITLUT_KEYSTORE_BASE64` locally:

```bash
base64 -w 0 .signing/bitlut-release.jks
```

## Manual production QA

1. Install the signed release APK on a device with Huawei Health and HMS Core.
2. Confirm the installed package is `com.openhealth.sync`.
3. Grant Health Connect write permissions for steps and heart rate.
4. Grant Huawei Health Kit read permissions for steps and heart rate.
5. Run manual sync.
6. Copy logs from the app and verify record counts.
7. Confirm records appear in Health Connect.

## Release build policy update
- Production version starts at versionName 1.0.0 / versionCode 1.
- Release builds must keep applicationId exactly `com.openhealth.sync`; no `.debug` suffix.
- `.huawei.env`, `.signing/`, `*.jks`, and `agconnect-services.json` are local/private and must not be committed.
- Missing Huawei values must not block Gradle configuration while AppGallery onboarding is in progress. Runtime Health Kit authorization remains user-driven through Huawei HMS SDK.

## 2026-05-25 - BitLut 1.0.1 runtime fixes
Observed on device:
- Huawei Health Kit authorization failed with code 31 when HMS Core was not installed.
- Health Connect SDK was available, but granted permissions were empty, so WorkManager sync could not write records.

1.0.1 goals:
- Do not silently fail Huawei authorization when HMS Core is missing.
- Show a clear user action and open AppGallery/market/web page for HMS Core installation or update.
- Do not start background sync when Health Connect write permissions are missing.
- Keep package name com.openhealth.sync and release signing unchanged.
