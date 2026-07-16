# CLAUDE.md

Read this first, every session, before exploring the codebase. It exists
specifically to save tokens: everything below was learned the hard way
across many previous sessions (several of them debugging real production
regressions from device logs), and re-deriving it by reading source from
scratch is wasted effort. Update this file whenever status changes
materially -- it is meant to stay current, not to be a historical record
(see CHANGELOG.md for history).

## What BitLut is

Free, open-source Android app (Kotlin + Jetpack Compose), single individual
developer, published on HUAWEI AppGallery. One job: read activity data from
HUAWEI Health (via HUAWEI Health Kit) and write it into Google Health
Connect, so it becomes usable by any other Health Connect-compatible app on
the same device. No ads, no data selling, no server component -- everything
happens on-device.

## Current status

- **HUAWEI Health Kit scope approval: PENDING.** Real device logs show
  `localHuaweiAuthorized=false` and error `50005` (HUAWEI_SCOPE_UNAUTHORIZED)
  on every sync attempt. The sync pipeline is fully built, tested, and
  behaves correctly in this state (graceful no-op, no crashes, no false
  data). No code changes are needed once HUAWEI approves the scope -- only
  check then whether in-app HUAWEI re-authorization is also required.
- **Requested/expected HUAWEI scope** (activity-only tier, individual
  developer): `HEALTHKIT_STEP_READ`, `HEALTHKIT_DISTANCE_READ`,
  `HEALTHKIT_ACTIVITY_READ`, `HEALTHKIT_ACTIVITY_RECORD_READ`,
  `HEALTHKIT_HISTORYDATA_OPEN_WEEK`. Read-only from HUAWEI; BitLut never
  writes back to HUAWEI Health.
- **Sleep / heart-rate / SpO2 / stress are intentionally absent everywhere**
  -- not requested from HUAWEI, not read/written to Health Connect, no UI
  for them. HUAWEI's advanced data tier is not available to individual
  developers at all (confirmed from HUAWEI's own docs), regardless of
  application quality -- this is a platform policy, not a fixable bug. If
  asked to add these, the honest answer is "would require registering as a
  HUAWEI enterprise developer first."
- **Screens: exactly 2** -- Today (Summary) and Settings. The History screen
  was removed from the bottom nav (its composables/logic are left in the
  codebase, unreachable, not deleted -- see Conventions below).
- **Today screen widgets (fixed set, not user-configurable):** steps today,
  workout time today, personal records, current streak, last imported
  workout. The old widget-visibility toggle feature was removed entirely.

## Architecture map

| File | Role |
|---|---|
| `MainActivity.kt` | Activity lifecycle. `onResume()` (not `onCreate()`) triggers sync + dashboard refresh on every foreground return -- fires once on cold launch too, so nothing needs to also live in `onCreate()`. |
| `di/AppContainer.kt` | Process-wide singleton DI container (GoogleHealthManager, HuaweiHealthManager, SyncOrchestrator, SyncRunLease, AchievementsStore, GoalPrefs, etc.). Everything shares these single instances -- no per-call fresh instances. |
| `domain/SyncOrchestrator.kt` | The UI-safe entry point for triggering a sync. Debounces repeat triggers within 5s. MainActivity and Settings call this, never WorkManager directly. |
| `data/worker/SyncWorker.kt` | The actual background sync job (`CoroutineWorker`). Per-dependency circuit breakers, acquires `SyncRunLease` before doing real work, retries with backoff. |
| `data/worker/SyncReliability.kt` | `SyncCircuitBreaker`, `SyncWindowPlanner`, `SyncRunLease`, `SyncRetryPolicy`. |
| `data/worker/BackgroundSyncScheduler.kt` | WorkManager scheduling. `UNIQUE_PERIODIC_SYNC` (every 30 min) and `UNIQUE_SYNC_NOW` (manual/launch-triggered) are **different** unique-work names -- WorkManager does not serialize them against each other, which is exactly why `SyncRunLease` exists at the app level. |
| `data/HuaweiHealthManager.kt` | Reads from HUAWEI Health Kit. Type-safe dedup (an `Any?`/`UNCHECKED_CAST` bug here was fixed long ago -- watch for regressions if touching this). |
| `data/GoogleHealthManager.kt` | Reads/writes Health Connect. `readDashboardSnapshot()` reads today's steps/distance/calories via `readRecords()` + manual sum, **not** `aggregate()` (see Gotcha 1). Coalesces concurrent permission checks behind a mutex + 3s cache (see Gotcha 6). |
| `ui/DashboardViewModel.kt` | `load()` drives the Today screen's state. Deliberately trimmed (2026-07-10) to only compute fields actually rendered somewhere reachable (see Gotcha 4). |
| `ui/screens/FinalBitLutShell.kt` | All UI lives in one file: `SummaryScreen`, `SettingsScreen`, and every card/widget composable (`PersonalRecordsCard`, `StreakCard`, `LastWorkoutCard`, `MinimalMetricCard`, `SettingsConnectionCard`, etc.). `HistoryScreen`/`WorkoutTypeCard`/`DashboardWidgetGrid`/`WeeklyComparisonCard` are defined but intentionally unused (dormant, see Conventions). |
| `ui/components/GlassNavigation.kt` | Bottom nav bar: Today tab, centered larger warm-orange `Glass20RefreshButton`, Settings tab. |
| `config/HealthPermissionPolicy.kt` | The authoritative Health Connect permission list. Activity-only, with an explicit in-code comment documenting that this is intentional, not incomplete. |
| `config/WidgetVisibilityPrefs.kt` | `DashboardWidget` enum + prefs -- the toggle *feature* was removed from Settings UI, but this underlying plumbing is left in place, currently unused from the UI. |
| `util/AppLogger.kt` | In-app diagnostic log. Viewable via a hidden `LogViewerScreen` (secret-tap trigger from the nav). **Use this for real device debugging** -- several real regressions in this project were only correctly diagnosed from an actual device log, not from reading source alone. |

## Hard-won gotchas (do not rediscover these the expensive way)

1. **`HealthConnectClient.aggregate()` is backed by a provider-side cache, not a live query.** It is only *eventually* consistent with recently-inserted records -- confirmed as the root cause of "sync only shows fresh data if I open Google Fit first, then reopen BitLut." Fix already applied: read raw records via `readRecords()` and sum in-app instead (this was already the pattern in `readWorkoutMinutesToday()`/`readActiveHoursToday()`, which never showed this symptom -- that consistency was itself corroborating evidence).

2. **`CancellationException` must always be re-thrown before a generic `catch (e: Exception)`** around any suspend call, or routine coroutine cancellation (e.g. `DashboardViewModel.load()` cancelling its own superseded previous call) gets logged as a fake error and can incorrectly stomp state (`isLoading=false` on a job that was only ever superseded, not failed). Every suspend-wrapping try/catch in this codebase should have this guard -- check any new one you add.

3. **A `SUCCEEDED` WorkInfo does not necessarily mean a sync did real work.** Check `info.outputData.getString("reason")` -- `"sync_already_running"` means a different worker already held `SyncRunLease` and this request was a no-op; refreshing the dashboard immediately on that signal reads stale data. `SyncOrchestrator` already handles this with deferred follow-up refreshes.

4. **`DashboardViewModel.load()` must stay cheap.** It used to eagerly compute `stepsBars` (one Health Connect call **per day** in range), `workoutSummaries`, and `weekComparison` for screens/cards that no longer exist in the UI -- roughly 16 Health Connect calls per single `load()`. Once sync-on-resume made `load()` fire on every app open, this tripped Health Connect's own platform rate limiter and broke *everything*, including data that is still shown. Only wire a new field into `GoogleDashboardSnapshot`/`load()` if it is actually rendered somewhere reachable from the current 2-screen nav.

5. **`SyncOrchestrator.triggerImmediateSync()` debounces repeat triggers within 5 seconds** (logged, not erroned). This does not affect the independently-scheduled 30-minute periodic worker. A real device log once showed 11+ manual/resume triggers inside 60 seconds before this existed.

6. **`GoogleHealthManager.grantedPermissionsOrEmpty()` coalesces concurrent permission checks** behind a mutex plus a 3-second result cache. Multiple near-simultaneous callers (dashboard load, sync preflight, worker preflight) share one real Health Connect call instead of each independently hitting the provider -- this is what prevents a burst of transient IPC hiccups from being misread as "permissions actually denied" (which flashes a false "Connect Health Connect" lock screen).

7. **Individual HUAWEI developers cannot obtain advanced-tier data (sleep/heart-rate/SpO2/stress) at all**, regardless of how the application is written -- this is a HUAWEI platform policy documented in their own developer docs, not something that can be worked around in code or in the application form.

8. **Several composables/functions are defined but deliberately unused** -- `HistoryScreen`, `WorkoutTypeCard`, `DashboardWidgetGrid`, `WeeklyComparisonCard`, `readStepsBars`, `readWeekOverWeekComparison` (the last one's *call site* was removed, the function itself may still exist). This is intentional minimal-diff precedent used throughout this project's patch history, not leftover cruft to "clean up" reflexively -- confirm a function is truly dead (no call sites, checked via grep across the whole non-backup tree) before touching it.

## Patch script conventions (follow exactly, for consistency with prior sessions)

Every code change in this project is delivered as a standalone Python patch
script that the person runs themselves in their GitHub Codespace -- never as
an inline diff applied by the assistant directly.

- `ROOT = Path(__file__).resolve().parent`; the script is copied into the
  repo root and run from there.
- Back up every file about to be touched to
  `.bitlut_patch_backup/<timestamp>_<short_name>/` before writing anything.
- Edits are **regex-anchored string replacements** (`old_str`/`new_str`
  substring matching), **never line-number-anchored**. Verify each anchor's
  count is exactly 1 in the live file before applying it; abort loudly with
  a clear error (do not guess or fall back to a different match) if it is
  not exactly 1.
- **Idempotency check:** test whether the NEW (already-patched) text is
  already present *first*, before counting the OLD anchor. For
  insertion-style edits, the old anchor often remains a substring of the
  already-patched result, so counting only the old anchor re-applies the
  edit forever on repeated runs. (This exact bug was caught and fixed once
  already in this project's own tooling -- do not reintroduce it.)
- After all edits: best-effort `./gradlew :app:compileDebugKotlin` (or
  `:app:processDebugResources` for resource/doc-only changes). Only
  `git add` + `git commit` + `git push origin HEAD:main` if that succeeds
  (or `gradlew` is absent, e.g. in a throwaway test sandbox).
- Print `==> step` style progress lines throughout the whole run -- this
  exact output is what gets pasted back for debugging when something goes
  wrong.
- **Test every script end-to-end against real extracted file content
  before delivering it**, including a second run to confirm idempotency.
  Do not deliver an untested script.

## Where things not in the codebase live

- The HUAWEI Health Kit permission application content (Data Usage / App
  Info / Self-Check sheets for HUAWEI's Excel template) was drafted in a
  prior session, matching exactly the scope list in
  `HealthPermissionPolicy.kt` / `HuaweiHealthManager.kt`. Keep the
  application content and the actual requested scopes in sync if either
  changes.
- The in-app hidden Log Viewer is the fastest path to diagnosing a reported
  bug precisely -- ask for a fresh export before guessing at root causes
  for anything sync/data-related.
