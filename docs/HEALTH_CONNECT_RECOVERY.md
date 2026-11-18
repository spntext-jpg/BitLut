# Health Connect recovery investigation

Reviewed 2026-11-18 against the supplied Repomix snapshot. The corporate React Native project, its installed reader-library version and timestamped error logs were not supplied. This work fixes identifiable BitLut defects and adds a way to localize the remaining incident; it does not claim device-confirmed corporate recovery.

## Findings and confidence

| Finding | Evidence / limit | Implemented response |
|---|---|---|
| August SDK certificate/signature changes | Google’s Aug 12/26 release notes; relevant especially to APK-based providers. Device failure is not independently proven. | Deliberate Health Connect 1.2.0-alpha06 pin. Stable 1.1.0 remains the official stable release; the preview exception must be reviewed when stable catches up. |
| Toolchain dependency gate | Snapshot is compile 36.1 / target 36, but 1.2.0-alpha06 AAR metadata requires compile 37 and AGP 9.1+. | Move compile SDK to 37.0, AGP to 9.1.1 and Gradle to 9.3.1. Target/min remain 36/26; legacy Kotlin/DSL switches retain AGConnect compatibility. |
| Continuous corrections can be ignored | Distance/Floors/Elevation/ActiveCalories used metadata default version 1. | Persist stable value-sensitive versions with unchanged client IDs. |
| Raw import can churn | Raw Steps used a new wall-clock version on every import. | Reuse a version until the value changes. |
| Too many workout calls | One insert call per historical workout on every sync. | Pack complete bundles into transactions of at most 100 records. |
| Quota/service failure can cascade | Generic exceptions were swallowed per workout/category, allowing more calls. | Abort the provider cycle and defer to WorkManager; validation failures alone get bounded fallback. |
| Background cache refresh lacks its optional grant | Manifest requested no background-reading permission although workers perform reads. | Feature-gated optional request; skip worker reads on denial and use foreground refresh. Huawei export remains independent. |
| Daily steps can double count | Dashboard raw sum added both daily summation and session-scoped steps. | Exclude Huawei session-scoped steps from the daily sum; keep external session records. |
| Corporate reader may filter out the writer | Actual Health Connect writer is `com.openhealth.sync`, not Huawei, Google Fit or Google Health. Corporate code is unavailable. | Diagnostic source/count check and reader-team checklist; never spoof another origin. |

None of these findings establishes which single change caused the corporate incident. Historic Google Health app connection reports in earlier notes are hypotheses for this device until independently corroborated; Google Health/Fit, Android Health Connect and the corporate reader are separate applications with separate permissions.

## Toolchain migration

The first real compile rejected the new client on AGP 8.13.2 / compile 36.1. The patch respects that gate: API 37.0, AGP 9.1.1, Gradle 9.3.1 and build tools 36.0.0 are updated together. The SDK package is `platforms;android-37.0`, not `platforms;android-37`; the module pins minor API level 0 explicitly. The Gradle distribution SHA-256 is pinned. Huawei AGConnect 1.9.6.300 / Health Kit 6.11.0.303 remain unchanged.

Official temporary `android.builtInKotlin=false` and `android.newDsl=false` switches preserve the current external Kotlin and legacy Huawei plugin model while moving the build toolchain. They do not disable validation or supply a fake SDK. Target remains 36 to avoid unrelated runtime-behavior changes. Signed release and Huawei authorization/device acceptance remain necessary even after compilation.

References: [AGP 9.1.1 compatibility](https://developer.android.com/build/releases/agp-9-1-0-release-notes), [built-in Kotlin migration and opt-out](https://developer.android.com/build/migrate-to-built-in-kotlin).

## Reader-side checklist

The corporate app must initialize its native Health Connect integration, obtain its own read grants and include BitLut’s actual origin. A framework migration does not transfer these grants or create a new record schema automatically. The included `examples/health-connect-reader.ts` is a foreground diagnostic probe to adapt inside that app, not code that BitLut can deploy there.

Use ISO timestamps with explicit offsets, not ambiguous local dates or second/millisecond mixtures. Read all pages and treat both null and empty next tokens as completion. Do not create a tight polling loop. Background or older-history access needs the reader’s own supported permission and consent. A Changes consumer needs a bounded initial backfill, deletion handling, expired-token recovery, and durable checkpoints saved only after its own processing succeeds.

Do not assume every workout has calories, route, elevation, distance or steps. Preserve supported workouts with absent optional metrics. Derive duration from timestamps. For BitLut per-workout metrics, prefer exact-interval `bitlut_exercise_distance_` / `bitlut_exercise_steps_` records; do not raw-sum daily step totals together with those sub-records. Daily total and workout scope serve different queries.

These recommendations are integration checks, not confirmed defects in the unseen corporate app.

## Device acceptance sequence

1. On a real phone, record Android version, Health Connect APK/platform version, BitLut build and corporate app build/library version. Use matching timestamps; do not publish personal health logs.
2. Reconnect BitLut through its existing permission flow. Optional background read may be denied; foreground sync/export must still work.
3. Sync a real Huawei workout within the existing seven-day window. Check Health Connect data entries and Settings → Shared workouts. A zero count is not itself a failure if Huawei contains no workout in that window. Counts are bounded at 100 and indicate additional pages.
4. Independently reconnect the corporate reader. Run its foreground probe against `com.openhealth.sync`. If BitLut-origin sessions are present but the corporate app is empty, collect the reader’s error/filter/token evidence; changing BitLut’s target SDK cannot repair that reader.
5. Repeat unchanged sync, then a genuine source correction. Check stable IDs, no duplicate sessions and updated values. Test background/screen-off export and provider process restart.
6. Test Android 13 APK and Android 14+ platform paths. Do not ship the deliberate preview client exception until its compile/AAR/CI and device checks pass.

Do not clear the user’s Health Connect store, delete/reinsert a week of records, remove permission declarations indiscriminately or force a complete source-history replay as a first step. The diagnostic is read-only and does not inspect another app’s private state.

## References

- [Health Connect release notes](https://developer.android.com/jetpack/androidx/releases/health-connect) — Aug 12/26, 2026 signature/certificate fixes; stable/preview status.
- [Health Connect synchronization](https://developer.android.com/health-and-fitness/health-connect/sync-data) — identity/version upserts and Changes lifecycle.
- [Read data](https://developer.android.com/health-and-fitness/health-connect/read-data) — background/history access and pagination.
- [React Native integration setup](https://matinzd.github.io/react-native-health-connect/docs/get-started/) and [readRecords](https://matinzd.github.io/react-native-health-connect/docs/api/methods/readRecords/) — independent reader initialization and options. Confirm APIs against the corporate app’s installed package before adapting the probe.
