#!/usr/bin/env python3
"""
sprint2_fix_huawei_auth_reasons.py

BitLut hotfix -- triggered by a real AppGallery review rejection whose only
visible symptom was BitLut's own generic toast: "Huawei Health Kit has not
confirmed access yet. Check approval status." (traced to toast_huawei_pending
in strings.xml -- confirmed word-for-word). That one message was shown for
ALL 5 possible Huawei Health Kit authorization failure codes (scope pending
review, privacy terms not accepted, certificate mismatch, invalid
config/App ID, or anything unrecognized), so neither a reviewer nor a
developer reading it could tell which of 5 very different problems was
actually happening. This patch:

1. Adds a HuaweiAuthFailureReason classification (HealthDataContracts.kt)
   and persists the specific reason from the last authorization attempt
   (HuaweiHealthManager.kt), instead of only ever tracking the 50005/
   pending-approval boolean that existed before.
2. Exposes that reason through SyncUiState (SyncViewModel.kt).
3. Generalizes the Settings screen's single 50005-only explanation card
   into one that shows the right explanation for whichever of the 5
   reasons actually happened (FinalBitLutShell.kt), and adds a "Try
   connecting again" button for the two reasons where a retry can
   plausibly help (SCOPE_PENDING_APPROVAL, PRIVACY_NOT_ACCEPTED) --
   deliberately NOT shown for CERTIFICATE_MISMATCH/INVALID_CONFIGURATION,
   which need an AppGallery Connect-side fix before a retry could work.
4. Replaces the old generic toast with one that points to Settings for the
   specific explanation, since a Toast can't hold enough text to be useful
   on its own (MainActivity.kt).
5. Adds the necessary string resources, en+ru (strings.xml).

IMPORTANT -- what this script does NOT and CANNOT fix: the AppGallery
rejection itself, or any Huawei-side scope-approval/certificate/config
issue. That requires action in Huawei AppGallery Connect / Huawei Developer
Console, which this script has no access to. See the chat discussion for a
concrete verification checklist (Health Kit scope approval status, and if
using Huawei's own "App Signing", checking that its certificate SHA-256 --
not your local upload-key SHA-256 -- is what's registered in Health Kit's
config).

Also worth noting given how this specific rejection played out: if you've
just had Huawei approve the Health Kit scope application itself (a
server-side, app-level approval), that does NOT automatically re-authorize
any device that previously got a 50005 -- the locally cached
isAuthorized()/isPendingApproval() flags this app tracks only update from a
fresh, real authorization attempt (tapping "Connect Huawei Health" again,
which requires a live Activity -- SyncWorker deliberately never launches
that flow from the background). The new retry button this script adds
exists specifically to make that next step obvious, since Huawei's own
approval notification arrives outside the app entirely (e.g. by email) and
BitLut has no way to detect it on its own.

Run from the repo root inside your Codespace:
    python3 sprint2_fix_huawei_auth_reasons.py
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / f"{TIMESTAMP}_sprint2_fix_huawei_auth_reasons"

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


COMMIT_MESSAGE = """Distinguish Huawei auth failure reasons (scope pending / privacy / cert mismatch / invalid config), add retry button

Triggered by an AppGallery review rejection whose only symptom was a
generic toast that couldn't distinguish 5 different failure causes.
See script docstring for the full breakdown.
"""

log("Step 1/7: HealthDataContracts.kt -- add HuaweiAuthFailureReason")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HealthDataContracts.kt",
    "add HuaweiAuthFailureReason enum (5 cases: scope pending, privacy not accepted, cert mismatch, invalid config, unknown)",
    old='''    fun invalidateClientCache()
}

interface HuaweiHealthReader {
    fun requestedScopeNames(): String
    fun isAuthorized(): Boolean''',
    new='''    fun invalidateClientCache()
}

/**
 * Classification of *why* the last Huawei Health Kit authorization attempt
 * failed (sprint 2026-07-18, added after an AppGallery review rejection
 * whose only visible symptom -- a single generic toast -- could have meant
 * any of these). Each case maps to a distinct, actionable next step; see
 * HuaweiHealthManager's classifyFailure() for the exact HMS error code
 * mapping and CLAUDE.md for the platform-specific detail behind each one.
 */
enum class HuaweiAuthFailureReason {
    /** HMS code 50005. Huawei's own server-side review of this app's
     *  requested scopes hasn't completed yet -- purely a waiting state,
     *  not something fixable by changing app code or configuration. */
    SCOPE_PENDING_APPROVAL,

    /** HMS code 50011. The person hasn't accepted Huawei Health's own
     *  privacy terms yet -- resolved inside the Huawei Health app itself,
     *  not by BitLut. */
    PRIVACY_NOT_ACCEPTED,

    /** HMS codes 907135702 / 6003. The signing certificate this build was
     *  actually signed with doesn't match the SHA-256 fingerprint
     *  registered for Health Kit in AppGallery Connect -- very often
     *  caused by registering the local upload-key fingerprint instead of
     *  the certificate Huawei's own "App Signing" re-signs release builds
     *  with before a reviewer or end user ever sees them. */
    CERTIFICATE_MISMATCH,

    /** HMS code 907135000. Something in the Health Kit request itself
     *  (App ID, package name, agconnect-services.json) doesn't match
     *  what's registered in AppGallery Connect. */
    INVALID_CONFIGURATION,

    /** Any other/unrecognized failure, or no result intent at all. */
    UNKNOWN
}

interface HuaweiHealthReader {
    fun requestedScopeNames(): String
    fun isAuthorized(): Boolean''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HealthDataContracts.kt",
    "add lastAuthFailureReason() to the HuaweiHealthReader interface",
    old='''    fun isAppGalleryVerificationRequired(): Boolean
    fun clearAppGalleryVerificationRequired()
    fun markAppGalleryVerificationRequired()
    fun getAuthorizationIntent(): Intent
    fun getHuaweiIdAuthorizationIntent(): Intent
    fun handleAuthorizationResult(resultCode: Int, data: Intent?): Boolean''',
    new='''    fun isAppGalleryVerificationRequired(): Boolean
    fun clearAppGalleryVerificationRequired()
    fun markAppGalleryVerificationRequired()
    fun lastAuthFailureReason(): HuaweiAuthFailureReason?
    fun getAuthorizationIntent(): Intent
    fun getHuaweiIdAuthorizationIntent(): Intent
    fun handleAuthorizationResult(resultCode: Int, data: Intent?): Boolean''',
)
log("Step 2/7: HuaweiHealthManager.kt -- classify and persist the specific failure reason")
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt",
    "add lastAuthFailureReason() override reading the persisted reason back",
    old='''    override fun isPendingApproval(): Boolean =
        prefs.getBoolean(KEY_HUAWEI_PENDING_APPROVAL, false)

    override fun isAppGalleryVerificationRequired(): Boolean =
        prefs.getBoolean(KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED, false)
''',
    new='''    override fun isPendingApproval(): Boolean =
        prefs.getBoolean(KEY_HUAWEI_PENDING_APPROVAL, false)

    /**
     * Sprint 2026-07-18: the *specific* reason the last authorization
     * attempt failed, persisted separately from the isPendingApproval/
     * isAppGalleryVerificationRequired booleans above (which both only
     * ever fire for the 50005 case) so cert-mismatch/privacy/invalid-config
     * failures are distinguishable too -- see classifyFailure() below.
     */
    override fun lastAuthFailureReason(): HuaweiAuthFailureReason? {
        val raw = prefs.getString(KEY_HUAWEI_LAST_AUTH_FAILURE_REASON, null) ?: return null
        return try {
            HuaweiAuthFailureReason.valueOf(raw)
        } catch (_: IllegalArgumentException) {
            null
        }
    }

    override fun isAppGalleryVerificationRequired(): Boolean =
        prefs.getBoolean(KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED, false)
''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt",
    "handleAuthorizationResult(): pass failureReason=UNKNOWN on the no-result-intent branch",
    old='''
    override fun handleAuthorizationResult(resultCode: Int, data: Intent?): Boolean {
        if (data == null) {
            saveAuthorizationState(success = false, pendingApproval = false)
            AppLogger.e(TAG, "Huawei authorization returned no result intent")
            return false
        }''',
    new='''
    override fun handleAuthorizationResult(resultCode: Int, data: Intent?): Boolean {
        if (data == null) {
            saveAuthorizationState(success = false, pendingApproval = false, failureReason = HuaweiAuthFailureReason.UNKNOWN)
            AppLogger.e(TAG, "Huawei authorization returned no result intent")
            return false
        }''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt",
    "handleAuthorizationResult(): classify and persist the specific failure reason via classifyFailure()",
    old='''        val success = result?.isSuccess == true
        val code = result?.errorCode
        val pendingApproval = code == HUAWEI_SCOPE_UNAUTHORIZED

        saveAuthorizationState(success = success, pendingApproval = pendingApproval)

        if (success) {
            AppLogger.i(TAG, "Huawei Health Kit authorization granted")''',
    new='''        val success = result?.isSuccess == true
        val code = result?.errorCode
        val pendingApproval = code == HUAWEI_SCOPE_UNAUTHORIZED
        val failureReason = if (success) null else classifyFailure(code)

        saveAuthorizationState(success = success, pendingApproval = pendingApproval, failureReason = failureReason)

        if (success) {
            AppLogger.i(TAG, "Huawei Health Kit authorization granted")''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt",
    "add classifyFailure(): maps a raw HMS error code to a HuaweiAuthFailureReason",
    old='''        return false
    }

    override fun markAuthorizationUnknown() {
        saveAuthorizationState(success = false, pendingApproval = false)
    }

    override suspend fun readSnapshot(startTimeMs: Long, endTimeMs: Long): HuaweiHealthSnapshot {''',
    new='''        return false
    }

    /**
     * Maps a raw HMS error code to the coarser [HuaweiAuthFailureReason]
     * bucket the UI (Settings card + toast) actually branches on. Kept
     * separate from the dev-facing `hint` strings in handleAuthorizationResult
     * above -- those stay verbose/technical for AppLogger and the hidden Log
     * Viewer; this feeds short, localized, end-user-facing copy instead.
     */
    private fun classifyFailure(code: Int?): HuaweiAuthFailureReason = when (code) {
        HUAWEI_SCOPE_UNAUTHORIZED -> HuaweiAuthFailureReason.SCOPE_PENDING_APPROVAL
        HUAWEI_PRIVACY_NOT_ACCEPTED -> HuaweiAuthFailureReason.PRIVACY_NOT_ACCEPTED
        HUAWEI_CERT_MISMATCH, HUAWEI_CERT_VERIFY_FAILED -> HuaweiAuthFailureReason.CERTIFICATE_MISMATCH
        HUAWEI_INVALID_ARGS -> HuaweiAuthFailureReason.INVALID_CONFIGURATION
        else -> HuaweiAuthFailureReason.UNKNOWN
    }

    override fun markAuthorizationUnknown() {
        saveAuthorizationState(success = false, pendingApproval = false, failureReason = null)
    }

    override suspend fun readSnapshot(startTimeMs: Long, endTimeMs: Long): HuaweiHealthSnapshot {''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt",
    "saveAuthorizationState(): add failureReason param, persist/clear it in prefs",
    old='''        }
    }

    private fun saveAuthorizationState(success: Boolean, pendingApproval: Boolean) {
        prefs.edit()
            .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, success)
            .putBoolean(KEY_HUAWEI_PENDING_APPROVAL, pendingApproval)
            .putBoolean(KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED, pendingApproval)
            .apply()
    }

    private fun ensureRuntimeReady() {''',
    new='''        }
    }

    private fun saveAuthorizationState(success: Boolean, pendingApproval: Boolean, failureReason: HuaweiAuthFailureReason?) {
        val editor = prefs.edit()
            .putBoolean(HuaweiConfig.KEY_HUAWEI_AUTHORIZED, success)
            .putBoolean(KEY_HUAWEI_PENDING_APPROVAL, pendingApproval)
            .putBoolean(KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED, pendingApproval)
        if (failureReason != null) {
            editor.putString(KEY_HUAWEI_LAST_AUTH_FAILURE_REASON, failureReason.name)
        } else {
            editor.remove(KEY_HUAWEI_LAST_AUTH_FAILURE_REASON)
        }
        editor.apply()
    }

    private fun ensureRuntimeReady() {''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt",
    "add KEY_HUAWEI_LAST_AUTH_FAILURE_REASON constant",
    old='''
        const val KEY_HUAWEI_PENDING_APPROVAL = "huawei_pending_approval"
        const val KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED = "huawei_appgallery_verification_required"

        const val HUAWEI_SCOPE_UNAUTHORIZED = 50005
        const val HUAWEI_PRIVACY_NOT_ACCEPTED = 50011''',
    new='''
        const val KEY_HUAWEI_PENDING_APPROVAL = "huawei_pending_approval"
        const val KEY_HUAWEI_APPGALLERY_VERIFICATION_REQUIRED = "huawei_appgallery_verification_required"
        const val KEY_HUAWEI_LAST_AUTH_FAILURE_REASON = "huawei_last_auth_failure_reason"

        const val HUAWEI_SCOPE_UNAUTHORIZED = 50005
        const val HUAWEI_PRIVACY_NOT_ACCEPTED = 50011''',
)
log("Step 3/7: SyncViewModel.kt -- expose lastHuaweiAuthFailureReason")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt",
    "import HuaweiAuthFailureReason",
    old='''package com.openhealth.sync.ui
import com.openhealth.sync.data.HuaweiHealthReader
import com.openhealth.sync.data.HealthConnectManager

import android.content.Context''',
    new='''package com.openhealth.sync.ui
import com.openhealth.sync.data.HuaweiHealthReader
import com.openhealth.sync.data.HuaweiAuthFailureReason
import com.openhealth.sync.data.HealthConnectManager

import android.content.Context''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt",
    "SyncUiState: drop dead isHuaweiPendingApproval field, add lastHuaweiAuthFailureReason",
    old='''    val hasGooglePermissions: Boolean = false,
    val needsPermissionRefresh: Boolean = false,
    val isHuaweiAuthorized: Boolean = false,
    val isHuaweiPendingApproval: Boolean = false,
    val isSyncing: Boolean = false,
    val syncStatus: String = "sync_status_idle",
    val lastSyncTime: String = "sync_no_data"''',
    new='''    val hasGooglePermissions: Boolean = false,
    val needsPermissionRefresh: Boolean = false,
    val isHuaweiAuthorized: Boolean = false,
    val lastHuaweiAuthFailureReason: HuaweiAuthFailureReason? = null,
    val isSyncing: Boolean = false,
    val syncStatus: String = "sync_status_idle",
    val lastSyncTime: String = "sync_no_data"''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt",
    "refreshStatuses(): populate lastHuaweiAuthFailureReason instead of the dead isHuaweiPendingApproval",
    old='''                    hasGooglePermissions = hasPerms,
                    needsPermissionRefresh = isAvailable && !hasPerms,
                    isHuaweiAuthorized = huaweiHealthManager.isAuthorized(),
                    isHuaweiPendingApproval = huaweiHealthManager.isPendingApproval(),
                    lastSyncTime = savedTime
                )
            }''',
    new='''                    hasGooglePermissions = hasPerms,
                    needsPermissionRefresh = isAvailable && !hasPerms,
                    isHuaweiAuthorized = huaweiHealthManager.isAuthorized(),
                    lastHuaweiAuthFailureReason = huaweiHealthManager.lastAuthFailureReason(),
                    lastSyncTime = savedTime
                )
            }''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/SyncViewModel.kt",
    "onHuaweiAuthorizationResult(): populate lastHuaweiAuthFailureReason immediately on failure",
    old='''        _uiState.update {
            it.copy(
                isHuaweiAuthorized = success,
                syncStatus = if (success) "sync_status_success" else "sync_status_error"
            )
        }''',
    new='''        _uiState.update {
            it.copy(
                isHuaweiAuthorized = success,
                lastHuaweiAuthFailureReason = if (success) null else huaweiHealthManager.lastAuthFailureReason(),
                syncStatus = if (success) "sync_status_success" else "sync_status_error"
            )
        }''',
)
log("Step 4/7: FinalBitLutShell.kt -- generalize the Settings card to all 5 reasons + add a retry-connect button")
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "import HuaweiAuthFailureReason",
    old='''import androidx.work.WorkManager
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison''',
    new='''import androidx.work.WorkManager
import com.openhealth.sync.data.worker.SyncWorker
import com.openhealth.sync.data.ActivitySessionData
import com.openhealth.sync.data.HuaweiAuthFailureReason
import com.openhealth.sync.data.PersonalRecord
import com.openhealth.sync.data.StreakState
import com.openhealth.sync.data.WeekComparison''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "generalize the pending-approval condition to cover all 5 failure reasons + wire onRetryConnect",
    old='''            onSecondaryAction = onRefresh
        )

        // Sprint (2026-07-14): a calm, specific explanation instead of a
        // silent no-op degrade. Huawei's server-side scope review can take
        // days; without this, a new install just sees zero data flowing
        // with no indication of why, which reads as "broken" rather than
        // "waiting." Only shown while genuinely pending (confirmed via a
        // real 50005 response, not guessed) and not yet authorized.
        if (syncState.isHuaweiPendingApproval && !syncState.isHuaweiAuthorized) {
            HuaweiPendingApprovalCard(palette = palette)
        }

        SettingsConnectionCard(''',
    new='''            onSecondaryAction = onRefresh
        )

        // Sprint (2026-07-14, generalized 2026-07-18): a calm, specific
        // explanation instead of a silent no-op degrade or a generic toast.
        // Previously only shown for the 50005/pending-approval case; now
        // covers all known Huawei Health Kit failure reasons (see
        // HuaweiAuthFailureReason), since an AppGallery review rejection
        // showed that a reviewer or user hitting ANY of the other 4 cases
        // (cert mismatch, invalid config, privacy not accepted, unknown)
        // previously saw nothing here at all -- just the same generic toast
        // regardless of cause.
        val huaweiFailureReason = syncState.lastHuaweiAuthFailureReason
        if (!syncState.isHuaweiAuthorized && huaweiFailureReason != null) {
            HuaweiAuthIssueCard(palette = palette, reason = huaweiFailureReason, onRetryConnect = onRequestHuawei)
        }

        SettingsConnectionCard(''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "rename/generalize HuaweiPendingApprovalCard -> HuaweiAuthIssueCard (doc comment + signature)",
    old='''}

/**
 * Explains the 50005 / "scope not authorized" wait state in plain language
 * instead of leaving a new install to wonder why no Huawei data is showing
 * up. This is a review-queue wait, not a permission the person needs to
 * grant again -- re-tapping Connect won't skip the queue, so this card
 * intentionally has no primary action, only the explanation.
 */
@Composable
private fun HuaweiPendingApprovalCard(palette: BitPalette) {
    SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {
        Row(verticalAlignment = Alignment.Top) {
            Icon(''',
    new='''}

/**
 * Explains *why* the last Huawei Health Kit authorization attempt failed,
 * in plain language specific to the actual cause (sprint 2026-07-18,
 * generalized from a 50005-only card after an AppGallery review rejection
 * showed the other 4 cases had no explanation at all -- just a generic
 * toast). [onRetryConnect] re-triggers the real Huawei OAuth flow -- shown
 * only for the two reasons where a fresh attempt can plausibly succeed:
 * SCOPE_PENDING_APPROVAL (Huawei's own approval notification arrives
 * outside the app entirely, e.g. by email -- the app has no way to detect
 * that on its own, so a manual retry is the only way to pick it up) and
 * PRIVACY_NOT_ACCEPTED (resolved by accepting terms in Huawei Health, then
 * retrying here). CERTIFICATE_MISMATCH and INVALID_CONFIGURATION need an
 * AppGallery Connect-side fix first -- retrying before that's done would
 * just fail the same way again, so no retry button is shown for those.
 */
@Composable
private fun HuaweiAuthIssueCard(palette: BitPalette, reason: HuaweiAuthFailureReason, onRetryConnect: () -> Unit) {
    val title: String
    val body: String
    val showRetry: Boolean
    when (reason) {
        HuaweiAuthFailureReason.SCOPE_PENDING_APPROVAL -> {
            title = stringResource(R.string.huawei_pending_approval_title)
            body = stringResource(R.string.huawei_pending_approval_body)
            showRetry = true
        }
        HuaweiAuthFailureReason.PRIVACY_NOT_ACCEPTED -> {
            title = stringResource(R.string.huawei_reason_privacy_not_accepted_title)
            body = stringResource(R.string.huawei_reason_privacy_not_accepted_body)
            showRetry = true
        }
        HuaweiAuthFailureReason.CERTIFICATE_MISMATCH -> {
            title = stringResource(R.string.huawei_reason_cert_mismatch_title)
            body = stringResource(R.string.huawei_reason_cert_mismatch_body)
            showRetry = false
        }
        HuaweiAuthFailureReason.INVALID_CONFIGURATION -> {
            title = stringResource(R.string.huawei_reason_invalid_config_title)
            body = stringResource(R.string.huawei_reason_invalid_config_body)
            showRetry = false
        }
        HuaweiAuthFailureReason.UNKNOWN -> {
            title = stringResource(R.string.huawei_reason_unknown_title)
            body = stringResource(R.string.huawei_reason_unknown_body)
            showRetry = false
        }
    }

    SoftCard(palette = palette, accent = HealthAccent.activity, hero = false, tintWithAccent = true) {
        Row(verticalAlignment = Alignment.Top) {
            Icon(''',
)
apply_edit(
    "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt",
    "HuaweiAuthIssueCard body: branch title/body/showRetry per reason, add the retry-connect button",
    old='''            Spacer(Modifier.width(10.dp))
            Column {
                Text(
                    text = stringResource(R.string.huawei_pending_approval_title),
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 15.sp
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = stringResource(R.string.huawei_pending_approval_body),
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )
            }
        }
    }''',
    new='''            Spacer(Modifier.width(10.dp))
            Column {
                Text(
                    text = title,
                    color = palette.text,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 15.sp
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = body,
                    color = palette.secondaryText,
                    fontWeight = FontWeight.Medium,
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )
                if (showRetry) {
                    Spacer(Modifier.height(10.dp))
                    val interactionSource = remember { MutableInteractionSource() }
                    Box(
                        modifier = Modifier
                            .pressScale(interactionSource)
                            .clip(RoundedCornerShape(99.dp))
                            .background(HealthAccent.activity)
                            .clickable(interactionSource = interactionSource, indication = null) { onRetryConnect() }
                            .padding(horizontal = 16.dp, vertical = 9.dp)
                    ) {
                        Text(
                            text = stringResource(R.string.huawei_retry_connect),
                            color = Color.White,
                            fontWeight = FontWeight.Black,
                            fontSize = 13.sp
                        )
                    }
                }
            }
        }
    }''',
)
log("Step 5/7: MainActivity.kt -- point the toast at Settings instead of a misleading generic message")
apply_edit(
    "app/src/main/java/com/openhealth/sync/MainActivity.kt",
    "toast: use the generic toast_huawei_failed pointing to Settings instead of the misleading always-the-same toast_huawei_pending",
    old='''            syncViewModel.onHuaweiAuthorizationResult(success)
            syncViewModel.refreshStatuses()

            Toast.makeText(
                this,
                if (success) getString(R.string.toast_huawei_connected) else getString(R.string.toast_huawei_pending),
                Toast.LENGTH_LONG
            ).show()
        }''',
    new='''            syncViewModel.onHuaweiAuthorizationResult(success)
            syncViewModel.refreshStatuses()

            // Sprint (2026-07-18): previously this always showed the same
            // generic toast_huawei_pending text for every possible failure
            // (scope pending, privacy not accepted, cert mismatch, invalid
            // config) -- which is exactly the message an AppGallery reviewer
            // quoted in a real rejection report, with no way for anyone
            // reading it to tell which of those 4 very different causes was
            // actually in play. The specific reason (and full explanation)
            // now lives in the Settings screen's Huawei card instead of a
            // fleeting Toast, since a Toast can't hold enough text to be
            // useful here -- this toast just points there.
            Toast.makeText(
                this,
                if (success) getString(R.string.toast_huawei_connected) else getString(R.string.toast_huawei_failed),
                Toast.LENGTH_LONG
            ).show()
        }''',
)
log("Step 6/7: strings.xml (en) -- add reason-specific copy + retry button label")
apply_edit(
    "app/src/main/res/values/strings.xml",
    "replace dead toast_huawei_pending with toast_huawei_failed (en)",
    old='''    <string name="manual_sync">Manual sync</string>
    <string name="manual_sync_body">Start Huawei Health to Health Connect sync now.</string>
    <string name="toast_huawei_connected">Huawei Health connected.</string>
    <string name="toast_huawei_pending">Huawei Health Kit has not confirmed access yet. Check approval status.</string>
    <string name="toast_huawei_health_missing">Install Huawei Health and sign in.</string>
    <string name="toast_huawei_start_failed">Could not open Huawei Health authorization.</string>
    <string name="last_sync_never">Never synced</string>''',
    new='''    <string name="manual_sync">Manual sync</string>
    <string name="manual_sync_body">Start Huawei Health to Health Connect sync now.</string>
    <string name="toast_huawei_connected">Huawei Health connected.</string>
    <string name="toast_huawei_failed">Couldn\\'t connect to Huawei Health. Check Settings for details.</string>
    <string name="toast_huawei_health_missing">Install Huawei Health and sign in.</string>
    <string name="toast_huawei_start_failed">Could not open Huawei Health authorization.</string>
    <string name="last_sync_never">Never synced</string>''',
)
apply_edit(
    "app/src/main/res/values/strings.xml",
    "add huawei_reason_*_title/body strings for the other 4 failure reasons + huawei_retry_connect (en)",
    old='''    <string name="huawei_health_title">Huawei Health</string>
    <string name="huawei_pending_approval_title">Waiting for Huawei\\'s approval</string>
    <string name="huawei_pending_approval_body">This isn\\'t a bug. Huawei reviews every app\\'s data access request before it can start syncing — this can take a few days. BitLut will start working automatically the moment it\\'s approved, with nothing for you to do in the meantime.</string>
    <string name="manual_sync_title">Manual sync</string>
    <string name="import_archive_title">Import archive</string>
    <string name="import_archive_selected">Huawei Health archive selected</string>''',
    new='''    <string name="huawei_health_title">Huawei Health</string>
    <string name="huawei_pending_approval_title">Waiting for Huawei\\'s approval</string>
    <string name="huawei_pending_approval_body">This isn\\'t a bug. Huawei reviews every app\\'s data access request before it can start syncing — this can take a few days. BitLut will start working automatically the moment it\\'s approved, with nothing for you to do in the meantime.</string>
    <string name="huawei_reason_privacy_not_accepted_title">Accept Huawei Health\\'s privacy terms</string>
    <string name="huawei_reason_privacy_not_accepted_body">Open Huawei Health, accept its privacy terms, then try connecting again.</string>
    <string name="huawei_reason_cert_mismatch_title">Certificate configuration issue</string>
    <string name="huawei_reason_cert_mismatch_body">Huawei Health Kit is rejecting this app\\'s signing certificate. This usually means the SHA-256 fingerprint registered in AppGallery Connect doesn\\'t match how this build was actually signed — for example, if Huawei\\'s own "App Signing" re-signs release builds with a different certificate than the one registered for Health Kit. This needs to be fixed in AppGallery Connect, not in the app itself.</string>
    <string name="huawei_reason_invalid_config_title">Configuration issue</string>
    <string name="huawei_reason_invalid_config_body">Huawei Health Kit didn\\'t recognize this app\\'s configuration (App ID, package name, or agconnect-services.json). This needs to be fixed in AppGallery Connect, not in the app itself.</string>
    <string name="huawei_reason_unknown_title">Couldn\\'t connect to Huawei Health</string>
    <string name="huawei_reason_unknown_body">Something prevented Huawei Health Kit from authorizing this app. Check the in-app log viewer for the specific error code, or try again later.</string>
    <string name="huawei_retry_connect">Try connecting again</string>
    <string name="manual_sync_title">Manual sync</string>
    <string name="import_archive_title">Import archive</string>
    <string name="import_archive_selected">Huawei Health archive selected</string>''',
)
log("Step 7/7: strings.xml (ru) -- add reason-specific copy + retry button label")
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "replace dead toast_huawei_pending with toast_huawei_failed (ru)",
    old='''    <string name="manual_sync">Ручная синхронизация</string>
    <string name="manual_sync_body">Запустить синхронизацию Huawei Health в Health Connect сейчас.</string>
    <string name="toast_huawei_connected">Huawei Health подключён.</string>
    <string name="toast_huawei_pending">Huawei Health Kit пока не подтвердил доступ. Проверьте статус согласования.</string>
    <string name="toast_huawei_health_missing">Установите Huawei Health и войдите в аккаунт.</string>
    <string name="toast_huawei_start_failed">Не удалось открыть авторизацию Huawei Health.</string>
    <string name="last_sync_never">Синхронизации ещё не было</string>''',
    new='''    <string name="manual_sync">Ручная синхронизация</string>
    <string name="manual_sync_body">Запустить синхронизацию Huawei Health в Health Connect сейчас.</string>
    <string name="toast_huawei_connected">Huawei Health подключён.</string>
    <string name="toast_huawei_failed">Не удалось подключиться к Huawei Health. Подробности в настройках.</string>
    <string name="toast_huawei_health_missing">Установите Huawei Health и войдите в аккаунт.</string>
    <string name="toast_huawei_start_failed">Не удалось открыть авторизацию Huawei Health.</string>
    <string name="last_sync_never">Синхронизации ещё не было</string>''',
)
apply_edit(
    "app/src/main/res/values-ru/strings.xml",
    "add huawei_reason_*_title/body strings for the other 4 failure reasons + huawei_retry_connect (ru)",
    old='''    <string name="huawei_health_title">Huawei Health</string>
    <string name="huawei_pending_approval_title">Ждём подтверждения от Huawei</string>
    <string name="huawei_pending_approval_body">Это не ошибка. Huawei проверяет запрос на доступ к данным у каждого приложения, прежде чем синхронизация сможет заработать — это может занять несколько дней. BitLut заработает автоматически, как только заявка будет одобрена, делать ничего не нужно.</string>
    <string name="manual_sync_title">Ручная синхронизация</string>
    <string name="import_archive_title">Импорт архива</string>
    <string name="import_archive_selected">Архив Huawei Health выбран</string>''',
    new='''    <string name="huawei_health_title">Huawei Health</string>
    <string name="huawei_pending_approval_title">Ждём подтверждения от Huawei</string>
    <string name="huawei_pending_approval_body">Это не ошибка. Huawei проверяет запрос на доступ к данным у каждого приложения, прежде чем синхронизация сможет заработать — это может занять несколько дней. BitLut заработает автоматически, как только заявка будет одобрена, делать ничего не нужно.</string>
    <string name="huawei_reason_privacy_not_accepted_title">Примите условия конфиденциальности Huawei Health</string>
    <string name="huawei_reason_privacy_not_accepted_body">Откройте Huawei Health, примите условия конфиденциальности, затем попробуйте подключиться снова.</string>
    <string name="huawei_reason_cert_mismatch_title">Проблема с сертификатом</string>
    <string name="huawei_reason_cert_mismatch_body">Huawei Health Kit отклоняет сертификат подписи этого приложения. Обычно это значит, что SHA-256 отпечаток, зарегистрированный в AppGallery Connect, не совпадает с тем, каким на самом деле подписана эта сборка — например, если функция Huawei "App Signing" переподписывает релизные сборки другим сертификатом, отличным от зарегистрированного для Health Kit. Это нужно исправить в AppGallery Connect, а не в самом приложении.</string>
    <string name="huawei_reason_invalid_config_title">Проблема с конфигурацией</string>
    <string name="huawei_reason_invalid_config_body">Huawei Health Kit не распознал конфигурацию этого приложения (App ID, имя пакета или agconnect-services.json). Это нужно исправить в AppGallery Connect, а не в самом приложении.</string>
    <string name="huawei_reason_unknown_title">Не удалось подключиться к Huawei Health</string>
    <string name="huawei_reason_unknown_body">Что-то помешало Huawei Health Kit авторизовать это приложение. Проверьте код ошибки в просмотрщике логов внутри приложения или попробуйте позже.</string>
    <string name="huawei_retry_connect">Попробовать снова</string>
    <string name="manual_sync_title">Ручная синхронизация</string>
    <string name="import_archive_title">Импорт архива</string>
    <string name="import_archive_selected">Архив Huawei Health выбран</string>''',
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
