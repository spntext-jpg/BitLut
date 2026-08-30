# BitLut — Current Context

Updated: 2026-08-29

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
- Per-session Huawei distance has priority.
- Workouts written `ACTIVELY_RECORDED` with Huawei device manufacturer.
- Session + related calories written as a bundle.
- Stable deterministic client record identity/version for unchanged workouts.
- Type-aware dashboard metrics.
- Corporate wellness app still ignores BitLut-origin workouts; source-origin allowlisting is the leading external explanation. BitLut cannot spoof Health Connect `DataOrigin`.

## UI baseline

August colors remain unchanged. UI direction is quieter/content-first: flat outlined cards, restrained hero depth, pill buttons, 48 dp targets, restrained tween motion, one primary Settings action, no fake press animation on non-clickable cards. Bottom navbar: destination buttons ~20% smaller than the center Refresh button (46dp vs 72dp), symmetric between Today/Settings. Today header shows a fade in/out "Updating..." line while a sync is in progress.

## Do not regress

- Do not reintroduce aggregate workout distance reconstruction.
- Do not reintroduce stale Huawei activity ID tables.
- Do not change workout recording method back to automatic/unknown.
- Do not restore CSV/legacy widget-visibility/dead goal plumbing without a product requirement.
- Do not suppress lint or commit a failed build.
- Maintain EN/RU resource key parity.
- Never output `git diff -- ...` in delivery instructions.
