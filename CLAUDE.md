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

- **HUAWEI Health Kit scope: APPROVED at the app level** (Huawei's own
  approval notification for App ID 117824685, received 2026-07-18). This
  does **not** mean sync is live yet -- read the next bullet before
  assuming it "just works" now.
- **`localHuaweiAuthorized` is a LOCAL, per-device cached flag from the
  last real OAuth attempt -- fully decoupled from the server-side app-level
  scope approval above.** A real device log taken *after* the approval
  notification still showed `localHuaweiAuthorized=false` and error `50005`
  on every sync -- this is expected, not a sign the approval didn't take,
  because nothing has re-triggered the authorization intent since. Huawei's
  approval arrives outside the app entirely (e.g. by email); BitLut has no
  way to detect it on its own. `SyncWorker` deliberately never launches the
  OAuth flow itself (it needs a live foreground Activity) -- **the next
  required action is an explicit tap on "Connect Huawei Health" / the new
  "Try connecting again" button** (see Gotcha 12) on a real device, to
  actually pick up the approval. If that still 50005s after ~24-48h (a
  known HMS propagation lag), suspect a certificate/config mismatch instead
  -- see Gotcha 12 and the AppGallery review note below.
- **One AppGallery review rejection so far (2026-07-18), root-caused and
  fixed in code.** Rejection reason: "does not collect to Huawei Health
  successfully." The test evidence the reviewer quoted was BitLut's own
  generic `toast_huawei_pending` string (confirmed via exact text match) --
  meaning the reviewer hit the same 50005 wall real devices had been
  hitting for weeks, with no way to tell from that one message whether the
  real cause was still-pending-approval, a certificate mismatch, or
  something else (all 5 known HMS failure codes triggered the identical
  toast). Fixed: failure reasons are now classified and shown distinctly
  (see Gotcha 12) -- but this does NOT by itself guarantee re-review
  success; **confirm a real device can complete authorization successfully
  before resubmitting**, or risk a second rejection cycle for the same
  underlying reason.
- **Requested/expected HUAWEI scope** (activity-only tier, individual
  developer): `HEALTHKIT_STEP_READ`, `HEALTHKIT_DISTANCE_READ`,
  `HEALTHKIT_ACTIVITY_READ`, `HEALTHKIT_ACTIVITY_RECORD_READ`,
  `HEALTHKIT_HISTORYDATA_OPEN_WEEK`. Read-only from HUAWEI; BitLut never
  writes back to HUAWEI Health.
- **Sleep / heart-rate / SpO2 / stress are intentionally absent everywhere**
  -- not requested from HUAWEI, not read/written to Health Connect, no UI
  for them, and (as of 2026-07-14) no dead fields/serialization/color
  tokens for them left in the codebase either -- removed in full, not just
  disabled, down to `GoogleDashboardSnapshot`, `DashboardUiState`,
  `DashboardSnapshotCache` JSON (de)serialization, and the old
  `HealthAccent.heart`/`BitPalette.heart` color tokens. HUAWEI's advanced
  data tier is not available to individual developers at all (confirmed
  from HUAWEI's own docs), regardless of application quality -- this is a
  platform policy, not a fixable bug. If asked to add these, the honest
  answer is "would require registering as a HUAWEI enterprise developer
  first."
- **Screens: exactly 2** -- Today (Summary) and Settings. The History
  screen was removed from the bottom nav in an earlier sprint; as of
  2026-07-14 its code (`HistoryScreen`, `HistoryRangeChips`,
  `WorkoutTypeCard`, `readStepsBars`, `readWorkoutSummariesByType`,
  `computeMetricBarRanges` and its bucket helpers, the `MetricBar` type,
  the whole `MetricCharts.kt` file, and the now-dead `daysBack` parameter
  that only ever existed to feed History's range chips) was deleted
  outright rather than left dormant -- see Conventions below for why this
  is now the standing precedent instead of "leave it dormant."
- **Today screen widgets (fixed set, not user-configurable):** steps today,
  workout time today, personal records, current streak, last imported
  workout.
- **Also shipped since the removal sprint above (2026-07-14 through
  2026-07-18):** a single-tile home screen widget (Jetpack Glance --
  `widget/HomeWidget.kt`); a CSV export of daily totals + recent workouts
  (`util/CsvExporter.kt`); a "What data is shared" trust screen listing the
  real 5 scopes (`DataScopesScreen` in `FinalBitLutShell.kt`); a
  Huawei-auth-issue explanation card that branches on the *specific*
  failure reason instead of showing one generic message, with a retry
  button for the two reasons a retry can plausibly fix
  (`HuaweiAuthIssueCard`, see Gotcha 12); `enableEdgeToEdge()` + predictive
  back gesture support. See CHANGELOG.md for the full, dated breakdown of
  each.

## Architecture map

| File | Role |
|---|---|
| `MainActivity.kt` | Activity lifecycle. `onResume()` (not `onCreate()`) triggers sync + dashboard refresh on every foreground return -- fires once on cold launch too, so nothing needs to also live in `onCreate()`. |
| `di/AppContainer.kt` | Process-wide singleton DI container (GoogleHealthManager, HuaweiHealthManager, SyncOrchestrator, SyncRunLease, AchievementsStore, GoalPrefs, etc.). Everything shares these single instances -- no per-call fresh instances. |
| `domain/SyncOrchestrator.kt` | The UI-safe entry point for triggering a sync. Debounces repeat triggers within 5s. MainActivity and Settings call this, never WorkManager directly. |
| `data/worker/SyncWorker.kt` | The actual background sync job (`CoroutineWorker`). Per-dependency circuit breakers, acquires `SyncRunLease` before doing real work, retries with backoff. |
| `data/worker/SyncReliability.kt` | `SyncCircuitBreaker`, `SyncWindowPlanner`, `SyncRunLease`, `SyncRetryPolicy`. |
| `data/worker/BackgroundSyncScheduler.kt` | WorkManager scheduling. `UNIQUE_PERIODIC_SYNC` (every 30 min) and `UNIQUE_SYNC_NOW` (manual/launch-triggered) are **different** unique-work names -- WorkManager does not serialize them against each other, which is exactly why `SyncRunLease` exists at the app level. |
| `data/HuaweiHealthManager.kt` | Reads from HUAWEI Health Kit. Type-safe dedup (an `Any?`/`UNCHECKED_CAST` bug here was fixed long ago -- watch for regressions if touching this). Since 2026-07-18, `handleAuthorizationResult()` also classifies *why* an attempt failed into a `HuaweiAuthFailureReason` (see Gotcha 12) and persists it separately from the plain `isAuthorized()`/`isPendingApproval()` booleans. |
| `data/GoogleHealthManager.kt` | Reads/writes Health Connect. `readDashboardSnapshot()` (no `daysBack` param since 2026-07-14 -- it was only ever fed by History's now-deleted range chips) reads today's steps/distance/calories via `readRecords()` + manual sum, **not** `aggregate()` (see Gotcha 1). Coalesces concurrent permission checks behind a mutex + 3s cache (see Gotcha 6). `readDailyTotals()` (2026-07-18) feeds the CSV export, same raw-records pattern. |
| `ui/DashboardViewModel.kt` | `load()` drives the Today screen's state. Deliberately trimmed (2026-07-10) to only compute fields actually rendered somewhere reachable (see Gotcha 4). |
| `ui/screens/FinalBitLutShell.kt` | All UI lives in one file: `SummaryScreen`, `SettingsScreen`, and every card/widget composable (`PersonalRecordsCard`, `StreakCard`, `LastWorkoutCard`, `MinimalMetricCard`, `SettingsConnectionCard`, etc.). `DashboardWidgetGrid`/`WeeklyComparisonCard` are defined but intentionally unused (dormant, see Conventions). `HistoryScreen`/`HistoryRangeChips`/`WorkoutTypeCard` no longer exist at all (deleted 2026-07-14, not just dormant). Since 2026-07-14/18: `DataScopesScreen` (trust screen), `HuaweiAuthIssueCard` (reason-specific auth-failure explanation + conditional retry button, renamed/generalized from the old `HuaweiPendingApprovalCard`). |
| `ui/components/GlassNavigation.kt` | Bottom nav bar: Today tab, centered larger warm-orange `Glass20RefreshButton`, Settings tab. |
| `widget/HomeWidget.kt` | Home screen widget (Jetpack Glance, added 2026-07-14). One tile: today's steps + last-sync time, tap anywhere enqueues the same `BackgroundSyncScheduler.enqueueImmediateSync` work request Settings' "Sync now" uses. Reads `DashboardSnapshotCache` only (never calls Health Connect directly from `provideGlance()`); `SyncWorker` calls `HomeWidget().updateAll()` after every successful cache refresh, **including** the Huawei-blocked graceful-no-op paths (see Gotcha 11) so the widget doesn't stay stuck showing nothing while Huawei's approval is pending. Colors come from `values/colors.xml` + `values-night/colors.xml` (see Gotcha 9 for why, not inline `ColorProvider(day=,night=)`). |
| `util/CsvExporter.kt` | CSV export (added 2026-07-14). Writes to `cacheDir/export/`, hands off via `FileProvider` (`app/src/main/res/xml/file_paths.xml`) to the system share sheet. Exports exactly the same activity-only fields BitLut already reads for its own dashboard -- no new data source. |
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

8. **Some composables/functions are defined but deliberately unused** -- currently `DashboardWidgetGrid`, `WeeklyComparisonCard`, `readWeekOverWeekComparison` (the last one's *call site* was removed, the function itself may still exist). This is intentional minimal-diff precedent for code that might come back (e.g. if week-over-week UI returns) -- confirm a function is truly dead (no call sites, checked via grep across the whole non-backup tree) before touching it. This is a case-by-case call, not a blanket rule, though: `HistoryScreen`/`HistoryRangeChips`/`WorkoutTypeCard`/`readStepsBars`/`readWorkoutSummariesByType`/`computeMetricBarRanges`/`MetricBar` were all fully deleted on 2026-07-14 rather than left dormant, once it was clear History itself was never coming back and they had zero remaining callers -- "leave it dormant" is the default for something that might be reconnected later, not a permanent policy for code proven to be permanently dead.

9. **Jetpack Glance 1.1.1's `ColorProvider` has no `ColorProvider(day: Color, night: Color)` overload** -- only `ColorProvider(color: Color)` and `ColorProvider(resId: Int)` exist (confirmed from a real `compileDebugKotlin` failure, not assumed). Day/night widget colors must go through resource-qualified files (`values/colors.xml` + `values-night/colors.xml`) with `ColorProvider(resId)`, not inline `Color(0x...)` values passed to a nonexistent day/night factory.

10. **A screen that renders outside the main `Scaffold` gets none of its automatic safe-area inset padding.** `PermissionsOnboardingScreen` and `LogViewerScreen` are both siblings of the `Scaffold` (shown/hidden via `if (showX) { ... }` at the top level of `FinalBitLutShell`, not routed through the Scaffold's content slot) -- invisible before `enableEdgeToEdge()` (the OS reserved status/nav bar space outside the app's content entirely), but the moment edge-to-edge shipped, both screens' content started drawing under the status bar (reported as "the Copy button in Log Viewer slid up, half covered" from a real device). Fixed with `.statusBarsPadding().navigationBarsPadding()` on each screen's root `Box`. Any *future* full-screen overlay added the same way (outside the Scaffold) needs the same treatment -- it will not get it for free.

11. **`SyncWorker` must refresh the dashboard cache/widget on the Huawei-blocked no-op paths too, not only after a real Huawei sync succeeds.** It originally only called `refreshDashboardCacheAfterWrite()` deep inside the Huawei-success branch -- while Huawei stayed pending (as it did for weeks), that call was never reached, so the home screen widget (which only ever reads that cache, never Health Connect directly) stayed stuck showing stale/empty data indefinitely, even though Health Connect could already contain real data from other apps (Google Fit, Samsung Health, etc.) regardless of Huawei's approval state. Fixed by calling the refresh on the `isPendingApproval()` and `!localHuaweiAuthorized` no-op branches too.

12. **`isAuthorized()`/`isPendingApproval()` are per-device cached flags from the *last local OAuth attempt* -- not a live reflection of Huawei's server-side app-level scope approval, and a single generic failure message cannot distinguish the 5 different reasons an attempt can fail.** Both lessons came from the same real incident: an AppGallery review rejection quoted BitLut's own generic `toast_huawei_pending` toast as evidence of a broken app, when the toast was shown identically for `HUAWEI_SCOPE_UNAUTHORIZED` (50005, pending review), `HUAWEI_PRIVACY_NOT_ACCEPTED` (50011), `HUAWEI_CERT_MISMATCH`/`HUAWEI_CERT_VERIFY_FAILED` (907135702/6003), `HUAWEI_INVALID_ARGS` (907135000), and unknown/no-result cases -- giving no way to tell which was actually happening. Fixed with a `HuaweiAuthFailureReason` enum, classified and persisted per attempt (`HuaweiHealthManager.classifyFailure()`), surfaced via a reason-specific `HuaweiAuthIssueCard` in Settings instead of the old boolean-only pending-approval card. Relatedly: after Huawei approved BitLut's scope application, real device logs *still* showed `localHuaweiAuthorized=false`/50005 -- expected, since that approval is a separate, server-side, app-level fact that doesn't retroactively flip any device's locally cached grant; only a fresh, real (Activity-launched) authorization attempt updates it, which is exactly what the new "Try connecting again" retry button on the card exists to prompt (shown only for `SCOPE_PENDING_APPROVAL`/`PRIVACY_NOT_ACCEPTED`, where a retry can plausibly help -- not for `CERTIFICATE_MISMATCH`/`INVALID_CONFIGURATION`, which need an AppGallery Connect-side fix first).

13. **If Huawei's own "App Signing" re-signing feature is enabled for this app, the certificate fingerprint that matters for Health Kit is the App Signing certificate's SHA-256, not the local upload-keystore's SHA-256.** Not yet confirmed as an actual cause of anything in this project (the working theory as of 2026-07-18 is still that Gotcha 12's "local cache is stale" explanation fully accounts for the observed pending state), but flagged here because it's a very common, easy-to-miss source of a `CERTIFICATE_MISMATCH` (907135702/6003) failure specifically for builds that go through AppGallery review/distribution (as opposed to a developer's own locally-signed test builds, which may use a different certificate and could work fine while a reviewer's build fails). Check AppGallery Connect -> Distribution -> App information -> "App signing certificate fingerprint" against what's registered in Health Kit's config if `CERTIFICATE_MISMATCH` ever actually appears in `lastAuthFailureReason()`.

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
- The idempotency-check-ordering bug described above (checking `new`
  before `old`) recurred once more in this project's own tooling on
  2026-07-14 -- a short/generic `new` fragment (in that case, just the next
  function's signature, used only to mark where a deleted block ended)
  coincidentally already existed in an untouched file, producing a false
  "already applied" skip and risking silent duplication on a second run
  (caught before delivery, not after). The fix now checks the OLD anchor's
  count *first*; `new`-presence is only consulted as a fallback once `old`
  is confirmed absent. This is a recurring risk class worth remembering
  whenever a `new` value is short or structurally generic, not a one-time
  fix.
- When assembling a script by concatenating pieces via shell heredocs and
  `cat >>` (a common pattern for building these scripts), **use one
  absolute path consistently for every write, or store it in a shell
  variable and reuse the variable** -- mixing an absolute path for the
  initial `cat > /full/path/script.py << 'EOF'` with a bare relative
  filename for subsequent `cat piece.txt >> script.py` appends silently
  writes those appends to a *different* file resolved against whatever the
  shell's current working directory happens to be, leaving the file at the
  intended absolute path incomplete (but still syntactically valid Python,
  since a truncated-but-well-formed skeleton compiles fine) -- caught once
  in this project's own tooling via a `wc -l`/line-count sanity check after
  each write step, which is worth doing on any multi-step script assembly
  regardless.

## Where things not in the codebase live

- The HUAWEI Health Kit permission application content (Data Usage / App
  Info / Self-Check sheets for HUAWEI's Excel template) was drafted in a
  prior session, matching exactly the scope list in
  `HealthPermissionPolicy.kt` / `HuaweiHealthManager.kt`. Keep the
  application content and the actual requested scopes in sync if either
  changes.
- The in-app hidden Log Viewer is the fastest path to diagnosing a reported
  bug precisely -- ask for a fresh export before guessing at root causes
  for anything sync/data-related (still true this session -- several
  issues below were only correctly diagnosed from a real device log or a
  real AppGallery rejection report, not from reading code alone).
- Huawei's own correspondence -- the scope-approval notification (received
  2026-07-18, referenced in Current Status above) and the one AppGallery
  review rejection report so far -- lives in Paulo's inbox/AppGallery
  Connect console, not in this repo. If continuing work on either topic,
  ask whether there's newer correspondence since this file was last
  updated before assuming the status above is still current.
