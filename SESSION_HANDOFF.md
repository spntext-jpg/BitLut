# BitLut — session handoff (context transfer for a new conversation)

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
