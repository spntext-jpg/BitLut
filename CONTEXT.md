# BitLut — Current Context

Updated: 2026-09-16

BitLut is a local-first Kotlin/Jetpack Compose Android bridge from HUAWEI Health to Android Health Connect.

`sync.md` is the durable technical reference for the full sync pipeline (why it's built the way it is); this file stays the short current-state summary. `docs/SCALING_ROADMAP.md` is the durable reference for lifting the 100-user Huawei test-phase cap and any reachable scope expansion -- this is the current top-priority goal.

## Current product scope

Activity/workout data only. No backend/account. Real data first. The only approved estimate is a workout total-calories fallback used for BitLut's own dashboard display only (not written to Health Connect since 2026-09-10), documented in project docs.

## Current architecture

## Production build baseline (2026-09-11)

- Huawei AppGallery / Huawei Health remain first-class release constraints.
- Android: `compileSdk 36.1`, `targetSdk 36`, `minSdk 26`.
- Build: AGP `8.13.2`, Gradle `8.13`, Kotlin + Compose compiler plugin `2.3.21`, JDK 17.
- Huawei: AGConnect plugin `1.9.6.300`; device-side Health Kit artifact remains the proven `com.huawei.hms:health:6.11.0.303`.
- AndroidX: stable Health Connect `1.1.0`; Compose BOM `2026.06.01` (Compose 1.11.4 line); Core `1.18.0`; Activity `1.13.0`; Lifecycle `2.10.0`; AppCompat `1.8.0`; Glance `1.2.0`; WorkManager `2.11.2`. This is the newest stable dependency lane retained below the API 37 / AGP 9.1 boundary exposed by the first GitHub Actions AAR gate.
- No preview dependencies. AGP 9/Kotlin 2.4 are deferred until Huawei publishes or BitLut proves AGConnect compatibility with AGP 9's built-in Kotlin model.

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
- Distance/Steps (when the exercise type plausibly has them) are written as their own Health Connect records scoped to the exact session interval, so third-party readers see real per-workout metrics rather than only a bare session plus an unrelated background aggregate. Elevation and total-calories were removed from this bundle 2026-09-10.
- Stable deterministic client record identity/version for unchanged workouts.
- Type-aware dashboard metrics.
- The 2026-08-31 corporate-reader failure mode was fixed by session-scoped workout sub-metrics. A separate downstream symptom ("binder died" followed by a 24-hour sync-limit pause) appeared around the Google Health 5.05/5.07 update cycle. The 2026-09-16 recovery removes the obsolete TotalCalories write permission and fixes permission-cache/workout-version churn. A second 2026-09-16 fix removes a stronger code-level churn source: the 7-day daily-Steps reconcile was deleting all BitLut Steps -- including the new workout-scoped Steps -- every 30 minutes and recreating them, generating repeated downstream deletions/upsertions. Daily totals now use stable versions with no range delete, and Health Connect binder failures defer to WorkManager backoff instead of rapid full-pipeline retries. Stable Health Connect remains `1.1.0`; workout serialization metadata is unchanged.

## UI baseline

August colors remain unchanged. UI direction is quieter/content-first: flat outlined cards, restrained hero depth, pill buttons, 48 dp targets, restrained tween motion, one primary Settings action, no fake press animation on non-clickable cards. Bottom navbar: all controls share one common height (64dp); Refresh reads as primary via width (84dp pill), not height. Today header uses one fixed-height metadata row: source/freshness at rest and a Tangerine spinner + semantic high-contrast "Syncing..." label while `SyncUiState.isSyncing` (`isUiTriggeredSyncing || isBackgroundSyncActive`) is true. Background activity means WorkManager `RUNNING` only; periodic `ENQUEUED` work is idle scheduling. Settings ends with a small engraved-style signature (no new font asset).

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
- Health Connect writes stay sequential to bound provider IPC pressure, but daily Steps must never use a time-range delete: the former 7-day delete also removed valid workout-scoped Steps and recreated them every 30 minutes, producing downstream change-log churn.
- Do not apply a cached dashboard snapshot unconditionally on any code path; always guard against the cache predating today (see `zeroedDailyTotals()`).
