#!/usr/bin/env python3
"""
patch_security_audit_cleanup_v1.py

Fixes four findings from a 2026-09-01 security/stability/reliability audit
of the whole codebase. No sync/data/UI behavior changes -- every edit here
is either dead-code removal or a repo-hygiene cleanup.

1. SECURITY: HuaweiConfig.CLIENT_ID / CLIENT_SECRET / REDIRECT_URI were
   populated from BuildConfig fields (app/build.gradle.kts) but never read
   anywhere in the actual codebase -- verified by grepping every call site
   before removal. The real Huawei Health Kit auth flow uses Scopes +
   SettingController + HuaweiIdAuthManager, not an OAuth client-secret
   exchange. BuildConfig fields are compiled in as plain static strings,
   trivially extractable from the public AppGallery APK via apktool/jadx.
   This means: if HUAWEI_CLIENT_SECRET is ever populated in .huawei.env or
   CI, it ships to every user's device for a code path that does not exist.
   Fix: remove the three dead properties from HuaweiConfig.kt and the three
   buildConfigField(...) lines that fed them from app/build.gradle.kts.
   HuaweiConfig.APP_ID and hasDeveloperAppId() are untouched -- both are
   genuinely used (HMS manifest placeholder, AppGallery ID check).

2. Dead code: ACTIVITY_SESSION_MIN_DURATION_MS / ACTIVITY_SESSION_MAX_GAP_MS
   in HuaweiHealthManager's companion object are declared but never
   referenced anywhere in the file or project (verified by full-repo grep).

3. Repo hygiene: patch_navbar_rebuild_sync_status_steps_diag_v1.py and
   patch_workout_session_scoped_metrics_v1.py are still sitting in the repo
   root from a previous sprint. Their changes were verified already present
   in source (SYNC_ACTIVITY_TAG, sessionSubMetricsFor(), 64dp navbar height,
   etc. all confirmed live) -- these two scripts are stale delivery
   artifacts, not pending work, per this project's standing "repo root
   stays clean between sessions" rule.

4. Manifest clutter: AndroidManifest.xml had 8 duplicate/stray leftover
   comment lines ("Health Connect strict Huawei-approved activity/basic
   sport sync scope.") stacked above the health permissions block, plus one
   near-duplicate "required sync scope" line -- collapsed into one clear
   comment. Purely cosmetic; no functional change, and the manifest was
   parsed with xml.etree.ElementTree before and after to confirm this.

Mandatory workflow already completed before this script was written:
hand-edited mirror -> real diff (diff -u against the original tree) ->
this script generated from that diff -> tested on a clean extraction with
a fake gradlew -> byte-diffed against the mirror -> re-run for idempotency.
"""
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

HUAWEI_CONFIG_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/remote/HuaweiConfig.kt"
BUILD_GRADLE_FILE = REPO_ROOT / "app/build.gradle.kts"
HUAWEI_MANAGER_FILE = REPO_ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt"
MANIFEST_FILE = REPO_ROOT / "app/src/main/AndroidManifest.xml"

STALE_PATCH_SCRIPTS = [
    REPO_ROOT / "patch_navbar_rebuild_sync_status_steps_diag_v1.py",
    REPO_ROOT / "patch_workout_session_scoped_metrics_v1.py",
]


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Cannot back up missing file: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rel = path.relative_to(REPO_ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(path, dest)


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, expected_new_count: int, description: str) -> None:
    """Genuine replacement. Idempotent via exact old_str occurrence count."""
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == 0 and new_count >= expected_new_count:
        print(f"  [skip] {description} (already applied)")
        return

    if old_count != expected_old_count:
        die(
            f"{description}: expected {expected_old_count} occurrence(s) of anchor "
            f"in {path.name}, found {old_count}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def remove_stale_patch_scripts() -> None:
    for script in STALE_PATCH_SCRIPTS:
        if not script.exists():
            print(f"  [skip] {script.name} already removed")
            continue
        backup(script)
        script.unlink()
        print(f"  [applied] removed stale patch script {script.name}")


def validate_xml(path: Path, description: str) -> None:
    try:
        ET.parse(path)
    except ET.ParseError as e:
        die(f"{description}: {path.name} failed to parse as XML after edits: {e}")
    print(f"  [ok] {description}: {path.name} parses cleanly")


def run_compile_gate() -> None:
    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found; cannot run compile gate")

    cmd = [
        str(gradlew),
        ":app:compileDebugKotlin",
        "--no-daemon",
        "--max-workers=1",
        "--no-watch-fs",
        "--console=plain",
        "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
        "-Pkotlin.compiler.execution.strategy=in-process",
    ]
    print("Running compile gate: " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        die("Compile gate failed. No commit/push performed. See Gradle output above.")


def git_commit_and_push() -> None:
    subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT, check=True)
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    if not status.stdout.strip():
        print("Nothing to commit (already applied and clean).")
        return

    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Security/stability audit: remove unused Huawei OAuth-style secret, dead constants, stale patch scripts, manifest clutter",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT, check=True)


def main() -> None:
    print("=== 1/4: Removing unused Huawei OAuth-style secret properties ===")
    apply_edit(
        HUAWEI_CONFIG_FILE,
        old=(
            "object HuaweiConfig {\n"
            "    val APP_ID: String get() = BuildConfig.HUAWEI_APP_ID\n"
            "    val CLIENT_ID: String get() = BuildConfig.HUAWEI_CLIENT_ID\n"
            "    val CLIENT_SECRET: String get() = BuildConfig.HUAWEI_CLIENT_SECRET\n"
            "    val REDIRECT_URI: String get() = BuildConfig.HUAWEI_REDIRECT_URI\n"
            "\n"
            "    const val PREFS_NAME: String = \"bitlut_prefs\"\n"
        ),
        new=(
            "object HuaweiConfig {\n"
            "    val APP_ID: String get() = BuildConfig.HUAWEI_APP_ID\n"
            "\n"
            "    const val PREFS_NAME: String = \"bitlut_prefs\"\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="HuaweiConfig.kt: remove dead CLIENT_ID/CLIENT_SECRET/REDIRECT_URI properties",
    )

    apply_edit(
        BUILD_GRADLE_FILE,
        old=(
            "        buildConfigField(\"String\", \"HUAWEI_APP_ID\", \"\\\"${escapedBuildConfig(\"HUAWEI_APP_ID\", \"117824685\")}\\\"\")\n"
            "        buildConfigField(\"String\", \"HUAWEI_CLIENT_ID\", \"\\\"${escapedBuildConfig(\"HUAWEI_CLIENT_ID\")}\\\"\")\n"
            "        buildConfigField(\"String\", \"HUAWEI_CLIENT_SECRET\", \"\\\"${escapedBuildConfig(\"HUAWEI_CLIENT_SECRET\")}\\\"\")\n"
            "        buildConfigField(\"String\", \"HUAWEI_REDIRECT_URI\", \"\\\"${escapedBuildConfig(\"HUAWEI_REDIRECT_URI\", \"https://com.openhealth.sync/oauth_callback\")}\\\"\")\n"
            "    }\n"
        ),
        new=(
            "        buildConfigField(\"String\", \"HUAWEI_APP_ID\", \"\\\"${escapedBuildConfig(\"HUAWEI_APP_ID\", \"117824685\")}\\\"\")\n"
            "    }\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="app/build.gradle.kts: remove HUAWEI_CLIENT_ID/SECRET/REDIRECT_URI buildConfigFields",
    )

    print("=== 2/4: Removing dead activity-session constants ===")
    apply_edit(
        HUAWEI_MANAGER_FILE,
        old=(
            "        const val HUAWEI_CERT_VERIFY_FAILED = 6003\n"
            "\n"
            "        const val ACTIVITY_SESSION_MIN_DURATION_MS = 60_000L\n"
            "        const val ACTIVITY_SESSION_MAX_GAP_MS = 10L * 60L * 1000L\n"
            "\n"
            "        val VALUE_NUMERIC_METHODS = listOf(\n"
        ),
        new=(
            "        const val HUAWEI_CERT_VERIFY_FAILED = 6003\n"
            "\n"
            "        val VALUE_NUMERIC_METHODS = listOf(\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="HuaweiHealthManager.kt: remove unused ACTIVITY_SESSION_MIN_DURATION_MS/MAX_GAP_MS",
    )

    print("=== 3/4: Removing stale patch scripts ===")
    remove_stale_patch_scripts()

    print("=== 4/4: Cleaning up duplicated manifest comments ===")
    apply_edit(
        MANIFEST_FILE,
        old=(
            "    <!-- Health Connect required sync scope: Huawei activity/basic sport -> Google Health. -->\n"
            "\n"
            "    <!-- Health Connect optional dashboard-only reads. Never required for sync. -->\n"
            "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope. -->\n"
            "\n"
            "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope. -->\n"
            "\n"
            "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope. -->\n"
            "\n"
            "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope. -->\n"
            "\n"
            "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope. -->\n"
            "\n"
            "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope. -->\n"
            "\n"
            "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope. -->\n"
            "\n"
            "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope. -->\n"
            "    <uses-permission android:name=\"android.permission.health.READ_STEPS\" />\n"
        ),
        new=(
            "    <!-- Health Connect strict Huawei-approved activity/basic sport sync scope:\n"
            "         Huawei activity/basic sport -> Google Health. Optional dashboard-only\n"
            "         reads are never required for sync. -->\n"
            "    <uses-permission android:name=\"android.permission.health.READ_STEPS\" />\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="AndroidManifest.xml: collapse 9 duplicate/stray comment lines into one",
    )

    print("=== Validating XML after edits ===")
    validate_xml(MANIFEST_FILE, "AndroidManifest.xml post-edit validation")

    print("=== Running compile gate ===")
    run_compile_gate()

    print("=== Compile gate passed. Committing and pushing. ===")
    git_commit_and_push()

    print("Done.")


if __name__ == "__main__":
    main()
