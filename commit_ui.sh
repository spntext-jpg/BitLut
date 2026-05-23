#!/bin/bash
echo "🎨 Добавляем компоненты интерфейса MainScreen..."
git add app/src/main/java/com/openhealth/sync/ui/main/*
git commit -m "feat: add minimalist MainScreen UI and state management"
git push origin main
echo "✅ Интерфейс успешно сохранен на GitHub!"
