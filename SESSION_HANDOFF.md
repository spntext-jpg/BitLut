# BitLut — Session Handoff

**Current handoff:** 2026-09-11

**Repository state:** modernization + AndroidX compatibility + August UI polish + Android 16 lint cleanup completed and verified in GitHub Actions.

## Source of truth

For the next session, use this order of authority:

1. current repository source;
2. latest successful GitHub Actions release workflow;
3. `SESSION_HANDOFF.md`;
4. `CONTEXT.md`, `sync.md`, `design.md`, `CHANGELOG.md`;
5. older historical notes only when they do not conflict with the above.

The 2026-09-11 migration is complete. Do not revert it from older handoff text or old one-shot patch scripts.

## Current production baseline

- Android: `compileSdk 36.1`, `targetSdk 36`, `minSdk 26`.
- AGP: `8.13.2`.
- Gradle: `8.13`.
- Kotlin / Compose plugin: `2.3.21`.
- JDK: 17.
- Huawei AGConnect plugin: `1.9.6.300`.
- Huawei Health Kit: `6.11.0.303`.
- Health Connect: stable `1.1.0`.
- Compose BOM: `2026.06.01`.
- AndroidX Core: `1.18.0`.
- Lifecycle: `2.10.0`.

This is intentional. Compose 1.12 / Core 1.19 / Lifecycle 2.11 crossed into the API 37 / AGP 9.1+ requirement. Do not upgrade those lines independently. A future AGP 9/API 37 move is a dedicated Huawei compatibility migration because AGP 9 changes the Kotlin integration model.

## Verified workflow — keep this

**Codespaces is static-check only. Do not run Gradle there.** Repeated local Gradle/AGP invocations exhausted Codespace memory and terminated the terminal even for seemingly small tasks.

The working engineering flow is:

```text
Codespaces
  patch script
  -> built-in structural checks
  -> git diff --check
  -> git status --short
  -> commit / push

GitHub Actions
  AAR metadata compatibility
  -> lintRelease
  -> assembleRelease
  -> signing / APK verification
  -> artifact / release
```

This sequence is now proven. Keep release compilation and lint in GitHub Actions rather than moving them back into Codespaces.

The release workflow should keep an early `checkReleaseAarMetadata` gate before lint/build so SDK/AGP incompatibility fails quickly. Lint reports should remain uploaded with `if: always()` so CI failures expose the full blocker set.

## 2026-09-11 changes that are now landed

### Android / dependency modernization

- Migrated to Android 16 / API 36.1 on the last stable AGP 8.13 lane.
- Updated Gradle, Kotlin, AGConnect, Health Connect and compatible AndroidX dependencies.
- Migrated deprecated Kotlin compiler configuration to typed `kotlin.compilerOptions`.
- Kept Huawei/AppGallery as the primary deployment/runtime constraint rather than chasing incompatible API 37 dependencies.

### Sync hardening

- Huawei → Health Connect export is gated by write permissions; dashboard reads are gated by read permissions.
- WorkManager UI activity tracks actually `RUNNING` sync work, not merely `ENQUEUED`/`BLOCKED` periodic work.
- Workout writes preserve deterministic IDs and coherent exercise-session bundles.
- Overlapping Huawei sessions are normalized by retaining the richer real session; do not fabricate clipped sessions.
- Session-scoped workout metrics remain the interoperability-critical contract for downstream readers.
- 2026-09-10: workout bundle no longer includes elevation/total-calories (`ElevationGainedRecord`/`TotalCaloriesBurnedRecord`) -- only session, Distance, Steps -- reducing per-workout Health Connect payload after a corporate reader reported "binder died"/rate-limit sync failures. Targeted reduction, not a confirmed fix; see `docs/BACKLOG.md`.
- Dashboard cache consumers must preserve the midnight stale-cache guard; never reapply yesterday's daily totals as today's data.

### August UI polish

- Bottom navigation controls share the established sizing hierarchy and now use restrained spring micro-interactions: small compression, 2dp depth, tiny tilt and one short release tremor.
- Static cards/content must remain non-bouncy.
- The Today sync state renders immediately as a high-contrast August capsule in both themes.
- UI-triggered sync has a minimum ~1.1s visual dwell so fast syncs/lease collisions cannot disappear between Compose frames.
- Wording is `Sync in progress…` / `Идёт синхронизация…`.

### Android 16 / lint cleanup

- Compose locale reads now use observable configuration rather than `Locale.getDefault()` inside composables.
- Directional Material icons use AutoMirrored variants where required.
- Deprecated `LocalClipboardManager` usage was removed.
- Observer parameter naming and annotation-target warnings were cleaned.
- Deprecated manual system-bar color writes were removed; `enableEdgeToEdge()` remains the owner.
- Do not introduce a lint baseline or suppress new lint failures merely to unblock CI.

## Huawei-specific constraints

BitLut is **Huawei AppGallery / Huawei Health first**.

Huawei device-side Health Kit calls may be sensitive to background/screen-off state. The existing WorkManager/retry design is intentionally preserved. Do not replace it with a foreground-service architecture without real Huawei-device evidence.

Any future platform migration must regression-test at least:

- Huawei authorization through HMS Core;
- foreground manual sync;
- background / screen-off behavior;
- periodic catch-up;
- recovery after Huawei Health/HMS restart;
- Health Connect permissions and reconnect behavior;
- downstream corporate-app workout import;
- duplicate/overlap handling;
- release installation from AppGallery-style APK flow.

## UI rules to preserve

- August palette: Navy, Lime, Tangerine, Purple, Inter Variable.
- System light and dark themes both matter; do not validate only dark mode.
- Lime is reserved for primary action emphasis.
- Normal cards are flat/subtly outlined; hero depth remains restrained.
- Buttons are pill-shaped with comfortable touch targets.
- Navbar hierarchy comes from width/role, not inconsistent heights.
- Dashboard-card visibility/order is controlled only by `DashboardCardLayoutPrefs`.
- Settings remains intentionally minimal.

## Mandatory engineering guardrails

- Think/write code, comments, identifiers and commits in English.
- Make surgical changes; do not refactor unrelated working code.
- Before deleting code, search all call sites/contracts/resources. Never infer dead code from a lexical scan alone.
- Keep `values/strings.xml` and `values-ru/strings.xml` key parity in the same patch.
- XML comments must not contain literal `--`.
- Patch scripts must be idempotent, fail-closed, and use small symptom-based anchors.
- Codespaces verification: patch checks + `git diff --check` + `git status --short` only.
- GitHub Actions is the only compile/lint/release authority.
- If CI fails, fix the underlying issue; do not weaken lint, metadata checks, signing checks, or release verification.
- Do not include noisy `git diff -- ...` commands in delivery instructions.
- Remove one-shot patch scripts after successful application.
- Current source plus a green GitHub Actions run overrides stale historical documentation.

## Next-session starting point

There is no known migration blocker left from this session. Start from the current `main` branch and the latest successful GitHub Actions run.

If the corporate wellness app's sync failures recur after the 2026-09-10 payload reduction, capture the exact error time and a BitLut diagnostic log for the same window before making any further write-path change.

If the next task is UI-only, do not touch sync serialization. If it is sync-related, preserve the established Huawei-first permissions, stable IDs, overlap normalization, session-scoped metrics, and cache guards unless device evidence requires a change.
