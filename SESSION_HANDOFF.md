# BitLut — Session Handoff

Current handoff date: 2026-08-31.

Read `CLAUDE.md`, `CONTEXT.md`, `design.md`, and this file before changing code. Current source plus a successful `assembleDebug` + `lintDebug` is authoritative if historical notes conflict.

## Product

BitLut is a local-first Android bridge:

```text
HUAWEI Health -> BitLut -> Android Health Connect -> compatible readers
```

Scope is activity/workout data only. No account/backend. Do not fabricate missing metrics. The only documented exception is the existing workout total-calorie estimate used when Huawei provides no workout calories; do not extend that exception to distance, steps, elevation, heart data, sleep, etc.

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

### Corporate wellness app investigation

Still unresolved and likely external. Real-device evidence shows BitLut workouts arrive correctly in Health Connect but the corporate app does not count them, while Huawei -> Apple Health workouts are accepted.

Leading explanation: the corporate reader uses source-origin allowlisting/trust. Apple Health receives records from Huawei's first-party iOS app (`HKSource`), while Android Health Connect records written by BitLut necessarily have `Metadata.dataOrigin.packageName = com.openhealth.sync`. BitLut cannot legally/technically impersonate another package's `DataOrigin`.

Already tried and insufficient on their own: recording method, calorie attachment, device manufacturer, Health Connect data-source settings deep link, accurate session distance, corrected exercise types, stable record version and bundled workout writes.

Next useful test is on the corporate app side: confirm whether it accepts third-party Health Connect writer origins. Do not keep changing BitLut metadata blindly without new evidence.

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
- Bottom navbar: all controls (Today, Refresh, Settings) share one common height (64dp, was 46/72dp mismatched). Refresh reads as the primary action via width (84dp pill) instead of height -- the 2026-08-29 (b) height-based resize clipped the Today/Settings labels (confirmed real-device report) because a `Row.weight(1f)` child's height doesn't control its relative visual prominence, only width does. Both destination buttons remain identical to each other; do not resize one without the other. Do not resize navbar controls by height again for visual hierarchy -- use width.
- Today header shows an animated "Syncing..." / "Синхронизация..." status line under the last-sync trailing text while `SyncUiState.isSyncing` is true. The line's container is always present at a fixed reserved height; only its alpha animates (`graphicsLayer`), never `AnimatedVisibility`'s presence/layout toggle -- the latter collapsed the line's height to zero on exit and yanked the subtitle text upward (confirmed real-device report). `isSyncing` itself is now a computed property (`isUiTriggeredSyncing || isBackgroundSyncActive`), not a single stored flag -- see "Sync activity signal" below for why.
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
- Verification gate: `:app:assembleDebug` AND `:app:lintDebug`. A compile-only pass is not enough.
- Do not suppress lint, create a lint baseline, or weaken checks merely to get green output.
- If verification fails, do not commit/push. Show only compact compiler/lint errors, not full Gradle stack traces.
- Do not include `git diff -- ...` in delivery commands. It creates console noise and is explicitly unwanted.
- Preserve working sync/data behavior during UI work; UI refactors must not touch workout serialization unless required by evidence.
- Repo root is kept clean between sessions: delivered/verified patch scripts and `.bitlut_patch_backup/` are deleted once their changes are committed. A patch script or backup file sitting in the repo root is stale debris, not a sign of pending work -- check `git log`/`CHANGELOG.md` for what has actually landed.

## Final verification command used by delivery scripts

Resource-constrained Codespaces settings remain intentional: one Gradle worker, no daemon, no file watcher, 1 GB heap, Kotlin compiler in-process.
