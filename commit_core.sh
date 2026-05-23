#!/bin/bash
echo "⚙️ Фиксация точки входа и слоя Google Health..."
git add app/src/main/java/com/openhealth/sync/MainActivity.kt
git add app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt
git commit -m "feat: link UI to MainActivity and add GoogleHealthManager foundation"
git push origin main
echo "✅ Архитектурный слой успешно сохранен!"
