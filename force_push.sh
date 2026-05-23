#!/bin/bash
echo "🔍 Проверяем статус файлов..."
# Добавляем абсолютно все файлы в проект, включая скрытые настройки
git add .
git add -A

echo "💾 Создаем общий коммит..."
git commit -m "feat: complete project source code injection including dependencies and configurations"

echo "🚀 Отправляем файлы в репозиторий GitHub..."
git push origin main

echo "🎯 Проверяем, остались ли незатреканные файлы:"
git status
