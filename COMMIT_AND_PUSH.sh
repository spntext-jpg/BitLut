#!/bin/bash
# COMMIT_AND_PUSH.sh
# Run this AFTER DELETE_FIXES.sh.
# Stages all changes, creates a structured commit, and pushes to main.
#
# Run from the ROOT of the BitLut repository:
#   chmod +x COMMIT_AND_PUSH.sh && ./COMMIT_AND_PUSH.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "======================================================"
echo " BitLut — Commit & Push"
echo "======================================================"

# ── 1. Show what will be committed ───────────────────────────────────────────
echo ""
echo "[1/4] Current git status:"
git status --short
echo ""

# ── 2. Stage everything ───────────────────────────────────────────────────────
echo "[2/4] Staging all changes..."
git add -A
echo "      Done."

# ── 3. Commit with a structured message ──────────────────────────────────────
echo "[3/4] Committing..."
git commit -m "refactor: architectural overhaul — fix 14 engineering violations

BREAKING FIXES (correctness):
- fix(SyncWorker): replace fixed 24h window with persisted lastSyncTimestamp
  — was inserting duplicate data on every hourly run
- fix(GoogleHealthManager): replace 'async fun' (invalid Kotlin) with 'suspend fun'
  — was a compile/runtime crash
- fix(HuaweiAuthManager): fix broken Retrofit call
  .create(HuaweiApiService::class.Companion::class.java)
  — was creating wrong class, would crash at runtime

ARCHITECTURE:
- refactor(network): create NetworkClient singleton — removes 3 duplicate
  inline Retrofit builders across HuaweiAuthManager, HuaweiCallbackActivity,
  SyncWorker
- refactor(network): split HuaweiApiService into HuaweiOAuthService +
  HuaweiHealthApiService — two different base URLs cannot share one interface
- feat(config): add HuaweiConfig — single source of truth for all credentials,
  URLs, redirect URI, and SharedPreferences key names (was scattered across 3 files)
- refactor(models): replace Map<String,Any> + unsafe casts with typed DTOs
  (HuaweiHealthRequest, HuaweiHealthResponse, HuaweiSampleRecord)
- refactor(models): make HuaweiTokenResponse fields nullable + add isSuccess()
  — was crashing with NPE on Huawei error responses

SECURITY:
- feat(auth): migrate token storage to EncryptedSharedPreferences
  — tokens were stored in plaintext SharedPreferences

PERFORMANCE:
- perf(health): replace per-record insertRecords() calls with batch insertRecords()
  — was doing N IPC calls per sync; now 1 IPC call per data type
- perf(health): cache ZoneRules — was traversing timezone DB on every record

UI/UX:
- fix(MainActivity): isSyncing now correctly resets to false by observing
  WorkManager LiveData — sync button was permanently disabled after first tap
- fix(MainActivity): isHuaweiConnected now reads from HuaweiAuthManager.isAuthorized()
  — was a fake toggle disconnected from real auth state
- fix(MainActivity): add onResume() status refresh so UI updates after
  returning from Huawei OAuth browser tab

CLEANUP:
- chore: delete 18 legacy shell scripts that caused the corrupted directory tree
- chore: remove fractally-nested duplicate source files (src/ rogue tree)
- chore: remove duplicate AndroidManifest files (was 3, now 1 canonical)
- chore: consolidate two dependencies{} blocks in build.gradle.kts into one
- chore: fix gradle.properties — remove hardcoded embedded-jdk path
- chore: rewrite .gitignore — remove triplicated entries"

echo "      Committed."

# ── 4. Push ───────────────────────────────────────────────────────────────────
echo "[4/4] Pushing to origin main..."
git push origin main
echo "      Pushed."

echo ""
echo "======================================================"
echo " Done. Check GitHub Actions for build status."
echo "======================================================"
