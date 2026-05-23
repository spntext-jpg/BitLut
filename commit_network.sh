#!/bin/bash
echo "🌐 Создаем сетевой слой для работы с Huawei Cloud API..."
mkdir -p app/src/main/java/com/openhealth/sync/data/remote
git add app/src/main/java/com/openhealth/sync/data/remote/*
git commit -m "feat: add Huawei API service and auth data models"
git push origin main
echo "✅ Сетевой слой успешно добавлен на GitHub!"
