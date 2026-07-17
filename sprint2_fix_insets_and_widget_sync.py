#!/usr/bin/env python3
"""
sprint2_fix_insets_and_widget_sync.py

BitLut hotfix -- two real issues found from a device log + direct report
after sprint 2 landed.

1. UI regression from enableEdgeToEdge() (sprint 2 part 1): two full-screen
   overlays that render OUTSIDE the main Scaffold -- PermissionsOnboardingScreen
   and LogViewerScreen -- never got the Scaffold's automatic safe-area inset
   padding that ImportScreen/SummaryScreen/SettingsScreen get for free. That
   was invisible before edge-to-edge (the OS reserved status/nav bar space
   outside the app's content entirely); the moment edge-to-edge shipped,
   their content started drawing under the status bar -- reported as "the
   Copy button slid up, half covered" in the Log Viewer. Fixed with
   statusBarsPadding()/navigationBarsPadding() on both screens' root Box.
   (DataScopesScreen, added this same sprint, was NOT affected -- it renders
   inside SettingsScreen, which is inside the Scaffold's own content padding.)

2. The home screen widget (sprint 2 part 2) never shows real numbers while
   Huawei's approval is pending. Root cause: SyncWorker only ever refreshes
   the dashboard cache the widget reads from deep inside the Huawei-sync-
   succeeded code path -- while huaweiManager.isPendingApproval() is true
   (confirmed from a real device log: "Huawei Health Kit approval pending
   (50005); sync degraded to no-op" on every attempt), doWork() returns
   GracefulNoop long before ever reaching that refresh call, so the cache
   stays empty/stale indefinitely. Fixed by refreshing the cache/widget on
   the two Huawei-blocked GracefulNoop paths too, since a read from Google
   Health Connect doesn't actually depend on Huawei's authorization state --
   Health Connect can already contain real data from other apps (Google
   Fit, Samsung Health, etc.) regardless of whether Huawei's approved yet.

Note on the separately reported "sync only works after opening Google Fit"
symptom: this script does NOT attempt to fix that, because it's very likely
not a bug. DashboardViewModel.load() (the in-app Today screen) already does
a live readDashboardSnapshot() call gated only on Google Health Connect
permissions, not on Huawei's state -- confirmed by reading that code path
directly. With Huawei still blocked (per the same log), BitLut cannot write
anything to Health Connect right now, so whatever step data is showing up
must be coming from another app (most likely Google Fit) -- and if that
app only pushes to Health Connect when opened/foregrounded, that would
fully explain the symptom without any bug on BitLut's side. Once Huawei's
review completes this whole category of confusion goes away, since BitLut
itself starts actively writing on its own schedule. Worth re-checking once
that happens; not worth guessing a code change for now without a log that
actually shows a stale Health Connect read (this one doesn't).

Run from the repo root inside your Codespace:
    python3 sprint2_fix_insets_and_widget_sync.py
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / f"{TIMESTAMP}_sprint2_fix_insets_and_widget_sync"

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


COMMIT_MESSAGE = """Sprint 2 hotfix: edge-to-edge inset regression + widget stuck while Huawei pending

See script docstring for the two root causes.
"""

log("Step 1/3: SyncWorker.kt -- refresh dashboard cache/widget even while Huawei approval is pending")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt",
    "refresh cache/widget on graceful no-op (Huawei blocked but Google Health Connect still readable) -- hunk 0",
    old='''
        if (huaweiManager.isPendingApproval()) {
            AppLogger.w(TAG, "Huawei Health Kit approval pending (50005); sync degraded to no-op")
            return SyncAttemptOutcome.GracefulNoop
        }

        if (!localHuaweiAuthorized) {
            AppLogger.w(TAG, "Huawei not locally authorized; sync degraded to no-op")
            return SyncAttemptOutcome.GracefulNoop
        }
''',
    new='''
        if (huaweiManager.isPendingApproval()) {
            AppLogger.w(TAG, "Huawei Health Kit approval pending (50005); sync degraded to no-op")
            // Sprint (2026-07-16): refresh the dashboard cache/widget here too,
            // not just on a full Huawei sync success. Health Connect can
            // already contain real data from other apps (Google Fit, Samsung
            // Health, the device's own step counter) regardless of Huawei's
            // approval state -- BitLut just wasn't writing to it. Without this,
            // the Today screen still updates fine (DashboardViewModel.load()
            // does its own live readDashboardSnapshot() call, unaffected by
            // this), but the home screen widget -- which only ever reads the
            // cache this function writes -- would show "not synced yet"
            // forever until Huawei's review completes, even if there's real
            // step data sitting in Health Connect the whole time.
            refreshDashboardCacheAfterWrite(googleManager)
            return SyncAttemptOutcome.GracefulNoop
        }

        if (!localHuaweiAuthorized) {
            AppLogger.w(TAG, "Huawei not locally authorized; sync degraded to no-op")
            refreshDashboardCacheAfterWrite(googleManager)
            return SyncAttemptOutcome.GracefulNoop
        }
''',
)
log("Step 2/3: FinalBitLutShell.kt -- statusBarsPadding import")
log("Step 3/3: FinalBitLutShell.kt -- fix PermissionsOnboardingScreen/LogViewerScreen insets")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "add statusBarsPadding import",
    old='''import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.navigationBarsPadding

import android.content.Context
import android.os.Bundle''',
    new='''import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.statusBarsPadding

import android.content.Context
import android.os.Bundle''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "PermissionsOnboardingScreen: add statusBarsPadding()/navigationBarsPadding()",
    old='''    val clipboardManager = androidx.compose.ui.platform.LocalClipboardManager.current
    val logs by com.openhealth.sync.util.AppLogger.logs.collectAsStateWithLifecycle()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            Row(''',
    new='''    val clipboardManager = androidx.compose.ui.platform.LocalClipboardManager.current
    val logs by com.openhealth.sync.util.AppLogger.logs.collectAsStateWithLifecycle()

    // Sprint (2026-07-16): same fix as PermissionsOnboardingScreen just
    // above -- this screen also renders outside the Scaffold, so its Copy/
    // Close buttons started rendering half under the status bar the moment
    // enableEdgeToEdge() shipped (confirmed from a real device: "кнопка
    // слезла вверх, наполовину закрыта").
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
            .statusBarsPadding()
            .navigationBarsPadding()
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            Row(''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "LogViewerScreen: add statusBarsPadding()/navigationBarsPadding()",
    old='''
@Composable
private fun PermissionsOnboardingScreen(palette: BitPalette, onContinue: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
    ) {
        Column(
            modifier = Modifier''',
    new='''
@Composable
private fun PermissionsOnboardingScreen(palette: BitPalette, onContinue: () -> Unit) {
    // Sprint (2026-07-16): this screen renders outside the main Scaffold
    // (see FinalBitLutShell's root -- it's a sibling shown after the
    // Scaffold closes, not routed through its content padding), so it never
    // got the Scaffold's automatic safeDrawing inset padding that
    // ImportScreen/SummaryScreen/SettingsScreen get for free. That was
    // invisible before enableEdgeToEdge() (the OS reserved status/nav bar
    // space outside the app's content entirely), but became a real bug the
    // moment edge-to-edge was enabled: this screen's own content now draws
    // under the status bar with nothing pushing it down. Fixed here rather
    // than by routing this screen through the Scaffold, to keep this a
    // one-line fix instead of a structural change.
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(palette.backgroundBrush)
            .statusBarsPadding()
            .navigationBarsPadding()
    ) {
        Column(
            modifier = Modifier''',
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
