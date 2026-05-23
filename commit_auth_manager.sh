#!/bin/bash
echo "🛡️ Фиксация менеджера сессий Huawei (Компонент 9)..."
git add app/src/main/java/com/openhealth/sync/data/HuaweiAuthManager.kt
git commit -m "feat: add HuaweiAuthManager for token persistence and automatic session refresh"
git push origin main
echo "✅ Компонент 9 успешно отправлен на GitHub!"
