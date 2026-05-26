#!/usr/bin/env bash
set -e

echo "== Git =="
git status
git log --oneline -5

echo
echo "== Workflows =="
ls -la .github/workflows
grep -n "name:" .github/workflows/*.yml

echo
echo "== Health Connect permissions =="
grep -n "android.permission.health" app/src/main/AndroidManifest.xml || true

echo
echo "== Google Health permissions block =="
grep -n -A12 "val permissions" app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt || true

echo
echo "== Huawei expected approval handling =="
grep -R "50005\|Scope unauthorized\|pending approval\|not authorized" -n app/src/main/java || true

echo
echo "== Forbidden fake/mock data check =="
grep -R "fake\|mock\|TODO fake\|dummy" -n app/src/main/java || true

echo
echo "== Release workflow APK signing =="
grep -n -A35 "Prepare signed APK" .github/workflows/release.yml || true
