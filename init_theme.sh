#!/bin/bash
echo "🚀 Фиксация дизайн-системы Gemini 2026..."
git add settings.gradle.kts app/src/main/java/com/openhealth/sync/ui/theme/*
git commit -m "feat: add Gemini 2026 minimalist theme and colors"
git push origin main
echo "✅ Код успешно отправлен на GitHub!"
