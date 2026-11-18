# November validation record

Scope: the supplied Repomix snapshot and generated patch. Updated 2026-11-18.

## Local checks

- Parsed the original repository snapshot and reviewed architecture, sync history, permissions, UI/theme, journal, build/release setup and project documentation.
- XML parsing, EN/RU key/reference checks and catalog schema/range/source-ID checks are part of patch verification.
- The first real AAR gate rejected Health Connect 1.2.0-alpha06 on compile SDK 36.1 / AGP 8.13.2. This exposed a required build migration: compile SDK 37.0, AGP 9.1.1, Gradle 9.3.1, build tools 36.0.0, explicit legacy Kotlin/DSL compatibility. The final compile outcome is recorded below; source checks alone do not prove compilation.
- The snapshot omits binary resources and the Gradle wrapper JAR. The temporary compile checkout used a public Inter font and placeholder launcher PNGs solely to resolve missing resource names. They are not part of this patch and do not verify original branding assets or rendering.

## Recorded results

- Real `:app:checkDebugAarMetadata` and `:app:compileDebugKotlin` passed with JDK 17, Gradle 9.3.1, AGP 9.1.1, API 37.0 and the delivered 1 GiB / 384 MiB constrained JVM settings. The Huawei AGConnect plugin configured on that lane without disabling dependency checks. Legacy Kotlin/DSL deprecation notices are expected migration warnings.
- `:app:testDebugUnitTest` passed: 10 tests, zero failures/errors/skips. Coverage includes catalog provenance/count, gram arithmetic, EN/RU search, zero-energy foods, legacy migration, unknown macros/day filtering, invalid/corrupt data, version corrections and provider failure classification.
- All 321 EN/RU resource keys and format placeholders match; XML and source references parse; catalog count/unique IDs/ranges pass.
- Delivery workflow harness passed six scenarios: normal apply/verify/commit/push/remote verification/self-delete; apply-only/resume; failed compile; source drift; unrelated work; failed push/resume. Only that workflow harness substitutes a compiler stub to exercise failure paths; the Android compile/unit runs above are real.
- Full lint, debug APK assembly, release signing and real-device rendering/corporate import are not claimed. They remain CI/device acceptance gates. Temporary resource fixtures are not shipped.

## Mandatory Codespaces gate

The patch runs static checks, `:app:checkDebugAarMetadata` and `:app:compileDebugKotlin` before commit/push. It cannot bypass failure, suppress lint or claim remote CI passed. It refuses unrelated staged/working changes and unexpected source fingerprints. Backups/resume state stay under Git metadata; the untracked script is deleted only after a normal push and remote hash verification. Use `--apply-only` for an applied/compiled working tree without commit/push; it retains the script.

## CI and device gates

The push/PR workflow runs AAR compatibility, unit tests, lint and debug APK assembly. The existing release workflow performs signing/APK checks separately. CI success and a real-device test remain mandatory before publishing a release.

Device gates: Huawei auth and scope, live/periodic/screen-off export, provider restart, unchanged and corrected source data, Android 13 APK versus 14+ platform, corporate foreground and background imports, source priority, large fonts, TalkBack, keyboard, editor recreation, all theme modes, rail/resize, offline catalog, legacy journal, delete/undo and midnight rollover.

The corporate reader code/logs were not included. End-to-end incident resolution is pending that evidence, regardless of whether the source compiles. The SDK preview exception is explicit and must pass device acceptance. No automatic store publication is part of the patch.
