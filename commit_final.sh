#!/bin/bash
echo "🏁 Фиксация финальной архитектуры приложения OpenHealthSync..."
git add app/src/main/java/com/openhealth/sync/HuaweiCallbackActivity.kt
git add app/src/main/java/com/openhealth/sync/MainActivity.kt
git add app/src/main/AndroidManifest.xml
git commit -m "feat: complete architecture with OAuth2 callback handler and automated periodic syncing"
git push origin main
echo "🎉 Архитектура полностью собрана и загружена на GitHub!"
