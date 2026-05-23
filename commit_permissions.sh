#!/bin/bash
echo "🔒 Обновляем логику разрешений Google Health Connect..."
git add app/src/main/java/com/openhealth/sync/MainActivity.kt
git add app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt
git commit -m "feat: implement Health Connect permission request flow"
git push origin main
echo "✅ Изменения успешно отправлены на GitHub!"
