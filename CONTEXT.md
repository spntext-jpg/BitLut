# BitLut — Current Context

Updated: 2026-08-31

BitLut is a local-first Kotlin/Jetpack Compose Android bridge from HUAWEI Health to Android Health Connect.

## Current product scope

Activity/workout data only. No backend/account. Real data first. The only approved estimate is workout `TotalCaloriesBurnedRecord` fallback documented in project docs.

## Current architecture

- Huawei live source: `HuaweiHealthManager`
- Huawei archive source: `HuaweiExportParser`
- Shared workout mapping: `HuaweiWorkoutTypeMapper`
- Health Connect writer/reader: `GoogleHealthManager`
- Sync orchestration: `SyncWorker` / `SyncOrchestrator`
- Dashboard: `DashboardViewModel` + `FinalBitLutShell`
- Card order/visibility: `DashboardCardLayoutPrefs`
- Goal preferences: steps only (`GoalPrefs`)

## Workout interoperability baseline

- Current Huawei IDs mapped centrally.
- Non-workout activity states filtered.
- Per-session Huawei distance has priority; steps/calories/elevation summary metrics are summed across all matching Huawei sample points, not just the first. Steps can still be missing for some activities (Huawei-side `dataSummary` gap under investigation; diagnostic logging in place, no fix yet -- see `SESSION_HANDOFF.md`).
- Workouts written `ACTIVELY_RECORDED` with Huawei device manufacturer.
- Session + related calories written as a bundle; distance/steps/elevation (when the exercise type plausibly has them) are also written as their own Health Connect records scoped to the exact session interval, so third-party readers see real per-workout metrics rather than only a bare session plus an unrelated background aggregate.
- Stable deterministic client record identity/version for unchanged workouts.
- Type-aware dashboard metrics.
- Corporate wellness app still ignores BitLut-origin workouts; source-origin allowlisting is the leading external explanation. BitLut cannot spoof Health Connect `DataOrigin`.

## UI baseline

August colors remain unchanged. UI direction is quieter/content-first: flat outlined cards, restrained hero depth, pill buttons, 48 dp targets, restrained tween motion, one primary Settings action, no fake press animation on non-clickable cards. Bottom navbar: all controls share one common height (64dp); Refresh reads as primary via width (84dp pill), not height. Today header shows a fixed-height, alpha-only fade "Syncing..." line while `SyncUiState.isSyncing` (now `isUiTriggeredSyncing || isBackgroundSyncActive`) is true. Settings ends with a small engraved-style signature (no new font asset).

## Dashboard cache

`DashboardSnapshotCache` reads (both `buildInitialState()` on cold launch and `refreshFromCache()` after any sync completion or retry) zero daily-total fields when the cached snapshot predates today's calendar date, via a shared `zeroedDailyTotals()` helper. Recent-workout history is never zeroed by this.

## Do not regress

- Do not reintroduce aggregate workout distance reconstruction.
- Do not reintroduce stale Huawei activity ID tables.
- Do not change workout recording method back to automatic/unknown.
- Do not restore CSV/legacy widget-visibility/dead goal plumbing without a product requirement.
- Do not suppress lint or commit a failed build.
- Maintain EN/RU resource key parity.
- Never output `git diff -- ...` in delivery instructions.
- Do not resize navbar controls by height for visual hierarchy; use width. All navbar controls share one height.
- `writeSnapshot()`'s write order (steps before activitySessions) is load-bearing: the daily steps reconciliation's delete-then-reinsert must fully complete before workout-scoped `StepsRecord`s are written, or it silently deletes them. Preserve this ordering explicitly if these writes are ever parallelized.
- Do not apply a cached dashboard snapshot unconditionally on any code path; always guard against the cache predating today (see `zeroedDailyTotals()`).
