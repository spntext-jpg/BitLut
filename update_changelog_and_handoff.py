#!/usr/bin/env python3
"""
update_changelog_and_handoff.py

BitLut wrap-up script -- brings CLAUDE.md, CHANGELOG.md, README.md's status
block, and SESSION_HANDOFF.md current with everything that happened this
session, for a clean transfer into a new conversation.

Why this was needed: every prior script this session (sprint2_part1,
sprint2_part2, the widget-color hotfix, the insets/widget-sync hotfix, and
the Huawei-auth-reasons fix) touched only code -- none of them updated
CLAUDE.md or CHANGELOG.md, so a full sprint's worth of shipped work
(edge-to-edge, the trust screen, the Huawei pending/auth-issue card, CSV
export, the home screen widget, two real-device hotfixes, and the
Huawei-scope-approval status change) was completely undocumented there
until now.

This script updates:
  1. CLAUDE.md   -- rewrites "Current status" (Huawei scope approval landed,
     but local device re-authorization is a separate, still-open question),
     extends the architecture map with the new files/composables, and adds
     5 new Gotchas (9-13) for real bugs found and fixed this session.
  2. CHANGELOG.md -- inserts 3 new dated entries (2026-07-14 Sprint 2,
     2026-07-16 hotfixes, 2026-07-18 Huawei auth reasons) that were never
     logged until now.
  3. README.md   -- refreshes the maintained `BITLUT_STATUS` block between
     its markers.
  4. SESSION_HANDOFF.md -- full rewrite, replacing the handoff from the
     previous session (which described a "waiting on Huawei, nothing else
     to do" state that's now significantly out of date) with one reflecting
     this session's entire arc, including two real mistakes this session's
     own tooling made and caught before delivery.

IMPORTANT -- unlike this session's other (code) patch scripts, this one
does NOT run a Gradle gate (nothing here is compiled) and does NOT
auto-commit or push, matching this project's own established precedent for
doc-only wrap-up scripts ("so a human skims them first" -- see the
SESSION_HANDOFF.md this script is about to replace, in its own "Open
items" section, describing that exact precedent from the prior session).
Review the diff yourself, then commit and push when ready -- suggested
commands are printed at the end.

Run from the repo root inside your Codespace:
    python3 update_changelog_and_handoff.py
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / f"{TIMESTAMP}_update_changelog_and_handoff"

touched_files = set()
edits_applied = 0
edits_skipped = 0


def log(msg):
    print(f"==> {msg}")


def backup(path: Path):
    if path in touched_files:
        return
    touched_files.add(path)
    rel = path.relative_to(ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, dest)


def apply_edit(rel_path: str, description: str, old: str, new: str):
    """Regex-anchored (exact substring) replace. Idempotent, count-verified.

    Checks the OLD anchor's count FIRST, not the new text's presence -- a
    short/generic `new` fragment can coincidentally already exist in an
    untouched file, which would produce a false "already applied" skip if
    checked first. Old-anchor-absent is the trustworthy signal for
    "already applied", trusted only once the new text's presence is also
    confirmed; aborts loudly if neither is true.
    """
    global edits_applied, edits_skipped
    path = ROOT / rel_path
    if not path.exists():
        print(f"    !! ABORT: {rel_path} does not exist")
        sys.exit(1)
    text = path.read_text(encoding="utf-8")

    count = text.count(old)
    if count == 1:
        backup(path)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        print(f"    OK: {description}")
        edits_applied += 1
        return

    if count == 0:
        if (not new.strip()) or new in text:
            print(f"    (already applied) {description}")
            edits_skipped += 1
            return
        print(f"    !! ABORT: anchor not found in {rel_path}, and replacement text isn't there either")
        print(f"       description: {description}")
        print("       the file may have diverged from what this script expects -- not guessing, stopping here")
        sys.exit(1)

    print(f"    !! ABORT: expected exactly 1 match for anchor in {rel_path}")
    print(f"       description: {description}")
    print(f"       found: {count} match(es) (ambiguous, refusing to guess which one)")
    sys.exit(1)


def create_file(rel_path: str, description: str, content: str):
    """Writes rel_path with content, backing up any existing different
    content first. Idempotent: a byte-identical existing file is a no-op."""
    global edits_applied, edits_skipped
    path = ROOT / rel_path
    if path.exists() and path.read_text(encoding="utf-8") == content:
        print(f"    (already applied) {description}")
        edits_skipped += 1
        return
    if path.exists():
        backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"    OK: {description}")
    edits_applied += 1


log("Step 1/4: CLAUDE.md -- current status, architecture map, new gotchas, conventions addendum")
apply_edit(
    "CLAUDE.md",
    "rewrite 'Current status' section: Huawei scope approved at app level, local-vs-server auth state distinction, the AppGallery rejection + fix",
    old='''
## Current status

- **HUAWEI Health Kit scope approval: PENDING.** Real device logs show
  `localHuaweiAuthorized=false` and error `50005` (HUAWEI_SCOPE_UNAUTHORIZED)
  on every sync attempt. The sync pipeline is fully built, tested, and
  behaves correctly in this state (graceful no-op, no crashes, no false
  data). No code changes are needed once HUAWEI approves the scope -- only
  check then whether in-app HUAWEI re-authorization is also required.
- **Requested/expected HUAWEI scope** (activity-only tier, individual
  developer): `HEALTHKIT_STEP_READ`, `HEALTHKIT_DISTANCE_READ`,
  `HEALTHKIT_ACTIVITY_READ`, `HEALTHKIT_ACTIVITY_RECORD_READ`,''',
    new='''
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
  `HEALTHKIT_ACTIVITY_READ`, `HEALTHKIT_ACTIVITY_RECORD_READ`,''',
)
apply_edit(
    "CLAUDE.md",
    "architecture map: add widget/HomeWidget.kt, util/CsvExporter.kt rows; update HuaweiHealthManager.kt/GoogleHealthManager.kt/FinalBitLutShell.kt rows for new features",
    old='''  is now the standing precedent instead of "leave it dormant."
- **Today screen widgets (fixed set, not user-configurable):** steps today,
  workout time today, personal records, current streak, last imported
  workout. The old widget-visibility toggle feature was removed entirely.

## Architecture map
''',
    new='''  is now the standing precedent instead of "leave it dormant."
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
''',
)
apply_edit(
    "CLAUDE.md",
    "(merged into hunk 1 by the diff context window -- see description above)",
    old='''| `data/worker/SyncWorker.kt` | The actual background sync job (`CoroutineWorker`). Per-dependency circuit breakers, acquires `SyncRunLease` before doing real work, retries with backoff. |
| `data/worker/SyncReliability.kt` | `SyncCircuitBreaker`, `SyncWindowPlanner`, `SyncRunLease`, `SyncRetryPolicy`. |
| `data/worker/BackgroundSyncScheduler.kt` | WorkManager scheduling. `UNIQUE_PERIODIC_SYNC` (every 30 min) and `UNIQUE_SYNC_NOW` (manual/launch-triggered) are **different** unique-work names -- WorkManager does not serialize them against each other, which is exactly why `SyncRunLease` exists at the app level. |
| `data/HuaweiHealthManager.kt` | Reads from HUAWEI Health Kit. Type-safe dedup (an `Any?`/`UNCHECKED_CAST` bug here was fixed long ago -- watch for regressions if touching this). |
| `data/GoogleHealthManager.kt` | Reads/writes Health Connect. `readDashboardSnapshot()` (no `daysBack` param since 2026-07-14 -- it was only ever fed by History's now-deleted range chips) reads today's steps/distance/calories via `readRecords()` + manual sum, **not** `aggregate()` (see Gotcha 1). Coalesces concurrent permission checks behind a mutex + 3s cache (see Gotcha 6). |
| `ui/DashboardViewModel.kt` | `load()` drives the Today screen's state. Deliberately trimmed (2026-07-10) to only compute fields actually rendered somewhere reachable (see Gotcha 4). |
| `ui/screens/FinalBitLutShell.kt` | All UI lives in one file: `SummaryScreen`, `SettingsScreen`, and every card/widget composable (`PersonalRecordsCard`, `StreakCard`, `LastWorkoutCard`, `MinimalMetricCard`, `SettingsConnectionCard`, etc.). `DashboardWidgetGrid`/`WeeklyComparisonCard` are defined but intentionally unused (dormant, see Conventions). `HistoryScreen`/`HistoryRangeChips`/`WorkoutTypeCard` no longer exist at all (deleted 2026-07-14, not just dormant). |
| `ui/components/GlassNavigation.kt` | Bottom nav bar: Today tab, centered larger warm-orange `Glass20RefreshButton`, Settings tab. |
| `config/HealthPermissionPolicy.kt` | The authoritative Health Connect permission list. Activity-only, with an explicit in-code comment documenting that this is intentional, not incomplete. |
| `config/WidgetVisibilityPrefs.kt` | `DashboardWidget` enum + prefs -- the toggle *feature* was removed from Settings UI, but this underlying plumbing is left in place, currently unused from the UI. |
| `util/AppLogger.kt` | In-app diagnostic log. Viewable via a hidden `LogViewerScreen` (secret-tap trigger from the nav). **Use this for real device debugging** -- several real regressions in this project were only correctly diagnosed from an actual device log, not from reading source alone. |''',
    new='''| `data/worker/SyncWorker.kt` | The actual background sync job (`CoroutineWorker`). Per-dependency circuit breakers, acquires `SyncRunLease` before doing real work, retries with backoff. |
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
| `util/AppLogger.kt` | In-app diagnostic log. Viewable via a hidden `LogViewerScreen` (secret-tap trigger from the nav). **Use this for real device debugging** -- several real regressions in this project were only correctly diagnosed from an actual device log, not from reading source alone. |''',
)
apply_edit(
    "CLAUDE.md",
    "append Gotchas 9-13 (Glance ColorProvider API, Scaffold-external screen insets, widget-stuck-while-pending, local-vs-server auth state + reason classification, App Signing certificate)",
    old='''
8. **Some composables/functions are defined but deliberately unused** -- currently `DashboardWidgetGrid`, `WeeklyComparisonCard`, `readWeekOverWeekComparison` (the last one's *call site* was removed, the function itself may still exist). This is intentional minimal-diff precedent for code that might come back (e.g. if week-over-week UI returns) -- confirm a function is truly dead (no call sites, checked via grep across the whole non-backup tree) before touching it. This is a case-by-case call, not a blanket rule, though: `HistoryScreen`/`HistoryRangeChips`/`WorkoutTypeCard`/`readStepsBars`/`readWorkoutSummariesByType`/`computeMetricBarRanges`/`MetricBar` were all fully deleted on 2026-07-14 rather than left dormant, once it was clear History itself was never coming back and they had zero remaining callers -- "leave it dormant" is the default for something that might be reconnected later, not a permanent policy for code proven to be permanently dead.

## Patch script conventions (follow exactly, for consistency with prior sessions)

Every code change in this project is delivered as a standalone Python patch''',
    new='''
8. **Some composables/functions are defined but deliberately unused** -- currently `DashboardWidgetGrid`, `WeeklyComparisonCard`, `readWeekOverWeekComparison` (the last one's *call site* was removed, the function itself may still exist). This is intentional minimal-diff precedent for code that might come back (e.g. if week-over-week UI returns) -- confirm a function is truly dead (no call sites, checked via grep across the whole non-backup tree) before touching it. This is a case-by-case call, not a blanket rule, though: `HistoryScreen`/`HistoryRangeChips`/`WorkoutTypeCard`/`readStepsBars`/`readWorkoutSummariesByType`/`computeMetricBarRanges`/`MetricBar` were all fully deleted on 2026-07-14 rather than left dormant, once it was clear History itself was never coming back and they had zero remaining callers -- "leave it dormant" is the default for something that might be reconnected later, not a permanent policy for code proven to be permanently dead.

9. **Jetpack Glance 1.1.1's `ColorProvider` has no `ColorProvider(day: Color, night: Color)` overload** -- only `ColorProvider(color: Color)` and `ColorProvider(resId: Int)` exist (confirmed from a real `compileDebugKotlin` failure, not assumed). Day/night widget colors must go through resource-qualified files (`values/colors.xml` + `values-night/colors.xml`) with `ColorProvider(resId)`, not inline `Color(0x...)` values passed to a nonexistent day/night factory.

10. **A screen that renders outside the main `Scaffold` gets none of its automatic safe-area inset padding.** `PermissionsOnboardingScreen` and `LogViewerScreen` are both siblings of the `Scaffold` (shown/hidden via `if (showX) { ... }` at the top level of `FinalBitLutShell`, not routed through the Scaffold's content slot) -- invisible before `enableEdgeToEdge()` (the OS reserved status/nav bar space outside the app's content entirely), but the moment edge-to-edge shipped, both screens' content started drawing under the status bar (reported as "the Copy button in Log Viewer slid up, half covered" from a real device). Fixed with `.statusBarsPadding().navigationBarsPadding()` on each screen's root `Box`. Any *future* full-screen overlay added the same way (outside the Scaffold) needs the same treatment -- it will not get it for free.

11. **`SyncWorker` must refresh the dashboard cache/widget on the Huawei-blocked no-op paths too, not only after a real Huawei sync succeeds.** It originally only called `refreshDashboardCacheAfterWrite()` deep inside the Huawei-success branch -- while Huawei stayed pending (as it did for weeks), that call was never reached, so the home screen widget (which only ever reads that cache, never Health Connect directly) stayed stuck showing stale/empty data indefinitely, even though Health Connect could already contain real data from other apps (Google Fit, Samsung Health, etc.) regardless of Huawei's approval state. Fixed by calling the refresh on the `isPendingApproval()` and `!localHuaweiAuthorized` no-op branches too.

12. **`isAuthorized()`/`isPendingApproval()` are per-device cached flags from the *last local OAuth attempt* -- not a live reflection of Huawei's server-side app-level scope approval, and a single generic failure message cannot distinguish the 5 different reasons an attempt can fail.** Both lessons came from the same real incident: an AppGallery review rejection quoted BitLut's own generic `toast_huawei_pending` toast as evidence of a broken app, when the toast was shown identically for `HUAWEI_SCOPE_UNAUTHORIZED` (50005, pending review), `HUAWEI_PRIVACY_NOT_ACCEPTED` (50011), `HUAWEI_CERT_MISMATCH`/`HUAWEI_CERT_VERIFY_FAILED` (907135702/6003), `HUAWEI_INVALID_ARGS` (907135000), and unknown/no-result cases -- giving no way to tell which was actually happening. Fixed with a `HuaweiAuthFailureReason` enum, classified and persisted per attempt (`HuaweiHealthManager.classifyFailure()`), surfaced via a reason-specific `HuaweiAuthIssueCard` in Settings instead of the old boolean-only pending-approval card. Relatedly: after Huawei approved BitLut's scope application, real device logs *still* showed `localHuaweiAuthorized=false`/50005 -- expected, since that approval is a separate, server-side, app-level fact that doesn't retroactively flip any device's locally cached grant; only a fresh, real (Activity-launched) authorization attempt updates it, which is exactly what the new "Try connecting again" retry button on the card exists to prompt (shown only for `SCOPE_PENDING_APPROVAL`/`PRIVACY_NOT_ACCEPTED`, where a retry can plausibly help -- not for `CERTIFICATE_MISMATCH`/`INVALID_CONFIGURATION`, which need an AppGallery Connect-side fix first).

13. **If Huawei's own "App Signing" re-signing feature is enabled for this app, the certificate fingerprint that matters for Health Kit is the App Signing certificate's SHA-256, not the local upload-keystore's SHA-256.** Not yet confirmed as an actual cause of anything in this project (the working theory as of 2026-07-18 is still that Gotcha 12's "local cache is stale" explanation fully accounts for the observed pending state), but flagged here because it's a very common, easy-to-miss source of a `CERTIFICATE_MISMATCH` (907135702/6003) failure specifically for builds that go through AppGallery review/distribution (as opposed to a developer's own locally-signed test builds, which may use a different certificate and could work fine while a reviewer's build fails). Check AppGallery Connect -> Distribution -> App information -> "App signing certificate fingerprint" against what's registered in Health Kit's config if `CERTIFICATE_MISMATCH` ever actually appears in `lastAuthFailureReason()`.

## Patch script conventions (follow exactly, for consistency with prior sessions)

Every code change in this project is delivered as a standalone Python patch''',
)
apply_edit(
    "CLAUDE.md",
    "Patch script conventions: add addendum about the idempotency-check-ordering bug recurring, and the absolute-path shell heredoc lesson",
    old='''- **Test every script end-to-end against real extracted file content
  before delivering it**, including a second run to confirm idempotency.
  Do not deliver an untested script.

## Where things not in the codebase live
''',
    new='''- **Test every script end-to-end against real extracted file content
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
''',
)
apply_edit(
    "CLAUDE.md",
    "Where-things-live section: reword the Log Viewer bullet + add a new bullet about Huawei correspondence living outside the repo",
    old='''  changes.
- The in-app hidden Log Viewer is the fastest path to diagnosing a reported
  bug precisely -- ask for a fresh export before guessing at root causes
  for anything sync/data-related.''',
    new='''  changes.
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
  updated before assuming the status above is still current.''',
)
log("Step 2/4: CHANGELOG.md -- add the 3 missing dated entries for sprint 2's work")
apply_edit(
    "CHANGELOG.md",
    "insert 3 new dated entries (2026-07-18, 2026-07-16, 2026-07-14 Sprint 2) above the existing 2026-07-14 full-removal-sprint entry",
    old='''# Changelog

## 2026-07-14 -- full removal sprint: sleep/HR/SpO2/stress + History deleted outright

Follow-up to the 2026-07-10 series. That sprint removed History from the''',
    new='''# Changelog

## 2026-07-18 -- Huawei auth failure reasons + retry button (post-AppGallery-rejection)

Triggered by a real AppGallery review rejection: "does not collect to
Huawei Health successfully." The test evidence quoted was BitLut's own
`toast_huawei_pending` string, confirmed via exact text match -- meaning
the reviewer hit the same 50005 wall real devices had shown for weeks, with
no way to tell from that one message which of 5 different HMS failure
codes was actually in play (all 5 triggered the identical toast).

- Added `HuaweiAuthFailureReason` enum (`SCOPE_PENDING_APPROVAL`,
  `PRIVACY_NOT_ACCEPTED`, `CERTIFICATE_MISMATCH`, `INVALID_CONFIGURATION`,
  `UNKNOWN`) to `HealthDataContracts.kt`, plus `lastAuthFailureReason()` on
  `HuaweiHealthReader`.
- `HuaweiHealthManager.handleAuthorizationResult()` now classifies and
  persists the specific reason via a new `classifyFailure()` mapping (HMS
  codes 50005/50011/907135702/6003/907135000 -> the enum above), separately
  from the pre-existing `isAuthorized()`/`isPendingApproval()` booleans.
- Generalized the Settings screen's single 50005-only explanation card
  (`HuaweiPendingApprovalCard`) into `HuaweiAuthIssueCard`, which shows the
  right explanation for whichever of the 5 reasons actually happened --
  previously the other 4 cases showed nothing at all in Settings, just the
  same generic toast.
- Added a "Try connecting again" retry button on the card, shown only for
  `SCOPE_PENDING_APPROVAL` and `PRIVACY_NOT_ACCEPTED` (the two reasons a
  fresh attempt can plausibly fix) -- deliberately not shown for
  `CERTIFICATE_MISMATCH`/`INVALID_CONFIGURATION`, which need an AppGallery
  Connect-side fix first and would just fail the same way again.
- Replaced the old generic `toast_huawei_pending` toast (now dead, deleted)
  with `toast_huawei_failed`, which points to Settings for the specific
  explanation instead of trying to cram reason-specific detail into a
  fleeting Toast.
- Added `huawei_reason_*_title`/`_body` string resources for the 4
  previously-unhandled reasons, plus `huawei_retry_connect`, in both
  `values/strings.xml` and `values-ru/strings.xml`.
- Removed the now-dead `SyncUiState.isHuaweiPendingApproval` boolean field
  (fully superseded by `lastHuaweiAuthFailureReason`, confirmed zero
  remaining reads via grep) and its population in `refreshStatuses()`.

Separately: while this fix was in progress, Huawei approved BitLut's
Health Kit scope application at the app level (App ID 117824685). Device
logs taken immediately after still showed `localHuaweiAuthorized=false`/
50005 -- expected, not a regression, since that's a locally-cached flag
from the last real OAuth attempt, decoupled from the server-side approval
(see CLAUDE.md Gotcha 12). The new retry button exists specifically to
make the next required action -- a fresh authorization attempt -- obvious,
since Huawei's approval notification arrives outside the app entirely and
BitLut has no way to detect it on its own.

## 2026-07-16 -- two real-device hotfixes: widget colors, edge-to-edge insets, widget stuck while pending

Two separate real-device reports after the 2026-07-14 sprint below shipped,
each root-caused from device logs/screenshots rather than guessed.

**Widget colors (`Gradle compileDebugKotlin` failure, caught before commit)**
- `ColorProvider(day = Color(...), night = Color(...))` does not exist in
  `glance-appwidget:1.1.1` -- only `ColorProvider(color: Color)` and
  `ColorProvider(resId: Int)` do (see CLAUDE.md Gotcha 9). Switched
  `widget/HomeWidget.kt` to resource-qualified colors instead: added
  `widget_card`/`widget_text`/`widget_secondary_text` to both
  `values/colors.xml` (light) and a new `values-night/colors.xml` (dark).

**Edge-to-edge inset regression ("Copy button half covered" in Log Viewer)**
- `PermissionsOnboardingScreen` and `LogViewerScreen` both render as
  siblings of the main `Scaffold`, not through its content slot, so they
  never got the Scaffold's automatic safe-area inset padding -- invisible
  before `enableEdgeToEdge()`, a real visible bug the moment it shipped
  (see CLAUDE.md Gotcha 10). Fixed with `.statusBarsPadding()`/
  `.navigationBarsPadding()` on both screens' root `Box`. The 2026-07-14
  sprint's own new `DataScopesScreen` was unaffected -- it renders inside
  `SettingsScreen`, inside the Scaffold's own padding.

**Home screen widget stuck showing nothing while Huawei stayed pending**
- `SyncWorker` only ever called `refreshDashboardCacheAfterWrite()` (the
  function the widget's data ultimately comes from) deep inside the
  Huawei-sync-succeeded branch. While Huawei was pending -- true for weeks
  -- that branch was never reached, so the widget stayed stuck indefinitely
  even though Health Connect could already contain real data from other
  apps regardless of Huawei's state (see CLAUDE.md Gotcha 11). Fixed by
  calling the refresh on the `isPendingApproval()` and
  `!localHuaweiAuthorized` graceful-no-op paths too.
- Investigated but deliberately did NOT change: a separately reported
  "sync only works after opening Google Fit first" symptom. Traced
  `DashboardViewModel.load()`'s live `readDashboardSnapshot()` call and
  confirmed it does not depend on Huawei's auth state at all -- with
  Huawei still blocked at the time, BitLut could not have been writing the
  data being seen, so it was very likely coming from another app (Google
  Fit) that may only push to Health Connect when opened. Not a BitLut bug
  as far as the evidence showed; worth re-checking once Huawei sync is
  actually live and BitLut itself is writing on its own schedule.

## 2026-07-14 -- Sprint 2: edge-to-edge/predictive back, trust screen, Huawei pending-approval card, CSV export, home screen widget

Delivered as two scripts: Part 1 (no new Gradle dependency) and Part 2 (the
home screen widget, which adds `androidx.glance:glance-appwidget:1.1.1`),
kept separate specifically so a problem in the higher-risk widget piece
wouldn't block the other four.

**Edge-to-edge + predictive back**
- `MainActivity.onCreate()` now calls `enableEdgeToEdge()` before
  `setContent`. `AndroidManifest.xml`'s `<application>` tag gained
  `android:enableOnBackInvokedCallback="true"` for the predictive back
  gesture. targetSdk stayed at 35 (not bumped to 36) since the current AGP
  version doesn't support compileSdk 36.

**"What data is shared" trust screen**
- New `DataScopesScreen` composable, reachable any time from a link in
  Settings (not a one-time onboarding step) -- lists the actual 5 Huawei
  Health Kit scopes BitLut requests, matching `requestedScopeNames()`
  verbatim in substance, plus a one-line statement that everything goes to
  Google Health Connect on-device and nowhere else. Answers the most common
  complaint pattern in reviews of similar sync apps: "I don't understand
  what's being synced where."

**Huawei pending-approval status card**
- `SyncUiState` gained `isHuaweiPendingApproval`; a new
  `HuaweiPendingApprovalCard` in Settings explains the 50005 wait state in
  plain language instead of a silent no-op degrade, so a new install
  doesn't read "no data" as "broken." (Generalized into
  `HuaweiAuthIssueCard` on 2026-07-18 above -- this card's specific name
  and single-reason scope no longer exist as of that date.)

**CSV export**
- New `util/CsvExporter.kt`: writes daily totals (`GoogleHealthManager.
  readDailyTotals()`, added alongside it, same raw-records-not-aggregate
  pattern as the dashboard) plus recent workouts to a CSV in `cacheDir/
  export/`, handed off via a new `FileProvider` (`res/xml/file_paths.xml`)
  to the system share sheet. Reachable from a link in Settings.

**Home screen widget (Jetpack Glance)**
- New `widget/HomeWidget.kt` + `HomeWidgetReceiver`: one tile, today's
  steps + last-sync time, tap anywhere enqueues the same
  `BackgroundSyncScheduler.enqueueImmediateSync` work request the Settings
  "Sync now" button uses. Reads `DashboardSnapshotCache` only, never Health
  Connect directly, so `provideGlance()` stays cheap. New
  `res/xml/home_widget_info.xml` provider info (2x1 cell, 30-minute
  fallback `updatePeriodMillis`, real refresh driven by `SyncWorker`
  calling `updateAll()` after every successful cache write).

## 2026-07-14 -- full removal sprint: sleep/HR/SpO2/stress + History deleted outright

Follow-up to the 2026-07-10 series. That sprint removed History from the''',
)
log("Step 3/4: README.md -- refresh the maintained status block")
apply_edit(
    "README.md",
    "rewrite the Huawei Health Kit status paragraph + add an AppGallery review paragraph",
    old='''
_Этот блок поддерживается скриптом `update_readme_status.py` — перезапускайте его при смене статуса, не редактируйте руками между маркерами._

**HUAWEI Health Kit:** одобрение всё ещё ожидается со стороны Huawei (в логах — `localHuaweiAuthorized=false`, ошибка `50005`). Весь sync-пайплайн полностью готов, протестирован и корректно работает в режиме graceful no-op — как только Huawei одобрит scope, реальные данные пойдут без единой правки кода.

**Запрошенный/ожидаемый scope у Huawei** (activity-only, индивидуальный разработчик): `HEALTHKIT_STEP_READ`, `HEALTHKIT_DISTANCE_READ`, `HEALTHKIT_ACTIVITY_READ`, `HEALTHKIT_ACTIVITY_RECORD_READ`, `HEALTHKIT_HISTORYDATA_OPEN_WEEK`. Только чтение из Huawei — запись обратно не производится.
''',
    new='''
_Этот блок поддерживается скриптом `update_readme_status.py` — перезапускайте его при смене статуса, не редактируйте руками между маркерами._

**HUAWEI Health Kit:** заявка на scope одобрена Huawei на уровне приложения (App ID 117824685, одобрение получено 2026-07-18). Это **не значит**, что синк уже работает — `localHuaweiAuthorized` на устройстве это отдельный, локально закэшированный флаг с последней попытки авторизации, и он не обновляется автоматически при серверном одобрении. Реальный лог, снятый уже после одобрения, всё ещё показывал `localHuaweiAuthorized=false`/`50005` — это ожидаемо, а не регресс: нужно вручную нажать «Connect Huawei Health» (или новую кнопку «Попробовать снова» в Settings) ещё раз на реальном устройстве, чтобы подхватить одобрение. Если после этого снова 50005 в течение 1–2 дней — вероятно, дело в несовпадении сертификата (см. CLAUDE.md).

**AppGallery review:** было одно отклонение (2026-07-18) с формулировкой «does not collect to Huawei Health successfully» — ревьюер увидел тот же обобщённый тост на 50005, что и разработчик неделями видел в логах. Причина найдена и исправлена: теперь 5 разных причин ошибки авторизации Huawei показывают разные, конкретные объяснения в Settings вместо одного общего сообщения. Перед повторной отправкой на ревью нужно подтвердить, что живое устройство успешно проходит авторизацию.

**Запрошенный/ожидаемый scope у Huawei** (activity-only, индивидуальный разработчик): `HEALTHKIT_STEP_READ`, `HEALTHKIT_DISTANCE_READ`, `HEALTHKIT_ACTIVITY_READ`, `HEALTHKIT_ACTIVITY_RECORD_READ`, `HEALTHKIT_HISTORYDATA_OPEN_WEEK`. Только чтение из Huawei — запись обратно не производится.
''',
)
apply_edit(
    "README.md",
    "add a 'also shipped since 2026-07-14' paragraph + refresh the updated-date stamp",
    old='''
**Виджеты на Today (фиксированный набор, без возможности отключения):** шаги сегодня, время тренировок, личные рекорды, дней с целью подряд, последняя импортированная тренировка.

**Синхронизация:** автоматический триггер на каждом возврате в приложение (`onResume`, не только холодный старт), плюс кнопка Refresh в нижней навигации, плюс периодический воркер каждые 30 минут. Защищена debounce (5 сек между ручными триггерами) и process-wide lease против параллельных синков. Чтение сегодняшних метрик — через `readRecords()` с суммированием, не через `aggregate()` (у последнего есть задержка кэша на стороне Health Connect, что было подтверждённой причиной "синк работает только после открытия Google Fit").

_Обновлено: 2026-07-14_
<!-- BITLUT_STATUS:END -->

---''',
    new='''
**Виджеты на Today (фиксированный набор, без возможности отключения):** шаги сегодня, время тренировок, личные рекорды, дней с целью подряд, последняя импортированная тренировка.

**Также добавлено с 2026-07-14 по 2026-07-18:** виджет на рабочий стол (Jetpack Glance — шаги + время последней синхронизации, тап = синк); экспорт данных в CSV; экран «Что именно передаётся» со списком реальных 5 scope; edge-to-edge + жест «назад» (Android 15/16); карточка объяснения проблемы авторизации Huawei с конкретной причиной вместо общего сообщения.

**Синхронизация:** автоматический триггер на каждом возврате в приложение (`onResume`, не только холодный старт), плюс кнопка Refresh в нижней навигации, плюс периодический воркер каждые 30 минут. Защищена debounce (5 сек между ручными триггерами) и process-wide lease против параллельных синков. Чтение сегодняшних метрик — через `readRecords()` с суммированием, не через `aggregate()` (у последнего есть задержка кэша на стороне Health Connect, что было подтверждённой причиной "синк работает только после открытия Google Fit").

_Обновлено: 2026-07-22_
<!-- BITLUT_STATUS:END -->

---''',
)
log("Step 4/4: SESSION_HANDOFF.md -- full rewrite for this session")
create_file(
    "SESSION_HANDOFF.md",
    "overwrite SESSION_HANDOFF.md with a fresh handoff reflecting this entire session",
    '''# BitLut — session handoff (context transfer for a new conversation)

Paste or upload this file at the start of a new chat, along with a fresh
`repomix` export of the repo. Read `CLAUDE.md` from that export first — it
covers the codebase architecture, current status, and hard-won gotchas in a
form meant to be read once and trusted, not re-derived. This document
covers what CLAUDE.md deliberately doesn't: the narrative of *why* things
are the way they are, the working conventions specific to this person, and
the non-code backstory (the HUAWEI application process).

This replaces the previous handoff written at the end of the 2026-07-10
sprint series. Everything in that one has either been superseded (the
"pending approval" status, the dormant History code) or is still accurate
and repeated below where it still matters.

## Who you're talking to / how they work

- Individual developer, works exclusively through a GitHub Codespace/cloud
  shell — not a local machine, not Android Studio directly.
- **Every code change is delivered as a standalone Python patch script**
  that they copy into the repo root and run themselves (`python3
  script_name.py`). Never propose an inline diff or ask them to paste code
  changes manually — always a runnable script.
- They paste back real compiler errors and real device logs (via the
  hidden in-app Log Viewer, secret-tap-triggered) when something doesn't
  work, and real AppGallery review rejection reports when relevant. Several
  bugs across this project's history were only correctly diagnosed from an
  actual device log or a real rejection report after an initial
  code-reading-only guess was wrong or incomplete — ask for one before
  guessing twice on anything sync/auth/data-related.
- They communicate in Russian; code, comments, and commit messages stay in
  English (matches the existing codebase's own convention throughout).
- High bar for patch-script quality: every script this session was tested
  end-to-end against real extracted file content — including a second run
  to confirm idempotency, and a byte-for-byte diff against a known-good
  target state — before being delivered. Keep doing that; don't deliver an
  untested script.
- Workflow used successfully this session for building patch scripts: make
  the real edits directly against a local mirror of the repo first (using
  the actual edit tools, verifying each change as you go), THEN generate
  the patch script by diffing that mirror against the person's actual
  current repo state and turning each diff hunk into an `apply_edit()`
  call — rather than hand-writing `old`/`new` string literals from memory.
  This caught several real mistakes before delivery (see "Mistakes made
  and caught" below) that hand-writing likely would have missed.
- **Doc-only wrap-up scripts (CLAUDE.md/CHANGELOG.md/README status
  block/this handoff file) should NOT auto-commit or push**, unlike code
  patch scripts. This was an explicit, deliberate choice in the prior
  session ("so a human skims them first") and was followed again for the
  script that produced this very document — confirm with the person
  whether they've actually reviewed and committed these before assuming
  they're live.

## Project identity

BitLut: free, open-source Android app (Kotlin + Jetpack Compose), single
individual developer, published on HUAWEI AppGallery. One job: read
activity data from HUAWEI Health (via HUAWEI Health Kit) and write it into
Google Health Connect, so it's usable by any other Health Connect app on
the device. No ads, no server, no data sale.

## Current status (as of the end of this session — 2026-07-22)

- **HUAWEI Health Kit scope: APPROVED at the app level** (App ID 117824685,
  notification received 2026-07-18). **This is the single biggest status
  change since the last handoff** (which described this as the primary,
  entirely-external blocker with "nothing to do but wait"). That framing is
  now only half true — read the next two bullets before treating this as
  resolved.
- **The approval has NOT yet been confirmed to actually flow through to a
  working sync.** `localHuaweiAuthorized` is a local, per-device cached
  flag from the last real OAuth attempt, fully decoupled from the
  server-side approval above. A device log taken *after* the approval
  notification still showed `localHuaweiAuthorized=false`/error `50005` on
  every attempt — expected, not a regression, since nothing had re-run the
  actual authorization intent since approval landed (Huawei's notification
  arrives outside the app entirely, e.g. by email; BitLut cannot detect it
  on its own). **The next concrete action, if not already done by the time
  a new session picks this up: tap "Connect Huawei Health" (or the new
  "Try connecting again" retry button) on a real device, and check via the
  Log Viewer whether `localHuaweiAuthorized` finally flips to `true`.** If
  it still 50005s after ~24-48h, treat that as a real signal (HMS
  propagation lag exhausted) and move to checking a certificate/config
  mismatch instead (see CLAUDE.md Gotcha 13 — App Signing certificate
  fingerprint vs. local upload-key fingerprint is the leading suspect).
- **One AppGallery review rejection happened (2026-07-18).** Rejection
  text: "does not collect to Huawei Health successfully... affecting user
  experience," with test evidence quoting BitLut's own generic
  `toast_huawei_pending` message — confirmed via exact string match to be
  the app's own honest (if under-informative) error reporting, not a crash
  or genuinely broken feature. Root cause: that one toast covered 5 very
  different HMS failure codes identically, so neither the reviewer nor
  anyone reading the report could tell which was actually happening. Fixed
  in code (see below) — but **the fix does not retroactively guarantee
  the next review passes**; confirm a real device completes authorization
  successfully before resubmitting, to avoid a second rejection cycle over
  the same underlying (possibly still-unresolved) cause.
- **Sleep/HR/SpO2/stress and History: still fully deleted, not dormant**
  (unchanged from the last handoff — this remains accurate).
- **Screens: still exactly 2** (Today, Settings) — unchanged.
- **Substantial feature work shipped this session, all tested end-to-end
  and delivered as scripts** (see "What happened this session" below for
  the narrative, CHANGELOG.md for the itemized technical breakdown):
  edge-to-edge + predictive back gesture support; a "What data is shared"
  trust screen; a Huawei auth-issue card that explains the *specific*
  failure reason (not just "pending") with a conditional retry button; CSV
  export; a home screen widget (Jetpack Glance); two real-device hotfixes
  (a Glance color-API incompatibility, and an edge-to-edge inset
  regression + a bug where the widget stayed stuck empty while Huawei was
  pending).

## What happened this session, in order (condensed)

This session picked up directly from the previous handoff (uploaded at the
start, describing a "waiting on Huawei, nothing else to do" state) and a
fresh `repomix` export.

1. **Studied the repo, found the prior handoff's claims were slightly
   stale**: sleep/HR/SpO2/stress and History were described as fully
   removed, but the actual code still had dead fields (`GoogleDashboardSnapshot`,
   `DashboardSnapshotCache` serialization), a misleadingly-named
   `HealthAccent.sleep`, and History's screens/bar-chart infrastructure
   left dormant rather than deleted. Verified this by reading the actual
   extracted source, not by trusting the handoff's summary at face value —
   worth remembering that memory/handoff documents can drift from reality
   between sessions.
2. **Delivered `remove_sleep_hr_and_history.py`**: deleted all of the above
   outright (not just hardcoded to zero/left dormant) — see CHANGELOG.md's
   2026-07-14 "full removal sprint" entry for the itemized list. Updated
   CLAUDE.md/CHANGELOG.md/README as part of that same script.
3. **Gave a market comparison** against similar Huawei-to-Health-Connect
   sync apps (Health Sync/appyhapps as the main comparable) and 5 concrete,
   scope-appropriate recommendations: a home screen widget, edge-to-edge/
   predictive back modernization, a data-sharing trust screen, a calm
   Huawei-pending-approval status card, and CSV export.
4. **Implemented all 5 recommendations**, delivered as two scripts on
   purpose: `sprint2_part1_polish_trust_export.py` (edge-to-edge, trust
   screen, pending-approval card, CSV export — no new Gradle dependency)
   and `sprint2_part2_home_widget.py` (the widget — adds
   `androidx.glance:glance-appwidget`), kept separate specifically so a
   problem in the higher-risk widget piece wouldn't block the other four.
5. **Part 2's Gradle gate caught a real compile error before it reached
   git**: `ColorProvider(day=, night=)` doesn't exist in
   `glance-appwidget:1.1.1`. Diagnosed from the actual compiler output the
   person pasted back, fixed with resource-qualified `values`/`values-night`
   color files instead, delivered as `sprint2_part2_fix_widget_colors.py`.
6. **Two more real-device issues reported via logs/direct description**:
   the Log Viewer's Copy button rendering half-hidden under the status bar
   (an edge-to-edge inset regression on two Scaffold-external screens), and
   "sync only works after opening Google Fit first" (investigated and
   concluded this is very likely not a BitLut bug — see CHANGELOG.md's
   2026-07-16 entry for the reasoning — but a REAL bug was found alongside
   it: the widget never refreshed while Huawei stayed pending, since
   `SyncWorker` only refreshed the cache on the Huawei-success path).
   Delivered as `sprint2_fix_insets_and_widget_sync.py`.
7. **A real AppGallery review rejection came in.** Traced the exact
   rejection text to BitLut's own generic toast (confirmed via exact string
   match), explained clearly that the rejection itself isn't fixable by
   code (it needs Huawei-console-side verification), gave a concrete
   checklist for the person to run themselves (scope approval status,
   App Signing certificate fingerprint), and built the one legitimate code
   improvement available: classifying and surfacing the *specific* failure
   reason instead of one generic message.
8. **Mid-build, the person reported Huawei's scope approval had landed**,
   with a fresh device log still showing 50005/pending. Explained why
   that's expected (local cache vs. server-side approval are decoupled —
   see Current Status above), and added a "Try connecting again" retry
   button to the card being built, specifically to make the next required
   action obvious. Delivered as `sprint2_fix_huawei_auth_reasons.py`.
9. **This wrap-up**: CLAUDE.md, CHANGELOG.md (3 new dated entries — none
   of sprint 2's work had been logged there until now), README's status
   block, and this handoff document, all brought current.

### Mistakes made and caught this session (worth knowing about)

- **An idempotency-check-ordering bug recurred in the patch-script
  tooling itself** (checking whether the `new`/already-patched text was
  present *before* counting the `old` anchor's occurrences) — a short/
  generic `new` fragment coincidentally already existed in an untouched
  file, which would have produced a false "already applied" skip and risked
  silently duplicating a composable on a second run. Caught via a
  duplicate-symbol grep before delivery, not after. Fixed by checking the
  `old` anchor's count first. See CLAUDE.md's "Patch script conventions"
  section for the full writeup — this is a recurring risk class, not a
  one-time fix, and worth remembering on any future script.
- **A shell heredoc + relative-path mistake produced an incomplete script**
  while assembling `sprint2_fix_huawei_auth_reasons.py`: the initial
  `cat > /full/path/script.py << 'EOF'` used an absolute path, but the
  subsequent `cat piece.txt >> script.py` append commands used a bare
  relative filename, which silently wrote to a *different* file resolved
  against the shell's actual working directory — leaving the intended file
  at the full path incomplete (but still syntactically valid, since a
  truncated skeleton compiles fine on its own). Caught via a `wc -l`
  sanity check after each write step showing an unexpectedly small line
  count, and by the delivered script producing zero output when run.
  Fixed by using one consistent absolute path (stored in a shell variable)
  for every write in the assembly. See CLAUDE.md's "Patch script
  conventions" section.

## All patch scripts delivered this session (for traceability, in order)

`remove_sleep_hr_and_history.py`, `sprint2_part1_polish_trust_export.py`,
`sprint2_part2_home_widget.py`, `sprint2_part2_fix_widget_colors.py`,
`sprint2_fix_insets_and_widget_sync.py`,
`sprint2_fix_huawei_auth_reasons.py`, and the (unnamed by the person, but
referred to here as) CLAUDE.md/CHANGELOG.md/README/handoff wrap-up script
that produced this very document.

If continuing work in a new conversation, confirm with the person which of
these have actually been run/committed — this document assumes all of them
have been, since that's the point at which this handoff was written, but
don't assume that's still true without checking (e.g. asking them, or
checking a fresh repomix for the resulting code state). The wrap-up script
in particular was deliberately built to NOT auto-commit (matching the
prior session's own precedent) — it may be sitting reviewed-but-uncommitted,
or not yet even reviewed.

## Open items / what to watch for next

- **Primary open question: did a real device successfully re-authorize
  with Huawei Health after the scope approval landed?** This is the single
  most important thing to ask about or check first in a new session — it
  determines whether BitLut is now actually syncing real data for the
  first time in this project's history, or still blocked (and if still
  blocked, whether that's normal propagation lag or a certificate/config
  issue worth digging into per CLAUDE.md Gotcha 13).
- **If re-authorization succeeded**: the AppGallery review can be
  resubmitted. Consider whether the reviewer's specific test steps from the
  rejection report (tapping Connect, checking Huawei Health's own
  "Data sharing and authorization" management screen) should be manually
  re-run first as a final sanity check before resubmitting.
- **If re-authorization still fails after ~24-48h**: move to the
  certificate-fingerprint checklist (App Signing cert SHA-256 in
  AppGallery Connect vs. what's registered for Health Kit) rather than
  continuing to assume it's just propagation lag.
- **The Jetpack Glance widget has never been visually confirmed on a real
  device/launcher** — it compiles clean (confirmed via a real Gradle run)
  and its logic was reasoned through carefully, but nobody has actually
  looked at it rendered on a home screen yet. Worth asking about/checking
  early if any widget-related issue comes up.
- No other known open bugs as of the last device log referenced in this
  session.
''',
)

# ---------------------------------------------------------------------------
log(f"Done: {edits_applied} edit(s) applied, {edits_skipped} already up to date")

if edits_applied == 0:
    log("Nothing to do -- docs already match the target state.")
    sys.exit(0)

log(f"Backups written to {BACKUP_DIR.relative_to(ROOT)}")
log("")
log("This script deliberately does NOT commit or push (doc-only wrap-up")
log("scripts in this project never do -- see the script docstring). Review")
log("the changes yourself, then:")
log("")
log("    git add CLAUDE.md CHANGELOG.md README.md SESSION_HANDOFF.md")
log("    git commit -m \"Update CLAUDE.md/CHANGELOG.md/README/handoff for this session\"")
log("    git push origin HEAD:main")
