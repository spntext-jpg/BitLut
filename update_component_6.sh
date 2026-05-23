#!/bin/bash
echo "🔄 Синхронизируем полную версию GoogleHealthManager (Компонент 6)..."
git add app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt
git commit -m "fix: complete component 6 with data writing logic for Health Connect"
git push origin main
echo "✅ Компонент 6 успешно обновлен на GitHub!"
