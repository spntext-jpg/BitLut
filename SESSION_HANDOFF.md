# BitLut session handoff

Updated: 2026-11-18. Read `agents.md`, `context.md`, `design.md` and the current section of `sync.md` first.

## Delivered source changes

Health Connect certificate-fix client pin plus its AAR-required compile SDK 37.0 / AGP 9.1.1 / Gradle 9.3.1 migration (legacy Kotlin/DSL switches retained for Huawei), value-sensitive continuous/raw-step versions, bounded complete-workout transactions, whole-cycle provider failure deferral, optional background dashboard reads and a foreground-only bounded export diagnostic. Existing workout IDs, recording methods, overlap helpers, seven-day history, scope and lease remain. Huawei daily steps no longer count their own session-scoped duplicates in the dashboard.

Shared Material theme roles replace the fixed dark hero/white-tile behavior; System/Light/Dark choices persist and update content/system-bar contrast. Navigation has restrained tweens, a larger-window rail and bounded content. Four tabs and the brand palette remain.

Nutrition has 200 offline USDA-referenced foods/dishes, EN/RU search, gram scaling, calories/macros, custom entries, editing, delete/undo, historical days, optional user-defined kcal target and a Today card. Legacy journal values survive; unknown macros stay unknown. No nutrition export, network, account or backup.

Canonical documentation names are now `agents.md` and `context.md`. The historical sync document is preserved behind the current recovery section. Review `docs/VALIDATION_2026_11.md` for actual verification evidence and pending device gates.

AAR metadata and Kotlin compilation passed on the final JDK 17 / API 37.0 lane, and 10 unit tests passed. Build-only resource fixtures replaced binaries missing from Repomix; original branding, full lint/APK/release and device behavior remain unverified.

## Continue from evidence

- Run the supplied patch in the real Codespaces checkout. It refuses source drift/unrelated dirt, performs static/AAR checks and Kotlin compilation, commits only intended files, pushes normally, verifies the remote hash and only then deletes itself. Failure preserves it for retry.
- Push/PR CI now runs unit tests, AAR metadata, lint and APK assembly. The signed release remains a separate manual workflow.
- Re-test Huawei authorization, manual/background/screen-off sync and unchanged/corrected workout writes on Android 13 APK and Android 14+ platform providers.
- Compare Settings → Shared workouts with Health Connect itself and a timestamped corporate-reader run. The corporate source/logs are absent: the incident remains open until this succeeds. The TypeScript probe is a reader-team aid, not deployed corporate code.
- Verify live theme changes, both modes, Russian text, narrow phones, large fonts, keyboard, rail and midnight rollover on a real device. No screenshot/device validation is claimed by source inspection.
- Review AppGallery declarations for the expanded local nutrition journal and optional background health reading before the next store release. Do not add biometrics or change Huawei scopes as part of that review.
- Huawei scaling/calorie-scope console tasks remain in `docs/SCALING_ROADMAP.md`.
