# BitLut — Session Handoff

Current handoff date: 2026-09-11.

## 2026-09-11 lint/compiler cleanup sprint

- The API 36.1 / AGP 8.13.2 compatibility gate passes; the next GitHub Actions failure was lint-only: five `NonObservableLocale` errors in `FinalBitLutShell.kt`. All UI locale reads now observe `LocalConfiguration`, including number/date formatting helpers, so runtime locale changes recompose correctly instead of merely silencing lint.
- Explicit Kotlin compiler warnings from that run were cleaned surgically: AutoMirrored directional icons, Observer parameter naming, platform clipboard instead of deprecated Compose `LocalClipboardManager`, explicit `@param:ColorRes`, and removal of redundant deprecated Window system-bar color writes. `ComponentActivity.enableEdgeToEdge()` remains the single system-bar owner.
- Release CI is now staged as AAR compatibility -> lint -> build/sign. Lint reports upload with `if: always()`; a lint failure no longer wastes time assembling the APK before failing.
- No sync serialization, Huawei Health reads, Health Connect writes, permissions, workout mapping, August motion, or dashboard business logic changed in this cleanup.
- Codespaces remains static-check only. Do not run Gradle locally.

Read `CLAUDE.md`, `CONTEXT.md`, `design.md`, and this file before changing code. Current source plus a successful GitHub Actions release workflow is authoritative if historical notes conflict. Codespaces is static-check only; do not run local Gradle tasks.

## 2026-09-11 final UI sprint

- Bottom navigation keeps the established 64dp shared control height and 84dp Refresh width, but all three controls now have restrained tactile spring feedback: press depth, a very small tilt, compression, and one short release tremor. Motion tokens live in `AugustMotion`; static cards/content remain non-bouncy.
- The Today sync indicator no longer fades in from alpha 0. While syncing it renders immediately as a high-contrast August capsule (Tangerine spinner, semantic foreground, outlined Surface/NavySoft container) in both themes.
- `SyncViewModel` keeps UI-triggered sync state visible for at least 1.1s using elapsed realtime. This closes the fast-sync/lease-collision race where start/completion could be coalesced between Compose frames and the indicator never became perceptible.
- Sync wording is now `Sync in progress…` / `Идёт синхронизация…`.
- Codespaces verification policy changed after repeated memory pressure/terminal termination: no local Gradle, lint, dependency-resolution, or build tasks. Use patch structural checks + `git diff --check`; GitHub Actions is the compile/lint/release authority.

## 2026-09-11 current source-of-truth update

The temporary same-day Health Connect compatibility rollback is now superseded by a full, controlled Android 16 modernization. BitLut remains Huawei AppGallery/Huawei Health first. The first GitHub Actions AAR gate proved that Compose 1.12 / Core 1.19 / Lifecycle 2.11 already require API 37 and AGP 9.1+, so the production lane is intentionally capped at the newest stable AGP 8.13-compatible set: `compileSdk 36.1`, `targetSdk 36`, AGP `8.13.2`, Gradle `8.13`, Kotlin/Compose plugin `2.3.21`, AGConnect `1.9.6.300`, Health Connect `1.1.0`, Compose BOM `2026.06.01`, Core `1.18.0`, and Lifecycle `2.10.0`. JDK stays 17. All sync/GUI hardening from earlier on 2026-09-11 remains in force.


The 2026-09-11 Repomix snapshot supersedes older handoff wording. The previously fixed corporate-reader interoperability path is still preserved, but a new intermittent downstream import symptom appeared after late-August/early-September Google Health updates. Current evidence does **not** show a new Health Connect record schema requirement. Google Health 5.05 had a confirmed Health Connect permission/connection regression; Google Health 5.07 began rolling out on 2026-08-28 with a fix. Android's workout guidance updated 2026-09-08 also explicitly calls out overlapping sessions as a write-failure cause.

Current hardening in source:

### 2026-09-11 modernization boundary

The sprint intentionally stops at the newest stable classic Android Gradle/Kotlin lane: AGP `8.13.2` explicitly supports API 36.1 and Kotlin 2.3, while Kotlin `2.3.21` is the current bug-fix release for that compiler line. Do not move to AGP 9/Kotlin 2.4 as an incidental dependency bump: AGP 9 changes Android projects to built-in Kotlin and Huawei's current AGConnect Android guide does not establish compatibility with that migration. Treat a future AGP 9 move as a Huawei compatibility task, not routine maintenance.

The release workflow installs Android 16 QPR2 / API 36.1 explicitly and runs `lintRelease` before packaging. Codespaces does not run Gradle at all; only lightweight structural/static checks run before commit. GitHub Actions owns dependency/AAR validation, compile, lint, release packaging, signing, and final verification.

Huawei's current Android Health Service documentation still warns that device-side `DataController` calls may fail while the app is backgrounded or the screen is off. This is not treated as an Android 16 migration regression and this sprint does not convert the proven WorkManager pipeline into a foreground service without device evidence. The post-upgrade Huawei gate must explicitly cover foreground sync, screen-off/background behavior, periodic catch-up, and recovery after HMS/Huawei Health restarts.

- Production build baseline: `compileSdk 36.1`, `targetSdk 36`, AGP `8.13.2`, Gradle `8.13`, Kotlin/Compose plugin `2.3.21`, AGConnect `1.9.6.300`, Health Connect `1.1.0`, Compose BOM `2026.06.01`, Core `1.18.0`, Lifecycle `2.10.0`, JDK 17. `minSdk` remains 26. Huawei device-side Health Kit remains `6.11.0.303`.
- `writeActivitySessionsBatch()` preserves the interoperability-critical single bundle and stable IDs, but now normalizes overlapping source sessions by keeping the richer real source record rather than fabricating clipped timestamps.
- Huawei -> Health Connect export is gated by write permissions; dashboard reads are gated by read permissions. Revoking an unrelated read permission no longer blocks valid background export.
- WorkManager UI activity means `RUNNING` only. `ENQUEUED` is the normal idle state of periodic work and must never drive the Syncing indicator.
- Today header keeps a stable metadata row: source/freshness at rest; Tangerine spinner + high-contrast semantic text while syncing.
- Do not force clientRecordVersion churn, split the workout bundle into separate writes, spoof another app's DataOrigin, or change the load-bearing steps-before-activitySessions ordering.

If the corporate reader misses a newly synced workout on a device that has Google Health 5.07+, first verify the reader/Google Health Health Connect connection and Activity data-source priority, then inspect BitLut diagnostic logs for `Dropped overlapping workout` or `Workout bundle write failed`. Do not rewrite old workouts blindly.


## Product

BitLut is a local-first Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect -> compatible readers
```

Scope is activity/workout data only. No account/backend. Do not fabricate missing metrics. The only documented exception is the existing workout total-calorie estimate used when Huawei provides no workout calories; do not extend that exception to distance, steps, elevation, heart data, sleep, etc.

## Current top-priority goal: scaling

`docs/SCALING_ROADMAP.md` is the durable reference. Two separate tracks:

1. **Lift the Huawei Health Kit 100-user test-phase cap** via Huawei's "Applying for Verification" step -- individual account, no new scopes, ~15 working day review. This is the actual current goal; start here.
2. **Request `HEALTHKIT_CALORIES_READ`** -- a Basic-tier, individual-developer-reachable scope BitLut has never requested (its scope array is Step/Distance/Activity/ActivityRecord/HistoryWeek only). This would let real Huawei active-calorie data replace the `WorkoutCalorieEstimator` MET fallback wherever Huawei provides it; both call sites already prefer real data via `?:`, so no code restructuring is needed, only the scope addition + console request.

Do not pursue Advanced-tier scopes (sleep/heart rate/SpO2/stress) — permanently closed to individual developers regardless of app quality or review history; the only path is incorporating an enterprise entity with ≥CNY 5,000,000 paid-up capital, which is out of scope for this project.

## 2026-08-29 baseline

The app builds successfully after the workout interoperability hardening and follow-up build/lint repairs.

### Workout import and Health Connect

- Huawei activity IDs use `HuaweiWorkoutTypeMapper` as the single mapping source. Current Huawei IDs such as cycling `13`, strength training `79`, walking `90`, indoor cycling, treadmill, swimming, martial arts, rowing and other supported activities are normalized centrally.
- Non-workout Huawei states such as elevator, escalator, in-vehicle, sleep, still and tilting are filtered instead of becoming fake workouts.
- Live Huawei reads and Huawei archive import use the same mapper.
- Archive workouts preserve exercise type plus available distance, calories, steps and elevation.
- Workout distance comes from Huawei's per-activity `ActivityRecordReply.getSampleSet(record)` when available. Do not reconstruct session distance from coarse Health Connect daily/overlap aggregates.
- `readActivityRecordSummary()` sums steps/calories/elevation across ALL matching Huawei sample points for an activity, not just the first. Do not revert to `firstOrNull()` for these fields -- Huawei can and does split them across multiple points per activity (confirmed on-device: a real walk showed 2.5 km distance but only 250 steps before this fix, because distance already summed via its fallback path while steps took only the first point).
  - **2026-08-31 update: steps are still sometimes wrong after the sum fix** (real-device log showed a walking activity with `stepsTotalPointsMatched=0` -- Huawei's own `dataSummary` apparently emitted zero matching `steps.total` points for that activity, a different failure mode than the one the sum fix addressed). A raw-stream fallback (mirroring the distance fix's `getSampleSet(record)` approach) was considered and rejected: this file's own prior lesson already found raw `DT_CONTINUOUS_STEPS_DELTA` samples unreliable/absent for Huawei step totals during a daily read (see `readDailyStepTotals()`), so blindly reusing that approach for the per-activity case would repeat a category of fix already flagged unsafe, without real per-point evidence for this specific failure. Per-point diagnostic logging was added instead (type name + every field/value, matched or not, plus a final match-count summary) -- **do not attempt a structural fix here without a fresh real-device log showing what `dataSummary` actually contains for a failing activity.**
- **2026-08-31: workout metrics are now also written to Health Connect as session-scoped records, not just used for dashboard display.** `writeActivitySessionsBatch()` bundles `DistanceRecord`/`StepsRecord`/`ElevationGainedRecord` (plus a currently-always-null `ActiveCaloriesBurnedRecord`) into the same `insertRecords` call as the exercise session and its calorie total, scoped to the exact session interval -- gated by `sessionSubMetricsFor()`, which mirrors `workoutMetricDisplays()`'s per-type contract exactly (walk/run/treadmill get distance+steps; hiking adds elevation; biking gets distance+elevation, no steps; stationary biking gets distance only; swimming gets distance only; strength/weightlifting/HIIT/yoga/pilates get none of the three). This closes a real interoperability gap: previously, any third-party Health Connect reader querying a workout's own distance/steps/elevation (Health Connect has no explicit session<->metric link; readers query by time-range overlap) found only the separate, coarser background daily aggregate, not anything scoped to the workout itself. **Write ordering in `writeSnapshot()` is load-bearing**: `writeStepsBatch` (which can delete-then-reinsert a whole day's `StepsRecord`s during "complete daily summation" reconciliation) must keep running before `writeActivitySessionsBatch`, or that reconciliation will silently wipe the new workout-scoped `StepsRecord`s. This is currently true only because these are sequential suspend calls in one list literal; if that list is ever parallelized, this ordering must be preserved explicitly.
- BitLut writes workout sessions as `ACTIVELY_RECORDED`, because the original workout was actively started on the watch/phone even though BitLut relays it later.
- `bitlutRecordingDevice` uses manufacturer `Huawei`.
- Exercise session + related total-calorie record are inserted as one workout bundle.
- `clientRecordId` remains deterministic and `clientRecordVersion` is stable for unchanged workouts; do not bump versions on every sync.
- Health Connect `DataOrigin` remains `com.openhealth.sync`. Do not attempt to spoof Huawei/Google source identity; Health Connect owns writer attribution.

### Dashboard workout metrics

Display is exercise-type aware and only shows meaningful available values:

- walking/running/treadmill: Duration, Distance, Pace, Steps; measured Calories may fill an available fourth slot when another metric is absent.
- hiking: Duration, Distance, Elevation, measured Calories/Steps as available.
- outdoor cycling: Duration, Distance, Avg speed, measured Calories/Elevation as available.
- stationary cycling: Duration, measured Calories, then real distance/speed only if present.
- swimming: Duration, Distance, Pace / 100 m, measured Calories.
- strength/weightlifting: Duration + Calories; measured first, documented estimator only as fallback.
- HIIT/yoga/pilates: Duration + measured Calories.
- other types: Duration plus only real available Calories/Distance/Elevation/Steps.

Never show `0` as a substitute for a missing workout metric; omit the slot or show the established no-data UI where applicable.

**2026-08-31 note:** if a walking/running activity's Steps slot is missing despite the workout clearly having steps, this is very likely the still-open Huawei `dataSummary` steps issue noted above under "Workout import and Health Connect" -- not a display-layer bug. Check the diagnostic log line `Huawei activity summary steps diagnostic` for that activity's `stepsTotalPointsMatched` before assuming the display logic is at fault.

### Previous corporate wellness app issue — resolved 2026-08-31/09-01

Real-device evidence now confirms the corporate app reliably imports and accepts BitLut-synced workouts. The fix was the 2026-08-31 session-scoped Health Connect sub-metric write (`writeActivitySessionsBatch()` now bundles `DistanceRecord`/`StepsRecord`/`ElevationGainedRecord` into the workout's own time window instead of leaving the reader to fall back on the separate, coarser background daily aggregate). Full technical detail lives in `sync.md` section 4.6.

The original leading explanation (source-origin allowlisting/trust on the reader side) is still believed to be part of why earlier metadata-only attempts didn't work, but is no longer an open question requiring further code changes: recording method, calorie attachment, device manufacturer, Health Connect data-source settings deep link, accurate session distance, corrected exercise types, and stable record version were all tried and individually insufficient; the session-scoped sub-metrics were the piece that closed the gap.

That specific failure mode remains fixed. The newer 2026-09-11 intermittent downstream symptom is tracked separately in the current-source update above.

### Dashboard cache and midnight rollover

- `DashboardViewModel.buildInitialState()` zeroes daily-total fields (steps/distance/calories/workout minutes/active hours/elevation/floors) when the on-disk `DashboardSnapshotCache` predates today -- a new calendar day has genuinely started with zero activity so far, and showing yesterday's numbers as today's is misleading. `recentWorkouts` is untouched by this: a workout from yesterday is still real history.
- **2026-08-31: `refreshFromCache()` now applies the identical check** (extracted into a shared `zeroedDailyTotals()` helper). It previously applied the cached snapshot unconditionally, which was safe when called right after a sync's own completion (the cache is fresh by then) but not when called from `SyncOrchestrator`'s lease-collision retry timer (8s/12s after the *deferred* sync's own "already running" result -- independent of when the *winning* sync's cache write actually lands). A real device log showed the exact race: right after midnight, that retry could read the still-stale, pre-sync on-disk cache and re-apply yesterday's real numbers over the already-correctly-zeroed dashboard, for the few seconds until a later refresh corrected it again. Do not reintroduce an unconditional cache apply on any new cache-consuming code path -- always go through (or replicate) `zeroedDailyTotals()`'s guard.

## UI decisions

- Palette remains August v3: Navy, Lime, Tangerine, Purple, Inter Variable, system light/dark theme.
- Product reference is now a quieter 2026 content-first UI similar in spirit to ChatGPT: flatter surfaces, stronger spacing/hierarchy, rounded grouped controls, one obvious primary action, restrained motion.
- Non-clickable cards must not animate like buttons.
- Normal cards are flat with a subtle outline; hero can retain restrained depth.
- Buttons are pill-shaped with minimum 48 dp height; Lime is reserved for the primary action.
- Settings keeps the minimal data-source card and one merged action card. `Sync now` is the primary action; connect/import/refresh/Health Connect settings are secondary.
- Dashboard-card visibility/order is handled only by `DashboardCardLayoutPrefs` from the pencil editor.
- Settings exposes only the steps goal.
- Bottom navbar: all controls (Today, Refresh, Settings) share one common height (64dp); Refresh reads as primary via width (84dp), never height. Since the final 2026-09-11 UI sprint, controls also use shared August spring tokens for subtle compression, 2dp press depth, tiny asymmetric tilt, and one short under-damped release tremor. Keep the amplitude restrained and never apply this bounce to static cards/content.
- Today header shows `Sync in progress…` / `Идёт синхронизация…` while `SyncUiState.isSyncing` is true. Keep the fixed metadata-row height, but do not reintroduce the old alpha-from-zero transition: the active state renders immediately as a high-contrast August capsule. UI-triggered syncs have a 1.1s minimum visual dwell in `SyncViewModel`, while `isSyncing` remains the computed OR of UI-triggered and actually-RUNNING background work.
- **2026-08-31: "Syncing..." indicator visibility now also depends on real background sync activity, not just UI-triggered sync state.** `SyncViewModel.markSyncStarted()`/`markSyncCompleted()` alone were insufficient: they only fire from `MainActivity`'s two UI-triggered sync call sites, so a periodic background `SyncWorker` run that wins the sync-run lease race (confirmed on a real device log: the UI-triggered attempt's own started->completed pair collapsed to under a second while the periodic worker did the real ~10-second sync) never showed the indicator at all. `HuaweiConfig.SYNC_ACTIVITY_TAG` is now applied only to `SyncWorker`'s two enqueue sites (not `EveningReminderWorker`, which shares the older, broader `SYNC_WORKER_TAG` and is unrelated to health-data syncing) and observed via `WorkManager.getWorkInfosByTagLiveData()` in `MainActivity`, feeding `SyncViewModel.setBackgroundSyncActive()`.
- Settings screen ends with a small wood-carved-style signature (`EngravedSignature()`), built from Inter Black + letter-spacing + a two-layer engraved-shadow effect -- no new font asset was added (see the GMS-free/Downloadable-Fonts constraint above).

## Removed dead layers

- CSV export UI had already been removed; the now-unreachable callback chain, `CsvExporter`, manifest `FileProvider`, and `file_paths.xml` are removed too.
- `WidgetVisibilityPrefs` / `DashboardWidget` legacy visibility layer is removed; it had no remaining dashboard consumer.
- Distance, active-minutes and calories goal preference/state setters are removed; only steps goal remains.
- Dead `AchievementSummary` state/calculation is removed.
- `SoftCard` no longer carries unused `accent`, `tintWithAccent`, or `pressLift` compatibility parameters.
- One-off patch/hotfix/verify scripts are delivery artifacts and should not remain in the repository after a successful patch run.

## Settings changes already made before this session

1. `patch_walking_three_slots_v1.py`: walking card had been trimmed to three slots at that point. This was later superseded by the current exercise-type-aware metric contract above.
2. `patch_settings_minimalism_v1.py`: simplified Settings; removed workout-filter UI only. `WorkoutFilterPrefs` remains active in sync-time filtering.
3. `patch_hc_datasources_and_device_manufacturer_v2.py`: added Health Connect settings deep link and Huawei manufacturer metadata. v1 partially failed and is historical only.
4. `patch_workout_distance_source_fix_v1.py`: fixed the real ~40x workout-distance error by reading Huawei per-session samples and giving them priority over aggregate reconstruction.
5. `patch_navbar_resize_v1.py` / `patch_sync_status_indicator_v1.py` / `patch_navbar_sync_status_docs_v1.py`: navbar resize + animated background-sync status line (full detail in `CHANGELOG.md` 2026-08-29 (b)).
6. `patch_huawei_workout_summary_sum_v1.py` / `patch_settings_engraved_signature_v1.py` / `patch_sync_status_wording_and_docs_v1.py`: Huawei summary-metric sum fix, Settings signature, sync-status wording tightening (full detail in `CHANGELOG.md` 2026-08-29 (c)).
7. `patch_navbar_rebuild_sync_status_steps_diag_v1.py`: navbar rebuild (shared height, width-based hierarchy), "Syncing..." alpha-only fixed-height fix, steps-undercount diagnostic logging.
8. `patch_workout_session_scoped_metrics_v1.py`: session-scoped Distance/Steps/Elevation/ActiveCalories Health Connect records for every workout, gated by exercise type.
9. `patch_sync_activity_signal_and_midnight_cache_v1.py`: `SYNC_ACTIVITY_TAG` background-sync-activity signal for the "Syncing..." indicator; `refreshFromCache()` midnight-staleness guard.

(Full detail for 7-9 in `CHANGELOG.md` 2026-08-31.)

## What failed during the 2026-08-29 hardening and how to avoid it

- `v1`: UI helpers called `stringResource()` from non-`@Composable` local functions. Rule: Compose resource APIs stay in composable scope; pure formatting helpers receive already-resolved strings or remain pure Kotlin.
- `v3`: cleanup/generator edits left duplicate opening declarations in `AppLogger.d()` and `GoogleHealthManager.readStepsToday()`. Kotlin then parsed following members inside the wrong function and produced dozens of misleading unresolved references. Rule: run structural checks and inspect the first compiler errors before treating cascades as independent bugs.
- The same cleanup removed `cleanWorkoutCardTitle()` and `formatWorkoutDateTime()` even though live UI call sites remained. Rule: never call code dead from a private-name/lexical scan alone; search all call sites before deletion.
- After compile was repaired, lint still found Glance `RestrictedApi` usage plus two missing Russian strings. Rule: compile success is not sprint success; `lintDebug` is mandatory, restricted APIs must be replaced rather than suppressed, and EN/RU resource parity is checked before Gradle.

## Mandatory engineering guardrails

- Never infer dead code from a lexical scan alone. Before deletion, search all call sites/contracts/resources and then compile.
- Do not delete a helper because it looks unused in one file; `v3` caused cascading build errors by removing still-live declarations.
- When touching `values/strings.xml`, keep `values-ru/strings.xml` key parity in the same patch. Run XML parsing plus locale-key parity checks before Gradle.
- XML comments must never contain literal `--`.
- Patch scripts must be idempotent/fail-closed and use small symptom-based anchors, not one huge fragile multiline anchor.
- Codespaces gate: patch structural verification + XML/resource parity + `git diff --check` only. Do not run Gradle locally. GitHub Actions must pass compile + lint + release packaging/signing before release.
- Do not suppress lint, create a lint baseline, or weaken checks merely to get green output.
- If verification fails, do not commit/push. Show only compact compiler/lint errors, not full Gradle stack traces.
- Do not include `git diff -- ...` in delivery commands. It creates console noise and is explicitly unwanted.
- Preserve working sync/data behavior during UI work; UI refactors must not touch workout serialization unless required by evidence.
- Repo root is kept clean between sessions: delivered/verified patch scripts and `.bitlut_patch_backup/` are deleted once their changes are committed. A patch script or backup file sitting in the repo root is stale debris, not a sign of pending work -- check `git log`/`CHANGELOG.md` for what has actually landed.

## Verification split

Codespaces: no Gradle. Run only the patch's built-in static verification, `git diff --check`, and `git status --short`.

GitHub Actions: clean dependency resolution, compile, lint, release APK packaging, signing, and artifact verification. This is the authoritative build gate.

<!-- BITLUT_ANDROIDX_COMPAT_2026_09_11 -->
