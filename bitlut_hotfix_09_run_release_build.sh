#!/usr/bin/env bash
set -euo pipefail

log() { printf '\n==> %s\n' "$1"; }
warn() { printf '\nWARN: %s\n' "$1"; }
fail() { printf '\nERROR: %s\n' "$1" >&2; exit 1; }

log "Checking repository"
[ -f settings.gradle.kts ] || fail "Run this script from the repository root."
[ -f app/build.gradle.kts ] || fail "app/build.gradle.kts not found."

log "Ensuring we are on main"
git checkout main

log "Ensuring local Huawei env exists"
if [ ! -f .huawei.env ]; then
  cat > .huawei.env <<'ENV'
HUAWEI_APP_ID=117824685
HUAWEI_CLIENT_ID=
HUAWEI_CLIENT_SECRET=
HUAWEI_REDIRECT_URI=https://com.openhealth.sync/oauth_callback
HUAWEI_SCOPES=https://www.huawei.com/auth/healthkit.step.read+https://www.huawei.com/auth/healthkit.heartrate.read
ENV
fi

log "Ensuring local release signing exists"
mkdir -p .signing
if [ ! -f .signing/bitlut-release.jks ]; then
  keytool -genkeypair \
    -v \
    -keystore .signing/bitlut-release.jks \
    -storepass bitlut-local-release-change-me \
    -keypass bitlut-local-release-change-me \
    -alias bitlut_release \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -dname "CN=BitLut, OU=OpenHealth, O=BitLut, L=Unknown, ST=Unknown, C=US"
fi

# Make values available to Gradle even if app/build.gradle.kts only reads env/local.properties.
export HUAWEI_APP_ID="${HUAWEI_APP_ID:-117824685}"
export BITLUT_KEYSTORE_PATH="${BITLUT_KEYSTORE_PATH:-.signing/bitlut-release.jks}"
export BITLUT_KEYSTORE_PASSWORD="${BITLUT_KEYSTORE_PASSWORD:-bitlut-local-release-change-me}"
export BITLUT_KEY_ALIAS="${BITLUT_KEY_ALIAS:-bitlut_release}"
export BITLUT_KEY_PASSWORD="${BITLUT_KEY_PASSWORD:-bitlut-local-release-change-me}"

log "Ensuring secret files are ignored"
touch .gitignore
for pattern in ".huawei.env" ".signing/" "*.jks" "*.keystore" "agconnect-services.json"; do
  grep -qxF "$pattern" .gitignore || printf '%s\n' "$pattern" >> .gitignore
done

log "Showing current Gradle defaultConfig area"
nl -ba app/build.gradle.kts | sed -n '45,90p'

log "Checking for known broken Gradle syntax"
if grep -q 'nifestPlaceholders' app/build.gradle.kts; then
  fail "Broken token nifestPlaceholders is still present in app/build.gradle.kts."
fi
if grep -q 'HUAWEI_APP_ID is required for production release builds' app/build.gradle.kts; then
  warn "Old Huawei guard text is still present. Removing exact requestedReleaseBuild guard block."
  python3 - <<'PY'
from pathlib import Path
p = Path('app/build.gradle.kts')
s = p.read_text()
start = s.find('if (requestedReleaseBuild) {')
if start != -1:
    depth = 0
    end = None
    for i in range(start, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end:
        s = s[:start] + s[end:]
p.write_text(s)
PY
fi

log "Checking Kotlin DSL compilation via tasks"
./gradlew --no-daemon :app:tasks --stacktrace >/tmp/bitlut_gradle_tasks.log 2>&1 || {
  cat /tmp/bitlut_gradle_tasks.log
  fail "Gradle Kotlin DSL/configuration still fails."
}

echo "Gradle configuration OK."

log "Running production release build 1.0.0"
./gradlew --no-daemon :app:clean :app:assembleRelease --stacktrace

log "Release APKs"
find app/build/outputs/apk/release -maxdepth 1 -type f -name '*.apk' -print -exec ls -lh {} \;

log "Release signing SHA-256 for Huawei AppGallery Connect"
keytool -list -v \
  -keystore "$BITLUT_KEYSTORE_PATH" \
  -alias "$BITLUT_KEY_ALIAS" \
  -storepass "$BITLUT_KEYSTORE_PASSWORD" \
  -keypass "$BITLUT_KEY_PASSWORD" | grep 'SHA256:' || true

log "Committing and pushing main if build succeeded"
git add .
if git diff --cached --quiet; then
  echo "No tracked changes to commit."
else
  git commit -m "Prepare BitLut 1.0.0 production release"
fi
git push origin main

log "Done"
