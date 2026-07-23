#!/usr/bin/env python3
"""
fix_huawei_partial_scope_denial.py

BitLut hotfix -- triggered by a real device log showing genuine progress
(the first confirmed real-device Huawei Health authorization success in
this project's history: localHuaweiAuthorized=true, steps=176 points and
distance=232 points both read successfully) alongside a new bug: in that
SAME sync attempt, activeCalories alone failed with HUAWEI_SCOPE_UNAUTHORIZED
(50005) while steps/distance/elevation succeeded -- Huawei approves scopes
incrementally, and the code did not handle that.

Root cause: HuaweiHealthManager.readSnapshot() built its HuaweiHealthSnapshot
by evaluating all 6 category reads (steps, distance, floors, elevation,
activeCalories, activitySessions) as constructor arguments in one
expression. A SecurityException from any ONE of them (deliberately
re-thrown by readPointsRaw(), "propagate to caller") threw out of the whole
function -- discarding every already-successfully-read category, since
Kotlin evaluates a data class constructor's arguments eagerly, left to
right. SyncWorker's catch block then called
huaweiManager.markAppGalleryVerificationRequired() unconditionally on ANY
50005, which sets isAuthorized=false/pendingApproval=true -- incorrectly
resetting a CORRECTLY obtained authorization state back to "not authorized"
just because one specific data category (not everything) was still denied.
Every subsequent sync attempt then regressed to a full graceful no-op,
never even trying to read data again, despite steps/distance genuinely
working.

Fix: readSnapshot() now reads each of the 6 categories independently,
catching SecurityException per category and simply skipping that one (the
same graceful-degradation shape already used for floors on SDKs that don't
expose a floors DataType at all). Authorization is only treated as fully
denied -- re-throwing to trigger SyncWorker's existing 50005 handling
exactly as before -- if EVERY category comes back denied with zero
successes. A partial denial now proceeds normally with whatever categories
ARE authorized, and no longer touches the persisted authorization state at
all.

Also updates CLAUDE.md (refreshed Current Status reflecting the first
confirmed real-device auth success + this fix; corrected Gotcha 13's now-
stale framing; added Gotcha 14 documenting this exact bug) and CHANGELOG.md
(new 2026-07-22 entry).

IMPORTANT -- run order: this script assumes update_changelog_and_handoff.py
has already been run (its CLAUDE.md/CHANGELOG.md edits are the anchors this
script's own doc edits build on top of). If you haven't run that one yet,
run it first, then this one.

Run from the repo root inside your Codespace:
    python3 fix_huawei_partial_scope_denial.py
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / f"{TIMESTAMP}_fix_huawei_partial_scope_denial"

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
        print("       the file may have diverged from what this script expects (e.g. update_changelog_and_handoff.py hasn't been run yet, if this is CLAUDE.md/CHANGELOG.md) -- not guessing, stopping here")
        sys.exit(1)

    print(f"    !! ABORT: expected exactly 1 match for anchor in {rel_path}")
    print(f"       description: {description}")
    print(f"       found: {count} match(es) (ambiguous, refusing to guess which one)")
    sys.exit(1)


COMMIT_MESSAGE = """Fix: a single Huawei scope denial (e.g. activeCalories) no longer discards the whole sync or resets isAuthorized

Real device log showed Huawei approves scopes incrementally: steps/distance
succeeded while activeCalories alone returned 50005 in the same attempt.
See script docstring / CLAUDE.md Gotcha 14 for the full breakdown.
"""

log("Step 1/3: CLAUDE.md -- current status + Gotcha 13 correction + new Gotcha 14")
apply_edit(
    "CLAUDE.md",
    "rewrite Current Status: first confirmed real-device auth success, the partial-scope-denial bug + fix",
    old='''
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
  successfully." The test evidence the reviewer quoted was BitLut's own''',
    new='''
## Current status

- **HUAWEI Health Kit scope: APPROVED at the app level, AND real device
  authorization has now succeeded at least once** (App ID 117824685,
  approval received 2026-07-18; a device log from 2026-07-22 showed
  `localHuaweiAuthorized=true` with real steps/distance data successfully
  read from Huawei Health). This is the first confirmed evidence in this
  project's history of a real device completing authorization -- the
  "waiting on Huawei, nothing to do but wait" framing from earlier is now
  superseded. Read the next bullet: sync is not yet fully reliable even so.
- **Huawei can approve scopes incrementally, and the app didn't originally
  handle that -- fixed 2026-07-22 (Gotcha 14).** The same 2026-07-22 log
  that proved authorization works also showed `activeCalories` specifically
  still returning 50005 while steps/distance/elevation succeeded in the
  same attempt -- a partial scope rollout, not a full re-authorization
  need. Before the fix, that one denied category discarded the whole sync
  attempt's data and incorrectly reset `isAuthorized` back to `false` (see
  Gotcha 14 for the exact mechanism); now a single denied category is
  skipped without affecting the rest. If this or a similar report comes up
  again, check whether it's actually this same already-fixed pattern before
  assuming something new is wrong.
- **`localHuaweiAuthorized` is a LOCAL, per-device cached flag from the
  last real OAuth attempt -- fully decoupled from the server-side app-level
  scope approval above.** Confirmed still relevant background even though
  authorization has now succeeded once: Huawei's approval notification
  arrives outside the app entirely (e.g. by email), and BitLut has no way
  to detect it on its own -- `SyncWorker` deliberately never launches the
  OAuth flow itself (it needs a live foreground Activity). If a *future*
  device ever shows `localHuaweiAuthorized=false`/50005 again after
  previously working, the "Try connecting again" button (Gotcha 12) is the
  right next step, same as before -- this bullet's advice didn't change,
  only the fact that it's now been exercised successfully once.
- **One AppGallery review rejection so far (2026-07-18), root-caused and
  fixed in code.** Rejection reason: "does not collect to Huawei Health
  successfully." The test evidence the reviewer quoted was BitLut's own''',
)
apply_edit(
    "CLAUDE.md",
    "correct Gotcha 13's stale framing + add Gotcha 14 (partial Huawei scope denial no longer discards the whole sync)",
    old='''
12. **`isAuthorized()`/`isPendingApproval()` are per-device cached flags from the *last local OAuth attempt* -- not a live reflection of Huawei's server-side app-level scope approval, and a single generic failure message cannot distinguish the 5 different reasons an attempt can fail.** Both lessons came from the same real incident: an AppGallery review rejection quoted BitLut's own generic `toast_huawei_pending` toast as evidence of a broken app, when the toast was shown identically for `HUAWEI_SCOPE_UNAUTHORIZED` (50005, pending review), `HUAWEI_PRIVACY_NOT_ACCEPTED` (50011), `HUAWEI_CERT_MISMATCH`/`HUAWEI_CERT_VERIFY_FAILED` (907135702/6003), `HUAWEI_INVALID_ARGS` (907135000), and unknown/no-result cases -- giving no way to tell which was actually happening. Fixed with a `HuaweiAuthFailureReason` enum, classified and persisted per attempt (`HuaweiHealthManager.classifyFailure()`), surfaced via a reason-specific `HuaweiAuthIssueCard` in Settings instead of the old boolean-only pending-approval card. Relatedly: after Huawei approved BitLut's scope application, real device logs *still* showed `localHuaweiAuthorized=false`/50005 -- expected, since that approval is a separate, server-side, app-level fact that doesn't retroactively flip any device's locally cached grant; only a fresh, real (Activity-launched) authorization attempt updates it, which is exactly what the new "Try connecting again" retry button on the card exists to prompt (shown only for `SCOPE_PENDING_APPROVAL`/`PRIVACY_NOT_ACCEPTED`, where a retry can plausibly help -- not for `CERTIFICATE_MISMATCH`/`INVALID_CONFIGURATION`, which need an AppGallery Connect-side fix first).

13. **If Huawei's own "App Signing" re-signing feature is enabled for this app, the certificate fingerprint that matters for Health Kit is the App Signing certificate's SHA-256, not the local upload-keystore's SHA-256.** Not yet confirmed as an actual cause of anything in this project (the working theory as of 2026-07-18 is still that Gotcha 12's "local cache is stale" explanation fully accounts for the observed pending state), but flagged here because it's a very common, easy-to-miss source of a `CERTIFICATE_MISMATCH` (907135702/6003) failure specifically for builds that go through AppGallery review/distribution (as opposed to a developer's own locally-signed test builds, which may use a different certificate and could work fine while a reviewer's build fails). Check AppGallery Connect -> Distribution -> App information -> "App signing certificate fingerprint" against what's registered in Health Kit's config if `CERTIFICATE_MISMATCH` ever actually appears in `lastAuthFailureReason()`.

## Patch script conventions (follow exactly, for consistency with prior sessions)
''',
    new='''
12. **`isAuthorized()`/`isPendingApproval()` are per-device cached flags from the *last local OAuth attempt* -- not a live reflection of Huawei's server-side app-level scope approval, and a single generic failure message cannot distinguish the 5 different reasons an attempt can fail.** Both lessons came from the same real incident: an AppGallery review rejection quoted BitLut's own generic `toast_huawei_pending` toast as evidence of a broken app, when the toast was shown identically for `HUAWEI_SCOPE_UNAUTHORIZED` (50005, pending review), `HUAWEI_PRIVACY_NOT_ACCEPTED` (50011), `HUAWEI_CERT_MISMATCH`/`HUAWEI_CERT_VERIFY_FAILED` (907135702/6003), `HUAWEI_INVALID_ARGS` (907135000), and unknown/no-result cases -- giving no way to tell which was actually happening. Fixed with a `HuaweiAuthFailureReason` enum, classified and persisted per attempt (`HuaweiHealthManager.classifyFailure()`), surfaced via a reason-specific `HuaweiAuthIssueCard` in Settings instead of the old boolean-only pending-approval card. Relatedly: after Huawei approved BitLut's scope application, real device logs *still* showed `localHuaweiAuthorized=false`/50005 -- expected, since that approval is a separate, server-side, app-level fact that doesn't retroactively flip any device's locally cached grant; only a fresh, real (Activity-launched) authorization attempt updates it, which is exactly what the new "Try connecting again" retry button on the card exists to prompt (shown only for `SCOPE_PENDING_APPROVAL`/`PRIVACY_NOT_ACCEPTED`, where a retry can plausibly help -- not for `CERTIFICATE_MISMATCH`/`INVALID_CONFIGURATION`, which need an AppGallery Connect-side fix first).

13. **If Huawei's own "App Signing" re-signing feature is enabled for this app, the certificate fingerprint that matters for Health Kit is the App Signing certificate's SHA-256, not the local upload-keystore's SHA-256.** Flagged as a possible cause of a `CERTIFICATE_MISMATCH` (907135702/6003) failure specifically for builds that go through AppGallery review/distribution (as opposed to a developer's own locally-signed test builds, which may use a different certificate and could work fine while a reviewer's build fails). As of 2026-07-22 this is confirmed NOT the current blocker -- a real device log showed `localHuaweiAuthorized=true` with real steps/distance data successfully read, so basic authorization genuinely works; the remaining issue is Gotcha 14 below, a specific-category 50005 (`activeCalories`), which reads as a scope still being rolled out incrementally rather than a certificate problem. Still worth checking this if `CERTIFICATE_MISMATCH` ever actually appears in `lastAuthFailureReason()`.

14. **Huawei can approve Health Kit scopes incrementally -- some data categories authorized while others still return 50005 in the very same sync attempt -- and `readSnapshot()`/`SyncWorker` did not originally handle that.** A real device log (2026-07-22) showed `steps`/`distance`/`elevation` all read successfully with real data, while `activeCalories` alone failed with `HUAWEI_SCOPE_UNAUTHORIZED` (50005) in the same `readSnapshot()` call. Before the fix, that one denied category threw all the way out of `readSnapshot()` (a data class constructor's arguments evaluate eagerly, so the already-successfully-read categories were discarded the moment a later one threw), and `SyncWorker`'s catch block called `markAppGalleryVerificationRequired()` unconditionally on ANY 50005 -- wiping the correctly-obtained `isAuthorized=true` flag back to `false`, so every subsequent sync attempt regressed to a full graceful no-op without even trying to read data again. Fixed: `readSnapshot()` now catches a `SecurityException` per category independently (steps/distance/floors/elevation/activeCalories/activitySessions each isolated) and only re-throws (triggering the existing "fully unauthorized" handling) if EVERY category came back denied with zero successes -- a partial denial now just skips that one category and proceeds normally with whatever data IS authorized, matching the same graceful-degradation shape already used for floors on SDKs that don't expose a floors DataType at all. If a future report mentions a specific data category (not "everything") failing with 50005 while others work, that's this exact pattern -- check `deniedCategories` in the log rather than assuming a full re-authorization is needed.

## Patch script conventions (follow exactly, for consistency with prior sessions)
''',
)
log("Step 2/3: CHANGELOG.md -- add the 2026-07-22 dated entry")
apply_edit(
    "CHANGELOG.md",
    "insert 2026-07-22 dated entry above the 2026-07-18 entry",
    old='''# Changelog

## 2026-07-18 -- Huawei auth failure reasons + retry button (post-AppGallery-rejection)

Triggered by a real AppGallery review rejection: "does not collect to''',
    new='''# Changelog

## 2026-07-22 -- partial Huawei scope denial no longer discards the whole sync

Real device log evidence this time: `localHuaweiAuthorized=true`, with
steps (176 points) and distance (232 points) both read and deduplicated
successfully -- the first confirmed real-device authorization success in
this project's history. In the same sync attempt, `activeCalories` alone
failed with `HUAWEI_SCOPE_UNAUTHORIZED` (50005), while steps/distance/
elevation succeeded -- Huawei approves scopes incrementally, and the code
did not handle that.

- Root cause: `HuaweiHealthManager.readSnapshot()` built its
  `HuaweiHealthSnapshot` by evaluating all 6 category reads as constructor
  arguments in one expression. A `SecurityException` from any one of them
  (deliberately re-thrown by `readPointsRaw()`, "propagate to caller") threw
  out of the whole function, discarding every already-successfully-read
  category. `SyncWorker`'s catch block then called
  `huaweiManager.markAppGalleryVerificationRequired()` unconditionally on
  ANY 50005 -- which sets `isAuthorized=false`/`pendingApproval=true` --
  incorrectly resetting a *correctly obtained* authorization state back to
  "not authorized," so every subsequent sync attempt regressed to a full
  graceful no-op without even trying to read data again.
- Fix: `readSnapshot()` now reads each of the 6 categories (steps,
  distance, floors, elevation, activeCalories, activitySessions)
  independently, catching `SecurityException` per category and simply
  skipping that one (same graceful-degradation shape already used for
  floors on SDKs without a floors DataType). Authorization is only treated
  as fully denied -- re-throwing to trigger `SyncWorker`'s existing 50005
  handling exactly as before -- if EVERY category comes back denied with
  zero successes. A partial denial now proceeds normally with whatever
  categories ARE authorized, and no longer touches the persisted
  authorization state at all.
- Updated the stale comment on `readPointsRaw()`'s `SecurityException`
  re-throw (previously said "must propagate to SyncWorker" -- it now
  propagates to `readSnapshot()`, which decides skip-one-category vs.
  fully-unauthorized, not directly to `SyncWorker` for a single-category
  failure).
- Updated CLAUDE.md: refreshed "Current status" (first confirmed real
  device auth success; this fix), corrected Gotcha 13's now-stale "working
  theory" framing, added Gotcha 14 documenting the exact bug and fix.

## 2026-07-18 -- Huawei auth failure reasons + retry button (post-AppGallery-rejection)

Triggered by a real AppGallery review rejection: "does not collect to''',
)
log("Step 3/3: HuaweiHealthManager.kt -- the actual bug fix")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt",
    "readSnapshot(): read each of the 6 categories independently, only treat as fully denied if ALL of them fail",
    old='''
            AppLogger.i(TAG, "Reading real Huawei Health data from $startTimeMs to $endTimeMs")

            val snapshot = HuaweiHealthSnapshot(
                steps = readSteps(startTimeMs, endTimeMs),
                distances = readDistance(startTimeMs, endTimeMs),
                floors = readFloors(startTimeMs, endTimeMs),
                elevations = readElevation(startTimeMs, endTimeMs),
                activeCalories = readActiveCalories(startTimeMs, endTimeMs),
                activities = readActivitySessions(startTimeMs, endTimeMs)
            )

            AppLogger.i(
                TAG,
                "Huawei read complete: steps=${snapshot.steps.size}, distances=${snapshot.distances.size}, floors=${snapshot.floors.size}, elevations=${snapshot.elevations.size}, activeCalories=${snapshot.activeCalories.size}, activities=${snapshot.activities.size}"''',
    new='''
            AppLogger.i(TAG, "Reading real Huawei Health data from $startTimeMs to $endTimeMs")

            // Sprint (2026-07-22): each category is read independently now, and
            // a SecurityException (50005) from ANY ONE of them no longer
            // aborts the whole snapshot. A real device log showed Huawei can
            // approve scopes incrementally: steps/distance/elevation
            // succeeded with real data while activeCalories alone still
            // returned 50005 in the very same sync attempt. Before this fix,
            // that one denied category threw all the way out of this
            // function (a data class constructor's arguments are evaluated
            // eagerly, left-to-right, so the already-successfully-read
            // steps/distance/elevation were discarded the moment a later
            // argument threw), and SyncWorker's catch block treated it
            // identically to a fully-unauthorized app -- wiping the
            // correctly-obtained isAuthorized=true flag back to false via
            // markAppGalleryVerificationRequired(). That regressed every
            // subsequent sync attempt back to a full graceful no-op, never
            // even trying to read data again, despite steps/distance
            // genuinely working. Now: a category-specific 50005 is caught
            // right here, logged, and that category alone is skipped (the
            // same graceful-degradation shape already used for floors on
            // SDKs that don't expose a floors DataType at all) --
            // authorization is only treated as fully denied if EVERY
            // category comes back denied with zero successes, which
            // re-throws below so SyncWorker's existing 50005 handling still
            // fires correctly for that genuine case. See CLAUDE.md Gotcha 14.
            var anySucceeded = false
            var anyScopeDenied = false
            val deniedCategories = mutableListOf<String>()

            suspend fun <T> readCategory(label: String, block: suspend () -> List<T>): List<T> {
                return try {
                    val result = block()
                    anySucceeded = true
                    result
                } catch (e: SecurityException) {
                    anyScopeDenied = true
                    deniedCategories.add(label)
                    AppLogger.w(
                        TAG,
                        "Huawei $label is not yet authorized for this account/app (50005) -- skipping just this category, not the whole sync."
                    )
                    emptyList()
                }
            }

            val steps = readCategory("steps") { readSteps(startTimeMs, endTimeMs) }
            val distances = readCategory("distance") { readDistance(startTimeMs, endTimeMs) }
            val floors = readCategory("floors") { readFloors(startTimeMs, endTimeMs) }
            val elevations = readCategory("elevation") { readElevation(startTimeMs, endTimeMs) }
            val activeCalories = readCategory("activeCalories") { readActiveCalories(startTimeMs, endTimeMs) }
            val activities = readCategory("activitySessions") { readActivitySessions(startTimeMs, endTimeMs) }

            if (anyScopeDenied && !anySucceeded) {
                // Every category was scope-denied -- genuinely not authorized
                // at all yet, not a partial rollout. Re-throw so SyncWorker's
                // existing SecurityException/50005 handling fires exactly as
                // it did before this fix.
                throw SecurityException(
                    "$HUAWEI_SCOPE_UNAUTHORIZED: no Huawei Health category is authorized yet ($deniedCategories)"
                )
            }

            val snapshot = HuaweiHealthSnapshot(
                steps = steps,
                distances = distances,
                floors = floors,
                elevations = elevations,
                activeCalories = activeCalories,
                activities = activities
            )

            if (anyScopeDenied) {
                AppLogger.w(
                    TAG,
                    "Huawei read partially scope-denied (still pending approval for: $deniedCategories) -- proceeding with the categories that ARE authorized."
                )
            }

            AppLogger.i(
                TAG,
                "Huawei read complete: steps=${snapshot.steps.size}, distances=${snapshot.distances.size}, floors=${snapshot.floors.size}, elevations=${snapshot.elevations.size}, activeCalories=${snapshot.activeCalories.size}, activities=${snapshot.activities.size}"''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt",
    "clarify the readPointsRaw() SecurityException re-throw comment (propagates to readSnapshot() now, not directly to SyncWorker for a single category)",
    old='''            val chunkEnd = minOf(chunkStart + HUAWEI_READ_CHUNK_MS, endTimeMs)
            AppLogger.d(TAG, "readPoints chunk #$chunkIndex: $chunkStart..$chunkEnd")

            // SecurityException / 50005 must propagate to SyncWorker.
            merged.addAll(readPointsRaw(type, chunkStart, chunkEnd, label))

            chunkStart = chunkEnd''',
    new='''            val chunkEnd = minOf(chunkStart + HUAWEI_READ_CHUNK_MS, endTimeMs)
            AppLogger.d(TAG, "readPoints chunk #$chunkIndex: $chunkStart..$chunkEnd")

            // SecurityException / 50005 must propagate out of readPointsRaw
            // -- readSnapshot() is what decides (since 2026-07-22) whether a
            // single denied category is skipped or the whole read is
            // genuinely unauthorized; this function must not swallow it.
            merged.addAll(readPointsRaw(type, chunkStart, chunkEnd, label))

            chunkStart = chunkEnd''',
)

# ---------------------------------------------------------------------------
log(f"Done: {edits_applied} edit(s) applied, {edits_skipped} already up to date")

if edits_applied == 0:
    log("Nothing to do -- repo already matches the target state. Exiting without touching git.")
    sys.exit(0)

log(f"Backups written to {BACKUP_DIR.relative_to(ROOT)}")

gradlew = ROOT / "gradlew"
build_ok = None
if gradlew.exists():
    log("Running best-effort Gradle compile gate (compileDebugKotlin + processDebugResources)...")
    try:
        result = subprocess.run(
            ["./gradlew", "--console=plain", ":app:compileDebugKotlin", ":app:processDebugResources"],
            cwd=ROOT,
        )
        build_ok = result.returncode == 0
    except OSError as e:
        log(f"Could not run ./gradlew ({e}) -- skipping the compile gate.")
        build_ok = None

    if build_ok is False:
        log("Gradle check FAILED. Working tree is left patched (see backups above to revert if needed).")
        log("Not committing or pushing. Fix the reported error and re-run this script -- it is idempotent.")
        sys.exit(1)
    elif build_ok is True:
        log("Gradle check passed.")
else:
    log("No ./gradlew found in this directory -- skipping the compile gate (expected in a sandbox/test run).")

log("Committing and pushing...")
subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
commit = subprocess.run(
    ["git", "commit", "-m", COMMIT_MESSAGE],
    cwd=ROOT,
)
if commit.returncode != 0:
    log("git commit reported nothing to commit or failed -- check git status manually.")
    sys.exit(1)

push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT)
if push.returncode != 0:
    log("git push failed -- the commit is local; push manually once resolved (e.g. auth/network).")
    sys.exit(1)

log("Pushed to origin/main. Done.")
