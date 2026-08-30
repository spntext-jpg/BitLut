# BitLut — Session Handoff

Current handoff date: 2026-08-29.

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

### Corporate wellness app investigation

Still unresolved and likely external. Real-device evidence shows BitLut workouts arrive correctly in Health Connect but the corporate app does not count them, while Huawei -> Apple Health workouts are accepted.

Leading explanation: the corporate reader uses source-origin allowlisting/trust. Apple Health receives records from Huawei's first-party iOS app (`HKSource`), while Android Health Connect records written by BitLut necessarily have `Metadata.dataOrigin.packageName = com.openhealth.sync`. BitLut cannot legally/technically impersonate another package's `DataOrigin`.

Already tried and insufficient on their own: recording method, calorie attachment, device manufacturer, Health Connect data-source settings deep link, accurate session distance, corrected exercise types, stable record version and bundled workout writes.

Next useful test is on the corporate app side: confirm whether it accepts third-party Health Connect writer origins. Do not keep changing BitLut metadata blindly without new evidence.

## UI decisions

- Palette remains August v3: Navy, Lime, Tangerine, Purple, Inter Variable, system light/dark theme.
- Product reference is now a quieter 2026 content-first UI similar in spirit to ChatGPT: flatter surfaces, stronger spacing/hierarchy, rounded grouped controls, one obvious primary action, restrained motion.
- Non-clickable cards must not animate like buttons.
- Normal cards are flat with a subtle outline; hero can retain restrained depth.
- Buttons are pill-shaped with minimum 48 dp height; Lime is reserved for the primary action.
- Settings keeps the minimal data-source card and one merged action card. `Sync now` is the primary action; connect/import/refresh/Health Connect settings are secondary.
- Dashboard-card visibility/order is handled only by `DashboardCardLayoutPrefs` from the pencil editor.
- Settings exposes only the steps goal.
- Bottom navbar (2026-08-29): Today/Settings destination buttons are ~20% smaller than the center Refresh button (button height 46dp vs Refresh 72dp; destination icon 17/16dp vs Refresh icon 34dp), matching the exact ratios documented in `CHANGELOG.md`. The two destination buttons remain identical to each other; do not resize one without the other.
- Today header shows an animated "Syncing..." status line under the last-sync trailing text while `SyncUiState.isSyncing` is true (fades in/out via `AnimatedVisibility`, not a snap toggle). Driven entirely by existing `SyncViewModel.markSyncStarted()`/`markSyncCompleted()` state; no new sync logic was added for this. Wording tightened 2026-08-29 (c) to "Syncing..."/"Синхронизация...".
- Huawei per-activity summary aggregation (2026-08-29 (c)): `readActivityRecordSummary()` in `HuaweiHealthManager.kt` sums steps/calories/elevation across ALL matching sample points for an activity, not just the first. Do not revert to `firstOrNull()` for these fields -- Huawei can and does split them across multiple points per activity (confirmed on-device: a real walk showed 2.5 km distance but only 250 steps before this fix).

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

## Final verification command used by delivery scripts

Resource-constrained Codespaces settings remain intentional: one Gradle worker, no daemon, no file watcher, 1 GB heap, Kotlin compiler in-process.
