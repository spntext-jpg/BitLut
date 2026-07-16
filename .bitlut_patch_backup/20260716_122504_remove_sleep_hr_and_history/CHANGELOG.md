# Changelog

## 2026-07-10 -- sync reliability + UI simplification sprint series

Six days, one continuous thread: get the log-viewer build green, get the
HUAWEI Health Kit application resubmitted cleanly, then chase a sync
freshness bug through five distinct real root causes using actual device
logs rather than guessing. Ends with a fully working, tested sync pipeline
that is simply waiting on HUAWEI's own scope approval to show real data.

**Build fix**
- Added the missing `collectAsStateWithLifecycle` import that broke the
  log-viewer build (the other two reported compiler errors were cascades
  from this one, not separate bugs).

**HUAWEI Health Kit application**
- Diagnosed the "Basic activity management permission and scenario
  description are not provided" rejection: Huawei's Data Usage Scenario
  tab requires a description for every checked scope, matched 1:1 -- ours
  was missing for the already-approved basic scope.
- Confirmed individual developers cannot access HUAWEI's advanced data tier
  (sleep/heart-rate/SpO2/stress) at all, regardless of application quality
  -- dropped those from scope entirely rather than fighting an unwinnable
  approval.
- Drafted the Data Usage / App Info / Self-Check sheet content for the 5
  scopes actually used in code (Step, Distance/ascent/altitude, Activity
  record, Activity, Reading historical data).

**Health-data cleanup**
- Removed 24 unused sleep/heart-rate/SpO2/stress string resources (in both
  `values/strings.xml` and `values-ru/strings.xml`) left over from before
  the activity-only pivot -- confirmed unused via a full grep for
  `R.string.<name>` across every `.kt` file first.
- Fixed a stale README section that falsely described pulse/sleep/SpO2/
  stress as currently-working features; removed 4 stale rows from the
  "supported Health Connect records" table for the same reason.

**History screen removed**
- The unresolved "history bars don't update on range toggle" bug was never
  fully root-caused; the screen was removed from the bottom nav entirely
  instead (2-tab nav: Today, Settings). Its composables/view-model logic
  were left in place, unreachable, not deleted.

**Sync reliability chase (chronological, each one a real fix to a real
regression, found from actual device logs)**
1. Cold launch showed cached data with no auto-refresh -> added an
   automatic Huawei -> Health Connect sync trigger.
2. That trigger only ran once (`onCreate`, once per process) -> moved to
   `onResume()` so every return to the app re-triggers it, not just the
   first one.
3. A lease-collision race meant a no-op "already syncing" result could
   trigger a premature dashboard refresh before the real sync had actually
   finished writing -> `SyncOrchestrator` now checks the completion reason
   and defers follow-up refreshes instead of refreshing immediately on a
   no-op.
4. Concurrent permission checks at cold launch could produce a false
   "permissions missing" flash -> coalesced behind a mutex + 3s cache in
   `GoogleHealthManager`.
5. Root cause of "only fresh after opening Google Fit first":
   `HealthConnectClient.aggregate()` is a provider-side cache that lags
   behind recent writes -> switched steps/distance/calories reads to raw
   `readRecords()` + manual sum, matching the pattern already used
   (correctly) by workout-minutes/active-hours reads.
6. Root cause of "sync got worse, widgets disappear, Connect Health Connect
   flashes": `DashboardViewModel.load()` was making ~16 Health Connect calls
   per invocation, including ~9 for screens/cards removed from the UI
   sprints ago (`stepsBars` alone was one call per day in range) -> trimmed
   to only what's actually rendered, and added a 5-second debounce on
   manual/resume sync triggers. A real device log showed 11+ triggers in 60
   seconds before this fix; confirmed gone after.
7. `DashboardViewModel.load()` was catching its own routine
   `CancellationException` (from cancelling a superseded prior call) as a
   generic error, logging noise and forcing `isLoading=false` on jobs that
   were only ever superseded -> re-throw `CancellationException` before the
   generic catch, matching the guard already used everywhere else in this
   codebase.

Confirmed via a clean final device log: no rate-limit errors, no swallowed
cancellations, no foreground-only read failures. The only remaining blocker
to real data is HUAWEI's own scope approval (`localHuaweiAuthorized=false`,
error 50005) -- not a code issue.

**UI simplification sprint**
- Today screen fixed to exactly 5 widgets matching the actual data scope:
  steps today, workout time, personal records, streak, last imported
  workout. Removed the calories/active-hours mini-grid and the
  week-over-week comparison card from the UI (their code was left dormant,
  see the trimming fix above for why the *data calls* also had to go, not
  just the UI).
- Both remaining screens switched from scrolling `LazyColumn` to a fixed,
  compact `Column`. Settings: connection cards dropped their body/status
  text (title + icon only), Connect/Refresh buttons compacted onto one row
  each. Daily goals moved to the top of Settings, calories dropped from it.
  Widget-visibility toggle section removed entirely -- widget set is fixed
  now, not user-configurable.
- Added a centered, larger (66dp vs 54dp), warm-orange manual refresh
  button to the bottom nav, wired to the same action as Settings' "Sync
  now".
- Fixed the steps-today value font clipping past 10,000 (dynamic font size
  based on formatted string length instead of a fixed 56sp).
