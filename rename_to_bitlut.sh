#!/bin/bash
echo "🏷️ Переименовываем приложение в BitLut и обновляем манифест..."
git add app/src/main/res/values/strings.xml
git add app/src/main/AndroidManifest.xml
git commit -m "chore: rename application to BitLut and fix manifest resource links"
git push origin main
echo "✅ Проект BitLut успешно обновлен на GitHub!"
