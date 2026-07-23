# BitLut — session handoff (context transfer for a new conversation)

Paste or upload this file at the start of a new chat, along with a fresh
`repomix` export of the repo. If `CLAUDE.md` is present in that export
(it should be, once `create_claude_md.py` from this session has been run
and committed), read it first — it covers the codebase architecture,
current status, and hard-won gotchas in a form meant to be read once and
trusted, not re-derived. This document covers what CLAUDE.md deliberately
doesn't: the narrative of *why* things are the way they are, the working
conventions specific to this person, and the non-code backstory (the
HUAWEI application process).

## Who you're talking to / how they work

- Individual developer, works exclusively through a GitHub Codespace/cloud
  shell — not a local machine, not Android Studio directly.
- **Every code change is delivered as a standalone Python patch script**
  that they copy into the repo root and run themselves (`python3
  script_name.py`). Never propose an inline diff or ask them to paste
  code changes manually — always a runnable script.
- They paste back real compiler errors and real device logs (via a hidden
  in-app Log Viewer, `util/AppLogger.kt` + a secret-tap-triggered
  `LogViewerScreen`) when something doesn't work. Several bugs in this
  session were only correctly diagnosed from an actual device log after an
  initial code-reading-only guess was wrong or incomplete — ask for a log
  before guessing twice on anything sync/data-related.
- They communicate in Russian; code, comments, and commit messages stay in
  English (matches the existing codebase's own convention throughout).
- High bar for patch-script quality: every script in this session was
  tested end-to-end against real extracted file content — including a
  second run to confirm idempotency — before being delivered. Keep doing
  that; don't deliver an untested script.

## Project identity

BitLut: free, open-source Android app (Kotlin + Jetpack Compose), single
individual developer, published on HUAWEI AppGallery. One job: read
activity data from HUAWEI Health (via HUAWEI Health Kit) and write it into
Google Health Connect, so it's usable by any other Health Connect app on
the device. No ads, no server, no data sale.

## Current status (as of the end of this session)

- **HUAWEI Health Kit scope approval: still pending.** Confirmed from a
  real device log: every sync attempt hits `localHuaweiAuthorized=false`
  and error `50005` (scope not authorized), and degrades gracefully to a
  no-op — no crash, no false data. This is **not a code bug** — it's
  waiting on HUAWEI's own review. No code changes are needed once it's
  approved; only check then whether in-app HUAWEI re-authorization is also
  needed.
- Requested scope (activity-only, individual-developer tier):
  `HEALTHKIT_STEP_READ`, `HEALTHKIT_DISTANCE_READ`, `HEALTHKIT_ACTIVITY_READ`,
  `HEALTHKIT_ACTIVITY_RECORD_READ`, `HEALTHKIT_HISTORYDATA_OPEN_WEEK`.
- Sleep/heart-rate/SpO2/stress are **intentionally absent everywhere** —
  individual HUAWEI developers cannot get that data tier at all, regardless
  of application quality (confirmed from HUAWEI's own docs). Don't revisit
  this unless the person says they've registered as a HUAWEI enterprise
  developer.
- App is down to exactly 2 screens (Today, Settings) with a fixed,
  non-configurable 5-widget Today screen. See CLAUDE.md's architecture
  table for exact file responsibilities.
- The sync pipeline itself (permission checks, lease/circuit-breaker,
  debounce, dashboard refresh timing, raw-record reads instead of stale
  aggregates) was chased through **five distinct real regressions** this
  session and is now confirmed clean from a final device log — zero
  rate-limit errors, zero swallowed cancellations, zero foreground-only
  read failures. Don't re-litigate these from scratch if a *new* sync
  complaint comes in; check CLAUDE.md's gotchas list first, since the next
  bug (if any) is more likely a sixth distinct thing than a return of one
  of these five.

## What happened this session, in order (condensed)

1. **Build fix**: missing `collectAsStateWithLifecycle` import broke a
   log-viewer feature build; the other two reported compiler errors were
   cascades from that one root cause, not separate bugs.
2. **HUAWEI Health Kit application help**: diagnosed a rejection (missing
   per-scope scenario description in HUAWEI's Data Usage Scenario tab),
   established the individual-vs-enterprise data-tier constraint, drafted
   full Data Usage / App Info / Self-Check content for the actual 5 scopes
   used in code.
3. **Health-data cleanup**: removed 24 dead sleep/heart-rate/SpO2/stress
   string resources and corrected stale README prose that falsely
   described those as working features — all confirmed unused via a full
   grep first, not assumed.
4. **History screen removed** from the bottom nav (an earlier, separately
   unresolved "bars don't update on range toggle" bug became moot) — app
   simplified to 2 screens; History's code left dormant, not deleted.
5. **Sync reliability chase**, each a real fix to a real regression, found
   via device logs, not guessed:
   - cold-launch staleness → added an automatic sync trigger
   - that trigger only fired once per process (`onCreate`) → moved to
     `onResume()`
   - lease-collision race caused a premature stale-data refresh →
     `SyncOrchestrator` now checks *why* a sync "succeeded" before
     refreshing
   - concurrent permission checks at launch caused a false "permissions
     missing" flash → coalesced behind a mutex + short cache
   - **root cause of "only fresh after opening Google Fit first"**:
     `HealthConnectClient.aggregate()` is a lagging provider-side cache →
     switched to raw `readRecords()` + manual sum
   - **root cause of a full regression ("widgets disappear, Connect
     Health Connect flashes")**: `DashboardViewModel.load()` made ~16
     Health Connect calls per invocation (many for already-removed UI,
     `readStepsBars` alone was one call per day in range), and
     sync-on-resume made `load()` fire often enough to trip Health
     Connect's own rate limiter → trimmed to only what's rendered, added a
     5s debounce on manual/resume sync triggers
   - a swallowed `CancellationException` in `load()` was logging fake
     errors and stomping state on routine cancellations → re-throw before
     the generic catch, matching the guard already used elsewhere
6. **UI simplification sprint**: Today screen cut to exactly 5 widgets
   matching the real data scope (steps, workout time, personal records,
   streak, last workout); both screens switched to a fixed non-scrolling
   layout; Settings connection cards lost their body text (title + icon
   only, compact one-row buttons); Daily goals moved to the top of
   Settings with calories dropped; widget-visibility toggle feature
   removed entirely; added a centered, larger, warm-orange manual refresh
   button to the bottom nav; fixed steps-value font clipping past 10,000.
7. **This wrap-up**: created `CLAUDE.md` (persistent project brief),
   `CHANGELOG.md` (dated entry covering all of the above), a marker-based
   "current status" block in `README.md`, and this handoff document.

## All patch scripts delivered this session (for traceability)

In order: `fix_log_viewer_imports.py`, `strip_advanced_health_traces.py`,
`sprint_disable_history_autosync.py`, `sprint_sync_audit_fixes.py`,
`sprint_ui_widget_cleanup.py`, `sprint_refresh_button_and_fixes.py`,
`fix_permission_check_concurrency.py`, `fix_aggregate_cache_staleness.py`,
`fix_rate_limit_and_huawei_status.py`, `fix_load_cancellation_swallowed.py`,
`create_claude_md.py`, `update_changelog.py`, `update_readme_status.py`.
(A `BitLut_HealthKit_Application.xlsx` was also produced for the HUAWEI
application — not a code patch, reference only.)

If continuing work in a new conversation, confirm with the person which of
these have actually been run/committed — this document assumes all of them
have been, since that's the point at which this handoff was written, but
don't assume that's still true without checking (e.g. asking them, or
checking a fresh repomix for the resulting code state).

## Open items / what to watch for next

- **Primary blocker**: waiting on HUAWEI's Health Kit scope approval. No
  action available on the code side until that resolves.
- `CLAUDE.md`/`CHANGELOG.md`/README status block were just created and not
  auto-committed by their scripts (deliberately, so a human skims them
  first) — check whether they've actually been committed yet.
- No other known open bugs as of the last device log in this session.
