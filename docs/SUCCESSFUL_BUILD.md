# BitLut Successful Build Baseline

Status: successful internal production baseline.

Confirmed:

- Signed APK installs on Android device.
- Google Health Connect permission flow works.
- Google Health Connect grants:
  - WRITE_STEPS
  - WRITE_DISTANCE
  - WRITE_FLOORS_CLIMBED
  - WRITE_ELEVATION_GAINED
  - WRITE_ACTIVE_CALORIES_BURNED
  - WRITE_EXERCISE
- Huawei Health app is detected.
- HMS Core is detected.
- Huawei authorization reaches Health Kit approval gate.
- Current Huawei blocker is expected: 50005 Scope unauthorized.
- No fake health data is generated.
- Multi-record Health Connect writer architecture is prepared.
- GitHub Actions release workflow works.
- Manual release version input works.
- APK is signed explicitly in CI.

Production rule:

Do not change package name, signing key, Huawei App ID, or SHA-256 before Huawei approval.
